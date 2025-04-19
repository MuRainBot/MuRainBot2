"""
工具
"""
import os.path
import shutil
import sys
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from io import BytesIO

import requests

from .constants import *
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


def download_file_to_cache(url: str, headers=None, file_name: str = "",
                           download_path: str = None, stream=False, fake_headers: bool = True) -> str | None:
    """
    下载文件到缓存
    Args:
        url: 下载的url
        headers: 下载请求的请求头
        file_name: 文件名
        download_path: 下载路径
        stream: 是否使用流式传输
        fake_headers: 是否使用自动生成的假请求头
    Returns:
        文件路径
    """
    if headers is None:
        headers = {}

    if fake_headers:
        headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42")
        headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8,da;q=0.7,ko;q=0.6"
        headers["Accept-Encoding"] = "gzip, deflate, br"
        headers["Accept"] = ("text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                             "application/signed-exchange;v=b3;q=0.7")
        headers["Connection"] = "keep-alive"
        headers["Upgrade-Insecure-Requests"] = "1"
        headers["Cache-Control"] = "max-age=0"
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = "none"
        headers["Sec-Fetch-User"] = "?1"
        headers["Sec-Ch-Ua"] = "\"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\", \"Microsoft Edge\";v=\"113\""
        headers["Sec-Ch-Ua-Mobile"] = "?0"
        headers["Sec-Ch-Ua-Platform"] = "\"Windows\""
        headers["Host"] = url.split("/")[2]

    # 路径拼接
    if file_name == "":
        file_name = uuid.uuid4().hex + ".cache"

    if download_path is None:
        file_path = os.path.join(CACHE_PATH, file_name)
    else:
        file_path = os.path.join(download_path, file_name)

    # 路径不存在特判
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    try:
        # 下载
        if stream:
            with open(file_path, "wb") as f, requests.get(url, stream=True, headers=headers) as res:
                for chunk in res.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        break
                    f.write(chunk)
        else:
            # 不使用流式传输
            res = requests.get(url, headers=headers)

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
    if os.path.exists(CACHE_PATH):
        try:
            shutil.rmtree(CACHE_PATH, ignore_errors=True)
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
    try:
        import coredumpy
    except ImportError:
        logger.warning("coredumpy未安装，无法保存异常堆栈")
        return

    try:
        exc_type, exc_value, exc_traceback = sys.exc_info()
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
                path_ = os.path.join(DUMPS_PATH,
                                     f"coredumpy_"
                                     f"{time.strftime('%Y%m%d%H%M%S')}_"
                                     f"{frame.f_code.co_name}_{i}.dump")
            else:
                path_ = os.path.join(DUMPS_PATH,
                                     f"coredumpy_"
                                     f"{time.strftime('%Y%m%d%H%M%S')}_"
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
        logger.error(f"保存异常堆栈时发生错误: {repr(e)}\n"
                     f"{traceback.format_exc()}")
        return None

    return kwargs["path"]


def bytes_io_to_file(
        io_bytes: BytesIO,
        file_name: str | None = None,
        file_type: str | None = None,
        save_dir: str = CACHE_PATH
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
