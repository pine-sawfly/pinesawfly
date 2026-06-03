from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)


class FileProcessor:
    @staticmethod
    @safe_operation
    def get_php_files(directory: str) -> list[str]:
        try:
            return [str(file_path) for file_path in Path(directory).rglob("*.php")]
        except OSError as exc:
            logger.error("Failed to collect PHP files from %s: %s", directory, exc)
            return []

    @staticmethod
    @safe_operation
    def read_file_with_encoding(file_path: str) -> str:
        path = Path(file_path)
        for encoding in ("utf-8", "gbk", "latin1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeError(f"Unable to read file with supported encodings: {path}")

    @staticmethod
    @safe_operation
    def chunk_read_file(file_path: str, chunk_size: int = 8192) -> Iterator[str]:
        path = Path(file_path)
        try:
            with path.open("r", encoding="utf-8") as file:
                while chunk := file.read(chunk_size):
                    yield chunk
        except UnicodeDecodeError:
            with path.open("r", encoding="gbk") as file:
                while chunk := file.read(chunk_size):
                    yield chunk
