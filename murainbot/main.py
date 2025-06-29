import atexit
import logging
import os
import random
import sys
import threading
import time

from murainbot import paths

is_done = False

BANNER = r""" __  __       ____       _         ____        _   _____ 
|  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_|___  \
| |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __| __) |
| |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_ / __/ 
|_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|_____|"""
BANNER_LINK = "https://github.com/MuRainBot/MuRainBot2"

banner_start_color = (14, 190, 255)
banner_end_color = (255, 66, 179)


def color_text(text: str, text_color: tuple[int, int, int] = None, bg_color: tuple[int, int, int] = None):
    """
    富文本生成器
    @param text: 文本
    @param text_color: 文本颜色
    @param bg_color: 背景颜色
    @return: 富文本
    """
    text = text + "\033[0m" if text_color is not None or bg_color is not None else text
    if text_color is not None:
        text = f"\033[38;2;{text_color[0]};{text_color[1]};{text_color[2]}m" + text
    if bg_color is not None:
        text = f"\033[48;2;{bg_color[0]};{bg_color[1]};{bg_color[2]}m" + text
    return text


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


def print_loading(wait_str):
    """
    输出加载动画
    """
    loading_string_list = [r"|/-\\", r"▁▂▃▄▅▆▇█▇▆▅▄▃▂", "\u2801\u2808\u2810\u2820\u2880\u2900\u2804\u2802", r"←↖↑↗→↘↓↙"]
    loading_string = random.choice(loading_string_list)
    i = 0
    while not is_done:
        if i == len(loading_string):
            i = 0
        print("\r" + wait_str + color_text(loading_string[i], banner_start_color), end="")
        time.sleep(0.07)
        i += 1


def start(work_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    global is_done
    paths.init_paths(work_path)
    banner = BANNER.split("\n")
    color_banner = ""
    # 输出banner
    for i in range(len(banner)):
        for j in range(len(banner[i])):
            color_banner += color_text(
                banner[i][j],
                get_gradient(
                    banner_start_color,
                    banner_end_color,
                    ((j / (len(banner[i]) - 1) + i / (len(banner) - 1)) / 2)
                )
            )
        color_banner += "\n"

    print(color_banner.strip())

    # 输出项目链接
    for c in color_text(BANNER_LINK, get_gradient(banner_start_color, banner_end_color, 0.5)):
        print(c, end="")

    wait_str = color_text("正在加载 Lib, 首次启动可能需要几秒钟，请稍等...", banner_start_color)
    print("\n" + wait_str, end="")

    threading.Thread(target=print_loading, daemon=True, args=(wait_str,)).start()

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

    is_done = True

    print("\r" + color_text(
        f"Lib 加载完成！耗时: {round(time.time() - start_loading, 2)}s 正在启动 MuRainBot...  ",
        banner_end_color
    )
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
                f"{': \n' if len(PluginManager.plugins) >= 1 else ''}"
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
