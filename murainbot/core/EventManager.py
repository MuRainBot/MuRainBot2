"""
事件管理器，用于管理事件与事件监听器
"""
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from murainbot.core.ThreadPool import async_task
from murainbot.core import ConfigManager
from murainbot.utils import Logger
from murainbot.common import save_exc_dump

logger = Logger.get_logger()


class _Event:
    """
    请勿使用此事件类，使用Event继承以创建自定义事件
    """
    pass


class Hook(_Event):
    """
    钩子事件，用于在事件处理过程中跳过某些监听器
    """

    def __init__(self, event, listener):
        self.event = event
        self.listener = listener

    def call(self):
        """
        按优先级顺序同步触发所有监听器
        """
        if self.__class__ in event_listeners:
            for listener in sorted(event_listeners[self.__class__], key=lambda i: i.priority, reverse=True):
                try:
                    res = listener.func(self, **listener.kwargs)
                except Exception as e:
                    if ConfigManager.GlobalConfig().debug.save_dump:
                        dump_path = save_exc_dump(f"监听器中发生错误")
                    else:
                        dump_path = None
                    logger.error(f"监听器中发生错误: {repr(e)}"
                                 f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                                 exc_info=True)
                    continue
                if res is True:
                    return True
            return False
        return None


T = TypeVar('T', bound='_Event')


# 定义事件监听器的数据类
@dataclass(order=True)
class EventListener:
    """
    事件监听器数据类
    """
    priority: int  # 优先级，默认为排序的依据
    func: Callable[[T, ...], Any]  # 监听器函数
    kwargs: dict[str, Any] = field(default_factory=dict)  # 附加参数

    def __post_init__(self):
        # 确保监听器函数至少有一个参数
        assert len(inspect.signature(self.func).parameters) >= 1, "监听器至少接受 1 个参数"


# 定义监听器的类型和存储
event_listeners: dict[type[T], list[EventListener]] = {}


# 装饰器，用于注册监听器
def event_listener(event_class: type[T], priority: int = 0, **kwargs):
    """
    用于注册监听器

    Args:
        event_class: 事件类型
        priority: 优先级，默认为0
        **kwargs: 附加参数
    """
    if not issubclass(event_class, _Event):
        raise TypeError("event_class 类必须是 _Event 的子类")

    def wrapper(func: Callable[[T, ...], Any]):
        # 注册事件监听器
        listener = EventListener(priority=priority, func=func, kwargs=kwargs)
        event_listeners.setdefault(event_class, []).append(listener)
        return func

    return wrapper


def unregister_listener(event_class: type[T], func: Callable[[T, ...], Any]):
    """
    用于取消注册监听器
    注意，会删除所有与给定函数匹配的监听器。

    Args:
        event_class: 事件类型
        func: 监听器函数
    """
    if not issubclass(event_class, _Event):
        raise TypeError("event_class 类必须是 _Event 的子类")

    listeners_list = event_listeners.get(event_class)

    if not listeners_list:
        raise ValueError(f"事件类型 {event_class.__name__} 没有已注册的监听器。")

    # 查找所有与给定函数匹配的监听器对象
    listeners_to_remove = [listener for listener in listeners_list if listener.func == func]

    if not listeners_to_remove:
        # 如果没有找到匹配的函数
        raise ValueError(f"未找到函数 {func.__name__} 对应的监听器，无法为事件 {event_class.__name__} 注销。")

    # 移除所有找到的监听器
    removed_count = 0
    for listener_obj in listeners_to_remove:
        listeners_list.remove(listener_obj)
        removed_count += 1

    if not listeners_list:
        del event_listeners[event_class]


class Event(_Event):
    """
    基事件类，所有自定义事件均继承自此类，继承自此类以创建自定义事件
    """

    def _call_hook(self, listener):
        return Hook(self, listener).call()

    def call(self):
        """
        按优先级顺序同步触发所有监听器
        """
        if self.__class__ in event_listeners:
            res_list = []
            for listener in sorted(event_listeners[self.__class__], key=lambda i: i.priority, reverse=True):
                if self._call_hook(listener):
                    logger.debug(f"由 Hook 跳过监听器: {listener.func.__name__}")
                    continue
                try:
                    res = listener.func(self, **listener.kwargs)
                except Exception as e:
                    if ConfigManager.GlobalConfig().debug.save_dump:
                        dump_path = save_exc_dump(f"监听器中发生错误")
                    else:
                        dump_path = None
                    logger.error(f"监听器中发生错误: {repr(e)}"
                                 f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                                 exc_info=True)
                    continue
                res_list.append(res)

    @async_task
    def call_async(self):
        """
        无需等待的异步按优先级顺序触发所有监听器
        """
        self.call()


if __name__ == "__main__":
    # 示例：自定义事件
    """
    class MyEvent(Event):
        def __init__(self, message):
            self.message = message


    # 监听器函数
    @event_listener(MyEvent, priority=10, other_message="priority is 10")
    @event_listener(MyEvent, priority=100, other_message="priority is 100")
    @event_listener(MyEvent, other_message="I'm going to be skipped")
    def on_my_event(event, other_message=""):
        print(f"Received event: {event.message}!", other_message)


    @event_listener(Hook)
    def on_hook(event):
        if event.event.__class__ == MyEvent and event.listener.kwargs["other_message"] == "I'm going to be skipped":
            return True


    # 触发事件
    event = MyEvent("Hello, World")
    event.call()
"""
