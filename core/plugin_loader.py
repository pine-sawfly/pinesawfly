from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


class PluginLoader:
    def __init__(self, plugin_directory: str = "plugins"):
        self.plugin_directory = Path(plugin_directory)
        self.plugins: dict[str, ModuleType] = {}
        self.logger = logging.getLogger(__name__)

    def discover_plugins(self) -> list[str]:
        if not self.plugin_directory.exists():
            self.logger.warning("插件目录 %s 不存在", self.plugin_directory)
            return []

        return [
            item.name
            for item in self.plugin_directory.iterdir()
            if item.is_dir() and not item.name.startswith("__") and (item / "__init__.py").exists()
        ]

    def load_plugin(self, plugin_name: str) -> ModuleType | None:
        plugin_path = self.plugin_directory / plugin_name / "__init__.py"
        if not plugin_path.exists():
            self.logger.error("插件 %s 不存在: %s", plugin_name, plugin_path)
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                plugin_name,
                plugin_path,
                submodule_search_locations=[str(plugin_path.parent)],
            )
            if not spec or not spec.loader:
                self.logger.error("插件 %s 加载配置无效", plugin_name)
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
            if not hasattr(module, "PluginInterface"):
                self.logger.warning("插件 %s 未暴露 PluginInterface", plugin_name)

            self.plugins[plugin_name] = module
            self.logger.info("插件 %s 加载完成", plugin_name)
            return module
        except Exception as exc:
            self.logger.error("插件 %s 加载失败: %s", plugin_name, exc)
            return None

    def load_all_plugins(self) -> dict[str, ModuleType]:
        for plugin_name in self.discover_plugins():
            self.load_plugin(plugin_name)
        return self.plugins

    def get_plugin(self, plugin_name: str) -> ModuleType | None:
        return self.plugins.get(plugin_name)

    def unload_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self.plugins:
            return False
        del self.plugins[plugin_name]
        self.logger.info("插件 %s 已卸载", plugin_name)
        return True
