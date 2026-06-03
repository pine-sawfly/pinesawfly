import logging

from phply.phplex import lexer
from phply.phpparse import make_parser

from core.exception_handler import safe_operation
from modules.file_module import FileModule

logger = logging.getLogger(__name__)


class PHPParser:
    def __init__(self):
        self.parser = make_parser()

    @safe_operation
    def parse_file(self, file_path: str):
        try:
            logger.info(f"正在解析文件: {file_path}")
            ast = self.parser.parse(FileModule.read_file_with_encoding(file_path), lexer=lexer.clone())
            logger.info(f"文件 {file_path} 解析完成")
            return ast

        except Exception as e:
            logger.error(f"解析文件 {file_path} 失败: {e}")
            raise

    @safe_operation
    def parse_code(self, code: str):
        try:
            logger.info("正在解析代码字符串")
            ast = self.parser.parse(code, lexer=lexer.clone())
            logger.info("代码字符串解析完成")
            return ast
        except Exception as e:
            logger.error(f"解析代码字符串失败: {e}")
            raise
