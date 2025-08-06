"""
计时器管理器
"""
import dataclasses
import threading
import time
import heapq
from typing import Callable

from murainbot.common import save_exc_dump
from murainbot.core import ConfigManager

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
        self.execute_time = time.perf_counter() + self.delay


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
        now = time.perf_counter()

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
            # 防止睡眠时间太长导致中间插入的新的任务被拖太久
            time.sleep(min(sleep_duration, 1))
            continue

        t = time.perf_counter()
        try:
            task_to_run.target(*task_to_run.args, **task_to_run.kwargs)
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(
                    f"执行计时器 {task_to_run.target.__module__}.{task_to_run.target.__name__} 任务时出错")
            else:
                dump_path = None
            logger.error(
                f"执行计时器 {task_to_run.target.__module__}.{task_to_run.target.__name__} 任务时出错: {repr(e)}"
                f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                exc_info=True
            )
        if time.perf_counter() - t > 3:
            logger.warning(
                f"执行计时器 {task_to_run.target.__module__}.{task_to_run.target.__name__} "
                f"耗时过长: {round((time.perf_counter() - t) * 1000, 2)}ms。"
                f"这可能会导致其他任务阻塞，如果的确需要长时间的任务，请为此任务的函数添加@async_task装饰器，"
                f"以让其在线程池的另一个线程中运行。"
            )