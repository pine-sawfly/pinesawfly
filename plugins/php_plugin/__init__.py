import sys
import os

# 添加当前目录和父目录到Python路径
plugin_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(plugin_dir)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 导入插件类
from plugins.php_plugin.php_plugin import PHPPlugin

# 插件必须暴露 PluginInterface
PluginInterface = PHPPlugin