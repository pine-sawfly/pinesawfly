from phply.phplex import lexer
from phply.phpparse import make_parser
from phply import phpast as php
import logging
from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)

class PHPParser:
    """
    PHP代码解析器，使用phply库生成AST
    """
    
    def __init__(self):
        self.parser = make_parser()
    
    @safe_operation
    def parse_file(self, file_path: str):
        """
        解析PHP文件并生成AST
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            
            logger.info(f"正在解析文件: {file_path}")
            ast = self.parser.parse(code, lexer=lexer.clone())
            logger.info(f"文件 {file_path} 解析完成")
            return ast
            
        except UnicodeDecodeError as e:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    code = file.read()
                
                logger.info(f"使用GBK编码重新解析文件: {file_path}")
                ast = self.parser.parse(code, lexer=lexer.clone())
                logger.info(f"文件 {file_path} 解析完成")
                return ast
                
            except Exception as e:
                logger.error(f"解析文件 {file_path} 失败: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"解析文件 {file_path} 失败: {str(e)}")
            raise
    
    @safe_operation
    def parse_code(self, code: str):
        """
        解析PHP代码字符串并生成AST
        """
        try:
            logger.info("正在解析代码字符串")
            ast = self.parser.parse(code, lexer=lexer.clone())
            logger.info("代码字符串解析完成")
            return ast
        except Exception as e:
            logger.error(f"解析代码字符串失败: {str(e)}")
            raise