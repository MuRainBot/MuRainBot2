from Lib.utils import EventClassifier, Logger, Actions
from Lib.core import ConfigManager, EventManager, ThreadPool

import time

heartbeat_interval = -1
last_heartbeat_time = -1
logger = Logger.get_logger()


@ThreadPool.async_task
def restart_onebot(message):
    if ConfigManager.GlobalConfig().auto_restart_onebot.enable is False:
        logger.warning(f"检测到 {message}，由于未启用自动重启功能，将不会自动重启 Onebot 实现端")
        return
    logger.warning(f"因为 {message}，将尝试自动重启 Onebot 实现端！")
    action = Actions.SetRestart(2000).call()
    if action.get_result().is_ok:
        logger.warning("尝试重启 Onebot 实现端成功！")
    else:
        logger.error("尝试重启 Onebot 实现端失败！")


@EventManager.event_listener(EventClassifier.HeartbeatMetaEvent)
def on_heartbeat(event: EventClassifier.HeartbeatMetaEvent):
    global heartbeat_interval, last_heartbeat_time
    heartbeat_interval = event.interval / 1000
    last_heartbeat_time = time.time()
    status = event.status
    if status['online'] is not True or status['good'] is not True:
        logger.warning("心跳包状态异常，当前状态：%s" % status)
        restart_onebot("心跳包状态异常")


def check_heartbeat():
    flag = False
    while True:
        if heartbeat_interval != -1:
            if time.time() - last_heartbeat_time > heartbeat_interval * 2:
                logger.warning("心跳包超时！请检查 Onebot 实现端是否正常运行！")
                restart_onebot("心跳包超时")
                flag = True
            elif flag:
                logger.info("心跳包间隔已恢复正常")
