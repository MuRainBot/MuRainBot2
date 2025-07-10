"""
工具
"""
import inspect
import os.path
import urllib.parse
import shutil
import sys
import threading
import time
import uuid
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
from typing import Callable

import requests

from .paths import paths
from .utils import Logger

logger = Logger.get_logger()


class LimitedSizeDict(OrderedDict):
    """
    带有限制大小的字典
    """

    def __init__(self, max_size):
        self._max_size = max_size
        super().__init__()

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        elif len(self) >= self._max_size:
            oldest_key = next(iter(self))
            del self[oldest_key]
        super().__setitem__(key, value)


def restart() -> None:
    """
    MRB2重启
    Returns:
        None
    """
    # 获取当前解释器路径
    p = sys.executable
    try:
        # 启动新程序(解释器路径, 当前程序)
        os.execl(p, p, *sys.argv)
    except OSError:
        # 关闭当前程序
        sys.exit()


def download_file_to_cache(url: str,
                           headers=None,
                           file_name: str = None,
                           max_size: int = None,
                           timeout: int = 30,
                           download_path: str = paths.CACHE_PATH,
                           stream=True,
                           fake_headers: bool = True) -> str | None:
    """
    下载文件到缓存
    **请自行保证下载链接的安全性**
    Args:
        url: 下载的url
        headers: 下载请求的请求头
        file_name: 文件名
        max_size: 最大大小，单位字节，None则为不限制
        timeout: 请求超时时间
        download_path: 下载路径
        stream: 是否使用流式传输
        fake_headers: 是否使用自动生成的假请求头
    Returns:
        文件路径，如果请求失败则返回None
    """
    if headers is None:
        headers = {}

    if fake_headers:
        headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,da;q=0.7,ko;q=0.6",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                      "application/signed-exchange;v=b3;q=0.7",
            "Connection": "keep-alive",
            "Host": urllib.parse.urlparse(url).hostname
        })

    # 路径拼接
    if file_name is None:
        file_name = uuid.uuid4().hex + ".cache"

    file_path = Path(download_path) / file_name
    if paths.CACHE_PATH in file_path.parents:
        try:
            if not file_path.resolve().is_relative_to(paths.CACHE_PATH.resolve()):
                logger.warning("下载文件失败: 文件路径解析后超出缓存目录")
                return None
        except FileNotFoundError:
            pass
    file_path = str(file_path)

    try:
        # 下载
        if stream:
            # 使用流式下载
            with requests.get(url, stream=True, timeout=timeout, headers=headers) as res:
                res.raise_for_status()  # 请求失败则抛出异常

                # 优先从Content-Length判断
                content_length = res.headers.get('Content-Length')
                if max_size and content_length and int(content_length) > max_size:
                    logger.warning(f"下载中止: 文件大小 ({content_length} B) 超出限制 ({max_size} B)")
                    return None

                downloaded_size = 0
                with open(file_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        downloaded_size += len(chunk)
                        if max_size and downloaded_size > max_size:
                            logger.warning(f"下载中止: 文件在传输过程中超出大小限制 ({max_size} B)")
                            f.close()
                            os.remove(file_path)
                            return None
                        f.write(chunk)
        else:
            # 不使用流式传输
            if max_size is not None:
                # 获取响应头
                res = requests.head(url, timeout=timeout, headers=headers)
                if "Content-Length" in res.headers:
                    # 获取响应头中的Content-Length
                    content_length = int(res.headers["Content-Length"])
                    if content_length > max_size:
                        logger.warning(f"下载中止: 文件大小 ({content_length} B) 超出限制 ({max_size} B)")
                        return None
                else:
                    logger.warning(f"下载文件失败: HEAD请求未获取到文件大小，建议使用流式传输")
                    return None

            res = requests.get(url, headers=headers)
            res.raise_for_status()

            if len(res.content) > max_size:
                logger.warning(f"下载中止: 文件在传输过程中超出大小限制 ({max_size} B)")
                return None

            with open(file_path, "wb") as f:
                f.write(res.content)
    except requests.exceptions.RequestException as e:
        logger.warning(f"下载文件失败: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None

    return file_path


# 删除缓存文件
def clean_cache() -> None:
    """
    清理缓存
    Returns:
        None
    """
    if os.path.exists(paths.CACHE_PATH):
        try:
            shutil.rmtree(paths.CACHE_PATH, ignore_errors=True)
        except Exception as e:
            logger.warning("删除缓存时报错，报错信息: %s" % repr(e))


# 函数缓存
def function_cache(max_size: int, expiration_time: int = -1):
    """
    函数缓存
    Args:
        max_size: 最大大小
        expiration_time: 过期时间
    Returns:
        None
    """
    cache = LimitedSizeDict(max_size)

    def cache_decorator(func):
        """
        缓存装饰器
        Args:
            @param func:
        Returns:
            None
        """

        def wrapper(*args, **kwargs):
            key = str(func.__name__) + str(args) + str(kwargs)
            if key in cache and (expiration_time == -1 or time.time() - cache[key][1] < expiration_time):
                return cache[key][0]
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result

        def clear_cache():
            """清理缓存"""
            cache.clear()

        def get_cache():
            """获取缓存"""
            return dict(cache)

        def original_func(*args, **kwargs):
            """调用原函数"""
            return func(*args, **kwargs)

        wrapper.clear_cache = clear_cache
        wrapper.get_cache = get_cache
        wrapper.original_func = original_func
        return wrapper

    return cache_decorator


def thread_lock(func):
    """
    线程锁装饰器
    """
    thread_lock = threading.Lock()

    def wrapper(*args, **kwargs):
        with thread_lock:
            return func(*args, **kwargs)

    return wrapper


def finalize_and_cleanup():
    """
    结束运行
    @return:
    """
    logger.info("MuRainBot即将关闭，正在删除缓存")

    clean_cache()

    logger.warning("MuRainBot结束运行！")
    logger.info("再见！\n")


@thread_lock
def save_exc_dump(description: str = None, path: str = None):
    """
    保存异常堆栈
    Args:
        description: 保存的dump描述，为空则默认
        path: 保存的路径，为空则自动根据错误生成
    """
    # 扫描是否存在非当前日期且为归档的exc_dump
    exc_dump_files = [
        file for file in os.listdir(paths.DUMPS_PATH) if file.startswith("coredumpy_") and file.endswith(".dump")
    ]

    today_date = time.strftime("%Y%m%d")
    date_flags = []

    for file in exc_dump_files:
        file_date = file.split("coredumpy_", 1)[1].split("_", 1)[0][:len("YYYYMMDD")]
        if file_date != today_date:
            os.makedirs(os.path.join(paths.DUMPS_PATH, f"coredumpy_archive_{file_date}"), exist_ok=True)
            os.rename(os.path.join(paths.DUMPS_PATH, file), os.path.join(paths.DUMPS_PATH, f"coredumpy_archive_{file_date}", file))
            if file_date not in date_flags:
                logger.info(f"已自动归档 {file_date} 的异常堆栈到 coredumpy_archive_{file_date}")
                date_flags.append(file_date)

    # 保存dump文件
    try:
        import coredumpy
    except ImportError:
        logger.warning("coredumpy未安装，无法保存异常堆栈")
        return None

    try:
        _, _, exc_traceback = sys.exc_info()
        if not exc_traceback:
            raise Exception("No traceback found")

        # 遍历 traceback 链表，找到最后一个 frame (异常最初发生的位置)
        current_tb = exc_traceback
        frame = current_tb.tb_frame
        while current_tb:
            frame = current_tb.tb_frame
            current_tb = current_tb.tb_next

        i = 0
        while True:
            if i > 0:
                path_ = os.path.join(paths.DUMPS_PATH,
                                     f"coredumpy_"
                                     f"{time.strftime('%Y%m%d-%H%M%S')}_"
                                     f"{frame.f_code.co_name}_{i}.dump")
            else:
                path_ = os.path.join(paths.DUMPS_PATH,
                                     f"coredumpy_"
                                     f"{time.strftime('%Y%m%d-%H%M%S')}_"
                                     f"{frame.f_code.co_name}.dump")
            if not os.path.exists(path_):
                break
            i += 1

        for _ in ['?', '*', '"', '<', '>']:
            path_ = path_.replace(_, "")

        kwargs = {
            "frame": frame,
            "path": os.path.normpath(path_)
        }
        if description:
            kwargs["description"] = description
        if path:
            kwargs["path"] = path

        coredumpy.dump(**kwargs)
    except Exception as e:
        logger.error(f"保存异常堆栈时发生错误: {repr(e)}", exc_info=True)
        return None

    return kwargs["path"]


def bytes_io_to_file(
        io_bytes: BytesIO,
        file_name: str | None = None,
        file_type: str | None = None,
        save_dir: str = paths.CACHE_PATH
):
    """
    将BytesIO对象保存成文件，并返回路径
    Args:
        io_bytes: BytesIO对象
        file_name: 要保存的文件名，与file_type选一个填即可
        file_type: 文件类型(扩展名)，与file_name选一个填即可
        save_dir: 保存的文件夹

    Returns:
        保存的文件路径
    """
    if not isinstance(io_bytes, BytesIO):
        raise TypeError("bytes_io_to_file: 输入类型错误")
    if file_name is None:
        if file_type is None:
            file_type = "cache"
        file_name = uuid.uuid4().hex + "." + file_type
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    with open(os.path.join(save_dir, file_name), "wb") as f:
        f.write(io_bytes.getvalue())
    return os.path.join(save_dir, file_name)


def inject_dependencies(func: Callable, dependencies: dict):
    """
    一个简单的依赖注入函数。

    它会检查`func`的签名，并从`dependencies`字典中找到匹配的参数进行注入，
    然后执行函数并返回其结果。

    参数:
        func (function): 需要被注入依赖并执行的目标函数。
        dependencies (dict): 一个包含可用依赖项的字典，键是依赖项的名称。

    返回:
        dict: 包含注入的依赖项的参数字典。
    """
    # 1. 获取函数的签名
    sig = inspect.signature(func)

    # 2. 准备一个字典，用于存放需要传递给函数的参数
    kwargs_to_pass = {}

    # 3. 遍历函数签名的所有参数
    for param_name in sig.parameters:
        # 4. 如果参数名存在于我们的依赖字典中
        if param_name in dependencies:
            # 5. 将对应的键值对添加到准备传递的参数字典中
            kwargs_to_pass[param_name] = dependencies[param_name]

    return kwargs_to_pass
