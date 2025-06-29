"""
日志记录器
"""
import inspect
import logging
import logging.handlers as handlers
import os
import sys
from ..paths import paths

import coloredlogs


logger_instance: logging.Logger = None # 重命名全局变量以区分
FRAMEWORK_LOGGER_NAME = "murainbot"


def init(logs_path: str = None, logger_level: int = logging.INFO):
    """
    初始化日志记录器
    Args:
        @param logs_path:
        @param logger_level:
    Returns:
        None
    """
    global logger_instance

    if not logs_path:
        logs_path = paths.LOGS_PATH

    if logger_instance is not None:
        return logger_instance
    # 日志颜色
    log_colors = {
        "DEBUG": "white",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }
    log_field_styles = {
        "asctime": {"color": "green"},
        "hostname": {"color": "magenta"},
        "levelname": {"color": "white"}
    }
    # 日志格式
    fmt = "[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s"
    # 设置日志
    coloredlogs.install(isatty=True, stream=sys.stdout, field_styles=log_field_styles, fmt=fmt, colors=log_colors)

    # 设置文件日志
    logger_instance = logging.getLogger()

    logger_instance.setLevel(logger_level)
    coloredlogs.set_level(logger_level)

    log_name = "latest.log"
    log_path = os.path.join(logs_path, log_name)

    def namer(filename):
        """
        生成文件名
        Args:
            filename: 文件名
        Returns:
            文件名
        """
        dir_name, base_name = os.path.split(filename)
        base_name = base_name.replace(log_name + '.', "")
        rotation_filename = os.path.join(dir_name, base_name)
        return rotation_filename

    file_handler = handlers.TimedRotatingFileHandler(log_path, when="MIDNIGHT", encoding="utf-8")
    file_handler.namer = namer
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setFormatter(logging.Formatter(fmt))
    logger_instance.addHandler(file_handler)
    return logger_instance


def set_logger_level(level: int):
    """
    设置日志级别
    Args:
        level: 日志级别
    Returns:
        None
    """
    global logger_instance
    logger_instance.setLevel(level)
    coloredlogs.set_level(level)


def get_logger(name: str | None = None):
    """
    获取日志记录器
    Returns:
        Logger
    """

    if name is None:
        try:
            frame = inspect.currentframe().f_back
            # 从栈帧的全局变量中获取 __name__
            module_name = frame.f_globals.get('__name__')

            if module_name and isinstance(module_name, str):
                if module_name == "__main__":
                    logger_name = FRAMEWORK_LOGGER_NAME
                elif module_name.startswith("plugins"):
                    logger_name = FRAMEWORK_LOGGER_NAME + "." + module_name
                else:
                    logger_name = module_name
            else:
                logger_name = FRAMEWORK_LOGGER_NAME
        except Exception:
            logger_name = FRAMEWORK_LOGGER_NAME
    elif isinstance(name, str):
        logger_name = f"{FRAMEWORK_LOGGER_NAME}.{name}"
    else:
        logger_name = FRAMEWORK_LOGGER_NAME

    if not logger_instance:
        init()

    return logging.getLogger(logger_name)
