from __future__ import annotations

import base64
import binascii
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from tree_sitter import Node

from core.exception_handler import safe_operation
from .php_parser import PHPAst

logger = logging.getLogger(__name__)


@dataclass
class ValueState:
    tainted: bool = False
    suspicious_callable: bool = False
    sql_template: bool = False
    upload_file_entry: bool = False
    sources: list[str] = field(default_factory=list)
    transforms: list[str] = field(default_factory=list)
    literal_values: list[str] = field(default_factory=list)

    def merge(self, other: "ValueState") -> "ValueState":
        return ValueState(
            tainted=self.tainted or other.tainted,
            suspicious_callable=self.suspicious_callable or other.suspicious_callable,
            sql_template=self.sql_template or other.sql_template,
            upload_file_entry=self.upload_file_entry or other.upload_file_entry,
            sources=[*self.sources, *[source for source in other.sources if source not in self.sources]],
            transforms=[*self.transforms, *[item for item in other.transforms if item not in self.transforms]],
            literal_values=[*self.literal_values, *[value for value in other.literal_values if value not in self.literal_values]],
        )


class TaintAnalyzer:
    def __init__(self):
        self.superglobals = {"$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "$_SERVER", "$_FILES"}
        self.code_sinks = {"eval", "assert", "create_function"}
        self.command_sinks = {"system", "exec", "shell_exec", "passthru", "proc_open", "popen"}
        self.sql_sinks = {"mysql_query", "mysqli_query", "pg_query", "sqlite_query", "sqlite_exec"}
        self.sql_methods = {"query", "exec", "fetch", "fetchall"}
        self.file_include_sinks = {"include", "include_once", "require", "require_once"}
        self.file_read_sinks = {"file_get_contents", "readfile", "file", "fopen"}
        self.file_sinks = self.file_include_sinks | self.file_read_sinks
        self.callback_sinks = {
            "call_user_func",
            "call_user_func_array",
            "register_shutdown_function",
            "array_map",
            "array_filter",
            "array_walk",
            "ob_start",
        }
        self.decode_functions = {
            "base64_decode",
            "str_rot13",
            "gzinflate",
            "gzuncompress",
            "gzdecode",
            "urldecode",
            "rawurldecode",
            "hex2bin",
        }
        self.sanitizers = {"intval", "abs", "floatval", "boolval", "htmlspecialchars", "htmlentities", "filter_var"}
        self.sql_value_normalizers = {"md5", "sha1", "hash", "password_hash", "crc32"}
        self.sql_escapers = {"mysql_real_escape_string", "mysqli_real_escape_string", "addslashes"}
        self.dangerous_callable_names = self.code_sinks | self.command_sinks | {"preg_replace"}
        self.suspicious_command_pattern = re.compile(
            r"\b(wget|curl|nc|ncat|netcat|bash|sh|php|python|perl|ruby|powershell|cmd|certutil|whoami|id)\b|"
            r"base64_decode|hex2bin|gzuncompress|gzinflate|str_rot13|/bin/sh|/bin/bash|\be\s+/bin/",
            re.IGNORECASE,
        )
        self.variables: dict[str, ValueState] = {}
        self.results: list[dict[str, Any]] = []
        self.source = b""
        self.file_path = ""

    @safe_operation
    def analyze(self, ast: PHPAst, file_path: str) -> list[dict[str, Any]]:
        self.variables = {}
        self.results = []
        self.source = ast.source
        self.file_path = file_path
        self._process_block(ast.tree.root_node)
        self.results = self._dedupe_results(self.results)
        logger.info("污点分析在文件 %s 中发现 %s 个问题", file_path, len(self.results))
        return self.results

    def _process_block(self, node: Node) -> None:
        for child in node.children:
            if child.type in {"php_tag", ";", ","}:
                continue
            self._process_node(child)

    def _process_node(self, node: Node) -> ValueState:
        if node.type == "expression_statement":
            state = ValueState()
            for child in node.children:
                state = state.merge(self._process_node(child))
            return state

        if node.type == "assignment_expression":
            right = self._child_by_field(node, "right")
            left = self._child_by_field(node, "left")
            state = self._eval_expr(right) if right else ValueState()
            variable = self._variable_key(left)
            if variable:
                self._mark_callable_state(state)
                existing = self.variables.get(variable)
                if (
                    existing
                    and existing.tainted
                    and not state.tainted
                    and not self._is_sanitizer_call(right)
                    and not self._is_sql_variable(variable)
                ):
                    state = existing.merge(state)
                self.variables[variable] = state
                self._check_sql_assignment(node, variable, right, state)
            access_key = self._access_key(left)
            if access_key:
                self.variables[access_key] = state
            return state

        if node.type == "function_call_expression":
            return self._eval_function_call(node)

        if node.type == "member_call_expression":
            return self._eval_member_call(node)

        if node.type in {"include_expression", "include_once_expression", "require_expression", "require_once_expression"}:
            return self._eval_include_expression(node)

        state = ValueState()
        for child in node.children:
            if child.is_named:
                state = state.merge(self._process_node(child))
        return state

    def _eval_expr(self, node: Node | None) -> ValueState:
        if node is None:
            return ValueState()

        if node.type == "variable_name":
            variable = self._text(node)
            if variable in self.superglobals:
                return ValueState(tainted=True, sources=[variable])
            return self.variables.get(variable, ValueState())

        if node.type == "subscript_expression":
            if self._is_uploaded_tmp_name_access(node):
                return ValueState()
            access_key = self._access_key(node)
            if access_key and access_key in self.variables:
                return self.variables[access_key]
            if self._is_files_entry_access(node):
                return ValueState(tainted=True, upload_file_entry=True, sources=[self._text(node)])
            if self._is_superglobal_access(node):
                return ValueState(tainted=True, sources=[self._text(node)])
            state = ValueState()
            for child in node.children:
                state = state.merge(self._eval_expr(child))
            return state

        if node.type == "assignment_expression":
            return self._process_node(node)

        if node.type == "cast_expression":
            cast_type = next((self._text(child).lower() for child in node.children if child.type == "cast_type"), "")
            if cast_type in {"int", "integer", "float", "double", "real", "bool", "boolean"}:
                return ValueState()
            return self._merge_states(self._eval_expr(child) for child in node.children if child.is_named and child.type != "cast_type")

        if node.type == "function_call_expression":
            return self._eval_function_call(node)

        if node.type == "member_call_expression":
            return self._eval_member_call(node)

        if self._is_string_node(node):
            literal = self._literal_string(node)
            state = ValueState(literal_values=[literal] if literal else [])
            for child in node.children:
                if child.is_named:
                    state = state.merge(self._eval_expr(child))
            if self._looks_like_sql(self._text(node)):
                state.sql_template = True
                if self._has_risky_dynamic_interpolation(node):
                    state.transforms.append("dynamic-sql-template")
            return state

        if node.type == "binary_expression":
            left = node.named_children[0] if node.named_child_count >= 1 else None
            right = node.named_children[1] if node.named_child_count >= 2 else None
            left_state = self._eval_expr(left)
            right_state = self._eval_expr(right)
            merged = left_state.merge(right_state)
            concatenated = [
                left_value + right_value
                for left_value in left_state.literal_values
                for right_value in right_state.literal_values
            ]
            merged.literal_values = [*merged.literal_values, *[value for value in concatenated if value not in merged.literal_values]]
            return merged

        state = ValueState()
        for child in node.children:
            if child.is_named:
                state = state.merge(self._eval_expr(child))
        return state

    def _eval_function_call(self, node: Node) -> ValueState:
        function_node = self._child_by_field(node, "function")
        arguments = self._arguments(node)
        function_name = self._function_name(function_node)
        argument_state = self._merge_states(self._eval_expr(argument) for argument in arguments)

        if function_name:
            lowered = function_name.lower()
            self._check_named_sink(node, lowered, arguments, argument_state)
            if lowered in self.callback_sinks:
                self._check_callback_sink(node, lowered, arguments)
            if lowered in self.sanitizers:
                return ValueState()
            if lowered in self.sql_value_normalizers:
                return ValueState()
            if lowered in self.decode_functions:
                return self._decode_state(lowered, arguments, argument_state)
            if lowered in self.sql_escapers:
                argument_state.transforms.append(lowered)
                return argument_state
            return argument_state

        if function_node and function_node.type == "variable_name":
            callable_name = self._text(function_node)
            callable_state = self.variables.get(callable_name, ValueState())
            if callable_state.suspicious_callable and argument_state.tainted:
                self._add_result(
                    node,
                    "PHP_DYNAMIC_BACKDOOR",
                    "可疑动态函数后门",
                    "Critical",
                    f"变量 {callable_name} 由可疑 callable 赋值后调用，参数来自 {', '.join(argument_state.sources) or '用户输入'}",
                    callable_state.merge(argument_state),
                    self._text(node),
                )
            elif callable_state.suspicious_callable and self._has_suspicious_command(argument_state):
                self._add_result(
                    node,
                    "PHP_DYNAMIC_BACKDOOR",
                    "可疑动态函数后门",
                    "Critical",
                    f"变量 {callable_name} 由可疑 callable 赋值后调用，参数包含下载执行、反连或混淆解码特征",
                    callable_state.merge(argument_state),
                    self._text(node),
                )
            elif argument_state.tainted:
                self._add_result(
                    node,
                    "PHP_DYNAMIC_TAINT_CALL",
                    "动态函数调用用户输入",
                    "High",
                    f"动态函数 {callable_name} 使用了用户可控参数",
                    argument_state,
                    self._text(node),
                )
            return callable_state.merge(argument_state)

        return argument_state

    def _eval_member_call(self, node: Node) -> ValueState:
        arguments = self._arguments(node)
        method_name = self._member_method_name(node)
        argument_state = self._merge_states(self._eval_expr(argument) for argument in arguments)
        if method_name and method_name.lower() in self.sql_methods:
            self._check_sql_sink(node, f"->{method_name}", argument_state, arguments)
            return ValueState()
        return argument_state

    def _eval_include_expression(self, node: Node) -> ValueState:
        expression = next((child for child in node.children if child.is_named), None)
        state = self._eval_expr(expression)
        if state.tainted:
            self._add_result(
                node,
                "PHP_FILE_INCLUDE_TAINT",
                "用户输入进入文件包含函数",
                "High",
                f"文件包含表达式 {node.type.replace('_expression', '')} 的路径参数来自用户输入",
                state,
                self._text(node),
            )
        return state

    def _check_named_sink(self, node: Node, name: str, arguments: list[Node], argument_state: ValueState) -> None:
        if name in self.code_sinks and argument_state.tainted:
            self._add_result(
                node,
                "PHP_CODE_EXEC_TAINT",
                "用户输入进入代码执行函数",
                "Critical",
                f"危险函数 {name} 的参数来自 {', '.join(argument_state.sources) or '用户输入'}",
                argument_state,
                self._text(node),
            )
        elif name in self.command_sinks and argument_state.tainted:
            self._add_result(
                node,
                "PHP_COMMAND_EXEC_TAINT",
                "用户输入进入命令执行函数",
                "Critical",
                f"命令执行函数 {name} 的参数来自 {', '.join(argument_state.sources) or '用户输入'}",
                argument_state,
                self._text(node),
            )
        elif name in self.command_sinks and self._has_suspicious_command(argument_state):
            self._add_result(
                node,
                "PHP_COMMAND_EXEC_SUSPICIOUS",
                "命令执行函数运行可疑命令",
                "Critical",
                f"命令执行函数 {name} 的参数包含下载执行、反连或混淆解码特征",
                argument_state,
                self._text(node),
            )
        elif name in self.sql_sinks:
            self._check_sql_sink(node, name, argument_state, arguments)
            return
        elif name in self.file_sinks and argument_state.tainted:
            rule_id = "PHP_FILE_INCLUDE_TAINT" if name in self.file_include_sinks else "PHP_FILE_READ_TAINT"
            rule_name = "用户输入进入文件包含函数" if name in self.file_include_sinks else "用户输入进入文件读取函数"
            description = (
                f"文件包含函数 {name} 的路径参数来自用户输入"
                if name in self.file_include_sinks
                else f"文件读取函数 {name} 的路径参数来自用户输入"
            )
            self._add_result(node, rule_id, rule_name, "High", description, argument_state, self._text(node))
        elif name == "preg_replace" and self._is_preg_replace_eval(arguments) and argument_state.tainted:
            self._add_result(
                node,
                "PHP_PREG_REPLACE_E_TAINT",
                "preg_replace /e 代码执行",
                "Critical",
                "preg_replace 使用 /e 修饰符且参数包含用户输入",
                argument_state,
                self._text(node),
            )
        elif name == "preg_replace" and self._is_preg_replace_eval(arguments) and self._has_suspicious_command(argument_state):
            self._add_result(
                node,
                "PHP_PREG_REPLACE_E_SUSPICIOUS",
                "preg_replace /e 执行可疑命令",
                "Critical",
                "preg_replace 使用 /e 修饰符，替换表达式包含可疑命令执行特征",
                argument_state,
                self._text(node),
            )

    def _check_sql_assignment(self, node: Node, variable: str, right: Node | None, state: ValueState) -> None:
        if not right or not state.sql_template:
            return
        if not state.tainted and "dynamic-sql-template" not in state.transforms:
            return
        for item in (variable, self._text(right)):
            if item not in state.transforms:
                state.transforms.append(item)
        escaped = any(transform in self.sql_escapers for transform in state.transforms)
        source = ", ".join(state.sources) or "动态变量"
        description = f"变量 {variable} 被赋值为包含 {source} 的动态 SQL 模板"
        if escaped:
            description += "；检测到转义函数处理，但 addslashes/mysql_real_escape_string 不能替代参数化查询，GBK 等编码场景仍可能绕过"
        self._add_result(
            node,
            "PHP_SQL_INJECTION_TAINT",
            "动态 SQL 模板包含用户输入",
            "High",
            description,
            state,
            self._text(node),
        )

    def _check_sql_sink(self, node: Node, name: str, argument_state: ValueState, arguments: list[Node]) -> None:
        if self._is_parameterized_query(arguments):
            return
        if not argument_state.tainted and "dynamic-sql-template" not in argument_state.transforms:
            return
        escaped = any(transform in self.sql_escapers for transform in argument_state.transforms)
        source = ", ".join(argument_state.sources) or "动态 SQL"
        description = f"SQL 查询函数 {name} 的 SQL 参数来自 {source}"
        if escaped:
            description += "；检测到转义函数处理，但拼接 SQL 仍应使用参数化查询，并确认数值上下文已加引号或强制类型转换"
        self._add_result(
            node,
            "PHP_SQL_INJECTION_TAINT",
            "用户输入进入 SQL 查询",
            "High",
            description,
            argument_state,
            self._text(node),
        )

    def _is_parameterized_query(self, arguments: list[Node]) -> bool:
        if len(arguments) < 2:
            return False
        sql = self._literal_string(arguments[0]) or ""
        if not sql:
            return False
        return "?" in sql or bool(re.search(r":[A-Za-z_][A-Za-z0-9_]*", sql))

    def _check_callback_sink(self, node: Node, name: str, arguments: list[Node]) -> None:
        if not arguments:
            return
        callback = self._literal_string(arguments[0]) or self._variable_key(arguments[0])
        callback_state = self._eval_expr(arguments[0])
        rest_state = self._merge_states(self._eval_expr(argument) for argument in arguments[1:])
        dangerous = bool(callback and callback.lower() in self.dangerous_callable_names)
        if dangerous and name == "ob_start":
            self._add_result(
                node,
                "PHP_CALLBACK_SUSPICIOUS_COMMAND",
                "危险输出缓冲回调",
                "Critical",
                f"ob_start 注册危险回调 {callback}，后续输出会进入命令/代码执行函数",
                callback_state.merge(rest_state),
                self._text(node),
            )
            return
        if (dangerous or callback_state.suspicious_callable) and rest_state.tainted:
            self._add_result(
                node,
                "PHP_CALLBACK_TAINT",
                "用户输入进入危险回调",
                "Critical",
                f"{name} 调用危险回调 {callback or '动态回调'}，参数来自用户输入",
                callback_state.merge(rest_state),
                self._text(node),
            )
        elif (dangerous or callback_state.suspicious_callable) and self._has_suspicious_command(rest_state):
            self._add_result(
                node,
                "PHP_CALLBACK_SUSPICIOUS_COMMAND",
                "危险回调运行可疑命令",
                "Critical",
                f"{name} 调用危险回调 {callback or '动态回调'}，参数包含可疑命令特征",
                callback_state.merge(rest_state),
                self._text(node),
            )

    def _decode_state(self, name: str, arguments: list[Node], argument_state: ValueState) -> ValueState:
        decoded = [value for argument in arguments for value in self._decoded_literals(name, argument)]
        dangerous = [value for value in decoded if value.lower() in self.dangerous_callable_names]
        transforms = [name, *[f"{name}->{value}" for value in decoded[:3]]]
        return ValueState(
            tainted=argument_state.tainted,
            suspicious_callable=bool(decoded) or argument_state.suspicious_callable,
            sources=argument_state.sources,
            transforms=[*argument_state.transforms, *transforms, *[f"dangerous:{value}" for value in dangerous]],
            literal_values=[*argument_state.literal_values, *decoded],
        )

    def _decoded_literals(self, decoder: str, node: Node) -> list[str]:
        literal = self._literal_string(node)
        if not literal:
            return []
        values = []
        if decoder == "base64_decode":
            compact = re.sub(r"[^A-Za-z0-9+/=]", "", literal)
            for candidate in {literal, compact}:
                padded = candidate + "=" * (-len(candidate) % 4)
                try:
                    values.append(base64.b64decode(padded, validate=False).decode("utf-8", "ignore"))
                except (binascii.Error, UnicodeDecodeError, ValueError):
                    pass
        elif decoder == "str_rot13":
            values.append(literal.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm")))
        elif decoder in {"urldecode", "rawurldecode"}:
            try:
                from urllib.parse import unquote

                values.append(unquote(literal))
            except Exception:
                pass
        elif decoder == "hex2bin":
            try:
                values.append(bytes.fromhex(literal).decode("utf-8", "ignore"))
            except ValueError:
                pass
        return [value for value in values if value]

    def _has_suspicious_command(self, state: ValueState) -> bool:
        return any(self.suspicious_command_pattern.search(value) for value in state.literal_values + state.transforms)

    def _mark_callable_state(self, state: ValueState) -> None:
        if any(value.lower().lstrip("\\") in self.dangerous_callable_names for value in state.literal_values):
            state.suspicious_callable = True

    def _is_preg_replace_eval(self, arguments: list[Node]) -> bool:
        if not arguments:
            return False
        pattern = self._literal_string(arguments[0]) or ""
        return bool(re.search(r"/[a-zA-Z]*e[a-zA-Z]*$", pattern))

    def _add_result(self, node: Node, rule_id: str, rule_name: str, severity: str, description: str, state: ValueState, match: str) -> None:
        self.results.append({
            "type": "TaintAnalysis",
            "rule_id": rule_id,
            "rule_name": rule_name,
            "severity": severity,
            "file": self.file_path,
            "line": node.start_point.row + 1,
            "description": description,
            "match": match,
            "details": {
                "sources": state.sources,
                "transforms": state.transforms,
            },
        })

    def _dedupe_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[object, ...]] = set()
        unique: list[dict[str, Any]] = []
        for result in results:
            key = (result.get("rule_id"), result.get("line"), result.get("match"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
        return unique

    def _arguments(self, call_node: Node) -> list[Node]:
        arguments_node = self._child_by_field(call_node, "arguments")
        if not arguments_node:
            return []
        values = []
        for child in arguments_node.children:
            if child.type == "argument" and child.named_child_count:
                values.append(child.named_children[0])
            elif child.is_named:
                values.append(child)
        return values

    def _literal_string(self, node: Node) -> str | None:
        if node.type in {"encapsed_string", "string", "string_literal"}:
            return "".join(self._text(child) for child in node.children if child.type == "string_content")
        if node.type == "argument" and node.named_child_count:
            return self._literal_string(node.named_children[0])
        return None

    def _is_uploaded_tmp_name_access(self, node: Node) -> bool:
        if node.type != "subscript_expression":
            return False
        key = self._subscript_key(node)
        if key != "tmp_name":
            return False
        base = self._subscript_base(node)
        if not base:
            return False
        if "$_FILES" in self._text(base):
            return True
        if base.type == "variable_name":
            return self.variables.get(self._text(base), ValueState()).upload_file_entry
        return self._eval_expr(base).upload_file_entry

    def _is_files_entry_access(self, node: Node) -> bool:
        base = self._subscript_base(node)
        return bool(base and base.type == "variable_name" and self._text(base) == "$_FILES" and self._subscript_key(node) != "tmp_name")

    def _is_superglobal_access(self, node: Node) -> bool:
        base = self._subscript_base(node)
        return bool(base and base.type == "variable_name" and self._text(base) in self.superglobals)

    def _subscript_base(self, node: Node) -> Node | None:
        return next((child for child in node.children if child.is_named and child.type != "string"), None)

    def _subscript_key(self, node: Node) -> str | None:
        strings = [child for child in node.children if child.is_named and self._is_string_node(child)]
        return self._literal_string(strings[-1]) if strings else None

    def _function_name(self, node: Node | None) -> str | None:
        if not node:
            return None
        if node.type in {"name", "qualified_name", "namespace_name"}:
            return self._text(node).lstrip("\\")
        return None

    def _member_method_name(self, node: Node) -> str | None:
        for child in node.children:
            if child.type == "name":
                return self._text(child)
        return None

    def _is_sanitizer_call(self, node: Node | None) -> bool:
        if not node or node.type != "function_call_expression":
            return False
        function_name = self._function_name(self._child_by_field(node, "function"))
        return bool(function_name and function_name.lower() in self.sanitizers)

    def _is_sql_variable(self, variable: str) -> bool:
        return variable.lower() in {"$sql", "$query"} or "sql" in variable.lower() or "query" in variable.lower()

    def _variable_key(self, node: Node | None) -> str | None:
        if node and node.type == "variable_name":
            return self._text(node)
        return None

    def _access_key(self, node: Node | None) -> str | None:
        if node and node.type == "subscript_expression":
            return re.sub(r"\s+", "", self._text(node))
        return None

    def _child_by_field(self, node: Node, field: str) -> Node | None:
        return node.child_by_field_name(field)

    def _merge_states(self, states) -> ValueState:
        merged = ValueState()
        for state in states:
            merged = merged.merge(state)
        return merged

    def _is_string_node(self, node: Node) -> bool:
        return node.type in {"encapsed_string", "string", "string_literal"}

    def _has_risky_dynamic_interpolation(self, node: Node) -> bool:
        if node.type == "variable_name":
            variable = self._text(node)
            if variable in self.superglobals:
                return True
            state = self.variables.get(variable)
            return state is None or state.tainted
        if node.type in {"subscript_expression", "member_access_expression"}:
            state = self._eval_expr(node)
            if state.tainted:
                return True
            base = next((child for child in node.children if child.is_named), None)
            return self._has_risky_dynamic_interpolation(base) if base else True
        return any(child.is_named and self._has_risky_dynamic_interpolation(child) for child in node.children)

    def _looks_like_sql(self, value: str) -> bool:
        return bool(re.search(r"\b(select|insert|update|delete|replace|with)\b.+\b(from|into|set|where|values)\b", value, re.IGNORECASE | re.DOTALL))

    def _text(self, node: Node) -> str:
        return self.source[node.start_byte:node.end_byte].decode("utf-8", "replace")
