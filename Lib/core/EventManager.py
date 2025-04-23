"""
事件管理器，用于管理事件与事件监听器
"""
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from Lib.core import ConfigManager
from Lib.core.ThreadPool import async_task
from Lib.utils import Logger

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
                if not ConfigManager.GlobalConfig().debug.enable:
                    try:
                        res = listener.func(self, **listener.kwargs)
                    except Exception as e:
                        logger.error(f"Error occurred in listener: {repr(e)}", exc_info=True)
                        continue
                else:
                    res = listener.func(self, **listener.kwargs)
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
        assert len(inspect.signature(self.func).parameters) >= 1, "The listener takes at least 1 parameter"


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
    assert issubclass(event_class, _Event), "Event class must be a subclass of Event"

    def wrapper(func: Callable[[T, ...], Any]):
        # 注册事件监听器
        listener = EventListener(priority=priority, func=func, kwargs=kwargs)
        event_listeners.setdefault(event_class, []).append(listener)
        return func

    return wrapper


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
                    logger.debug(f"Skipped listener: {listener.func.__name__}")
                    continue
                if not ConfigManager.GlobalConfig().debug.enable:
                    try:
                        res = listener.func(self, **listener.kwargs)
                    except Exception as e:
                        logger.error(f"Error occurred in listener: {repr(e)}", exc_info=True)
                        continue
                else:
                    res = listener.func(self, **listener.kwargs)
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
