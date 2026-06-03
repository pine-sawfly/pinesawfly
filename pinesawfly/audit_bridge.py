from __future__ import annotations

import html
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QSettings, QThread, QUrl, Signal, Slot

from modules.file_module import FileModule
from modules.generic_rule_engine import GenericRuleEngine
from pinesawfly.syntax_highlighter import highlight_code

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".php", ".py", ".java", ".lua", ".go", ".js", ".ts", ".html", ".css"}
SCAN_EXTENSIONS = {".php", ".py", ".java"}
IGNORED_DIRS = {".git", ".venv", ".codegraph", "__pycache__", ".mypy_cache", ".pytest_cache"}


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
        except Exception as exc:  # noqa: BLE001 - surface the error to QML
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
            "ruleName": vuln.get("rule_name", "未知"),
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
        self._default_report_format = self._normalize_report_format(self._settings.value("report/defaultFormat", "Markdown", str))
        self._report_include_summary = self._settings.value("report/includeSummary", True, bool)
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
                files.append({"name": item.name, "relativePath": str(item.relative_to(root)), "absolutePath": str(item), "extension": item.suffix.lower().lstrip(".") or "file"})
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
        except Exception as exc:  # noqa: BLE001 - message is shown in UI
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
    def setDefaultReportFormat(self, value: str) -> None:
        value = self._normalize_report_format(value)
        if value != self._default_report_format:
            self._default_report_format = value
            self._settings.setValue("report/defaultFormat", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeSummary(self, value: bool) -> None:
        if value != self._report_include_summary:
            self._report_include_summary = value
            self._settings.setValue("report/includeSummary", value)
            self.reportSettingsChanged.emit()

    @Slot(bool)
    def setReportIncludeEvidence(self, value: bool) -> None:
        if value != self._report_include_evidence:
            self._report_include_evidence = value
            self._settings.setValue("report/includeEvidence", value)
            self.reportSettingsChanged.emit()

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

    def get_default_report_format(self) -> str:
        return self._default_report_format

    def set_default_report_format(self, value: str) -> None:
        self.setDefaultReportFormat(value)

    def get_report_include_summary(self) -> bool:
        return self._report_include_summary

    def set_report_include_summary(self, value: bool) -> None:
        self.setReportIncludeSummary(value)

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
    defaultReportFormat = Property(str, get_default_report_format, set_default_report_format, notify=reportSettingsChanged)
    reportIncludeSummary = Property(bool, get_report_include_summary, set_report_include_summary, notify=reportSettingsChanged)
    reportIncludeEvidence = Property(bool, get_report_include_evidence, set_report_include_evidence, notify=reportSettingsChanged)

    def _highlight_code(self, content: str, file_path: str) -> str:
        return highlight_code(content, file_path)

    def _normalize_report_format(self, value: str) -> str:
        value = (value or "Markdown").strip().lower()
        mapping = {"md": "Markdown", "markdown": "Markdown", "html": "HTML", "json": "JSON", "txt": "TXT", "text": "TXT"}
        return mapping.get(value, "Markdown")

    def _report_extension(self, report_format: str) -> str:
        return {"Markdown": ".md", "HTML": ".html", "JSON": ".json", "TXT": ".txt"}[report_format]

    def _build_report(self, report_format: str) -> str:
        if report_format == "JSON":
            return json.dumps(self._report_payload(), ensure_ascii=False, indent=2) + "\n"
        if report_format == "HTML":
            return self._build_html_report()
        if report_format == "TXT":
            return self._build_text_report()
        return self._build_markdown_report()

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
            severity = str(finding.get("severity", "Unknown"))
            severity_count[severity] = severity_count.get(severity, 0) + 1
        return {"total": len(self._findings), "severityCount": severity_count}

    def _build_markdown_report(self) -> str:
        payload = self._report_payload()
        lines = [
            f"# {payload['title']}",
            "",
            f"- 项目: {payload['projectPath']}",
            f"- 生成时间: {payload['generatedAt']}",
        ]
        if self._report_include_summary:
            lines.extend(["", "## 概览", "", f"- 问题总数: {payload['summary']['total']}"])
            for severity, count in payload["summary"]["severityCount"].items():
                lines.append(f"- {severity}: {count}")
        lines.extend(["", "## 发现", ""])
        if not self._findings:
            lines.append("未发现问题。")
        for index, finding in enumerate(self._findings, 1):
            lines.extend([
                f"### {index}. {finding.get('ruleName', '未知规则')}",
                "",
                f"- 规则: {finding.get('ruleId', '未知')}",
                f"- 风险: {finding.get('severity', '未知')}",
                f"- 位置: {finding.get('file', '')}:{finding.get('line', 0)}",
                f"- 描述: {finding.get('description', '')}",
            ])
            if self._report_include_evidence and finding.get("match"):
                lines.extend(["", "```", str(finding.get("match", "")), "```"])
            lines.append("")
        return "\n".join(lines)

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
            lines.append(f"{index}. [{finding.get('severity', '未知')}] {finding.get('ruleName', '未知规则')}")
            lines.append(f"   位置: {finding.get('file', '')}:{finding.get('line', 0)}")
            lines.append(f"   描述: {finding.get('description', '')}")
            if self._report_include_evidence and finding.get("match"):
                lines.append(f"   证据: {finding.get('match', '')}")
            lines.append("")
        if not self._findings:
            lines.append("未发现问题。")
        return "\n".join(lines)

    def _build_html_report(self) -> str:
        payload = self._report_payload()
        rows = []
        for finding in self._findings:
            evidence = ""
            if self._report_include_evidence and finding.get("match"):
                evidence = f"<pre>{html.escape(str(finding.get('match', '')))}</pre>"
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(finding.get('severity', '未知')))}</td>"
                f"<td>{html.escape(str(finding.get('ruleName', '未知规则')))}</td>"
                f"<td>{html.escape(str(finding.get('file', '')))}:{html.escape(str(finding.get('line', 0)))}</td>"
                f"<td>{html.escape(str(finding.get('description', '')))}{evidence}</td>"
                "</tr>"
            )
        summary = ""
        if self._report_include_summary:
            summary_items = "".join(f"<li>{html.escape(severity)}: {count}</li>" for severity, count in payload["summary"]["severityCount"].items())
            summary = f"<section><h2>概览</h2><p>问题总数: {payload['summary']['total']}</p><ul>{summary_items}</ul></section>"
        empty = "<p>未发现问题。</p>" if not rows else ""
        return (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(str(payload['title']))}</title>"
            "<style>body{font-family:Segoe UI,Microsoft YaHei,sans-serif;margin:32px;color:#1d1b20}"
            "table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #ddd;padding:10px;text-align:left;vertical-align:top}"
            "pre{white-space:pre-wrap;background:#f4f4f4;padding:10px;border-radius:8px}</style></head><body>"
            f"<h1>{html.escape(str(payload['title']))}</h1>"
            f"<p>项目: {html.escape(str(payload['projectPath']))}</p>"
            f"<p>生成时间: {html.escape(str(payload['generatedAt']))}</p>"
            f"{summary}<h2>发现</h2>{empty}<table><thead><tr><th>风险</th><th>规则</th><th>位置</th><th>描述</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
            "</body></html>"
        )
