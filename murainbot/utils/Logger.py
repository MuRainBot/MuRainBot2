import inspect
import logging
import logging.handlers as handlers
import os
from datetime import datetime
from typing import Optional, ClassVar, Type

from rich import get_console
from rich.console import Group, Console, ConsoleRenderable
from rich.highlighter import Highlighter, ReprHighlighter
from rich.table import Table
from rich.text import Text
from rich.traceback import Traceback

from ..paths import paths

logger_instance: logging.Logger = None
FRAMEWORK_LOGGER_NAME = "murainbot"


class CustomRichHandler(logging.Handler):
    """
    自定义日志记录器
    """
    # 关键字高亮
    KEYWORDS: ClassVar[Optional[list[str]]] = [
        "GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE", "PATCH",
    ]
    HIGHLIGHTER_CLASS: ClassVar[Type[Highlighter]] = ReprHighlighter

    def __init__(
            self,
            level: int | str = logging.NOTSET,
            console: Optional[Console] = None,
            *,
            markup: bool = False,
            rich_tracebacks: bool = True,
            tracebacks_show_locals: bool = False
    ) -> None:
        super().__init__(level=level)
        self.console = console or get_console()
        self.highlighter = self.HIGHLIGHTER_CLASS()
        self.markup = markup
        self.rich_tracebacks = rich_tracebacks
        self.tracebacks_show_locals = tracebacks_show_locals

        # 自定义级别 -> (4字符缩写, 颜色)
        self.level_map = {
            logging.DEBUG: ("DEBG", "white"),
            logging.INFO: ("INFO", "cyan"),
            logging.WARNING: ("WARN", "yellow"),
            logging.ERROR: ("EROR", "red"),
            logging.CRITICAL: ("CRIT", "bold red"),
        }

    def emit(self, record: logging.LogRecord) -> None:
        """由 logging 调用来处理日志记录。"""
        try:
            message = self.format(record)
            traceback = None
            if (
                    self.rich_tracebacks
                    and record.exc_info
                    and record.exc_info != (None, None, None)
            ):
                exc_type, exc_value, exc_traceback = record.exc_info
                assert exc_type is not None
                assert exc_value is not None
                # 从 RichHandler 复制过来的 traceback 创建逻辑
                traceback = Traceback.from_exception(
                    exc_type,
                    exc_value,
                    exc_traceback,
                    show_locals=self.tracebacks_show_locals,
                )
                message = record.getMessage()

            log_renderable = self.render(
                record=record,
                message=message,
                traceback=traceback,
            )
            self.console.print(log_renderable)
        except Exception:
            self.handleError(record)

    def render(
            self,
            *,
            record: logging.LogRecord,
            message: str,
            traceback: Optional[Traceback],
    ) -> ConsoleRenderable:
        """渲染日志"""
        log_time = datetime.fromtimestamp(record.created)
        time_str = log_time.strftime("[%Y-%m-%d %H:%M:%S]")
        time_text = Text(time_str, style="log.time")

        level_char, level_style = self.level_map.get(record.levelno, ("????", "red"))
        level_text = Text(f"[{level_char}]", style=f"bold {level_style}")

        use_markup = getattr(record, "markup", self.markup)
        message_text = Text.from_markup(message) if use_markup else Text(message)
        message_text = self.highlighter(message_text)
        if self.KEYWORDS:
            message_text.highlight_words(self.KEYWORDS, "logging.keyword")

        path = f"{record.name}"
        # 使用 rich 的内置日志样式
        path_text = Text(path, style="log.path", justify="right")

        single_line_table = Table.grid(expand=True, padding=(0, 1))
        single_line_table.add_column(style="log.time")
        single_line_table.add_column(width=6)
        single_line_table.add_column(ratio=1)
        single_line_table.add_column(style="log.path")
        single_line_table.add_row(time_text, level_text, message_text, path_text)

        capture_console = Console(width=self.console.width, record=True)
        with capture_console.capture() as capture:
            capture_console.print(single_line_table)

        # 3. 分析捕获到的字符串，判断行数
        # .strip() 是为了去掉可能的尾部换行符
        rendered_text = capture.get().strip()
        is_multiline = "\n" in rendered_text

        if not is_multiline:
            # 如果没有换行符，说明单行搞定
            final_layout = single_line_table
        else:
            # 否则，切换到健壮的两行布局
            meta_table = Table.grid(expand=True, padding=(0, 1))
            meta_table.add_column(style="log.time")
            meta_table.add_column(width=6)
            meta_table.add_column(ratio=1)
            meta_table.add_column(style="log.path")
            meta_table.add_row(time_text, level_text, Text(r"↩"), path_text)

            final_layout = Group(meta_table, message_text)

        # --- 组合最终布局和 Traceback ---
        if traceback:
            return Group(final_layout, traceback)
        else:
            return final_layout


def init(logs_path: str = None, logger_level: int = logging.INFO):
    """
    初始化日志记录器
    """
    global logger_instance
    if logger_instance is not None:
        return logger_instance

    if not logs_path:
        logs_path = paths.LOGS_PATH

    logger_instance = logging.getLogger()
    logger_instance.setLevel(logger_level)

    console_handler = CustomRichHandler(
        level=logger_level,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True
    )
    log_name = "latest.log"
    log_path = os.path.join(logs_path, log_name)

    def namer(filename):
        dir_name, base_name = os.path.split(filename)
        base_name = base_name.replace(log_name + '.', "")
        rotation_filename = os.path.join(dir_name, base_name)
        return rotation_filename

    file_handler = handlers.TimedRotatingFileHandler(
        log_path, when="MIDNIGHT", encoding="utf-8"
    )
    file_handler.namer = namer
    file_handler.suffix = "%Y-%m-%d.log"
    # 文件日志需要一个传统的 Formatter
    file_formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logger_level)  # 为文件 handler 也设置级别

    # 将两个 Handler 都添加到根 logger
    logger_instance.addHandler(console_handler)
    logger_instance.addHandler(file_handler)

    return logger_instance


def set_logger_level(level: int):
    """
    设置日志级别
    """
    global logger_instance
    if not logger_instance:
        init(logger_level=level)
    else:
        logger_instance.setLevel(level)
        for handler in logger_instance.handlers:
            handler.setLevel(level)


def get_logger(name: str | None = None):
    """
    获取日志记录器
    """
    if name is None:
        try:
            frame = inspect.currentframe().f_back
            module_name = frame.f_globals.get('__name__')

            if module_name and isinstance(module_name, str):
                if module_name.startswith("plugins"):
                    logger_name = FRAMEWORK_LOGGER_NAME + "." + module_name
                else:
                    logger_name = module_name
            else:
                logger_name = FRAMEWORK_LOGGER_NAME
        except Exception:
            logger_name = FRAMEWORK_LOGGER_NAME
    else:
        logger_name = name

    if not logger_instance:
        init()

    # 返回一个以计算出的名称命名的 logger 实例
    # 它会自动继承根 logger 的 handlers
    return logging.getLogger(logger_name)
