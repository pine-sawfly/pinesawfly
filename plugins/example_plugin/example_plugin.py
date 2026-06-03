from __future__ import annotations

from typing import Any

from core.plugin_interface import PluginInterface


class ExamplePlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "example_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "示例插件"

    def initialize(self) -> bool:
        return True

    def execute(self, args: dict[str, Any]) -> Any:
        return {"result": "success", "data": args}

    def cleanup(self) -> None:
        pass


plugin = ExamplePlugin()
PluginInterface = ExamplePlugin
