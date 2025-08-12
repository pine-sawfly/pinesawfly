import os
import logging
from pathlib import Path
from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)

class FileProcessor:
    """
    文件处理工具类
    """
    
    @staticmethod
    @safe_operation
    def get_php_files(directory: str) -> list:
        """
        获取目录中的所有PHP文件
        """
        php_files = []
        try:
            path = Path(directory)
            for file_path in path.rglob("*.php"):
                php_files.append(str(file_path))
        except Exception as e:
            logger.error(f"获取目录 {directory} 中的PHP文件时出错: {str(e)}")
        
        logger.info(f"在目录 {directory} 中找到 {len(php_files)} 个PHP文件")
        return php_files
    
    @staticmethod
    @safe_operation
    def read_file_with_encoding(file_path: str) -> str:
        """
        以适当的编码读取文件
        """
        encodings = ['utf-8', 'gbk', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    logger.info(f"使用 {encoding} 编码成功读取文件 {file_path}")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"读取文件 {file_path} 时出错: {str(e)}")
                raise
        
        raise UnicodeDecodeError(f"无法使用常见编码读取文件 {file_path}")
    
    @staticmethod
    @safe_operation
    def chunk_read_file(file_path: str, chunk_size: int = 8192):
        """
        分块读取大文件
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(file_path, 'r', encoding='gbk') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk