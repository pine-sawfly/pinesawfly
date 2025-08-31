from core.plugin_interface import ScannerPluginInterface
from core.exception_handler import safe_operation
from typing import Any, Dict, List
from .php_parser import PHPParser
from .taint_analyzer import TaintAnalyzer
import logging

logger = logging.getLogger(__name__)

class PHPPlugin(ScannerPluginInterface):
    """
    PHP代码审计插件
    """
    
    def __init__(self):
        self._name = "php_plugin"
        self._version = "1.0.0"
        self._description = "PHP代码审计插件，支持AST解析和污点分析"
        self._supported_languages = ["php"]
        self.parser = None
        self.taint_analyzer = None
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
    def supported_languages(self) -> List[str]:
        return self._supported_languages
    
    def initialize(self) -> bool:
        """
        初始化PHP插件
        """
        try:
            self.parser = PHPParser()
            self.taint_analyzer = TaintAnalyzer()
            self.initialized = True
            logger.info(f"PHP插件 {self.name} 初始化成功")
            return True
        except Exception as e:
            logger.error(f"PHP插件初始化失败: {str(e)}")
            self.initialized = False
            return False
    
    @safe_operation
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        执行插件主要功能
        """
        if not self.initialized:
            logger.error("插件未初始化")
            return {"result": "error", "message": "插件未初始化"}
        
        file_path = args.get("file_path")
        if not file_path:
            logger.error("缺少文件路径参数")
            return {"result": "error", "message": "缺少文件路径参数"}
        
        # 扫描文件
        results = self.scan(file_path)
        return {"result": "success", "data": results}
    
    @safe_operation
    def scan(self, file_path: str, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        扫描PHP文件（只使用AST分析和污点分析，不使用规则引擎）
        """
        if not self.initialized:
            logger.error("插件未初始化")
            return []
        
        try:
            logger.info(f"开始扫描文件: {file_path}")
            
            # 解析PHP文件
            ast = self.parser.parse_file(file_path)
            
            # 使用污点分析扫描（移除了规则引擎扫描）
            taint_results = self.taint_analyzer.analyze(ast, file_path)
            
            logger.info(f"文件 {file_path} 扫描完成，发现 {len(taint_results)} 个问题")
            return taint_results
            
        except Exception as e:
            logger.error(f"扫描文件 {file_path} 时出错: {str(e)}")
            return []
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """
        获取插件的规则列表
        """
        return []
    
    def cleanup(self) -> None:
        """
        清理插件资源
        """
        logger.info(f"清理插件 {self.name} 的资源")
