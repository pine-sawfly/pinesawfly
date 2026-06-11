from __future__ import annotations

import base64
import binascii
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from tree_sitter import Node

from core.exception_handler import safe_operation
from .php_parser import PHPAst

logger = logging.getLogger(__name__)
MAX_ANALYSIS_SECONDS = 2.5
MAX_ANALYSIS_NODES = 30000
MAX_STATE_ITEMS = 40
MAX_LITERAL_VALUES = 12


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
            sources=self._merge_limited(self.sources, other.sources, MAX_STATE_ITEMS),
            transforms=self._merge_limited(self.transforms, other.transforms, MAX_STATE_ITEMS),
            literal_values=self._merge_limited(self.literal_values, other.literal_values, MAX_LITERAL_VALUES),
        )

    @staticmethod
    def _merge_limited(left: list[str], right: list[str], limit: int) -> list[str]:
        values = list(left[:limit])
        for item in right:
            if item not in values:
                values.append(item)
                if len(values) >= limit:
                    break
        return values


class TaintAnalyzer:
    def __init__(self):
        self.superglobals = {"$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "$_SERVER", "$_FILES"}
        self.client_server_keys = {
            "HTTP_HOST",
            "HTTP_USER_AGENT",
            "HTTP_REFERER",
            "HTTP_ORIGIN",
            "HTTP_X_FORWARDED_FOR",
            "HTTP_X_REAL_IP",
            "HTTP_CLIENT_IP",
            "HTTP_ACCEPT_LANGUAGE",
            "QUERY_STRING",
            "REQUEST_URI",
        }
        self.code_sinks = {"eval", "assert", "create_function"}
        self.command_sinks = {"system", "exec", "shell_exec", "passthru", "proc_open", "popen"}
        self.sql_sinks = {"mysql_query", "mysqli_query", "pg_query", "sqlite_query", "sqlite_exec"}
        self.sql_methods = {"query", "exec", "fetch", "fetchall", "get_one"}
        self.file_include_sinks = {"include", "include_once", "require", "require_once"}
        self.file_read_sinks = {"file_get_contents", "readfile", "file", "fopen"}
        self.file_sinks = self.file_include_sinks | self.file_read_sinks
        self.deserialize_sinks = {"unserialize"}
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
        self.validator_methods = {"is_number", "is_letter", "is_rec", "get_legal_id"}
        self.sql_value_normalizers = {"md5", "sha1", "hash", "password_hash", "crc32"}
        self.sql_escapers = {"mysql_real_escape_string", "mysqli_real_escape_string", "addslashes"}
        self.strong_sql_escapers = {"mysql_real_escape_string", "mysqli_real_escape_string"}
        self.dangerous_callable_names = self.code_sinks | self.command_sinks | {"preg_replace"}
        self.suspicious_command_pattern = re.compile(
            r"\b(wget|curl|nc|ncat|netcat|bash|sh|php|python|perl|ruby|powershell|cmd|certutil|whoami|id)\b|"
            r"base64_decode|hex2bin|gzuncompress|gzinflate|str_rot13|/bin/sh|/bin/bash|\be\s+/bin/",
            re.IGNORECASE,
        )
        self.variables: dict[str, ValueState] = {}
        self.results: list[dict[str, Any]] = []
        self.validated_expression_stack: list[set[str]] = []
        self.source = b""
        self.file_path = ""
        self.started_at = 0.0
        self.visited_nodes = 0

    @safe_operation
    def analyze(self, ast: PHPAst, file_path: str) -> list[dict[str, Any]]:
        self.variables = {}
        self.results = []
        self.validated_expression_stack = []
        self.source = ast.source
        self.file_path = file_path
        self.started_at = time.perf_counter()
        self.visited_nodes = 0
        try:
            self._process_block(ast.tree.root_node)
        except TimeoutError as exc:
            logger.warning("跳过文件 %s: %s", file_path, exc)
            return []
        self.results = self._dedupe_results(self.results)
        logger.info("污点分析在文件 %s 中发现 %s 个问题", file_path, len(self.results))
        return self.results

    def _check_budget(self) -> None:
        self.visited_nodes += 1
        if self.visited_nodes > MAX_ANALYSIS_NODES:
            raise TimeoutError(f"污点分析节点数超过限制: {MAX_ANALYSIS_NODES}")
        if self.started_at and time.perf_counter() - self.started_at > MAX_ANALYSIS_SECONDS:
            raise TimeoutError(f"污点分析超过 {MAX_ANALYSIS_SECONDS:.0f} 秒")

    def _process_block(self, node: Node) -> None:
        self._check_budget()
        for child in node.children:
            if child.type in {"php_tag", ";", ","}:
                continue
            self._process_node(child)

    def _process_node(self, node: Node) -> ValueState:
        self._check_budget()
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
                self.variables[variable] = state
                self._check_sql_assignment(node, variable, right, state)
            access_key = self._access_key(left)
            if access_key:
                self._check_session_assignment(node, access_key, state)
                self.variables[access_key] = state
            return state

        if node.type == "if_statement":
            return self._process_if_statement(node)

        if node.type == "switch_statement":
            return self._process_switch_statement(node)

        if node.type in {"case_statement", "default_statement"}:
            return self._process_case_statement(node)

        if node.type == "function_call_expression":
            return self._eval_function_call(node)

        if node.type == "member_call_expression":
            return self._eval_member_call(node)

        if node.type == "echo_statement":
            return self._eval_output_statement(node, "echo")

        if node.type == "print_intrinsic":
            return self._eval_output_statement(node, "print")

        if node.type in {"include_expression", "include_once_expression", "require_expression", "require_once_expression"}:
            return self._eval_include_expression(node)

        state = ValueState()
        for child in node.children:
            if child.is_named:
                state = state.merge(self._process_node(child))
        return state

    def _eval_expr(self, node: Node | None) -> ValueState:
        self._check_budget()
        if node is None:
            return ValueState()

        if node.type == "variable_name":
            variable = self._text(node)
            if variable in self.superglobals:
                return ValueState(tainted=True, sources=[variable])
            return self.variables.get(variable, ValueState())

        if node.type == "subscript_expression":
            upload_state = self._eval_upload_file_access(node)
            if upload_state is not None:
                return upload_state
            access_key = self._access_key(node)
            if access_key and self._is_validated_expression(access_key):
                return ValueState()
            if access_key and access_key in self.variables:
                return self.variables[access_key]
            server_state = self._eval_server_access(node)
            if server_state is not None:
                return server_state
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

        if node.type == "conditional_expression":
            return self._eval_conditional_expression(node)

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
                for left_value in left_state.literal_values[:MAX_LITERAL_VALUES]
                for right_value in right_state.literal_values[:MAX_LITERAL_VALUES]
            ]
            merged.literal_values = ValueState._merge_limited(merged.literal_values, concatenated, MAX_LITERAL_VALUES)
            return merged

        state = ValueState()
        for child in node.children:
            if child.is_named:
                state = state.merge(self._eval_expr(child))
        return state

    def _process_if_statement(self, node: Node) -> ValueState:
        condition = next((child for child in node.children if child.is_named and child.type == "parenthesized_expression"), None)
        validated = self._validated_inputs_from_condition(condition)
        state = self._eval_expr(condition) if condition else ValueState()
        body_seen = False

        for child in node.children:
            if not child.is_named or child is condition:
                continue
            if child.type == "compound_statement" and not body_seen:
                body_seen = True
                self.validated_expression_stack.append(validated)
                try:
                    self._process_block(child)
                finally:
                    self.validated_expression_stack.pop()
                continue
            state = state.merge(self._process_node(child))
        return state

    def _process_switch_statement(self, node: Node) -> ValueState:
        state = ValueState()
        condition = next((child for child in node.children if child.is_named and child.type == "parenthesized_expression"), None)
        if condition:
            state = state.merge(self._eval_expr(condition))
        base_variables = dict(self.variables)
        branch_variables: dict[str, ValueState] = {}
        for child in node.children:
            if not child.is_named or child is condition:
                continue
            if child.type == "switch_block":
                for case_child in child.children:
                    if not case_child.is_named:
                        continue
                    self.variables = dict(base_variables)
                    state = state.merge(self._process_node(case_child))
                    for key, value in self.variables.items():
                        branch_variables[key] = branch_variables.get(key, ValueState()).merge(value)
                continue
            state = state.merge(self._process_node(child))
        self.variables = dict(base_variables)
        for key, value in branch_variables.items():
            self.variables[key] = self.variables.get(key, ValueState()).merge(value)
        return state

    def _process_case_statement(self, node: Node) -> ValueState:
        state = ValueState()
        for child in node.children:
            if not child.is_named:
                continue
            if child.type in {"string", "integer", "float", "name"}:
                continue
            state = state.merge(self._process_node(child))
        return state

    def _eval_function_call(self, node: Node) -> ValueState:
        function_node = self._child_by_field(node, "function")
        arguments = self._arguments(node)
        function_name = self._function_name(function_node)
        argument_state = self._merge_states(self._eval_expr(argument) for argument in arguments)

        if function_name:
            lowered = function_name.lower()
            if lowered == "file_get_contents" and self._has_php_input_argument(arguments):
                return ValueState(tainted=True, sources=["php://input"], transforms=[self._text(node)])
            if lowered == "move_uploaded_file":
                self._check_upload_sink(node, arguments)
                return ValueState()
            if lowered in self.file_read_sinks:
                self._check_file_sink(node, lowered, argument_state)
                return ValueState()
            if lowered in self.sql_sinks:
                self._check_sql_sink(node, lowered, argument_state, arguments)
                return ValueState()
            self._check_named_sink(node, lowered, arguments, argument_state)
            if lowered in self.callback_sinks:
                self._check_callback_sink(node, lowered, arguments)
            if lowered == "cookie" and len(arguments) == 1:
                return ValueState(tainted=True, sources=[self._text(node)], transforms=["cookie"])
            if lowered in self.sanitizers:
                return ValueState()
            if lowered in self.deserialize_sinks and argument_state.tainted:
                self._add_result(
                    node,
                    "PHP_UNSERIALIZE_TAINT",
                    "用户输入进入反序列化",
                    "High",
                    f"unserialize 参数来自 {', '.join(argument_state.sources) or '用户输入'}",
                    argument_state,
                    self._text(node),
                )
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
            if callable_state.tainted:
                state = callable_state.merge(argument_state)
                detail = f"动态函数名 {callable_name} 来自 {', '.join(callable_state.sources) or '用户输入'}"
                if argument_state.tainted:
                    detail += f"，参数来自 {', '.join(argument_state.sources) or '用户输入'}"
                self._add_result(
                    node,
                    "PHP_DYNAMIC_FUNCTION_NAME_TAINT",
                    "用户输入控制动态函数名",
                    "Critical",
                    detail,
                    state,
                    self._text(node),
                )
                return ValueState()
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
            return ValueState()

        return argument_state

    def _eval_member_call(self, node: Node) -> ValueState:
        arguments = self._arguments(node)
        method_name = self._member_method_name(node)
        argument_state = self._merge_states(self._eval_expr(argument) for argument in arguments)
        if method_name and self._is_request_input_call(node, method_name):
            return ValueState(tainted=True, sources=[self._text(node)], transforms=[f"request->{method_name}"])
        if method_name and method_name.lower() in self.validator_methods:
            return ValueState(transforms=[method_name.lower()])
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

    def _eval_conditional_expression(self, node: Node) -> ValueState:
        named = [child for child in node.children if child.is_named]
        if len(named) >= 3 and self._is_validator_call(named[0]):
            fallback_state = self._eval_expr(named[2])
            if not fallback_state.tainted:
                method = self._member_method_name(named[0]) or "validator"
                return ValueState(transforms=[method.lower()])
        return self._merge_states(self._eval_expr(child) for child in named)

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
        if not state.tainted:
            return
        for item in (variable, self._text(right)):
            if item not in state.transforms:
                state.transforms.append(item)

    def _check_sql_sink(self, node: Node, name: str, argument_state: ValueState, arguments: list[Node]) -> None:
        if self._is_parameterized_query(arguments):
            return
        if not argument_state.tainted:
            return
        escaped = any(transform in self.sql_escapers for transform in argument_state.transforms)
        if self._is_strong_sql_escaped(argument_state):
            return
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
        if callback_state.tainted:
            state = callback_state.merge(rest_state)
            detail = f"{name} 的回调函数名来自 {', '.join(callback_state.sources) or '用户输入'}"
            if rest_state.tainted:
                detail += f"，回调参数来自 {', '.join(rest_state.sources) or '用户输入'}"
            self._add_result(
                node,
                "PHP_DYNAMIC_CALLBACK_NAME_TAINT",
                "用户输入控制动态回调",
                "Critical",
                detail,
                state,
                self._text(node),
            )
            return
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

    def _check_session_assignment(self, node: Node, access_key: str, state: ValueState) -> None:
        if not access_key.startswith("$_SESSION[") or not state.tainted:
            return
        self._add_result(
            node,
            "PHP_SESSION_TAINT_WRITE",
            "用户输入写入 Session",
            "High",
            f"用户输入写入 {access_key}，如果存在 session 文件包含链路，可能造成本地文件包含利用",
            state,
            self._text(node),
        )

    def _eval_output_statement(self, node: Node, name: str) -> ValueState:
        state = self._merge_states(self._eval_expr(child) for child in node.named_children)
        if state.tainted and not state.upload_file_entry:
            self._add_result(
                node,
                "PHP_OUTPUT_TAINT",
                "用户输入输出到响应",
                "High",
                f"{name} 输出内容来自 {', '.join(state.sources) or '用户输入'}，需要确认是否经过适合当前上下文的编码",
                state,
                self._text(node),
            )
        return state

    def _has_php_input_argument(self, arguments: list[Node]) -> bool:
        return any((self._literal_string(argument) or "").lower() == "php://input" for argument in arguments)

    def _check_upload_sink(self, node: Node, arguments: list[Node]) -> None:
        if len(arguments) < 2:
            return
        destination_state = self._eval_expr(arguments[1])
        if not destination_state.tainted:
            return
        self._add_result(
            node,
            "PHP_UPLOAD_TAINTED_DESTINATION",
            "上传文件保存路径可控",
            "High",
            f"move_uploaded_file 的保存路径包含 {', '.join(destination_state.sources) or '用户输入'}，需要确认扩展名、文件名和目录不可被绕过",
            destination_state,
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

    def _eval_upload_file_access(self, node: Node) -> ValueState | None:
        if node.type != "subscript_expression":
            return None
        key = self._subscript_key(node)
        base = self._subscript_base(node)
        if not base:
            return None

        if base.type == "variable_name" and self._text(base) == "$_FILES":
            return ValueState(upload_file_entry=True, sources=[self._text(node)])

        if base.type == "subscript_expression":
            base_state = self._eval_upload_file_access(base)
        elif base.type == "variable_name":
            base_state = self.variables.get(self._text(base), ValueState())
        else:
            base_state = ValueState()

        if not base_state.upload_file_entry:
            return None
        if key in {"tmp_name", "size", "error"}:
            return ValueState()
        if key in {"name", "type", "full_path"}:
            return ValueState(tainted=True, upload_file_entry=True, sources=[self._text(node)])
        return ValueState(tainted=True, upload_file_entry=True, sources=[self._text(node)])

    def _is_superglobal_access(self, node: Node) -> bool:
        base = self._subscript_base(node)
        return bool(base and base.type == "variable_name" and self._text(base) in self.superglobals)

    def _eval_server_access(self, node: Node) -> ValueState | None:
        base = self._subscript_base(node)
        if not (base and base.type == "variable_name" and self._text(base) == "$_SERVER"):
            return None
        key = self._subscript_key(node)
        if key in self.client_server_keys or (key and key.startswith("HTTP_")):
            return ValueState(tainted=True, sources=[self._text(node)])
        return ValueState()

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

    def _is_validator_call(self, node: Node) -> bool:
        if node.type != "member_call_expression":
            return False
        method_name = self._member_method_name(node)
        return bool(method_name and method_name.lower() in self.validator_methods)

    def _validated_inputs_from_condition(self, node: Node | None) -> set[str]:
        if not node:
            return set()
        validated: set[str] = set()
        if self._is_validator_call(node):
            for argument in self._arguments(node):
                key = self._normalized_expr(argument)
                if key:
                    validated.add(key)
            return validated
        for child in node.children:
            if child.is_named:
                validated.update(self._validated_inputs_from_condition(child))
        return validated

    def _is_validated_expression(self, expression: str) -> bool:
        normalized = re.sub(r"\s+", "", expression)
        return any(normalized in scope for scope in reversed(self.validated_expression_stack))

    def _normalized_expr(self, node: Node | None) -> str | None:
        if not node:
            return None
        return re.sub(r"\s+", "", self._text(node))

    def _is_request_input_call(self, node: Node, method_name: str) -> bool:
        method = method_name.lower()
        if method not in {"get", "post", "param", "request", "put", "delete", "patch", "input", "all", "file"}:
            return False
        text = self._text(node).lower()
        return "request" in text or "input(" in text

    def _is_strong_sql_escaped(self, state: ValueState) -> bool:
        strong = any(transform in self.strong_sql_escapers for transform in state.transforms)
        weak = any(transform == "addslashes" for transform in state.transforms)
        return strong and not weak

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
            return bool(state and state.tainted)
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
