from __future__ import annotations

import html
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, QSettings, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument

from modules.file_module import FileModule
from modules.generic_rule_engine import GenericRuleEngine
from pinesawfly.syntax_highlighter import highlight_code, parser_for

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".php", ".py", ".java", ".lua", ".go", ".js", ".ts", ".html", ".css"}
SCAN_EXTENSIONS = {".php", ".py", ".java"}
IGNORED_DIRS = {".git", ".venv", ".codegraph", "__pycache__", ".mypy_cache", ".pytest_cache"}
SNIPPET_LANGUAGES = {
    ".php": "php",
    ".py": "python",
    ".java": "java",
    ".lua": "lua",
    ".go": "go",
}
SNIPPET_SCOPE_NODES = {
    "assignment_expression",
    "class_declaration",
    "class_definition",
    "constructor_declaration",
    "expression_statement",
    "for_statement",
    "foreach_statement",
    "function_declaration",
    "function_definition",
    "if_statement",
    "interface_declaration",
    "local_function",
    "method_declaration",
    "method_definition",
    "switch_statement",
    "trait_declaration",
    "try_statement",
    "while_statement",
}
REPORT_SYMBOLS = [
    "{{ title }}",
    "{{ logo }}",
    "{{ author }}",
    "{{ project_path }}",
    "{{ generated_at }}",
    "{{ overview }}",
    "{{ findings }}",
    "{{ affected_locations }}",
    "{{ highlighted_code_snippets }}",
]


def normalize_path(path_or_url: str) -> str:
    if path_or_url.startswith("file:"):
        return QUrl(path_or_url).toLocalFile()
    return path_or_url


class ScanWorker(QObject):
    finished = Signal(list, int, str)
    failed = Signal(str)

    def __init__(self, project_path: str) -> None:
        super().__init__()
        self.project_path = project_path

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
            if any(part in IGNORED_DIRS for part in file_path.parts):
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
            if not php_plugin.initialize():
                return
            for php_file in project.rglob("*.php"):
                if any(part in IGNORED_DIRS for part in php_file.parts):
                    continue
                for vuln in php_plugin.scan(str(php_file)):
                    results.append(self._normalize_vuln(project, php_file, vuln))
        except Exception:
            logger.exception("plugin scan failed")

    def _dedupe_results(self, results: list[dict[str, object]]) -> list[dict[str, object]]:
        seen: set[tuple[object, ...]] = set()
        unique: list[dict[str, object]] = []
        for result in results:
            key = (
                result.get("ruleId"),
                result.get("absolutePath"),
                result.get("line"),
                result.get("match"),
                result.get("description"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
        return unique

    def _normalize_vuln(self, project: Path, file_path: Path, vuln: dict) -> dict[str, object]:
        return {
            "ruleId": vuln.get("rule_id", "未知"),
            "ruleName": vuln.get("rule_name", "未知规则"),
            "severity": vuln.get("severity", "未知"),
            "file": str(file_path.relative_to(project)),
            "line": int(vuln.get("line") or 0),
            "description": vuln.get("description", ""),
            "match": vuln.get("match", ""),
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
        self._report_title = self._settings.value("report/title", "PineSawFly 审计报告", str)
        self._report_author = self._settings.value("report/author", "", str)
        self._report_template_format = "Markdown"
        self._report_template_content = self._load_report_template(self._report_template_format)
        self._report_include_project_path = self._settings.value("report/includeProjectPath", True, bool)
        self._report_include_generated_at = self._settings.value("report/includeGeneratedAt", True, bool)
        self._report_include_summary = self._settings.value("report/includeSummary", True, bool)
        self._report_include_logo = self._settings.value("report/includeLogo", True, bool)
        self._report_include_affected_location = self._settings.value("report/includeAffectedLocation", True, bool)
        self._report_include_code_snippet = self._settings.value("report/includeCodeSnippet", True, bool)
        self._report_include_evidence = self._settings.value("report/includeEvidence", True, bool)
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
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
        self._files = self._collect_files(self._project_path)
        self.projectPathChanged.emit()
        self.filesChanged.emit()
        self._set_status(f"已打开项目: {self._project_path}")

    def _collect_files(self, project_path: str) -> list[dict[str, object]]:
        root = Path(project_path)
        files: list[dict[str, object]] = []
        for item in sorted(root.rglob("*")):
            if any(part in IGNORED_DIRS for part in item.parts):
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
        self._worker = ScanWorker(self._project_path)
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
        self._set_status("AI 分析入口已预留，当前尚未配置 AI 分析后端")

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
        value = value.strip() or "PineSawFly 审计报告"
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
    def setReportIncludeAffectedLocation(self, value: bool) -> None:
        if value != self._report_include_affected_location:
            self._report_include_affected_location = value
            self._settings.setValue("report/includeAffectedLocation", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeCodeSnippet(self, value: bool) -> None:
        if value != self._report_include_code_snippet:
            self._report_include_code_snippet = value
            self._settings.setValue("report/includeCodeSnippet", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeEvidence(self, value: bool) -> None:
        if value != self._report_include_evidence:
            self._report_include_evidence = value
            self._settings.setValue("report/includeEvidence", value)
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

    def get_report_include_affected_location(self) -> bool:
        return self._report_include_affected_location

    def set_report_include_affected_location(self, value: bool) -> None:
        self.setReportIncludeAffectedLocation(value)

    def get_report_include_code_snippet(self) -> bool:
        return self._report_include_code_snippet

    def set_report_include_code_snippet(self, value: bool) -> None:
        self.setReportIncludeCodeSnippet(value)

    def get_report_include_evidence(self) -> bool:
        return self._report_include_evidence

    def set_report_include_evidence(self, value: bool) -> None:
        self.setReportIncludeEvidence(value)

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
    reportTemplateContent = Property(str, get_report_template_content, notify=reportSettingsChanged)
    reportTemplateSymbols = Property("QVariantList", get_report_template_symbols, constant=True)
    reportIncludeProjectPath = Property(bool, get_report_include_project_path, set_report_include_project_path, notify=reportSettingsChanged)
    reportIncludeGeneratedAt = Property(bool, get_report_include_generated_at, set_report_include_generated_at, notify=reportSettingsChanged)
    reportIncludeSummary = Property(bool, get_report_include_summary, set_report_include_summary, notify=reportSettingsChanged)
    reportIncludeLogo = Property(bool, get_report_include_logo, set_report_include_logo, notify=reportSettingsChanged)
    reportIncludeAffectedLocation = Property(bool, get_report_include_affected_location, set_report_include_affected_location, notify=reportSettingsChanged)
    reportIncludeCodeSnippet = Property(bool, get_report_include_code_snippet, set_report_include_code_snippet, notify=reportSettingsChanged)
    reportIncludeEvidence = Property(bool, get_report_include_evidence, set_report_include_evidence, notify=reportSettingsChanged)

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
        document = QTextDocument()
        document.setHtml(self._render_template("PDF"))
        document.print_(writer)

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
                "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>{{ title }}</title></head><body>"
                "<h1>{{ title }}</h1>{{ logo }}<p>{{ author }}</p><p>{{ project_path }}</p><p>{{ generated_at }}</p>"
                "{{ overview }}<h2>审计发现</h2>{{ findings }}{{ affected_locations }}{{ highlighted_code_snippets }}</body></html>"
            )
        return "# {{ title }}\n\n{{ logo }}\n\n{{ author }}\n\n{{ project_path }}\n\n{{ generated_at }}\n\n{{ overview }}\n\n## 审计发现\n\n{{ findings }}\n\n{{ affected_locations }}\n\n{{ highlighted_code_snippets }}\n"

    def _render_template(self, report_format: str) -> str:
        template = self._load_report_template(report_format)
        values = self._template_values(report_format in {"HTML", "PDF"})
        for symbol, value in values.items():
            template = template.replace(symbol, value)
        return template

    def _report_payload(self) -> dict[str, object]:
        return {
            "title": self._report_title,
            "projectPath": self._project_path,
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "summary": self._report_summary(),
            "findings": self._findings,
        }

    def _report_summary(self) -> dict[str, object]:
        severity_count: dict[str, int] = {}
        for finding in self._findings:
            severity = str(finding.get("severity", "未知"))
            severity_count[severity] = severity_count.get(severity, 0) + 1
        return {"total": len(self._findings), "severityCount": severity_count}

    def _template_values(self, html_mode: bool) -> dict[str, str]:
        payload = self._report_payload()
        return {
            "{{ title }}": html.escape(str(payload["title"])) if html_mode else str(payload["title"]),
            "{{ logo }}": self._render_logo(html_mode),
            "{{ author }}": self._render_author(html_mode),
            "{{ project_path }}": self._render_project_path(html_mode, str(payload["projectPath"])),
            "{{ generated_at }}": self._render_generated_at(html_mode, str(payload["generatedAt"])),
            "{{ overview }}": self._render_overview(html_mode, payload["summary"]),
            "{{ findings }}": self._render_findings(html_mode),
            "{{ affected_locations }}": self._render_affected_locations(html_mode),
            "{{ highlighted_code_snippets }}": self._render_code_snippets(html_mode),
        }

    def _render_logo(self, html_mode: bool) -> str:
        if not self._report_include_logo:
            return ""
        logo = self._app_root / "assets" / "icons" / "app.svg"
        if not logo.exists():
            logo = self._app_root / "assets" / "icons" / "app.ico"
        if not logo.exists():
            return ""
        logo_url = QUrl.fromLocalFile(str(logo)).toString()
        return f'<img class="logo" src="{html.escape(logo_url)}" alt="PineSawFly Logo">' if html_mode else f"![PineSawFly Logo]({logo.as_posix()})"

    def _render_author(self, html_mode: bool) -> str:
        if not self._report_author:
            return ""
        return self._metadata_span("作者", self._report_author, html_mode)

    def _render_project_path(self, html_mode: bool, project_path: str) -> str:
        if not self._report_include_project_path:
            return ""
        return self._metadata_span("项目路径", project_path, html_mode)

    def _render_generated_at(self, html_mode: bool, generated_at: str) -> str:
        if not self._report_include_generated_at:
            return ""
        return self._metadata_span("生成时间", generated_at, html_mode)

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
        if html_mode:
            stats = "".join(
                f'<span class="stat-badge {self._severity_class(str(severity))}">{html.escape(str(severity))}: {count}</span>'
                for severity, count in severity_count.items()
            )
            return (
                '<section class="summary">'
                "<h2>执行摘要</h2>"
                f"<p>本次扫描共发现 <strong>{summary.get('total', 0)}</strong> 个问题。请优先处理高危和可被用户输入触发的问题。</p>"
                f'<div class="stats"><span class="stat-badge total">总数: {summary.get("total", 0)}</span>{stats}</div>'
                "</section>"
            )
        lines = ["## 执行摘要", "", f"- 问题总数: {summary.get('total', 0)}"]
        lines.extend(f"- {severity}: {count}" for severity, count in severity_count.items())
        return "\n".join(lines)

    def _render_findings(self, html_mode: bool) -> str:
        if not self._findings:
            return '<p class="empty">未发现问题。</p>' if html_mode else "未发现问题。"
        if html_mode:
            return "".join(self._render_finding_card(index, finding) for index, finding in enumerate(self._findings, 1))
        lines: list[str] = []
        for index, finding in enumerate(self._findings, 1):
            evidence = self._finding_evidence(finding)
            lines.extend([
                f"### Finding {index:03d}: {finding.get('ruleName', '未知规则')}",
                "",
                f"- **规则 ID**: {finding.get('ruleId', '未知')}",
                f"- **风险等级**: {finding.get('severity', '未知')}",
                f"- **受影响位置**: {finding.get('file', '')}:{finding.get('line', 0)}",
                f"- **问题描述**: {finding.get('description', '')}",
            ])
            if self._report_include_evidence and evidence:
                lines.extend(["", "**匹配证据**", "", "```", evidence, "```"])
            lines.append("")
        return "\n".join(lines)

    def _render_finding_card(self, index: int, finding: dict[str, object]) -> str:
        severity = str(finding.get("severity", "未知"))
        location = f"{finding.get('file', '')}:{finding.get('line', 0)}"
        evidence = self._finding_evidence(finding)
        evidence_block = ""
        if self._report_include_evidence and evidence:
            evidence_block = f'<div class="finding-section"><h3>匹配证据</h3><pre>{html.escape(evidence)}</pre></div>'
        return (
            f'<article class="finding risk-{self._severity_class(severity)}">'
            '<div class="finding-header">'
            f'<div><div class="finding-kicker">Finding {index:03d}</div>'
            f'<h2>{html.escape(str(finding.get("ruleName", "未知规则")))}</h2></div>'
            f'<span class="risk-tag">{html.escape(severity)}</span>'
            "</div>"
            '<div class="finding-body">'
            '<dl class="finding-meta">'
            f'<div><dt>规则 ID</dt><dd>{html.escape(str(finding.get("ruleId", "未知")))}</dd></div>'
            f'<div><dt>受影响位置</dt><dd>{html.escape(location)}</dd></div>'
            "</dl>"
            f'<div class="finding-section"><h3>问题描述</h3><p>{html.escape(str(finding.get("description", "")))}</p></div>'
            f"{evidence_block}"
            "</div>"
            "</article>"
        )

    def _render_affected_locations(self, html_mode: bool) -> str:
        if not self._report_include_affected_location or not self._findings:
            return ""
        if html_mode:
            items = "".join(
                f"<li>{html.escape(str(finding.get('file', '')))}:{html.escape(str(finding.get('line', 0)))}</li>"
                for finding in self._findings
            )
            return f'<section class="affected"><h2>受影响代码位置</h2><ul>{items}</ul></section>'
        lines = ["## 受影响代码位置", ""]
        lines.extend(f"- {finding.get('file', '')}:{finding.get('line', 0)}" for finding in self._findings)
        return "\n".join(lines)

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
        path = Path(str(finding.get("absolutePath", "")))
        line = int(finding.get("line") or 0)
        if not path.exists() or line <= 0:
            return ""
        try:
            lines = FileModule.read_file_with_encoding(path).splitlines()
        except OSError:
            return ""
        start, end = self._snippet_range(path, lines, line)
        selected = [(number, lines[number - 1]) for number in range(start, end + 1)]
        language = self._snippet_language_name(path)
        title = f"Finding {index:03d} - {finding.get('file', path.name)}:{line}"
        if html_mode:
            body = []
            for number, content in selected:
                klass = ' class="hit"' if number == line else ""
                body.append(f'<span{klass}><b>{number:>4}</b> {html.escape(content)}</span>')
            return f'<div class="code-card"><h3>{html.escape(title)}</h3><pre>{"<br>".join(body)}</pre></div>'
        body = []
        for number, content in selected:
            marker = ">" if number == line else " "
            body.append(f"{marker} {number:>4}: {content}")
        return f"### {title}\n\n```{language}\n" + "\n".join(body) + "\n```"

    def _snippet_range(self, path: Path, lines: list[str], line: int) -> tuple[int, int]:
        language = SNIPPET_LANGUAGES.get(path.suffix.lower())
        if not language:
            return self._fallback_snippet_range(lines, line)
        try:
            content = "\n".join(lines)
            source = content.encode("utf-8", errors="replace")
            parser_language = "php" if language == "php" and "<?" in content else ("php_only" if language == "php" else language)
            tree = parser_for(parser_language).parse(source)
            node = self._smallest_node_at_line(tree.root_node, line - 1)
            scoped = self._best_snippet_node(node)
            if scoped is not None:
                start = max(1, scoped.start_point[0] + 1)
                end = min(len(lines), scoped.end_point[0] + 1)
                if 1 <= end - start <= 90:
                    return start, end
        except Exception:
            logger.debug("tree-sitter snippet range failed for %s", path, exc_info=True)
        return self._fallback_snippet_range(lines, line)

    def _smallest_node_at_line(self, node: Any, row: int) -> Any | None:
        if node.start_point[0] > row or node.end_point[0] < row:
            return None
        for child in node.children:
            found = self._smallest_node_at_line(child, row)
            if found is not None:
                return found
        return node

    def _best_snippet_node(self, node: Any | None) -> Any | None:
        current = node
        fallback = node
        while current is not None:
            if current.type in SNIPPET_SCOPE_NODES:
                return current
            if current.end_point[0] - current.start_point[0] >= 1:
                fallback = current
            current = current.parent
        return fallback

    def _fallback_snippet_range(self, lines: list[str], line: int) -> tuple[int, int]:
        return max(1, line - 3), min(len(lines), line + 3)

    def _finding_evidence(self, finding: dict[str, object]) -> str:
        source_line = self._finding_source_line(finding)
        if source_line:
            return source_line
        return str(finding.get("match", "")).strip()

    def _finding_source_line(self, finding: dict[str, object]) -> str:
        path = Path(str(finding.get("absolutePath", "")))
        line = int(finding.get("line") or 0)
        if not path.exists() or line <= 0:
            return ""
        try:
            lines = FileModule.read_file_with_encoding(path).splitlines()
        except OSError:
            return ""
        if line > len(lines):
            return ""
        return lines[line - 1].rstrip()

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
            f"生成时间: {payload['generatedAt']}",
        ]
        if self._report_include_summary:
            lines.append(f"问题总数: {payload['summary']['total']}")
            for severity, count in payload["summary"]["severityCount"].items():
                lines.append(f"{severity}: {count}")
        lines.append("")
        for index, finding in enumerate(self._findings, 1):
            lines.append(f"Finding {index:03d}: [{finding.get('severity', '未知')}] {finding.get('ruleName', '未知规则')}")
            lines.append(f"  规则: {finding.get('ruleId', '未知')}")
            lines.append(f"  位置: {finding.get('file', '')}:{finding.get('line', 0)}")
            lines.append(f"  描述: {finding.get('description', '')}")
            evidence = self._finding_evidence(finding)
            if self._report_include_evidence and evidence:
                lines.append(f"  证据: {evidence}")
            lines.append("")
        if not self._findings:
            lines.append("未发现问题。")
        return "\n".join(lines)
