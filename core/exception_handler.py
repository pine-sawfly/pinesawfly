import logging
import traceback
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def safe_operation(func):
    """
    异常捕获装饰器，用于包装可能出错的操作
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"操作 {func.__name__} 失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            # 可以选择重新抛出异常或返回默认值
            raise
    return wrapper

class ExceptionHandler:
    """
    异常处理类
    """
    
    @staticmethod
    def log_exception(exception: Exception, context: str = ""):
        """
        记录异常信息
        """
        logger.error(f"异常发生在 {context}: {str(exception)}")
        logger.error(traceback.format_exc())
        
    @staticmethod
    def handle_file_operation(operation_func):
        """
        处理文件操作的装饰器
        """
        @wraps(operation_func)
        def wrapper(*args, **kwargs):
            try:
                return operation_func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.error(f"文件未找到: {str(e)}")
            except PermissionError as e:
                logger.error(f"权限不足: {str(e)}")
            except IOError as e:
                logger.error(f"IO错误: {str(e)}")
            except Exception as e:
                logger.error(f"文件操作失败: {str(e)}")
                logger.error(traceback.format_exc())
        return wrapper