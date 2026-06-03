from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Language, Parser, Tree
import tree_sitter_php

from core.exception_handler import safe_operation
from modules.file_module import FileModule


@dataclass(frozen=True)
class PHPAst:
    tree: Tree
    source: bytes
    content: str


class PHPParser:
    def __init__(self):
        self.parser = Parser(Language(tree_sitter_php.language_php()))

    @safe_operation
    def parse_file(self, file_path: str) -> PHPAst:
        content = FileModule.read_file_with_encoding(file_path)
        return self.parse_code(content)

    @safe_operation
    def parse_code(self, code: str) -> PHPAst:
        source = code.encode("utf-8", errors="replace")
        return PHPAst(tree=self.parser.parse(source), source=source, content=code)
