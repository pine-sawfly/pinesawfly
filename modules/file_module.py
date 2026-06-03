from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class FileModule:
    @staticmethod
    def read_file_with_encoding(file_path: str | os.PathLike[str]) -> str:
        path = Path(file_path)
        for encoding in ("utf-8", "gbk", "gb2312", "latin1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                logger.error("Failed to read %s with %s: %s", path, encoding, exc)
                continue

        try:
            return path.read_bytes().decode("utf-8", errors="ignore")
        except OSError as exc:
            logger.error("Failed to force-decode %s: %s", path, exc)
            raise OSError(f"Unable to read file {path}") from exc

    @staticmethod
    def get_file_extension(file_path: str | os.PathLike[str]) -> str:
        return os.path.splitext(str(file_path))[1].lower()
