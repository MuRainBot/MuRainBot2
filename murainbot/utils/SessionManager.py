"""
会话管理器
"""
import dataclasses
import functools
import inspect
import threading
import time
from typing import Generator, Any, Callable

from murainbot.common import exc_logger
from murainbot.core import EventManager
from murainbot.core.ThreadPool import async_task
from murainbot.utils import Logger, TimerManager
from murainbot.utils.EventClassifier import Event

logger = Logger.get_logger()

waiting_handlers = []
_handler_lock = threading.Lock()


class WaitTimeoutError(Exception):
    """
    等待超时异常
    """


@dataclasses.dataclass
class WaitHandlerData:
    """
    等待中的处理器的数据
    """
    generator: Generator["WaitAction", tuple[EventManager.Event | None, Any], Any]
    raw_event_data: Event
    raw_handler: Callable[[...], ...]
    wait_timeout: int | None = 60


@dataclasses.dataclass
class WaitAction:
    """
    等待操作
    """
    wait_trigger: Callable[["TriggerEvent"], ...]
    timeout: int | None = 60
    wait_handler: WaitHandlerData = dataclasses.field(init=False)

    def set_data(self, wait_handler: WaitHandlerData):
        """
        设置数据，由框架调用，**无需插件开发者手动调用**
        Args:
            wait_handler: 等待处理器
        """
        self.wait_handler = wait_handler


class TriggerEvent(EventManager.Event):
    def __init__(self, wait_handler: WaitHandlerData):
        self.wait_handler = wait_handler
        self.data = None

    def set_data(self, data):
        """
        设置返回数据
        Args:
            data: 返回数据
        """
        self.data = data


def _throw_timeout_error(handler: WaitHandlerData):
    """
    抛出超时错误
    Args:
        handler: 等待的处理器

    Returns:
        None
    """
    for waiting_handler in waiting_handlers:
        if waiting_handler is handler:
            try:
                waiting_handler.generator.throw(WaitTimeoutError("等待超时"))
            except StopIteration:
                pass
            try:
                waiting_handlers.remove(waiting_handler)
            except ValueError:
                pass
            return


def _on_trigger_event(wait_handler: WaitHandlerData):
    @async_task
    def _on_event(event: TriggerEvent):
        nonlocal wait_handler
        if event.wait_handler is not wait_handler:
            return None
        try:
            wait_action = wait_handler.generator.send(event.data)
        except StopIteration:
            return True
        except Exception as e:
            exc_logger(e, f"执行等待处理器 {wait_handler.raw_handler.__module__}.{wait_handler.raw_handler.__name__} 发生错误")
            return True
        finally:
            try:
                waiting_handlers.remove(wait_handler)
                EventManager.unregister_listener(TriggerEvent, _on_event)
            except ValueError:
                pass

        if not isinstance(wait_action, WaitAction):
            wait_handler.generator.throw(TypeError("wait_action must be a WaitAction"))
            return True

        wait_handler = WaitHandlerData(
            generator=wait_handler.generator,
            raw_event_data=wait_handler.raw_event_data,
            raw_handler=wait_handler.raw_handler,
            wait_timeout=wait_action.timeout
        )
        wait_action.set_data(wait_handler)
        waiting_handlers.append(wait_handler)
        if wait_handler.wait_timeout is not None:
            TimerManager.delay(
                wait_handler.wait_timeout,
                _throw_timeout_error,
                handler=wait_handler
            )
        targeter_event = TriggerEvent(wait_handler)
        EventManager.event_listener(TriggerEvent)(_on_trigger_event(wait_handler))
        t = time.perf_counter()
        wait_action.wait_trigger(targeter_event)
        if time.perf_counter() - t > 1.5:
            logger.warning(
                f"在执行处理器 "
                f"{wait_handler.raw_handler.__module__}.{wait_handler.raw_handler.__name__} "
                f"时，其返回的等待处理器触发器 "
                f"{wait_action.wait_trigger.__module__}.{wait_action.wait_trigger.__name__} "
                f"初始化时间过长，"
                f"耗时: {round((time.perf_counter() - t) * 1000, 2)}ms，"
                f"等待处理器运行请仅进行初始化，不要在其中执行耗时操作，如果的确有需求请使用"
                f"@async_task装饰器，让其运行在线程池的其他线程中"
            )
        return True

    return _on_event


def session_handler(func: Callable[[...], ...]):
    """
    会话处理装饰器
    Args:
        func: 处理器
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """
        会话处理函数
        Args:
            *args: 参数
            **kwargs: 参数
        """
        if not args or not isinstance(args[0], Event):
            raise TypeError("session_handler must be used in event handler")
        if not inspect.isgeneratorfunction(func):
            raise TypeError("session_handler must be used in generator function")
        generator = func(*args, **kwargs)
        wait_handler = WaitHandlerData(
            generator=generator,
            raw_event_data=args[0],
            raw_handler=func,
            wait_timeout=None
        )
        waiting_handlers.append(wait_handler)
        EventManager.event_listener(TriggerEvent)(_on_trigger_event(wait_handler))
        targeter_event = TriggerEvent(wait_handler)
        targeter_event.call()
    return wrapper


if __name__ == "__main__":
    def delay_trigger(delay):
        def trigger(trigger_event):
            TimerManager.delay(delay, trigger_event.call)

        return trigger


    @session_handler
    def test(event):
        print("test")
        yield WaitAction(delay_trigger(5))
        print("test")
        yield WaitAction(delay_trigger(3))
        print("test")

    test(Event({
        "post_type": "test",
        "time": time.time(),
        "data": {},
        "self_id": "test",
    }))
