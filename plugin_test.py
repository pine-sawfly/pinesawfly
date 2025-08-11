import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from core.plugin_loader import PluginLoader
from core.plugin_interface import PluginInterface
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_plugin_system():
    """
    测试插件系统
    """
    print("=== 测试插件系统 ===")
    
    # 创建插件加载器
    plugin_loader = PluginLoader("plugins")
    
    # 发现插件
    print("\n1. 发现插件...")
    plugins = plugin_loader.discover_plugins()
    print(f"发现的插件: {plugins}")
    
    # 加载所有插件
    print("\n2. 加载插件...")
    loaded_plugins = plugin_loader.load_all_plugins()
    print(f"加载的插件: {list(loaded_plugins.keys())}")
    
    # 测试每个插件
    print("\n3. 测试插件功能...")
    for plugin_name, plugin_module in loaded_plugins.items():
        print(f"\n测试插件: {plugin_name}")
        try:
            # 检查插件是否实现了PluginInterface
            if hasattr(plugin_module, 'PluginInterface'):
                # 创建插件实例
                plugin_class = plugin_module.PluginInterface
                plugin_instance = plugin_class()
                
                print(f"  插件名称: {plugin_instance.name}")
                print(f"  插件版本: {plugin_instance.version}")
                print(f"  插件描述: {plugin_instance.description}")
                
                # 测试初始化
                init_result = plugin_instance.initialize()
                print(f"  初始化结果: {init_result}")
                
                # 测试执行
                exec_result = plugin_instance.execute({"test": "data"})
                print(f"  执行结果: {exec_result}")
                
                # 测试清理
                plugin_instance.cleanup()
                print(f"  清理完成")
            else:
                print(f"  插件 {plugin_name} 没有实现 PluginInterface")
        except Exception as e:
            print(f"  测试插件 {plugin_name} 时出错: {e}")
            logging.exception(e)
    
    # 测试获取特定插件
    print("\n4. 测试获取特定插件...")
    example_plugin = plugin_loader.get_plugin("example_plugin")
    if example_plugin:
        print(f"成功获取插件: example_plugin")
    else:
        print("未能获取插件: example_plugin")
    
    print("\n=== 插件系统测试完成 ===")

if __name__ == "__main__":
    test_plugin_system()