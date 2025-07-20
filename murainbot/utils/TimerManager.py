"""
计时器管理器
"""
import dataclasses
import threading
import time
import heapq
from typing import Callable

from murainbot.utils.Logger import get_logger

logger = get_logger()

queue_lock = threading.Lock()


@dataclasses.dataclass(order=True)
class TimerTask:
    """
    定时任务
    """
    execute_time: float = dataclasses.field(init=False, compare=True)
    delay: float = dataclasses.field(repr=False)  # 延迟多少秒执行

    target: Callable = dataclasses.field(compare=False)  # 要执行的函数
    args: tuple = dataclasses.field(default_factory=tuple, compare=False)
    kwargs: dict = dataclasses.field(default_factory=dict, compare=False)

    def __post_init__(self):
        self.execute_time = time.time() + self.delay


timer_queue: list[TimerTask] = []


def delay(delay_time: float, target: Callable, *args, **kwargs):
    """
    延迟执行
    Args:
        delay_time: 延迟多少秒执行，不要用其执行要求精确延迟或耗时的任务，这可能会导致拖垮其他计时器的运行
        如果实在要执行请为其添加murainbot.core.ThreadPool.async_task的装饰器
        target: 要执行的函数
        *args: 函数的参数
        **kwargs: 函数的参数
    """
    timer_task = TimerTask(delay=delay_time, target=target, args=args, kwargs=kwargs)
    with queue_lock:
        heapq.heappush(timer_queue, timer_task)


def run_timer():
    """
    运行计时器
    """
    while True:
        now = time.time()

        with queue_lock:
            if not timer_queue:
                sleep_duration = 1
            else:
                next_task = timer_queue[0]
                if now >= next_task.execute_time:
                    task_to_run = heapq.heappop(timer_queue)
                    sleep_duration = 0
                else:
                    sleep_duration = next_task.execute_time - now

        if sleep_duration > 0:
            time.sleep(sleep_duration)
            continue

        try:
            task_to_run.target(*task_to_run.args, **task_to_run.kwargs)
        except Exception as e:
            logger.error(f"执行计时器任务时出错: {repr(e)}", exc_info=True)
