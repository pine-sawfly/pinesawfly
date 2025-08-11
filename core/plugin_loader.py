import os
import importlib.util
from typing import Dict, Any, List
import logging

class PluginLoader:
    """
    动态加载插件的核心类
    """
    def __init__(self, plugin_directory: str = "plugins"):
        self.plugin_directory = plugin_directory
        self.plugins: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def discover_plugins(self) -> List[str]:
        """
        发现所有可用的插件
        """
        plugins = []
        if not os.path.exists(self.plugin_directory):
            self.logger.warning(f"Plugin directory {self.plugin_directory} does not exist")
            return plugins
            
        for item in os.listdir(self.plugin_directory):
            item_path = os.path.join(self.plugin_directory, item)
            if os.path.isdir(item_path) and not item.startswith('__'):
                # 检查插件目录中是否有 __init__.py 文件
                if os.path.exists(os.path.join(item_path, '__init__.py')):
                    plugins.append(item)
        return plugins
    
    def load_plugin(self, plugin_name: str) -> Any:
        """
        动态加载单个插件
        """
        try:
            plugin_path = os.path.join(self.plugin_directory, plugin_name, '__init__.py')
            if not os.path.exists(plugin_path):
                self.logger.error(f"Plugin {plugin_name} not found at {plugin_path}")
                return None
                
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查插件是否实现了必要的接口
            if not hasattr(module, 'PluginInterface'):
                self.logger.warning(f"Plugin {plugin_name} does not implement PluginInterface")
            
            self.plugins[plugin_name] = module
            self.logger.info(f"Successfully loaded plugin: {plugin_name}")
            return module
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {str(e)}")
            return None
    
    def load_all_plugins(self) -> Dict[str, Any]:
        """
        加载所有发现的插件
        """
        plugin_names = self.discover_plugins()
        for plugin_name in plugin_names:
            self.load_plugin(plugin_name)
        return self.plugins
    
    def get_plugin(self, plugin_name: str) -> Any:
        """
        获取已加载的插件
        """
        return self.plugins.get(plugin_name)
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        """
        if plugin_name in self.plugins:
            del self.plugins[plugin_name]
            self.logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
        return False