"""
自动重启 Onebot 实现端
"""

from murainbot.utils import EventClassifier, Logger, Actions
from murainbot.core import ConfigManager, EventManager, ThreadPool

import time

heartbeat_interval = -1
last_heartbeat_time = -1
logger = Logger.get_logger()


@ThreadPool.async_task
def restart_onebot(message):
    """
    重启 Onebot 实现端
    Args:
        message: 触发重启的原因
    Returns:
        None
    """
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
    """
    心跳包事件监听器
    Args:
        event: 心跳包事件
    """
    global heartbeat_interval, last_heartbeat_time
    heartbeat_interval = event.interval / 1000
    last_heartbeat_time = time.time()
    status = event.status
    if status['online'] is not True or status['good'] is not True:
        logger.warning("心跳包状态异常，当前状态：%s" % status)
        restart_onebot("心跳包状态异常")


def check_heartbeat():
    """
    心跳包检查线程
    """
    flag = -1  # 心跳包状态，-1表示正常，其他表示异常
    interval = 0.1  # 心跳包检查间隔
    has_new_heartbeat = False  # 是否有有新的心跳包
    _last_heartbeat_time = -1  # 用于检测是否有新的心跳包
    while True:
        if heartbeat_interval != -1:
            interval = heartbeat_interval / 4

            # 检查是否有新的心跳包
            if _last_heartbeat_time != last_heartbeat_time:
                has_new_heartbeat = True
                _last_heartbeat_time = last_heartbeat_time

            # 检查心跳包是否超时
            if time.time() - last_heartbeat_time > heartbeat_interval * 2:
                if flag == -1:
                    logger.warning("心跳包超时！请检查 Onebot 实现端是否正常运行！")
                    restart_onebot("心跳包超时")
                flag = 3
            elif flag > 0 and has_new_heartbeat:
                flag -= 1
                has_new_heartbeat = False
            elif flag == 0:
                logger.info("心跳包间隔已恢复正常")
                flag = -1

        time.sleep(interval)
