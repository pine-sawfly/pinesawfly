from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from modules.generic_rule_engine import GenericRuleEngine

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".php", ".py", ".java", ".lua", ".go", ".js", ".ts", ".html", ".css"}
SCAN_EXTENSIONS = {".php", ".py", ".java"}
ALWAYS_IGNORED_DIRS = {
    ".git",
    ".venv",
    ".codegraph",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}
DEPENDENCY_DIRS = {"vendor", "node_modules", "bower_components", "thinkphp"}
PLUGIN_LANGUAGE_EXTENSIONS = {
    "php_plugin": {".php"},
}


def is_ignored_path(path: Path, include_dependencies: bool = False) -> bool:
    if any(part in ALWAYS_IGNORED_DIRS for part in path.parts):
        return True
    if include_dependencies:
        return False
    return any(_is_dependency_dir(parent) for parent in (path, *path.parents))


def _is_dependency_dir(path: Path) -> bool:
    if path.name not in DEPENDENCY_DIRS:
        return False
    if path.name == "vendor":
        return (path / "autoload.php").exists() or (path / "composer").is_dir() or (path.parent / "composer.json").is_file()
    if path.name == "node_modules":
        return (path.parent / "package.json").is_file()
    if path.name == "bower_components":
        return (path.parent / "bower.json").is_file()
    if path.name == "thinkphp":
        return (path / "base.php").is_file() or (path / "library" / "think").is_dir()
    return False


class ScanWorker(QObject):
    finished = Signal(list, int, str)
    failed = Signal(str)

    def __init__(self, project_path: str, include_dependencies: bool = False) -> None:
        super().__init__()
        self.project_path = project_path
        self.include_dependencies = include_dependencies

    @Slot()
    def run(self) -> None:
        try:
            rows = self._run_scan()
            self.finished.emit(rows, len(rows), f"扫描完成，发现 {len(rows)} 个问题")
        except Exception as exc:  # noqa: BLE001
            logger.exception("scan failed")
            self.failed.emit(str(exc))

    def _run_scan(self) -> list[dict[str, object]]:
        project = Path(self.project_path)
        rule_engine = GenericRuleEngine()
        results: list[dict[str, object]] = []
        self._prepare_codegraph(project)
        for file_path in project.rglob("*"):
            if is_ignored_path(file_path, self.include_dependencies):
                continue
            if file_path.is_file() and file_path.suffix.lower() in SCAN_EXTENSIONS:
                for vuln in rule_engine.scan_file(str(file_path)):
                    results.append(self._normalize_vuln(project, file_path, vuln))
        self._append_language_plugin_results(project, results)
        return self._dedupe_results(results)

    def _prepare_codegraph(self, project: Path) -> None:
        try:
            subprocess.run(
                ["codegraph", "init", "-i"],
                cwd=str(project),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.debug("codegraph init skipped for %s", project, exc_info=True)

    def _append_language_plugin_results(self, project: Path, results: list[dict[str, object]]) -> None:
        try:
            from core.plugin_loader import PluginLoader

            app_root = Path(__file__).resolve().parent.parent
            plugin_loader = PluginLoader(str(app_root / "plugins"))
            plugin_loader.load_all_plugins()
            for plugin_name, extensions in PLUGIN_LANGUAGE_EXTENSIONS.items():
                self._append_plugin_results(project, results, plugin_loader, plugin_name, extensions)
        except Exception:
            logger.exception("plugin scan failed")

    def _append_plugin_results(self, project: Path, results: list[dict[str, object]], plugin_loader, plugin_name: str, extensions: set[str]) -> None:
        plugin_module = plugin_loader.get_plugin(plugin_name)
        if not plugin_module:
            return
        plugin = plugin_module.PluginInterface()
        if not plugin.initialize(str(project)):
            return
        for file_path in project.rglob("*"):
            if is_ignored_path(file_path, self.include_dependencies):
                continue
            if not file_path.is_file() or file_path.suffix.lower() not in extensions:
                continue
            for vuln in plugin.scan(str(file_path)):
                results.append(self._normalize_vuln(project, file_path, vuln))

    def _dedupe_results(self, results: list[dict[str, object]]) -> list[dict[str, object]]:
        unique_by_key: dict[tuple[object, ...], dict[str, object]] = {}
        for result in results:
            key = self._result_fingerprint(result)
            existing = unique_by_key.get(key)
            if not existing:
                unique_by_key[key] = result
                continue
            if self._result_rank(result) > self._result_rank(existing):
                unique_by_key[key] = result
        return list(unique_by_key.values())

    def _result_fingerprint(self, result: dict[str, object]) -> tuple[object, ...]:
        match = self._normalize_match_text(str(result.get("match") or ""))
        if not match:
            match = self._normalize_match_text(str(result.get("description") or ""))
        return (
            result.get("absolutePath"),
            result.get("line"),
            self._result_family(result),
            match,
        )

    def _normalize_match_text(self, value: str) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        return value[:240]

    def _result_rank(self, result: dict[str, object]) -> tuple[int, int]:
        severity_rank = {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1,
            "Info": 0,
        }.get(str(result.get("severity") or ""), 0)
        result_type = str(result.get("type") or "")
        type_rank = {
            "TaintAnalysis": 4,
            "RouteAuthAnalysis": 3,
            "ASTAnalysis": 2,
            "StaticAnalysis": 1,
        }.get(result_type, 0)
        rule_id = str(result.get("ruleId") or "")
        if rule_id.endswith("_TAINT") or "_TAINT" in rule_id:
            type_rank = max(type_rank, 4)
        return severity_rank, type_rank

    def _result_family(self, result: dict[str, object]) -> str:
        rule_id = str(result.get("ruleId") or "").upper()
        rule_name = str(result.get("ruleName") or "").upper()
        text = f"{rule_id} {rule_name}"
        families = {
            "SQL": ("SQL", "MYSQL", "PDO", "QUERY"),
            "COMMAND": ("COMMAND", "EXEC", "SYSTEM", "SHELL", "命令"),
            "CODE_EXEC": ("CODE_EXEC", "EVAL", "ASSERT", "PREG_REPLACE", "代码执行"),
            "FILE": ("FILE", "INCLUDE", "READ", "UPLOAD", "文件"),
            "DESERIALIZE": ("UNSERIALIZE", "DESERIAL", "反序列化"),
            "CALLBACK": ("CALLBACK", "CALL_USER_FUNC", "动态函数"),
            "XSS": ("XSS", "CROSS_SITE", "跨站"),
            "SSRF": ("SSRF", "CURL", "URL"),
            "AUTH": ("AUTH", "ACCESS", "鉴权", "访问控制"),
        }
        for family, markers in families.items():
            if any(marker in text for marker in markers):
                return family
        return rule_id or "UNKNOWN"

    def _normalize_vuln(self, project: Path, file_path: Path, vuln: dict) -> dict[str, object]:
        return {
            "type": vuln.get("type", ""),
            "ruleId": vuln.get("rule_id", "未知"),
            "ruleName": vuln.get("rule_name", "未知规则"),
            "severity": vuln.get("severity", "未知"),
            "file": str(file_path.relative_to(project)),
            "line": int(vuln.get("line") or 0),
            "description": vuln.get("description", ""),
            "match": vuln.get("match", ""),
            "details": vuln.get("details", {}),
            "absolutePath": str(file_path),
        }
