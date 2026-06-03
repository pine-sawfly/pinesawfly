from __future__ import annotations

import logging
from typing import Any

from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)


class TaintAnalyzer:
    def __init__(self):
        self.taint_sources = {"$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "$_SERVER"}
        self.sink_functions = {"eval", "assert", "system", "exec", "shell_exec", "passthru", "proc_open", "popen"}
        self.file_inclusion_functions = {"include", "include_once", "require", "require_once"}

    @safe_operation
    def analyze(self, ast, file_path: str) -> list[dict[str, Any]]:
        results = []

        for sink in self._find_calls(ast, self.sink_functions):
            results.append({
                "type": "TaintAnalysis",
                "rule_id": "TAINT001",
                "rule_name": "潜在污点传播",
                "severity": "High",
                "file": file_path,
                "line": sink.get("line", 0),
                "description": f"检测到危险函数 {sink.get('function')} 调用，请确认参数来源是否可控",
                "details": sink,
            })

        for inclusion in self._find_calls(ast, self.file_inclusion_functions):
            if self._has_variable_argument(inclusion):
                results.append({
                    "type": "FileInclusion",
                    "rule_id": "FILEINC001",
                    "rule_name": "文件包含漏洞",
                    "severity": "High",
                    "file": file_path,
                    "line": inclusion.get("line", 0),
                    "description": f"检测到文件包含函数 {inclusion.get('function')} 使用变量参数",
                    "details": inclusion,
                })

        logger.info("污点分析在文件 %s 中发现 %s 个问题", file_path, len(results))
        return results

    def _find_calls(self, ast, function_names: set[str]) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []

        def traverse(node) -> None:
            if isinstance(node, list):
                for item in node:
                    traverse(item)
                return

            if not hasattr(node, "__dict__"):
                return

            if type(node).__name__ == "FunctionCall":
                func_name = getattr(node, "name", "")
                if func_name in function_names:
                    calls.append({
                        "function": func_name,
                        "line": getattr(node, "lineno", 0),
                        "args": getattr(node, "params", []),
                    })

            for value in node.__dict__.values():
                if hasattr(value, "__dict__") or isinstance(value, list):
                    traverse(value)

        traverse(ast)
        return calls

    def _has_variable_argument(self, inclusion_call: dict[str, Any]) -> bool:
        return any(self._is_variable_expression(arg) for arg in inclusion_call.get("args", []))

    def _is_variable_expression(self, node) -> bool:
        if isinstance(node, list):
            return any(self._is_variable_expression(item) for item in node)

        if not hasattr(node, "__dict__"):
            return False

        node_type = type(node).__name__
        if node_type in {
            "Variable",
            "Expr_Variable",
            "ArrayOffset",
            "Expr_ArrayDimFetch",
            "BinaryOp",
            "Expr_BinaryOp_Concat",
            "FunctionCall",
            "Property",
            "Expr_PropertyFetch",
        }:
            return True

        return any(self._is_variable_expression(value) for value in node.__dict__.values())
