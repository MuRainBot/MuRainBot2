"""
线程池
Created by BigCookie233
"""

import atexit
from concurrent.futures import ThreadPoolExecutor

from murainbot.common import exc_logger
from murainbot.core.ConfigManager import GlobalConfig
from murainbot.utils.Logger import get_logger

thread_pool = None
logger = get_logger()


def shutdown():
    """
    关闭线程池
    """
    global thread_pool
    if isinstance(thread_pool, ThreadPoolExecutor):
        logger.debug("Closing Thread Pool")
        thread_pool.shutdown()
        thread_pool = None


def init():
    """
    初始化线程池
    Returns:
        None
    """
    global thread_pool
    thread_pool = ThreadPoolExecutor(max_workers=GlobalConfig().thread_pool.max_workers)
    atexit.register(shutdown)


def _wrapper(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        exc_logger(e, f"Error in async task({func.__module__}.{func.__name__})")
        return None


def async_task(func):
    """
    异步任务装饰器
    """
    def wrapper(*args, **kwargs):
        if isinstance(thread_pool, ThreadPoolExecutor):
            return thread_pool.submit(_wrapper, func, *args, **kwargs)
        else:
            logger.warning("Thread Pool is not initialized. Please call init() before using it.")
            return func(*args, **kwargs)

    return wrapper
