from core.plugin_interface import PluginInterface
from typing import Any, Dict, List

class ExamplePlugin(PluginInterface):
    """
    示例插件实现
    """
    
    @property
    def name(self) -> str:
        return "example_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "示例插件，展示插件接口的实现"
    
    def initialize(self) -> bool:
        print(f"初始化插件: {self.name}")
        return True
    
    def execute(self, args: Dict[str, Any]) -> Any:
        print(f"执行插件: {self.name}，参数: {args}")
        return {"result": "success", "data": "示例数据"}
    
    def cleanup(self) -> None:
        print(f"清理插件: {self.name}")

# 创建插件实例
plugin = ExamplePlugin()

# 插件必须暴露 PluginInterface
PluginInterface = ExamplePlugin