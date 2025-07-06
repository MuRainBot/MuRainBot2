import atexit
import logging
import os
import sys
import threading
import time

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.style import Style
from rich.text import Text

from murainbot import paths

console = Console()

BANNER = r""" __  __       ____       _         ____        _   _____ 
|  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_|___  \
| |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __| __) |
| |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_ / __/ 
|_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|_____|"""
BANNER_LINK = "https://github.com/MuRainBot/MuRainBot2"

banner_start_color = (14, 190, 255)
banner_end_color = (255, 66, 179)


def get_gradient(start_color: tuple[int, int, int], end_color: tuple[int, int, int], length: float):
    """
    渐变色生成
    @param start_color: 开始颜色
    @param end_color: 结束颜色
    @param length: 0-1的值
    @return: RGB颜色
    """
    return (
        int(start_color[0] + (end_color[0] - start_color[0]) * length),
        int(start_color[1] + (end_color[1] - start_color[1]) * length),
        int(start_color[2] + (end_color[2] - start_color[2]) * length)
    )


def start(work_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    """
    启动MRB2
    Args:
        work_path: MRB2实例的工作目录，默认为安装目录，谨慎填写
    """
    paths.init_paths(work_path)
    paths.paths.ensure_all_dirs_exist()

    banner_lines = BANNER.split("\n")
    rich_banner = Text()
    for i, line in enumerate(banner_lines):
        for j, char in enumerate(line):
            # 计算当前字符的渐变颜色
            gradient_pos = ((j / (len(line) - 1) + i / (len(banner_lines) - 1)) / 2)
            r, g, b = get_gradient(banner_start_color, banner_end_color, gradient_pos)
            # 使用 rich.style.Style 添加颜色
            style = Style(color=f"rgb({r},{g},{b})")
            rich_banner.append(char, style=style)
        rich_banner.append("\n")

    console.print(rich_banner, end="")

    link_color = get_gradient(banner_start_color, banner_end_color, 0.5)
    link_text = Text(BANNER_LINK, style=f"rgb({link_color[0]},{link_color[1]},{link_color[2]})")
    link_text.stylize(f"link {BANNER_LINK}")
    console.print(link_text)

    loading_text = f"[rgb({banner_start_color[0]},{banner_start_color[1]},{banner_start_color[2]})]正在加载 Lib, 首次启动可能需要几秒钟，请稍等...[/]"

    live = Live(Spinner("dots", text=loading_text), console=console, transient=True)
    live.start()
    # 开始加载
    start_loading = time.time()

    from .utils import Logger

    Logger.init()

    from .core import ThreadPool, ConfigManager, PluginManager, ListenerServer, OnebotAPI

    ThreadPool.init()

    from . import common
    atexit.register(common.finalize_and_cleanup)

    from .utils import AutoRestartOnebot

    Logger.set_logger_level(logging.DEBUG if ConfigManager.GlobalConfig().debug.enable else logging.INFO)
    live.stop()

    # Live 动画结束后，打印加载完成信息
    end_color_str = f"rgb({banner_end_color[0]},{banner_end_color[1]},{banner_end_color[2]})"
    console.print(
        f"[{end_color_str}]Lib 加载完成！耗时: {round(time.time() - start_loading, 2)}s 正在启动 MuRainBot...[/]"
    )

    logger = Logger.get_logger()

    logger.info("日志初始化完成，MuRainBot正在启动...")

    if ConfigManager.GlobalConfig().account.user_id == 0 or not ConfigManager.GlobalConfig().account.nick_name:
        logger.info("正在尝试获取用户信息...")
        try:
            account = OnebotAPI.api.get_login_info()
            new_account = ConfigManager.GlobalConfig().config.get("account")
            new_account.update({
                "user_id": account['user_id'],
                "nick_name": account['nickname']
            })

            ConfigManager.GlobalConfig().set("account", new_account)
        except Exception as e:
            logger.warning(f"获取用户信息失败, 可能会导致严重的问题: {repr(e)}")

    logger.info(f"欢迎使用: {ConfigManager.GlobalConfig().account.nick_name}"
                f"({ConfigManager.GlobalConfig().account.user_id})")

    logger.debug(f"准备加载插件")
    PluginManager.load_plugins()
    logger.info(f"插件加载完成！共成功加载了 {len(PluginManager.plugins)} 个插件"
                f"{': \n' if PluginManager.plugins else ''}"
                f"{'\n'.join(
                    [
                        f'{_['name']}: {_['info'].NAME}' if 'info' in _ and _['info'] else _['name']
                        for _ in PluginManager.plugins
                    ]
                )}")

    threading.Thread(target=AutoRestartOnebot.check_heartbeat, daemon=True).start()

    logger.info(f"启动监听服务器: {ConfigManager.GlobalConfig().server.server}")

    if ConfigManager.GlobalConfig().server.server == "werkzeug":
        # 禁用werkzeug的日志记录
        log = logging.getLogger('werkzeug')
        log.disabled = True

    threading.Thread(target=ListenerServer.start_server, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("正在关闭...")
    sys.exit(0)
