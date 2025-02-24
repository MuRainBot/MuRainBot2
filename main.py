"""
MuRainBot2
"""

#   __  __       ____       _         ____        _   _____
#  |  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_|___  \
#  | |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __| __) |
#  | |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_ / __/
#  |_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|_____|
import atexit
import logging
import threading

BANNER = r""" __  __       ____       _         ____        _   _____ 
|  \/  |_   _|  _ \ __ _(_)_ __   | __ )  ___ | |_|___  \
| |\/| | | | | |_) / _` | | '_ \  |  _ \ / _ \| __| __) |
| |  | | |_| |  _ < (_| | | | | | | |_) | (_) | |_ / __/ 
|_|  |_|\__,_|_| \_\__,_|_|_| |_| |____/ \___/ \__|_____|"""
BANNER_LINK = "https://github.com/MuRainBot/MuRainBot2"


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


# 主函数
if __name__ == '__main__':
    banner_start_color = (14, 190, 255)
    banner_end_color = (255, 66, 179)
    color_banner = ""
    banner = BANNER.split("\n")
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
    print(color_banner + color_text(BANNER_LINK, get_gradient(banner_start_color, banner_end_color, 0.5))
          + color_text("\n正在加载 Lib, 首次启动可能需要几秒钟，请稍等...", banner_start_color), end="")
    import time

    start_loading = time.time()

    from Lib.utils import Logger

    Logger.init()

    from Lib.core import *

    from Lib import *

    # 结束运行
    @atexit.register
    def finalize_and_cleanup():
        """
        结束运行
        @return:
        """
        logger.info("MuRainBot即将关闭，正在删除缓存")

        common.clean_cache()

        logger.warning("MuRainBot结束运行！")
        logger.info("再见！\n")


    ThreadPool.init()

    Logger.set_logger_level(logging.DEBUG if ConfigManager.GlobalConfig().debug.enable else logging.INFO)

    print("\r" + color_text(
        f"Lib 加载完成！耗时: {round(time.time() - start_loading, 2)}s 正在启动 MuRainBot...",
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
            logger.warning(f"获取用户信息失败: {repr(e)}, 可能会导致严重的问题！")

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
