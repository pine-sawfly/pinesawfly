import logging
import traceback
from functools import wraps

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def safe_operation(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"操作 {func.__name__} 失败: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise
    return wrapper


class ExceptionHandler:
    @staticmethod
    def log_exception(exception: Exception, context: str = ""):
        logger.error(f"异常发生在 {context}: {exception}")
        logger.error(traceback.format_exc())

    @staticmethod
    def handle_file_operation(operation_func):
        @wraps(operation_func)
        def wrapper(*args, **kwargs):
            try:
                return operation_func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.error(f"文件未找到: {e}")
            except PermissionError as e:
                logger.error(f"权限不足: {e}")
            except IOError as e:
                logger.error(f"IO 错误: {e}")
            except Exception as e:
                logger.error(f"文件操作失败: {e}")
                logger.error(traceback.format_exc())
        return wrapper
