from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .php_parser import PHPAst


@dataclass
class ProjectContext:
    root: Path
    is_mvc: bool = False
    framework_hints: list[str] = field(default_factory=list)
    has_login_middleware: bool = False
    has_auth_middleware: bool = False


class ProjectContextBuilder:
    def build(self, project_path: str | Path | None) -> ProjectContext | None:
        if not project_path:
            return None
        root = Path(project_path)
        if not root.exists():
            return None

        hints: list[str] = []
        if (root / "app").is_dir() and any(root.glob("app/**/controller")):
            hints.append("app/**/controller")
        if any(root.glob("app/**/config/route.php")) or (root / "route").is_dir():
            hints.append("route-config")
        if any(root.glob("app/**/http/middleware/*.php")) or (root / "app" / "middleware.php").is_file():
            hints.append("middleware")
        if (root / "composer.json").is_file():
            composer = (root / "composer.json").read_text(encoding="utf-8", errors="ignore").lower()
            if any(name in composer for name in ("thinkphp", "laravel", "symfony", "yii")):
                hints.append("composer-framework")

        has_login = any(root.glob("app/**/http/middleware/*Login*Middleware.php"))
        has_auth = any(root.glob("app/**/http/middleware/*Auth*Middleware.php"))
        return ProjectContext(
            root=root,
            is_mvc=len(hints) >= 2 or (has_login and has_auth),
            framework_hints=hints,
            has_login_middleware=has_login,
            has_auth_middleware=has_auth,
        )


class RouteAuthAnalyzer:
    RISKY_SINKS = re.compile(
        r"\b(call_user_func_array|call_user_func|readfile|file_get_contents|fopen|include|require|system|exec|shell_exec|passthru|eval|assert)\s*\(",
        re.IGNORECASE,
    )
    REQUEST_SOURCE = re.compile(r"(\$this->request->|request\s*\(|input\s*\(|\$_(?:GET|POST|REQUEST|COOKIE|FILES)\b)", re.IGNORECASE)

    def __init__(self, context: ProjectContext | None = None):
        self.context = context

    def analyze(self, ast: PHPAst, file_path: str) -> list[dict[str, Any]]:
        if not self.context or not self.context.is_mvc:
            return []
        path = Path(file_path)
        if "controller" not in {part.lower() for part in path.parts}:
            return []

        content = ast.content
        not_need_login = self._string_list_property(content, "notNeedLogin")
        not_need_auth = self._string_list_property(content, "notNeedAuth")
        if not not_need_login and not not_need_auth:
            return []

        results: list[dict[str, Any]] = []
        for method, start, body in self._public_methods(content):
            if method in not_need_login:
                risk = self._risky_method_result(file_path, content, method, start, body, unauthenticated=True)
                if risk:
                    results.append(risk)
            elif method in not_need_auth:
                risk = self._risky_method_result(file_path, content, method, start, body, unauthenticated=False)
                if risk:
                    results.append(risk)
        return results

    def _risky_method_result(
        self,
        file_path: str,
        content: str,
        method: str,
        start: int,
        body: str,
        unauthenticated: bool,
    ) -> dict[str, Any] | None:
        sink = self.RISKY_SINKS.search(body)
        if not sink:
            return None
        request_source = self.REQUEST_SOURCE.search(body)
        if not request_source:
            return None
        line = content[: start + sink.start()].count("\n") + 1
        scope = "免登录" if unauthenticated else "免权限"
        return {
            "type": "RouteAuthAnalysis",
            "rule_id": "PHP_MVC_UNAUTHENTICATED_RISKY_ACTION" if unauthenticated else "PHP_MVC_UNAUTHORIZED_RISKY_ACTION",
            "rule_name": f"MVC {scope}危险接口",
            "severity": "Critical" if unauthenticated else "High",
            "file": file_path,
            "line": line,
            "description": f"Controller 方法 {method} 被配置为{scope}，且用户输入进入危险操作 {sink.group(1)}",
            "match": sink.group(0),
            "details": {
                "sources": [request_source.group(0)],
                "transforms": [f"route-auth:{scope}", f"method:{method}", f"sink:{sink.group(1)}"],
            },
        }

    def _string_list_property(self, content: str, name: str) -> set[str]:
        pattern = re.compile(rf"\${name}\s*=\s*\[(?P<body>.*?)\]\s*;", re.DOTALL)
        match = pattern.search(content)
        if not match:
            return set()
        return set(re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", match.group("body")))

    def _public_methods(self, content: str) -> list[tuple[str, int, str]]:
        methods: list[tuple[str, int, str]] = []
        for match in re.finditer(r"\bpublic\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{", content):
            body_start = match.end()
            body_end = self._matching_brace(content, body_start - 1)
            if body_end > body_start:
                methods.append((match.group(1), body_start, content[body_start:body_end]))
        return methods

    def _matching_brace(self, content: str, open_brace: int) -> int:
        depth = 0
        i = open_brace
        while i < len(content):
            char = content[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return len(content)
