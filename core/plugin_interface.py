from abc import ABC, abstractmethod
from typing import Any, Dict, List


class PluginInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass


class ScannerPluginInterface(PluginInterface):
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        pass

    @abstractmethod
    def scan(self, file_path: str, options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_rules(self) -> List[Dict[str, Any]]:
        pass
