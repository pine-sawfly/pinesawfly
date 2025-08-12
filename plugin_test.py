# import sys
# import os
# sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# from core.plugin_loader import PluginLoader
# from core.plugin_interface import PluginInterface
# import logging

# # 设置日志
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def test_plugin_system():
#     """
#     测试插件系统
#     """
#     print("=== 测试插件系统 ===")
    
#     # 创建插件加载器
#     plugin_loader = PluginLoader("plugins")
    
#     # 发现插件
#     print("\n1. 发现插件...")
#     plugins = plugin_loader.discover_plugins()
#     print(f"发现的插件: {plugins}")
    
#     # 加载所有插件
#     print("\n2. 加载插件...")
#     loaded_plugins = plugin_loader.load_all_plugins()
#     print(f"加载的插件: {list(loaded_plugins.keys())}")
    
#     # 测试每个插件
#     print("\n3. 测试插件功能...")
#     for plugin_name, plugin_module in loaded_plugins.items():
#         print(f"\n测试插件: {plugin_name}")
#         try:
#             # 检查插件是否实现了PluginInterface
#             if hasattr(plugin_module, 'PluginInterface'):
#                 # 创建插件实例
#                 plugin_class = plugin_module.PluginInterface
#                 plugin_instance = plugin_class()
                
#                 print(f"  插件名称: {plugin_instance.name}")
#                 print(f"  插件版本: {plugin_instance.version}")
#                 print(f"  插件描述: {plugin_instance.description}")
                
#                 # 测试初始化
#                 init_result = plugin_instance.initialize()
#                 print(f"  初始化结果: {init_result}")
                
#                 # 测试执行
#                 exec_result = plugin_instance.execute({"test": "data"})
#                 print(f"  执行结果: {exec_result}")
                
#                 # 测试清理
#                 plugin_instance.cleanup()
#                 print(f"  清理完成")
#             else:
#                 print(f"  插件 {plugin_name} 没有实现 PluginInterface")
#         except Exception as e:
#             print(f"  测试插件 {plugin_name} 时出错: {e}")
#             logging.exception(e)
    
#     # 测试获取特定插件
#     print("\n4. 测试获取特定插件...")
#     example_plugin = plugin_loader.get_plugin("example_plugin")
#     if example_plugin:
#         print(f"成功获取插件: example_plugin")
#     else:
#         print("未能获取插件: example_plugin")
    
#     print("\n=== 插件系统测试完成 ===")

# if __name__ == "__main__":
#     test_plugin_system()



import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins.php_plugin.php_plugin import PHPPlugin
import json

def test_php_plugin():
    """
    测试PHP插件功能
    """
    print("开始测试PHP插件...")
    
    # 创建插件实例
    plugin = PHPPlugin()
    
    # 测试插件属性
    print(f"插件名称: {plugin.name}")
    print(f"插件版本: {plugin.version}")
    print(f"插件描述: {plugin.description}")
    print(f"支持的语言: {plugin.supported_languages}")
    
    # 初始化插件
    print("\n初始化插件...")
    init_result = plugin.initialize()
    print(f"初始化结果: {init_result}")
    
    if not init_result:
        print("插件初始化失败，无法继续测试")
        return
    
    # 获取规则
    print("\n获取插件规则...")
    rules = plugin.get_rules()
    print(f"获取到 {len(rules)} 条规则")
    for rule in rules:
        print(f"  - {rule['id']}: {rule['name']} ({rule['severity']})")
    
    # 创建测试PHP文件
    test_php_content = '''<?php
// 测试PHP文件，包含一些常见的安全问题
$input = $_GET['input'];
eval($input);

$file = $_POST['file'];
include($file);

$cmd = $_REQUEST['cmd'];
system($cmd);

$data = $_COOKIE['data'];
unserialize($data);

echo "测试完成";
?>
'''
    
    # 写入测试文件
    with open('test_vuln.php', 'w', encoding='utf-8') as f:
        f.write(test_php_content)
    
    print("\n创建测试PHP文件: test_vuln.php")
    
    # 扫描测试文件
    print("\n扫描测试文件...")
    results = plugin.scan('test_vuln.php')
    
    print(f"\n扫描结果:")
    print(f"发现 {len(results)} 个问题")
    
    for result in results:
        print(f"\n问题类型: {result.get('type', 'Rule')}")
        print(f"规则ID: {result.get('rule_id')}")
        print(f"规则名称: {result.get('rule_name')}")
        print(f"严重程度: {result.get('severity')}")
        print(f"文件: {result.get('file')}")
        print(f"行号: {result.get('line')}")
        print(f"描述: {result.get('description')}")
    
    # 清理测试文件
    if os.path.exists('test_vuln.php'):
        os.remove('test_vuln.php')
        print("\n清理测试文件: test_vuln.php")
    
    # 清理插件资源
    plugin.cleanup()
    print("插件资源清理完成")

if __name__ == "__main__":
    test_php_plugin()