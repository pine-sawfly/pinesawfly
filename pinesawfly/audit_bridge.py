from __future__ import annotations

import html
import json
import logging
import os
import re
import subprocess
import base64
import ctypes
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import hashlib
from typing import Any

from PySide6.QtCore import QObject, Property, QLineF, QRectF, QSettings, QSizeF, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPageSize, QPainter, QPdfWriter, QTextDocument
from PySide6.QtSvg import QSvgRenderer
from openai import OpenAI

from modules.file_module import FileModule
from modules.generic_rule_engine import GenericRuleEngine
from pinesawfly.syntax_highlighter import highlight_code

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
SNIPPET_LANGUAGES = {
    ".php": "php",
    ".py": "python",
    ".java": "java",
    ".lua": "lua",
    ".go": "go",
}
REPORT_SYMBOLS = [
    "{{ title }}",
    "{{ color_logo }}",
    "{{ mono_logo }}",
    "{{ author }}",
    "{{ unit }}",
    "{{ project_path }}",
    "{{ generated_at }}",
    "{{ date }}",
    "{{ overview }}",
    "{{# findings }}",
    "{{ finding_id }}",
    "{{ rule_id }}",
    "{{ risk_level }}",
    "{{ issue_summary }}",
    "{{ vulnerability_location }}",
    "{{ data_flow }}",
    "{{ evidence_code }}",
    "{{ ai_analysis }}",
    "{{/ findings }}",
]
FINDING_LOOP_PATTERN = re.compile(r"{{#\s*findings\s*}}(.*?){{/\s*findings\s*}}", re.DOTALL)
AI_ANALYSIS_TIMEOUT_SECONDS = 30
AI_ANALYSIS_MAX_WORKERS = 8
AI_ANALYSIS_CACHE_TTL_SECONDS = 24 * 60 * 60
AI_PROVIDER_PRESETS = [
    "DeepSeek 官方",
    "OpenAI 官方",
    "自定义 API",
]
KNOWN_AI_MODEL_NAMES = {
    "deepseek",
    "deepseek api",
    "deepseek-chat",
    "deepseek-reasoner",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-latest",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "qwen-plus",
    "qwen-max",
}


def normalize_path(path_or_url: str) -> str:
    if path_or_url.startswith("file:"):
        return QUrl(path_or_url).toLocalFile()
    return path_or_url


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
        self._append_plugin_results(project, results)
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

    def _append_plugin_results(self, project: Path, results: list[dict[str, object]]) -> None:
        try:
            from core.plugin_loader import PluginLoader

            app_root = Path(__file__).resolve().parent.parent
            plugin_loader = PluginLoader(str(app_root / "plugins"))
            plugin_loader.load_all_plugins()
            php_plugin_module = plugin_loader.get_plugin("php_plugin")
            if not php_plugin_module:
                return
            php_plugin = php_plugin_module.PluginInterface()
            if not php_plugin.initialize(str(project)):
                return
            for php_file in project.rglob("*.php"):
                if is_ignored_path(php_file, self.include_dependencies):
                    continue
                for vuln in php_plugin.scan(str(php_file)):
                    results.append(self._normalize_vuln(project, php_file, vuln))
        except Exception:
            logger.exception("plugin scan failed")

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


class AuditBridge(QObject):
    filesChanged = Signal()
    projectPathChanged = Signal()
    currentFileChanged = Signal()
    currentContentChanged = Signal()
    currentHighlightedContentChanged = Signal()
    currentLineChanged = Signal()
    findingsChanged = Signal()
    statusChanged = Signal()
    scanningChanged = Signal()
    reportSettingsChanged = Signal()
    pluginSettingsChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("PineSawFly", "PineSawFly")
        self._app_root = Path(__file__).resolve().parent.parent
        self._report_template_dir = self._app_root / "templates" / "reports"
        self._report_template_dir.mkdir(parents=True, exist_ok=True)
        self._project_path = os.getcwd()
        self._files: list[dict[str, object]] = []
        self._findings: list[dict[str, object]] = []
        self._current_file = ""
        self._current_line = 0
        self._current_content = "请选择左侧文件以查看代码。"
        self._current_highlighted_content = self._highlight_code(self._current_content, "")
        self._status = "就绪"
        self._scanning = False
        self._report_title = self._settings.value("report/title", "Pinesawfly审计报告", str)
        self._report_author = self._settings.value("report/author", "", str)
        self._report_unit = self._settings.value("report/unit", "", str)
        self._report_template_format = "Markdown"
        self._report_template_content = self._load_report_template(self._report_template_format)
        self._report_include_project_path = self._settings.value("report/includeProjectPath", True, bool)
        self._report_include_generated_at = self._settings.value("report/includeGeneratedAt", True, bool)
        self._report_include_summary = self._settings.value("report/includeSummary", True, bool)
        self._report_include_logo = self._settings.value("report/includeLogo", True, bool)
        self._report_include_code_snippet = self._settings.value("report/includeCodeSnippet", True, bool)
        self._ai_plugin_enabled = self._settings.value("plugins/aiAnalysis/enabled", False, bool)
        self._include_dependency_scan = self._settings.value("plugins/phpAnalysis/includeDependencies", False, bool)
        self._ai_api_configs = self._load_ai_api_configs()
        self._ai_analysis_by_finding: dict[int, str] = {}
        self._last_ai_error = ""
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._cleanup_ai_analysis_cache()
        self.setProjectPath(self._project_path)

    def _set_status(self, message: str) -> None:
        if message != self._status:
            self._status = message
            self.statusChanged.emit()

    def _set_scanning(self, value: bool) -> None:
        if value != self._scanning:
            self._scanning = value
            self.scanningChanged.emit()

    def _set_current_line(self, value: int) -> None:
        value = max(0, int(value or 0))
        if value != self._current_line:
            self._current_line = value
            self.currentLineChanged.emit()

    @Slot(str)
    def setProjectPath(self, path_or_url: str) -> None:
        path = normalize_path(path_or_url)
        if not path or not os.path.isdir(path):
            self._set_status(f"项目目录无效: {path}")
            return
        self._project_path = os.path.abspath(path)
        self._cleanup_ai_analysis_cache()
        self._files = self._collect_files(self._project_path)
        self.projectPathChanged.emit()
        self.filesChanged.emit()
        self._set_status(f"已打开项目: {self._project_path}")

    def _collect_files(self, project_path: str) -> list[dict[str, object]]:
        root = Path(project_path)
        files: list[dict[str, object]] = []
        for item in sorted(root.rglob("*")):
            if is_ignored_path(item):
                continue
            if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append({
                    "name": item.name,
                    "relativePath": str(item.relative_to(root)),
                    "absolutePath": str(item),
                    "extension": item.suffix.lower().lstrip(".") or "file",
                })
        return files

    @Slot(str)
    def openFile(self, path_or_url: str) -> None:
        path = normalize_path(path_or_url)
        if not os.path.isabs(path):
            path = os.path.join(self._project_path, path)
        try:
            self._current_content = FileModule.read_file_with_encoding(path)
            self._current_highlighted_content = self._highlight_code(self._current_content, path)
            self._current_file = path
            self._set_current_line(0)
            self.currentContentChanged.emit()
            self.currentHighlightedContentChanged.emit()
            self.currentFileChanged.emit()
            self._set_status(f"已加载文件: {path}")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"无法读取文件: {exc}")

    @Slot(str, int)
    def openFinding(self, file_path: str, line: int) -> None:
        self.openFile(file_path)
        if line:
            self._set_current_line(line)
            self._set_status(f"定位到 {file_path}:{line}")

    @Slot()
    def startScan(self) -> None:
        if self._scanning:
            return
        self._set_scanning(True)
        self._set_status("正在扫描...")
        self._findings = []
        self.findingsChanged.emit()
        self._thread = QThread()
        self._worker = ScanWorker(self._project_path, self._include_dependency_scan)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.failed.connect(self._on_scan_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._cleanup_worker)
        self._thread.start()

    @Slot()
    def startAiAnalysis(self) -> None:
        if self._scanning:
            return
        if not self._findings:
            self._set_status("请先完成扫描，再进行 AI 分析")
            return
        if not self._ai_plugin_enabled:
            self._set_status("请先在插件页面启用 AI 分析")
            return
        if not self._usable_ai_api_configs():
            self._set_status("请先配置可用的 AI API URL 和 Key")
            return
        pending = sum(1 for finding in self._findings if isinstance(finding, dict) and not str(finding.get("aiAnalysis", "")).strip())
        if pending == 0:
            self._set_status("AI 分析已存在，无需重复请求")
            return
        self._set_scanning(True)
        self._set_status("正在进行 AI 分析...")
        try:
            self._prepare_ai_analysis()
            for index, finding in enumerate(self._findings, 1):
                if isinstance(finding, dict) and index in self._ai_analysis_by_finding:
                    finding["aiAnalysis"] = self._ai_analysis_by_finding.get(index, "")
            self.findingsChanged.emit()
            count = sum(1 for value in self._ai_analysis_by_finding.values() if value.strip())
            if count:
                self._save_ai_analysis_cache()
                self._set_status(f"AI 分析完成，新增 {count} 条分析结果")
            elif self._last_ai_error:
                self._set_status(f"AI 分析请求失败: {self._last_ai_error}")
            else:
                self._set_status("AI 分析完成，未生成有效内容")
        finally:
            self._set_scanning(False)

    @Slot(str, str, result=bool)
    def exportReport(self, report_format: str, path_or_url: str) -> bool:
        report_format = self._normalize_report_format(report_format)
        path = normalize_path(path_or_url).strip()
        if not path:
            self._set_status("请选择报告保存位置")
            return False

        target = Path(path)
        if target.is_dir():
            target = target / f"pinesawfly-report{self._report_extension(report_format)}"
        if not target.suffix:
            target = target.with_suffix(self._report_extension(report_format))

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if report_format == "PDF":
                self._write_pdf_report(target)
            else:
                target.write_text(self._build_report(report_format), encoding="utf-8")
            self._set_status(f"报告已导出: {target}")
            return True
        except OSError as exc:
            self._set_status(f"报告导出失败: {exc}")
            return False

    @Slot(str)
    def setReportTitle(self, value: str) -> None:
        value = value.strip() or "Pinesawfly审计报告"
        if value != self._report_title:
            self._report_title = value
            self._settings.setValue("report/title", value)
            self.reportSettingsChanged.emit()

    @Slot(str)
    def setReportAuthor(self, value: str) -> None:
        value = value.strip()
        if value != self._report_author:
            self._report_author = value
            self._settings.setValue("report/author", value)
            self.reportSettingsChanged.emit()

    @Slot(str)
    def setReportUnit(self, value: str) -> None:
        value = value.strip()
        if value != self._report_unit:
            self._report_unit = value
            self._settings.setValue("report/unit", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeSummary(self, value: bool) -> None:
        if value != self._report_include_summary:
            self._report_include_summary = value
            self._settings.setValue("report/includeSummary", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeProjectPath(self, value: bool) -> None:
        if value != self._report_include_project_path:
            self._report_include_project_path = value
            self._settings.setValue("report/includeProjectPath", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeGeneratedAt(self, value: bool) -> None:
        if value != self._report_include_generated_at:
            self._report_include_generated_at = value
            self._settings.setValue("report/includeGeneratedAt", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeLogo(self, value: bool) -> None:
        if value != self._report_include_logo:
            self._report_include_logo = value
            self._settings.setValue("report/includeLogo", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeCodeSnippet(self, value: bool) -> None:
        if value != self._report_include_code_snippet:
            self._report_include_code_snippet = value
            self._settings.setValue("report/includeCodeSnippet", value)
            self.reportSettingsChanged.emit()

    @Slot(str, result=str)
    def loadReportTemplate(self, report_format: str) -> str:
        self._report_template_format = self._normalize_report_format(report_format)
        self._report_template_content = self._load_report_template(self._report_template_format)
        self.reportSettingsChanged.emit()
        return self._report_template_content

    @Slot(str, str, result=bool)
    def saveReportTemplate(self, report_format: str, content: str) -> bool:
        report_format = self._normalize_report_format(report_format)
        try:
            path = self._report_template_path(report_format)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self._report_template_format = report_format
            self._report_template_content = content
            self._set_status(f"报告模板已保存: {path}")
            self.reportSettingsChanged.emit()
            return True
        except OSError as exc:
            self._set_status(f"报告模板保存失败: {exc}")
            return False

    @Slot(str, result=str)
    def resetReportTemplate(self, report_format: str) -> str:
        report_format = self._normalize_report_format(report_format)
        content = self._default_report_template(report_format)
        self.saveReportTemplate(report_format, content)
        return content

    @Slot(list, int, str)
    def _on_scan_finished(self, findings: list, _count: int, message: str) -> None:
        self._findings = findings
        self._restore_ai_analysis_cache()
        self.findingsChanged.emit()
        self._set_status(message)
        self._set_scanning(False)

    @Slot(str)
    def _on_scan_failed(self, message: str) -> None:
        self._set_status(f"扫描失败: {message}")
        self._set_scanning(False)

    @Slot()
    def _cleanup_worker(self) -> None:
        self._worker = None
        self._thread = None

    def get_files(self) -> list[dict[str, object]]:
        return self._files

    def get_project_path(self) -> str:
        return self._project_path

    def get_current_file(self) -> str:
        return self._current_file

    def get_current_content(self) -> str:
        return self._current_content

    def get_current_highlighted_content(self) -> str:
        return self._current_highlighted_content

    def get_current_line(self) -> int:
        return self._current_line

    def get_findings(self) -> list[dict[str, object]]:
        return self._findings

    def get_status(self) -> str:
        return self._status

    def get_scanning(self) -> bool:
        return self._scanning

    def get_report_title(self) -> str:
        return self._report_title

    def set_report_title(self, value: str) -> None:
        self.setReportTitle(value)

    def get_report_author(self) -> str:
        return self._report_author

    def set_report_author(self, value: str) -> None:
        self.setReportAuthor(value)

    def get_report_unit(self) -> str:
        return self._report_unit

    def set_report_unit(self, value: str) -> None:
        self.setReportUnit(value)

    def get_report_template_content(self) -> str:
        return self._report_template_content

    def get_report_template_symbols(self) -> list[str]:
        return REPORT_SYMBOLS

    def get_report_include_project_path(self) -> bool:
        return self._report_include_project_path

    def set_report_include_project_path(self, value: bool) -> None:
        self.setReportIncludeProjectPath(value)

    def get_report_include_generated_at(self) -> bool:
        return self._report_include_generated_at

    def set_report_include_generated_at(self, value: bool) -> None:
        self.setReportIncludeGeneratedAt(value)

    def get_report_include_summary(self) -> bool:
        return self._report_include_summary

    def set_report_include_summary(self, value: bool) -> None:
        self.setReportIncludeSummary(value)

    def get_report_include_logo(self) -> bool:
        return self._report_include_logo

    def set_report_include_logo(self, value: bool) -> None:
        self.setReportIncludeLogo(value)

    def get_report_include_code_snippet(self) -> bool:
        return self._report_include_code_snippet

    def set_report_include_code_snippet(self, value: bool) -> None:
        self.setReportIncludeCodeSnippet(value)

    def get_ai_plugin_enabled(self) -> bool:
        return self._ai_plugin_enabled

    def set_ai_plugin_enabled(self, value: bool) -> None:
        self.setAiPluginEnabled(value)

    def get_include_dependency_scan(self) -> bool:
        return self._include_dependency_scan

    def set_include_dependency_scan(self, value: bool) -> None:
        self.setIncludeDependencyScan(value)

    def get_ai_api_configs(self) -> list[dict[str, object]]:
        return [self._public_ai_api_config(index, config) for index, config in enumerate(self._ai_api_configs)]

    def get_ai_provider_presets(self) -> list[str]:
        return AI_PROVIDER_PRESETS

    @Slot(bool)
    def setIncludeDependencyScan(self, value: bool) -> None:
        if value != self._include_dependency_scan:
            self._include_dependency_scan = value
            self._settings.setValue("plugins/phpAnalysis/includeDependencies", value)
            self.pluginSettingsChanged.emit()

    @Slot(bool)
    def setAiPluginEnabled(self, value: bool) -> None:
        if value != self._ai_plugin_enabled:
            self._ai_plugin_enabled = value
            self._settings.setValue("plugins/aiAnalysis/enabled", value)
            self.pluginSettingsChanged.emit()

    @Slot()
    def addAiApiConfig(self) -> None:
        self._ai_api_configs.append({
            "apiName": "DeepSeek 官方",
            "apiUrl": "https://api.deepseek.com",
            "modelName": "deepseek-v4-flash",
            "keyName": "DEEPSEEK_API_KEY",
            "apiKey": "",
        })
        self._save_ai_api_configs()

    @Slot(int)
    def deleteAiApiConfig(self, index: int) -> None:
        if 0 <= index < len(self._ai_api_configs):
            self._ai_api_configs.pop(index)
            self._save_ai_api_configs()

    @Slot(int, str, str, str, str, str)
    def updateAiApiConfig(self, index: int, api_name: str, api_url: str, model_name: str, key_name: str, api_key: str) -> None:
        if 0 <= index < len(self._ai_api_configs):
            current_key = self._ai_api_configs[index].get("apiKey", "")
            api_key = api_key.strip()
            self._ai_api_configs[index] = {
                "apiName": api_name.strip(),
                "apiUrl": api_url.strip(),
                "modelName": model_name.strip(),
                "keyName": key_name.strip(),
                "apiKey": api_key if api_key else current_key,
            }
            self._save_ai_api_configs()

    def _load_ai_api_configs(self) -> list[dict[str, str]]:
        raw = self._settings.value("plugins/aiAnalysis/apis", "[]", str)
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        configs = []
        for item in data:
            if isinstance(item, dict):
                api_name = str(item.get("apiName", "")).strip()
                api_url = str(item.get("apiUrl", "")).strip()
                model_name = str(item.get("modelName", "")).strip()
                if not model_name and self._looks_like_model_name(api_name):
                    model_name = self._legacy_model_name(api_name, api_url)
                    api_name = self._provider_name_from_url(api_url)
                configs.append({
                    "apiName": api_name,
                    "apiUrl": api_url,
                    "modelName": model_name,
                    "keyName": str(item.get("keyName", "")),
                    "apiKey": self._decrypt_secret(str(item.get("apiKey", ""))),
                })
        return configs

    def _save_ai_api_configs(self) -> None:
        encrypted = []
        for config in self._ai_api_configs:
            encrypted.append({
                "apiName": config.get("apiName", ""),
                "apiUrl": config.get("apiUrl", ""),
                "modelName": config.get("modelName", ""),
                "keyName": config.get("keyName", ""),
                "apiKey": self._encrypt_secret(config.get("apiKey", "")),
            })
        self._settings.setValue("plugins/aiAnalysis/apis", json.dumps(encrypted, ensure_ascii=False))
        self.pluginSettingsChanged.emit()

    def _public_ai_api_config(self, index: int, config: dict[str, str]) -> dict[str, object]:
        api_key = config.get("apiKey", "")
        return {
            "index": index,
            "apiName": config.get("apiName", ""),
            "apiUrl": config.get("apiUrl", ""),
            "modelName": config.get("modelName", ""),
            "keyName": config.get("keyName", ""),
            "apiKey": "",
            "maskedKey": self._mask_secret(api_key),
            "keyFingerprint": self._key_fingerprint(api_key),
        }

    def _looks_like_model_name(self, value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in KNOWN_AI_MODEL_NAMES or normalized.startswith(("gpt-", "claude-", "gemini-", "qwen-", "deepseek-"))

    def _legacy_model_name(self, api_name: str, api_url: str) -> str:
        normalized = api_name.strip().lower()
        if normalized in {"deepseek", "deepseek api", "deepseek-chat"}:
            return "deepseek-v4-flash"
        if normalized == "deepseek-reasoner":
            return "deepseek-v4-pro"
        return api_name.strip() or self._default_model_for_url(api_url)

    def _provider_name_from_url(self, api_url: str) -> str:
        lowered = api_url.lower()
        if "deepseek" in lowered:
            return "DeepSeek 官方"
        if "openai" in lowered:
            return "OpenAI 官方"
        return "自定义 API"

    def _default_model_for_url(self, api_url: str) -> str:
        lowered = api_url.lower()
        if "deepseek" in lowered:
            return "deepseek-v4-flash"
        if "openai" in lowered:
            return "gpt-5-mini"
        return "gpt-5-mini"

    def _mask_secret(self, value: str) -> str:
        if not value:
            return ""
        if len(value) <= 11:
            return "*" * len(value)
        return f"{value[:7]}{'*' * max(4, len(value) - 11)}{value[-4:]}"

    def _key_fingerprint(self, value: str) -> str:
        if not value:
            return ""

        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]

    def _encrypt_secret(self, value: str) -> str:
        if not value:
            return ""
        if os.name != "nt":
            return value
        protected = self._dpapi_protect(value.encode("utf-8"))
        return "dpapi:" + base64.b64encode(protected).decode("ascii")

    def _decrypt_secret(self, value: str) -> str:
        if not value:
            return ""
        if not value.startswith("dpapi:"):
            return value
        if os.name != "nt":
            return ""
        try:
            data = base64.b64decode(value.removeprefix("dpapi:"))
            return self._dpapi_unprotect(data).decode("utf-8")
        except Exception:
            logger.debug("unable to decrypt AI API key", exc_info=True)
            return ""

    def _dpapi_protect(self, data: bytes) -> bytes:
        return self._dpapi_crypt(data, protect=True)

    def _dpapi_unprotect(self, data: bytes) -> bytes:
        return self._dpapi_crypt(data, protect=False)

    def _dpapi_crypt(self, data: bytes, protect: bool) -> bytes:
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

        in_buffer = ctypes.create_string_buffer(data)
        in_blob = DATA_BLOB(len(data), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        out_blob = DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if protect:
            ok = crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob))
        else:
            ok = crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob))
        if not ok:
            raise OSError(ctypes.get_last_error())
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def _prepare_ai_analysis(self) -> None:
        self._ai_analysis_by_finding = {}
        self._last_ai_error = ""
        if not self._ai_plugin_enabled or not self._findings:
            return

        configs = self._usable_ai_api_configs()
        if not configs:
            return

        prompt_template = self._load_ai_prompt_template()
        pending_findings = [
            (index, finding)
            for index, finding in enumerate(self._findings, 1)
            if isinstance(finding, dict) and not str(finding.get("aiAnalysis", "")).strip()
        ]
        if not pending_findings:
            return
        workers = min(AI_ANALYSIS_MAX_WORKERS, max(1, len(pending_findings)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._request_ai_analysis, configs[(index - 1) % len(configs)], prompt_template, index, finding): index
                for index, finding in pending_findings
            }
            for future in as_completed(futures):
                finding_index = futures[future]
                try:
                    content = future.result().strip()
                except Exception:
                    logger.debug("AI analysis failed for finding %s", finding_index, exc_info=True)
                    content = ""
                if content:
                    self._ai_analysis_by_finding[finding_index] = content

    def _restore_ai_analysis_cache(self) -> None:
        project_cache = self._current_project_ai_cache()
        items = project_cache.get("items", {})
        if not isinstance(items, dict) or not items:
            return
        changed = False
        for finding in self._findings:
            if not isinstance(finding, dict) or str(finding.get("aiAnalysis", "")).strip():
                continue
            cached = items.get(self._ai_analysis_cache_key(finding), {})
            content = cached.get("content", "") if isinstance(cached, dict) else str(cached)
            if content:
                finding["aiAnalysis"] = content
                changed = True
        if changed:
            self._set_status("已加载本地 AI 分析缓存")

    def _save_ai_analysis_cache(self) -> None:
        cache = self._load_ai_analysis_cache()
        project_key = self._ai_project_cache_key()
        now = datetime.now().timestamp()
        project_cache = cache.get(project_key, {})
        if not isinstance(project_cache, dict):
            project_cache = {}
        items = project_cache.get("items", {})
        if not isinstance(items, dict):
            items = {}
        for finding in self._findings:
            if not isinstance(finding, dict):
                continue
            content = str(finding.get("aiAnalysis", "")).strip()
            if content:
                key = self._ai_analysis_cache_key(finding)
                previous = items.get(key, {})
                created_at = previous.get("createdAt", now) if isinstance(previous, dict) else now
                items[key] = {"content": content, "createdAt": created_at, "updatedAt": now}
        cache[project_key] = {
            "projectPath": os.path.abspath(self._project_path),
            "createdAt": project_cache.get("createdAt", now),
            "updatedAt": now,
            "items": items,
        }
        self._settings.setValue("plugins/aiAnalysis/cache", json.dumps(cache, ensure_ascii=False))

    def _load_ai_analysis_cache(self) -> dict[str, object]:
        raw = self._settings.value("plugins/aiAnalysis/cache", "{}", str)
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): value for key, value in data.items()}

    def _current_project_ai_cache(self) -> dict[str, object]:
        cache = self._load_ai_analysis_cache()
        project_cache = cache.get(self._ai_project_cache_key(), {})
        return project_cache if isinstance(project_cache, dict) else {}

    def _cleanup_ai_analysis_cache(self) -> None:
        cache = self._load_ai_analysis_cache()
        if not cache:
            return
        now = datetime.now().timestamp()
        changed = False
        cleaned: dict[str, object] = {}
        for project_key, project_cache in cache.items():
            if not isinstance(project_cache, dict):
                changed = True
                continue
            project_updated = float(project_cache.get("updatedAt") or project_cache.get("createdAt") or 0)
            if project_updated and now - project_updated > AI_ANALYSIS_CACHE_TTL_SECONDS:
                changed = True
                continue
            items = project_cache.get("items", {})
            if not isinstance(items, dict):
                changed = True
                continue
            cleaned_items = {}
            for item_key, item in items.items():
                if not isinstance(item, dict):
                    changed = True
                    continue
                item_updated = float(item.get("updatedAt") or item.get("createdAt") or 0)
                if item_updated and now - item_updated <= AI_ANALYSIS_CACHE_TTL_SECONDS:
                    cleaned_items[str(item_key)] = item
                else:
                    changed = True
            if cleaned_items:
                project_cache["items"] = cleaned_items
                project_cache["updatedAt"] = max(
                    float(item.get("updatedAt") or item.get("createdAt") or 0)
                    for item in cleaned_items.values()
                    if isinstance(item, dict)
                )
                cleaned[str(project_key)] = project_cache
            else:
                changed = True
        if changed:
            self._settings.setValue("plugins/aiAnalysis/cache", json.dumps(cleaned, ensure_ascii=False))

    def _ai_project_cache_key(self) -> str:
        return hashlib.sha256(os.path.abspath(self._project_path).encode("utf-8", "replace")).hexdigest()

    def _ai_analysis_cache_key(self, finding: dict[str, object]) -> str:
        payload = "|".join(
            [
                str(finding.get("absolutePath") or finding.get("file") or ""),
                str(finding.get("line") or ""),
                str(finding.get("ruleId") or ""),
                str(finding.get("description") or ""),
                str(finding.get("dataFlow") or ""),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8", "replace")).hexdigest()

    def _load_ai_prompt_template(self) -> str:
        path = self._app_root / "templates" / "ai" / "analysis_prompt.md"
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                logger.debug("unable to read AI prompt template %s", path, exc_info=True)
        return self._default_ai_prompt_template()

    def _default_ai_prompt_template(self) -> str:
        return (
            "你是资深应用安全专家。请根据以下漏洞信息，严格按格式输出，总字数不超过300字。\n"
            "判断规则：\n"
            "若存在漏洞，按格式输出：\n"
            "确认存在安全漏洞，修复建议：...\n"
            "修复代码：（仅展示修复核心代码）\n"
            "若不存在漏洞，按格式输出：\n"
            "该项漏洞为误报，理由：...（只说明理由，不要输出任何建议或代码）\n"
            "漏洞信息如下：\n"
            "漏洞位置：{{ vulnerability_location }}\n"
            "传递链路：{{ data_flow }}\n"
            "问题概述：{{ issue_summary }}\n"
            "代码证据片段：{{ evidence_code }}\n"
        )

    def _usable_ai_api_configs(self) -> list[dict[str, str]]:
        return [
            config
            for config in self._ai_api_configs
            if config.get("apiUrl", "").strip() and config.get("apiKey", "").strip()
        ]

    def _request_ai_analysis(
        self,
        config: dict[str, str],
        prompt_template: str,
        index: int,
        finding: dict[str, object],
    ) -> str:
        prompt = self._render_ai_prompt(prompt_template, index, finding)
        api_url = config.get("apiUrl", "").strip()
        if self._uses_bearer_auth(config):
            return self._request_openai_compatible_analysis(config, prompt, api_url)

        return self._request_raw_chat_completions(config, prompt, api_url)

    def _request_openai_compatible_analysis(self, config: dict[str, str], prompt: str, api_url: str) -> str:
        api_key = config.get("apiKey", "").strip()
        base_url = self._ai_base_url(api_url)
        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=AI_ANALYSIS_TIMEOUT_SECONDS)
            kwargs: dict[str, object] = {
                "model": self._ai_model_name(config),
                "messages": [
                    {"role": "system", "content": "你是严谨的应用安全审计助手。"},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }
            if "deepseek" in base_url.lower() and self._ai_model_name(config) == "deepseek-v4-pro":
                kwargs["reasoning_effort"] = "high"
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            self._last_ai_error = self._format_ai_exception(exc)
            logger.debug("OpenAI-compatible AI API request failed: %s", base_url, exc_info=True)
            return ""

    def _request_raw_chat_completions(self, config: dict[str, str], prompt: str, api_url: str) -> str:
        chat_url = self._ai_chat_completions_url(api_url)
        api_key = config.get("apiKey", "").strip()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self._ai_auth_headers(config))
        payload = {
            "model": self._ai_model_name(config),
            "messages": [
                {"role": "system", "content": "你是严谨的应用安全审计助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 600,
        }
        request = urllib.request.Request(
            chat_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=AI_ANALYSIS_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            self._last_ai_error = f"HTTP {exc.code} {body}".strip()
            logger.debug("AI API request failed: %s", chat_url, exc_info=True)
            return ""
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            self._last_ai_error = str(exc)
            logger.debug("AI API request failed: %s", chat_url, exc_info=True)
            return ""
        return self._extract_ai_response_text(data)

    def _ai_auth_headers(self, config: dict[str, str]) -> dict[str, str]:
        api_key = config.get("apiKey", "").strip()
        key_name = config.get("keyName", "").strip()
        if self._uses_bearer_auth(config):
            return {"Authorization": api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"}
        return {key_name: api_key}

    def _uses_bearer_auth(self, config: dict[str, str]) -> bool:
        key_name = config.get("keyName", "").strip()
        api_url = config.get("apiUrl", "").lower()
        if any(provider in api_url for provider in ("deepseek", "openai")):
            return True
        normalized = key_name.lower().replace("-", "_")
        return (
            not key_name
            or normalized == "authorization"
            or normalized.endswith("_api_key")
            or normalized in {"api_key", "openai_api_key", "deepseek_api_key"}
        )

    def _ai_model_name(self, config: dict[str, str]) -> str:
        model_name = config.get("modelName", "").strip()
        api_url = config.get("apiUrl", "").lower()
        if not model_name:
            return self._default_model_for_url(api_url)
        if model_name.lower() == "deepseek-chat":
            return "deepseek-v4-flash"
        if model_name.lower() == "deepseek-reasoner":
            return "deepseek-v4-pro"
        return model_name

    def _ai_chat_completions_url(self, api_url: str) -> str:
        value = api_url.strip().rstrip("/")
        if not value:
            return value
        lowered = value.lower()
        if lowered.endswith("/chat/completions") or lowered.endswith("/v1/chat/completions"):
            return value
        if lowered.endswith("/v1"):
            return f"{value}/chat/completions"
        return f"{value}/chat/completions"

    def _ai_base_url(self, api_url: str) -> str:
        value = api_url.strip().rstrip("/")
        lowered = value.lower()
        if lowered.endswith("/chat/completions"):
            return value[: -len("/chat/completions")]
        return value

    def _format_ai_exception(self, exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                body = response.text[:300]
            except Exception:
                body = ""
        else:
            body = str(exc)
        if status_code:
            return f"HTTP {status_code} {body}".strip()
        return body[:300]

    def _render_ai_prompt(self, template: str, index: int, finding: dict[str, object]) -> str:
        values = self._finding_template_values(index, finding, html_mode=False)
        values["{{ evidence_code }}"] = self._plain_evidence_code(finding)
        values["{{ highlighted_code }}"] = values["{{ evidence_code }}"]
        rendered = template
        for symbol, value in values.items():
            rendered = rendered.replace(symbol, value)
        return rendered

    def _plain_evidence_code(self, finding: dict[str, object]) -> str:
        return self._code_snippet(0, finding, html_mode=False)

    def _extract_ai_response_text(self, data: object) -> str:
        if not isinstance(data, dict):
            return ""
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                text = first.get("text")
                if isinstance(text, str):
                    return text
        content = data.get("content")
        return content if isinstance(content, str) else ""

    files = Property("QVariantList", get_files, notify=filesChanged)
    projectPath = Property(str, get_project_path, notify=projectPathChanged)
    currentFile = Property(str, get_current_file, notify=currentFileChanged)
    currentContent = Property(str, get_current_content, notify=currentContentChanged)
    currentHighlightedContent = Property(str, get_current_highlighted_content, notify=currentHighlightedContentChanged)
    currentLine = Property(int, get_current_line, notify=currentLineChanged)
    findings = Property("QVariantList", get_findings, notify=findingsChanged)
    status = Property(str, get_status, notify=statusChanged)
    scanning = Property(bool, get_scanning, notify=scanningChanged)
    reportTitle = Property(str, get_report_title, set_report_title, notify=reportSettingsChanged)
    reportAuthor = Property(str, get_report_author, set_report_author, notify=reportSettingsChanged)
    reportUnit = Property(str, get_report_unit, set_report_unit, notify=reportSettingsChanged)
    reportTemplateContent = Property(str, get_report_template_content, notify=reportSettingsChanged)
    reportTemplateSymbols = Property("QVariantList", get_report_template_symbols, constant=True)
    reportIncludeProjectPath = Property(bool, get_report_include_project_path, set_report_include_project_path, notify=reportSettingsChanged)
    reportIncludeGeneratedAt = Property(bool, get_report_include_generated_at, set_report_include_generated_at, notify=reportSettingsChanged)
    reportIncludeSummary = Property(bool, get_report_include_summary, set_report_include_summary, notify=reportSettingsChanged)
    reportIncludeLogo = Property(bool, get_report_include_logo, set_report_include_logo, notify=reportSettingsChanged)
    reportIncludeCodeSnippet = Property(bool, get_report_include_code_snippet, set_report_include_code_snippet, notify=reportSettingsChanged)
    aiPluginEnabled = Property(bool, get_ai_plugin_enabled, set_ai_plugin_enabled, notify=pluginSettingsChanged)
    includeDependencyScan = Property(bool, get_include_dependency_scan, set_include_dependency_scan, notify=pluginSettingsChanged)
    aiApiConfigs = Property("QVariantList", get_ai_api_configs, notify=pluginSettingsChanged)
    aiProviderPresets = Property("QVariantList", get_ai_provider_presets, constant=True)

    def _highlight_code(self, content: str, file_path: str) -> str:
        return highlight_code(content, file_path)

    def _normalize_report_format(self, value: str) -> str:
        value = (value or "Markdown").strip().lower()
        mapping = {"md": "Markdown", "markdown": "Markdown", "html": "HTML", "json": "JSON", "pdf": "PDF", "txt": "TXT", "text": "TXT"}
        return mapping.get(value, "Markdown")

    def _report_extension(self, report_format: str) -> str:
        return {"Markdown": ".md", "HTML": ".html", "JSON": ".json", "PDF": ".pdf", "TXT": ".txt"}[report_format]

    def _build_report(self, report_format: str) -> str:
        if report_format == "JSON":
            return json.dumps(self._report_payload(), ensure_ascii=False, indent=2) + "\n"
        if report_format == "TXT":
            return self._build_text_report()
        return self._render_template(report_format)

    def _write_pdf_report(self, target: Path) -> None:
        writer = QPdfWriter(str(target))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setResolution(96)

        page_rect = QRectF(writer.pageLayout().paintRectPixels(writer.resolution()))
        margin = 54.0
        footer_height = 34.0
        content_width = page_rect.width() - margin * 2
        content_height = page_rect.height() - margin * 2 - footer_height

        html_parts = self._split_pdf_pages(self._render_template("PDF"))
        documents = []
        for html_part in html_parts:
            document = QTextDocument()
            document.setHtml(html_part)
            document.setPageSize(QSizeF(content_width, content_height))
            page_count = max(1, int((document.size().height() + content_height - 1) // content_height))
            documents.append((document, page_count))

        total_pages = sum(page_count for _document, page_count in documents)
        current_page = 0
        painter = QPainter(writer)
        try:
            for document, page_count in documents:
                for page in range(page_count):
                    if current_page > 0:
                        writer.newPage()
                    current_page += 1
                    painter.save()
                    painter.translate(margin, margin - page * content_height)
                    document.drawContents(painter, QRectF(0, page * content_height, content_width, content_height))
                    painter.restore()
                    self._draw_pdf_footer(painter, page_rect, margin, current_page, total_pages)
        finally:
            painter.end()

    def _split_pdf_pages(self, html_text: str) -> list[str]:
        marker = '<div class="page-break"></div>'
        if marker not in html_text:
            return [html_text]

        body_match = re.search(r"<body[^>]*>", html_text, re.IGNORECASE)
        if body_match is None:
            return [part for part in html_text.split(marker) if part.strip()]

        head = html_text[:body_match.end()]
        parts = html_text.split(marker)
        documents: list[str] = []
        for index, part in enumerate(parts):
            if not part.strip():
                continue
            if index == 0:
                documents.append(part + "</body></html>")
            else:
                documents.append(head + part)
        return documents

    def _draw_pdf_footer(self, painter: QPainter, page_rect: QRectF, margin: float, page: int, page_count: int) -> None:
        footer_y = page_rect.bottom() - margin + 14
        painter.save()
        painter.setPen(QColor("#8a938d"))
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.drawLine(QLineF(margin, footer_y - 12, page_rect.width() - margin, footer_y - 12))

        logo_path = self._mono_logo_path()
        if logo_path is not None:
            renderer = QSvgRenderer(str(logo_path))
            if renderer.isValid():
                renderer.render(painter, QRectF(margin, footer_y - 9, 18, 18))

        painter.drawText(
            QRectF(margin, footer_y - 8, page_rect.width() - margin * 2, 20),
            int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
            "Copyright © PineSawFly",
        )
        painter.drawText(
            QRectF(page_rect.width() - margin - 120, footer_y - 8, 120, 20),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            f"第 {page} / {page_count} 页",
        )
        painter.restore()

    def _report_template_path(self, report_format: str) -> Path:
        return self._report_template_dir / {"Markdown": "markdown.md", "HTML": "html.html", "PDF": "pdf.html"}.get(report_format, "markdown.md")

    def _load_report_template(self, report_format: str) -> str:
        path = self._report_template_path(report_format)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                logger.debug("unable to read report template %s", path, exc_info=True)
        return self._default_report_template(report_format)

    def _default_report_template(self, report_format: str) -> str:
        if report_format in {"HTML", "PDF"}:
            return (
                '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{{ title }}</title></head><body>'
                "<h1>{{ title }}</h1>{{ color_logo }}<p>作者：{{ author }}</p><p>单位：{{ unit }}</p>"
                "<p>项目路径：{{ project_path }}</p><p>日期：{{ date }}</p>"
                "{{ overview }}<h2>审计发现</h2>{{# findings }}<h3>Finding {{ finding_id }}</h3>"
                "<p>规则 ID：{{ rule_id }} / 风险等级：{{ risk_level }}</p><p>{{ issue_summary }}</p>"
                "<p>漏洞位置：{{ vulnerability_location }}</p><p>传递链路：{{ data_flow }}</p>{{ evidence_code }}{{ ai_analysis }}{{/ findings }}</body></html>"
            )
        return (
            "# {{ title }}\n\n"
            "{{ color_logo }}\n\n"
            "作者：{{ author }}\n\n"
            "单位：{{ unit }}\n\n"
            "项目路径：{{ project_path }}\n\n"
            "日期：{{ date }}\n\n"
            "{{ overview }}\n\n"
            "## 审计发现\n\n"
            "{{# findings }}\n"
            "### Finding {{ finding_id }}\n\n"
            "- **规则 ID**: {{ rule_id }}  **风险等级**: {{ risk_level }}\n"
            "- **问题概述**: {{ issue_summary }}\n\n"
            "- **漏洞位置**: {{ vulnerability_location }}\n"
            "- **传递链路**: {{ data_flow }}\n\n"
            "{{ evidence_code }}\n\n"
            "{{ ai_analysis }}\n\n"
            "{{/ findings }}\n"
        )

    def _render_template(self, report_format: str) -> str:
        template = self._load_report_template(report_format)
        if report_format in {"HTML", "PDF"}:
            template = self._inline_report_styles(template, report_format)
        html_mode = report_format in {"HTML", "PDF"}
        template = self._render_finding_loops(template, html_mode)
        values = self._template_values(html_mode, report_format)
        for symbol, value in values.items():
            template = template.replace(symbol, value)
        return template

    def _inline_report_styles(self, template: str, report_format: str) -> str:
        base_dir = self._report_template_path(report_format).parent

        def replace(match: re.Match[str]) -> str:
            href = html.unescape(match.group("href"))
            css_path = (base_dir / href).resolve()
            try:
                if not css_path.is_file() or base_dir.resolve() not in css_path.parents:
                    return match.group(0)
                css = css_path.read_text(encoding="utf-8")
            except OSError:
                logger.debug("unable to inline report stylesheet %s", css_path, exc_info=True)
                return match.group(0)
            return f"<style>\n{css}\n</style>"

        pattern = re.compile(
            r"<link\b(?=[^>]*\brel=[\"']stylesheet[\"'])(?=[^>]*\bhref=[\"'](?P<href>[^\"']+)[\"'])[^>]*>",
            re.IGNORECASE,
        )
        return pattern.sub(replace, template)

    def _report_payload(self) -> dict[str, object]:
        now = datetime.now()
        summary = self._report_summary()
        return {
            "title": self._report_title,
            "author": self._report_author,
            "unit": self._report_unit,
            "projectPath": self._project_path,
            "generatedAt": now.isoformat(timespec="seconds"),
            "date": f"{now.year}年{now.month}月{now.day}日",
            "overview": self._overview_text(int(summary.get("total", 0) or 0), summary.get("severityCount", {})),
            "summary": summary,
            "findings": [self._finding_payload(index, finding) for index, finding in enumerate(self._findings, 1)],
        }

    def _report_summary(self) -> dict[str, object]:
        severity_count: dict[str, int] = {}
        for finding in self._findings:
            severity = str(finding.get("severity", "未知"))
            severity_count[severity] = severity_count.get(severity, 0) + 1
        return {"total": len(self._findings), "severityCount": severity_count}

    def _template_values(self, html_mode: bool, report_format: str = "HTML") -> dict[str, str]:
        payload = self._report_payload()
        pdf_mode = report_format == "PDF"
        return {
            "{{ title }}": html.escape(str(payload["title"])) if html_mode else str(payload["title"]),
            "{{ logo }}": self._render_logo(html_mode, pdf_mode),
            "{{ color_logo }}": self._render_logo(html_mode, pdf_mode),
            "{{ mono_logo }}": self._render_mono_logo(html_mode),
            "{{ author }}": self._render_author(html_mode),
            "{{ author_value }}": html.escape(self._report_author) if html_mode else self._report_author,
            "{{ unit }}": self._render_unit(html_mode),
            "{{ unit_value }}": html.escape(self._report_unit) if html_mode else self._report_unit,
            "{{ project_path }}": self._render_project_path(html_mode, str(payload["projectPath"])),
            "{{ generated_at }}": self._render_generated_at(html_mode, str(payload["generatedAt"])),
            "{{ generated_at_value }}": html.escape(str(payload["generatedAt"])) if html_mode else str(payload["generatedAt"]),
            "{{ date }}": self._render_generated_at(html_mode, str(payload["date"])),
            "{{ overview }}": self._render_overview(html_mode, payload["summary"]),
            "{{ findings }}": self._render_findings(html_mode),
            "{{ affected_locations }}": "",
            "{{ evidence_code_snippets }}": self._render_code_snippets(html_mode),
            "{{ highlighted_code_snippets }}": self._render_code_snippets(html_mode),
        }

    def _render_logo(self, html_mode: bool, pdf_mode: bool = False) -> str:
        if not self._report_include_logo:
            return ""
        logo = self._color_logo_path()
        if logo is None:
            return ""
        logo_url = self._image_src(logo) if html_mode else logo.as_posix()
        if html_mode:
            if pdf_mode:
                return f'<img class="logo" src="{html.escape(logo_url)}" alt="PineSawFly Logo" width="160" style="width:160px;height:auto;">'
            return f'<img class="logo" src="{html.escape(logo_url)}" alt="PineSawFly Logo" style="width:25%;height:auto;">'
        return f'<img src="{logo.as_posix()}" alt="PineSawFly Logo" width="25%">'

    def _render_mono_logo(self, html_mode: bool) -> str:
        if not self._report_include_logo:
            return ""
        logo = self._mono_logo_path()
        if logo is None:
            return ""
        logo_url = self._image_src(logo) if html_mode else logo.as_posix()
        if html_mode:
            return f'<img class="mono-logo" src="{html.escape(logo_url)}" alt="PineSawFly Logo">'
        return f'<img src="{logo.as_posix()}" alt="PineSawFly Logo">'

    def _image_src(self, image_path: Path) -> str:
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(image_path.suffix.lower(), "application/octet-stream")
        try:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"
        except OSError:
            return QUrl.fromLocalFile(str(image_path)).toString()

    def _color_logo_path(self) -> Path | None:
        candidates = [
            self._app_root / "assets" / "icons" / "app.jpg",
            self._app_root / "assets" / "icons" / "app.ico",
            self._app_root / "assets" / "icons" / "app.png",
            self._app_root / "assets" / "icons" / "app.svg",
        ]
        return next((item for item in candidates if item.exists()), None)

    def _mono_logo_path(self) -> Path | None:
        logo = self._app_root / "assets" / "icons" / "app.svg"
        return logo if logo.exists() else None

    def _render_author(self, html_mode: bool) -> str:
        if not self._report_author:
            return ""
        return html.escape(self._report_author) if html_mode else self._report_author

    def _render_unit(self, html_mode: bool) -> str:
        if not self._report_unit:
            return ""
        return html.escape(self._report_unit) if html_mode else self._report_unit

    def _render_project_path(self, html_mode: bool, project_path: str) -> str:
        if not self._report_include_project_path:
            return ""
        return html.escape(project_path) if html_mode else project_path

    def _render_generated_at(self, html_mode: bool, generated_at: str) -> str:
        if not self._report_include_generated_at:
            return ""
        return html.escape(generated_at) if html_mode else generated_at

    def _metadata_span(self, label: str, value: str, html_mode: bool) -> str:
        if html_mode:
            return (
                '<div class="info-item">'
                f'<span class="info-label">{html.escape(label)}</span>'
                f'<span class="info-value">{html.escape(value)}</span>'
                "</div>"
            )
        return f"**{label}**: {value}"

    def _render_overview(self, html_mode: bool, summary: dict[str, object]) -> str:
        if not self._report_include_summary:
            return ""
        severity_count = summary.get("severityCount", {})
        total = int(summary.get("total", 0) or 0)
        overview_text = self._overview_text(total, severity_count)
        return html.escape(overview_text) if html_mode else overview_text

    def _overview_text(self, total: int, severity_count: dict[str, object]) -> str:
        critical = self._count_severity(severity_count, {"critical", "严重", "致命"})
        high = self._count_severity(severity_count, {"high", "高危", "高"})
        medium = self._count_severity(severity_count, {"medium", "中危", "中"})
        low = self._count_severity(severity_count, {"low", "低危", "低"})
        return f"共发现{total}个安全缺陷，其中严重漏洞{critical}个、高危{high}个、中危{medium}个、低危{low}个。"

    def _count_severity(self, severity_count: dict[str, object], names: set[str]) -> int:
        total = 0
        for severity, count in severity_count.items():
            if str(severity).lower() in names:
                total += int(count or 0)
        return total

    def _render_findings(self, html_mode: bool) -> str:
        if not self._findings:
            return '<p class="empty">未发现问题。</p>' if html_mode else "未发现问题。"
        block = self._default_finding_block(html_mode)
        return self._render_finding_loop_block(block, html_mode)

    def _render_finding_card(self, index: int, finding: dict[str, object], html_mode: bool = True) -> str:
        return self._render_finding_block(self._default_finding_block(html_mode), index, finding, html_mode)

    def _render_finding_loops(self, template: str, html_mode: bool) -> str:
        def replace(match: re.Match[str]) -> str:
            return self._render_finding_loop_block(match.group(1), html_mode)

        return FINDING_LOOP_PATTERN.sub(replace, template)

    def _render_finding_loop_block(self, block: str, html_mode: bool) -> str:
        if not self._findings:
            return '<p class="empty">未发现问题。</p>' if html_mode else "未发现问题。"
        return "\n".join(
            self._render_finding_block(block, index, finding, html_mode)
            for index, finding in enumerate(self._findings, 1)
        )

    def _render_finding_block(self, block: str, index: int, finding: dict[str, object], html_mode: bool) -> str:
        rendered = block
        for symbol, value in self._finding_template_values(index, finding, html_mode).items():
            rendered = rendered.replace(symbol, value)
        return rendered

    def _finding_template_values(self, index: int, finding: dict[str, object], html_mode: bool) -> dict[str, str]:
        payload = self._finding_payload(index, finding)
        values = {
            "{{ finding_id }}": str(payload["id"]),
            "{{ rule_id }}": str(payload["ruleId"]),
            "{{ risk_level }}": str(payload["severity"]),
            "{{ risk_class }}": str(payload["riskClass"]),
            "{{ issue_summary }}": str(payload["summary"]),
            "{{ vulnerability_location }}": str(payload["location"]),
            "{{ data_flow }}": str(payload["dataFlow"]),
            "{{ evidence_code }}": self._code_snippet(index, finding, html_mode) if self._report_include_code_snippet else "",
            "{{ highlighted_code }}": self._code_snippet(index, finding, html_mode) if self._report_include_code_snippet else "",
            "{{ ai_analysis }}": self._ai_analysis_markup(index, html_mode),
        }
        html_safe_symbols = {"{{ evidence_code }}", "{{ highlighted_code }}", "{{ ai_analysis }}"}
        if html_mode:
            return {symbol: value if symbol in html_safe_symbols else html.escape(value) for symbol, value in values.items()}
        return values

    def _finding_payload(self, index: int, finding: dict[str, object]) -> dict[str, object]:
        severity = str(finding.get("severity", "未知"))
        return {
            "id": f"{index:03d}",
            "ruleId": str(finding.get("ruleId", "未知")),
            "ruleName": str(finding.get("ruleName", "未知规则")),
            "severity": severity,
            "riskClass": self._severity_class(severity),
            "summary": str(finding.get("description", "")),
            "location": self._finding_location(finding),
            "dataFlow": self._finding_data_flow(finding),
            "match": str(finding.get("match", "")),
            "file": str(finding.get("file", "")),
            "line": int(finding.get("line") or 0),
            "aiAnalysis": str(finding.get("aiAnalysis", "")),
        }

    def _default_finding_block(self, html_mode: bool) -> str:
        if html_mode:
            return (
                '<article class="finding risk-{{ risk_class }}">'
                '<div class="finding-header">'
                '<div><h2>Finding {{ finding_id }}</h2></div>'
                '</div>'
                '<div class="finding-body">'
                '<p class="finding-line"><strong>规则 ID：</strong>{{ rule_id }} <strong>风险等级：</strong>{{ risk_level }}</p>'
                '<p class="finding-summary"><strong>问题概述：</strong>{{ issue_summary }}</p>'
                '<p class="finding-location"><strong>漏洞位置：</strong>{{ vulnerability_location }}</p>'
                '<p class="finding-flow"><strong>传递链路：</strong>{{ data_flow }}</p>'
                '{{ evidence_code }}'
                '{{ ai_analysis }}'
                '</div>'
                '</article>'
            )
        return (
            "### Finding {{ finding_id }}\n\n"
            "- **规则 ID**: {{ rule_id }}  **风险等级**: {{ risk_level }}\n"
            "- **问题概述**: {{ issue_summary }}\n\n"
            "- **漏洞位置**: {{ vulnerability_location }}\n"
            "- **传递链路**: {{ data_flow }}\n\n"
            "{{ evidence_code }}\n"
            "{{ ai_analysis }}\n"
        )

    def _ai_analysis_markup(self, index: int, html_mode: bool) -> str:
        if index <= 0 or index > len(self._findings):
            return ""
        content = str(self._findings[index - 1].get("aiAnalysis", "")).strip()
        if not content:
            return ""
        if html_mode:
            return f'<p class="finding-ai"><strong>AI 分析：</strong>{html.escape(content).replace(chr(10), "<br>")}</p>'
        return f"**AI 分析**: {content}"

    def _finding_location(self, finding: dict[str, object]) -> str:
        file_name = str(finding.get("file") or "")
        line = int(finding.get("line") or 0)
        if not file_name:
            return ""
        if line <= 0:
            return file_name.replace("\\", "/")

        path = Path(str(finding.get("absolutePath", "")))
        end = line
        if path.is_file():
            try:
                lines = FileModule.read_file_with_encoding(path).splitlines()
                ranges = self._evidence_ranges(lines, line, finding)
                end = ranges[-1][1] if ranges else line
            except OSError:
                end = line
        suffix = f":{line}" if end == line else f":{line}-{end}"
        normalized_file = file_name.replace("\\", "/")
        return f"/{normalized_file}{suffix}"

    def _finding_data_flow(self, finding: dict[str, object]) -> str:
        details = finding.get("details", {})
        sources = details.get("sources", []) if isinstance(details, dict) else []
        transforms = details.get("transforms", []) if isinstance(details, dict) else []
        match = str(finding.get("match") or "").strip()
        parts = [str(item) for item in sources if self._is_report_flow_token(str(item))]
        parts.extend(str(item) for item in transforms if self._is_report_flow_token(str(item)))
        if parts and match:
            parts.append(match)
        if parts:
            return " -> ".join(self._dedupe_flow_parts(parts))
        rule_id = str(finding.get("ruleId") or "静态规则")
        return f"{rule_id} 静态规则匹配 -> {match}" if match else f"{rule_id} 静态规则匹配"

    def _is_report_flow_token(self, token: str) -> bool:
        token = token.strip()
        return bool(token and token not in {"dynamic-sql-template"} and not token.startswith("dangerous:"))

    def _dedupe_flow_parts(self, parts: list[str]) -> list[str]:
        unique: list[str] = []
        for part in parts:
            if part not in unique:
                unique.append(part)
        return unique

    def _render_code_snippets(self, html_mode: bool) -> str:
        if not self._report_include_code_snippet or not self._findings:
            return ""
        snippets = [self._code_snippet(index, finding, html_mode) for index, finding in enumerate(self._findings, 1)]
        snippets = [snippet for snippet in snippets if snippet]
        if not snippets:
            return ""
        if html_mode:
            return '<section class="snippets"><h2>高亮代码片段</h2>' + "".join(snippets) + "</section>"
        return "## 高亮代码片段\n\n" + "\n\n".join(snippets)

    def _code_snippet(self, index: int, finding: dict[str, object], html_mode: bool) -> str:
        absolute_path = str(finding.get("absolutePath", "")).strip()
        if not absolute_path:
            return ""
        path = Path(absolute_path)
        line = int(finding.get("line") or 0)
        if not path.is_file() or line <= 0:
            return ""
        try:
            lines = FileModule.read_file_with_encoding(path).splitlines()
        except OSError:
            return ""
        evidence_lines = self._evidence_line_numbers(lines, line, finding)
        ranges = self._merge_line_windows(sorted(evidence_lines), len(lines))
        selected: list[tuple[int | None, str]] = []
        for index_range, (start, end) in enumerate(ranges):
            if index_range > 0:
                selected.append((None, "..."))
            selected.extend((number, lines[number - 1]) for number in range(start, end + 1))
        language = self._snippet_language_name(path)
        if html_mode:
            body = []
            for number, content in selected:
                if number is None:
                    body.append(f'<span class="gap">{html.escape(content)}</span>')
                    continue
                klass = ' class="hit"' if number in evidence_lines else ""
                body.append(f'<span{klass}><b>{number:>4}</b> {html.escape(content)}</span>')
            return f'<div class="code-card"><pre>{"<br>".join(body)}</pre></div>'
        body = []
        for number, content in selected:
            if number is None:
                body.append("  ...")
                continue
            marker = ">" if number in evidence_lines else " "
            body.append(f"{marker} {number:>4}: {content}")
        return f"```{language}\n" + "\n".join(body) + "\n```"

    def _evidence_ranges(self, lines: list[str], line: int, finding: dict[str, object]) -> list[tuple[int, int]]:
        evidence_lines = self._evidence_line_numbers(lines, line, finding)
        return self._merge_line_windows(sorted(evidence_lines), len(lines))

    def _evidence_line_numbers(self, lines: list[str], line: int, finding: dict[str, object]) -> set[int]:
        evidence_lines = {line}
        for token in self._evidence_tokens(finding):
            token_lines = self._find_token_lines(lines, token)
            if len(token_lines) == 1:
                evidence_lines.update(token_lines)
        return evidence_lines

    def _evidence_tokens(self, finding: dict[str, object]) -> list[str]:
        details = finding.get("details", {})
        tokens: list[str] = []
        if isinstance(details, dict):
            for key in ("sources", "transforms"):
                values = details.get(key, [])
                if isinstance(values, list):
                    tokens.extend(str(value) for value in values)
        match = str(finding.get("match") or "")
        if match:
            tokens.append(match)
        return [token.strip() for token in tokens if self._is_specific_evidence_token(token)]

    def _is_specific_evidence_token(self, token: str) -> bool:
        token = token.strip()
        if not token:
            return False
        if re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", token):
            return False
        if token in {"$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "$_SERVER", "$_FILES"}:
            return False
        if token in {"dynamic-sql-template"}:
            return False
        if token.startswith("dangerous:"):
            return False
        return True

    def _find_token_lines(self, lines: list[str], token: str) -> set[int]:
        if len(token) > 120 or "\n" in token:
            return set()
        compact_token = re.sub(r"\s+", "", token)
        found: set[int] = set()
        for number, content in enumerate(lines, 1):
            if token in content or (compact_token and compact_token in re.sub(r"\s+", "", content)):
                found.add(number)
        return found

    def _merge_line_windows(self, evidence_lines: list[int], total_lines: int) -> list[tuple[int, int]]:
        windows = []
        for number in evidence_lines:
            if number <= 0:
                continue
            windows.append((max(1, number - 2), min(total_lines, number + 2)))
        if not windows:
            return []
        windows.sort()
        merged = [windows[0]]
        for start, end in windows[1:]:
            prev_start, prev_end = merged[-1]
            if start <= prev_end + 1:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))
        return merged[:4]

    def _snippet_language_name(self, path: Path) -> str:
        return {
            ".php": "php",
            ".py": "python",
            ".java": "java",
            ".lua": "lua",
            ".go": "go",
            ".js": "javascript",
            ".ts": "typescript",
            ".html": "html",
            ".css": "css",
        }.get(path.suffix.lower(), "")

    def _severity_class(self, severity: str) -> str:
        value = severity.lower()
        if value in {"critical", "严重", "致命"}:
            return "critical"
        if value in {"high", "高危", "高"}:
            return "high"
        if value in {"medium", "中危", "中"}:
            return "medium"
        if value in {"low", "低危", "低"}:
            return "low"
        return "info"

    def _build_text_report(self) -> str:
        payload = self._report_payload()
        lines = [
            str(payload["title"]),
            f"项目: {payload['projectPath']}",
            f"日期: {payload['date']}",
        ]
        if self._report_include_summary:
            lines.append("执行摘要")
            lines.append(str(payload["overview"]))
        lines.append("")
        for finding in payload["findings"]:
            lines.append(f"Finding {finding['id']}")
            lines.append(f"  规则 ID: {finding['ruleId']}  风险等级: {finding['severity']}")
            lines.append(f"  漏洞位置: {finding['location']}")
            lines.append(f"  传递链路: {finding['dataFlow']}")
            lines.append(f"  问题概述: {finding['summary']}")
            if finding.get("aiAnalysis"):
                lines.append(f"  AI 分析: {finding['aiAnalysis']}")
            lines.append("")
        if not payload["findings"]:
            lines.append("未发现问题。")
        return "\n".join(lines)
