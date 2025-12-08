"""
计时器管理器
"""
import dataclasses
import heapq
import threading
import time
from typing import Callable

from murainbot.common import exc_logger
from murainbot.utils.Logger import get_logger

logger = get_logger()

queue_lock = threading.Lock()
timer_queue_cv = threading.Condition(queue_lock)


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
        self.execute_time = time.perf_counter() + self.delay


timer_queue: list[TimerTask] = []


def delay(delay_time: float, target: Callable, *args, **kwargs):
    """
    延迟执行
    Args:
        delay_time: 延迟多少秒执行，不要用于执行耗时的任务，这可能会导致拖垮其他计时器的运行
        如果实在要执行请为其添加murainbot.core.ThreadPool.async_task的装饰器
        注意，也不要用于要求精确延迟的任务，因为随着任务的增多，精确性会下降
        target: 要执行的函数
        *args: 函数的参数
        **kwargs: 函数的参数
    """
    timer_task = TimerTask(delay=delay_time, target=target, args=args, kwargs=kwargs)
    with queue_lock:
        before_next_task_exec_time = timer_queue[0].execute_time if timer_queue else None
        heapq.heappush(timer_queue, timer_task)
        if before_next_task_exec_time is None or timer_task.execute_time < before_next_task_exec_time:
            timer_queue_cv.notify()


def run_timer():
    """
    运行计时器
    """
    while True:
        now = time.perf_counter()

        with queue_lock:
            if not timer_queue:
                sleep_duration = None
            else:
                next_task = timer_queue[0]
                if now >= next_task.execute_time:
                    task_to_run = heapq.heappop(timer_queue)
                    sleep_duration = 0
                else:
                    sleep_duration = next_task.execute_time - now

            if sleep_duration > 0 or sleep_duration is None:
                timer_queue_cv.wait(sleep_duration)
                continue

        t = time.perf_counter()
        try:
            task_to_run.target(*task_to_run.args, **task_to_run.kwargs)
        except Exception as e:
            exc_logger(e, f"执行计时器 {task_to_run.target.__module__}.{task_to_run.target.__name__} 任务时出错")
        if time.perf_counter() - t > 3:
            logger.warning(
                f"执行计时器 {task_to_run.target.__module__}.{task_to_run.target.__name__} "
                f"耗时过长: {round((time.perf_counter() - t) * 1000, 2)}ms。"
                f"这可能会导致其他任务阻塞，如果的确需要长时间的任务，请为此任务的函数添加@async_task装饰器，"
                f"以让其在线程池的另一个线程中运行。"
            )
