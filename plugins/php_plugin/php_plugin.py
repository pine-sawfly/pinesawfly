from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from core.exception_handler import safe_operation
from core.plugin_interface import ScannerPluginInterface

from .taint_analyzer import TaintAnalyzer
from .route_auth_analyzer import ProjectContext, ProjectContextBuilder, RouteAuthAnalyzer

if TYPE_CHECKING:
    from .php_parser import PHPParser

logger = logging.getLogger(__name__)


class PHPPlugin(ScannerPluginInterface):
    def __init__(self):
        self._name = "php_plugin"
        self._version = "1.0.0"
        self._description = "PHP 代码审计插件，支持 AST 解析和污点分析"
        self._supported_languages = ["php"]
        self.parser: PHPParser | None = None
        self.taint_analyzer: TaintAnalyzer | None = None
        self.project_context: ProjectContext | None = None
        self.route_auth_analyzer: RouteAuthAnalyzer | None = None
        self.initialized = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def supported_languages(self) -> list[str]:
        return self._supported_languages

    def initialize(self, project_path: str | None = None) -> bool:
        try:
            from .php_parser import PHPParser

            self.parser = PHPParser()
            self.taint_analyzer = TaintAnalyzer()
            self.project_context = ProjectContextBuilder().build(project_path)
            self.route_auth_analyzer = RouteAuthAnalyzer(self.project_context)
            self.initialized = True
            logger.info("PHP 插件 %s 初始化成功", self.name)
            return True
        except Exception as exc:
            logger.error("PHP 插件初始化失败: %s", exc)
            self.initialized = False
            return False

    @safe_operation
    def execute(self, args: dict[str, Any]) -> Any:
        if not self.initialized:
            logger.error("插件未初始化")
            return {"result": "error", "message": "插件未初始化"}

        file_path = args.get("file_path")
        if not file_path:
            logger.error("缺少文件路径参数")
            return {"result": "error", "message": "缺少文件路径参数"}

        return {"result": "success", "data": self.scan(file_path)}

    @safe_operation
    def scan(self, file_path: str, options: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self.initialized or not self.parser or not self.taint_analyzer:
            logger.error("插件未初始化")
            return []

        try:
            logger.info("开始扫描文件: %s", file_path)
            ast = self.parser.parse_file(file_path)
            results = self.taint_analyzer.analyze(ast, file_path)
            if self.route_auth_analyzer:
                results.extend(self.route_auth_analyzer.analyze(ast, file_path))
            logger.info("文件 %s 扫描完成，发现 %s 个问题", file_path, len(results))
            return results
        except Exception as exc:
            logger.error("扫描文件 %s 时出错: %s", file_path, exc)
            return []

    def get_rules(self) -> list[dict[str, Any]]:
        return []

    def cleanup(self) -> None:
        logger.info("清理插件 %s 的资源", self.name)
