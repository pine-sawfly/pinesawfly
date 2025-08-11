from abc import ABC, abstractmethod
from typing import Any, Dict, List

class PluginInterface(ABC):
    """
    所有插件必须实现的统一接口
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化插件
        返回: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        执行插件的主要功能
        参数: args - 执行参数
        返回: 执行结果
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        清理插件资源
        """
        pass

class ScannerPluginInterface(PluginInterface):
    """
    扫描器插件接口，继承自基础插件接口
    """
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """插件支持的语言列表"""
        pass
    
    @abstractmethod
    def scan(self, file_path: str, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        扫描文件
        参数: 
            file_path - 文件路径
            options - 扫描选项
        返回: 漏洞结果列表
        """
        pass
    
    @abstractmethod
    def get_rules(self) -> List[Dict[str, Any]]:
        """
        获取插件的规则列表
        返回: 规则列表
        """
        pass