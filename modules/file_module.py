import logging

logger = logging.getLogger(__name__)

class FileModule:
    """
    文件处理模块，处理文件读取等相关功能
    """
    
    @staticmethod
    def read_file_with_encoding(file_path):
        """
        尝试用不同编码读取文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件内容
            
        Raises:
            Exception: 当所有编码尝试均失败时抛出异常
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    logger.info(f"使用 {encoding} 编码成功读取文件 {file_path}")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"使用 {encoding} 编码读取文件 {file_path} 时出错: {str(e)}")
                continue
        
        # 如果所有编码都失败了，以二进制模式读取并强制解码
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                # 尝试解码，忽略错误
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"强制解码文件 {file_path} 时出错: {str(e)}")
            raise Exception(f"无法读取文件 {file_path}，所有编码尝试均失败")