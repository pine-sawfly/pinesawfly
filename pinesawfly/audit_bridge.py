from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, Property, QThread, QUrl, Signal, Slot

from modules.file_module import FileModule
from modules.generic_rule_engine import GenericRuleEngine
from pinesawfly.syntax_highlighter import highlight_code

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".php", ".py", ".java", ".lua", ".go", ".js", ".ts", ".html", ".css"}
SCAN_EXTENSIONS = {".php", ".py", ".java"}
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache"}


def normalize_path(path_or_url: str) -> str:
    if path_or_url.startswith("file:"):
        return QUrl(path_or_url).toLocalFile()
    return path_or_url


class ScanWorker(QObject):
    finished = Signal(list, int, str)
    failed = Signal(str)

    def __init__(self, project_path: str, deep: bool) -> None:
        super().__init__()
        self.project_path = project_path
        self.deep = deep

    @Slot()
    def run(self) -> None:
        try:
            rows = self._run_scan()
            label = "??????" if self.deep else "????"
            self.finished.emit(rows, len(rows), f"{label}??? {len(rows)} ???")
        except Exception as exc:  # noqa: BLE001 - surface the error to QML
            logger.exception("scan failed")
            self.failed.emit(str(exc))

    def _run_scan(self) -> list[dict[str, object]]:
        project = Path(self.project_path)
        rule_engine = GenericRuleEngine()
        results: list[dict[str, object]] = []
        for file_path in project.rglob("*"):
            if any(part in IGNORED_DIRS for part in file_path.parts):
                continue
            if file_path.is_file() and file_path.suffix.lower() in SCAN_EXTENSIONS:
                for vuln in rule_engine.scan_file(str(file_path)):
                    results.append(self._normalize_vuln(project, file_path, vuln))
        if self.deep:
            self._append_plugin_results(project, results)
        return results

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
                for vuln in php_plugin.scan(str(php_file)):
                    results.append(self._normalize_vuln(project, php_file, vuln))
        except Exception:
            logger.exception("plugin scan failed")

    def _normalize_vuln(self, project: Path, file_path: Path, vuln: dict) -> dict[str, object]:
        return {
            "ruleId": vuln.get("rule_id", "??"),
            "ruleName": vuln.get("rule_name", "??"),
            "severity": vuln.get("severity", "??"),
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
    findingsChanged = Signal()
    statusChanged = Signal()
    scanningChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._project_path = os.getcwd()
        self._files: list[dict[str, object]] = []
        self._findings: list[dict[str, object]] = []
        self._current_file = ""
        self._current_content = "?????????????"
        self._current_highlighted_content = self._highlight_code(self._current_content, "")
        self._status = "??"
        self._scanning = False
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

    @Slot(str)
    def setProjectPath(self, path_or_url: str) -> None:
        path = normalize_path(path_or_url)
        if not path or not os.path.isdir(path):
            self._set_status(f"??????: {path}")
            return
        self._project_path = os.path.abspath(path)
        self._files = self._collect_files(self._project_path)
        self.projectPathChanged.emit()
        self.filesChanged.emit()
        self._set_status(f"?????: {self._project_path}")

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
            self.currentContentChanged.emit()
            self.currentHighlightedContentChanged.emit()
            self.currentFileChanged.emit()
            self._set_status(f"?????: {path}")
        except Exception as exc:  # noqa: BLE001 - message is shown in UI
            self._set_status(f"??????: {exc}")

    @Slot(str, int)
    def openFinding(self, file_path: str, line: int) -> None:
        self.openFile(file_path)
        if line:
            self._set_status(f"??? {file_path}:{line}")

    @Slot(bool)
    def startScan(self, deep: bool = False) -> None:
        if self._scanning:
            return
        self._set_scanning(True)
        self._set_status("????...")
        self._findings = []
        self.findingsChanged.emit()
        self._thread = QThread()
        self._worker = ScanWorker(self._project_path, deep)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.failed.connect(self._on_scan_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._cleanup_worker)
        self._thread.start()

    @Slot(list, int, str)
    def _on_scan_finished(self, findings: list, _count: int, message: str) -> None:
        self._findings = findings
        self.findingsChanged.emit()
        self._set_status(message)
        self._set_scanning(False)

    @Slot(str)
    def _on_scan_failed(self, message: str) -> None:
        self._set_status(f"????: {message}")
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

    def get_findings(self) -> list[dict[str, object]]:
        return self._findings

    def get_status(self) -> str:
        return self._status

    def get_scanning(self) -> bool:
        return self._scanning

    files = Property("QVariantList", get_files, notify=filesChanged)
    projectPath = Property(str, get_project_path, notify=projectPathChanged)
    currentFile = Property(str, get_current_file, notify=currentFileChanged)
    currentContent = Property(str, get_current_content, notify=currentContentChanged)
    currentHighlightedContent = Property(str, get_current_highlighted_content, notify=currentHighlightedContentChanged)
    findings = Property("QVariantList", get_findings, notify=findingsChanged)
    status = Property(str, get_status, notify=statusChanged)
    scanning = Property(bool, get_scanning, notify=scanningChanged)

    def _highlight_code(self, content: str, file_path: str) -> str:
        return highlight_code(content, file_path)
