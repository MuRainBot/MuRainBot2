"""
QQ富文本
"""
from __future__ import annotations

import inspect
import json
import os
from typing import Generator
from urllib.parse import urlparse

from murainbot.common import save_exc_dump
from murainbot.core import ConfigManager
from murainbot.utils import QQDataCacher, Logger


def cq_decode(text, in_cq: bool = False) -> str:
    """
    CQ解码
    Args:
        text: 文本（CQ）
        in_cq: 该文本是否是在CQ内的
    Returns:
        解码后的文本
    """
    text = str(text)
    if in_cq:
        return text.replace("&amp;", "&").replace("&#91;", "["). \
            replace("&#93;", "]").replace("&#44;", ",")
    else:
        return text.replace("&amp;", "&").replace("&#91;", "["). \
            replace("&#93;", "]")


def cq_encode(text, in_cq: bool = False) -> str:
    """
    CQ编码
    Args:
        text: 文本
        in_cq: 该文本是否是在CQ内的
    Returns:
        编码后的文本
    """
    text = str(text)
    if in_cq:
        return text.replace("&", "&amp;").replace("[", "&#91;"). \
            replace("]", "&#93;").replace(",", "&#44;")
    else:
        return text.replace("&", "&amp;").replace("[", "&#91;"). \
            replace("]", "&#93;")


def cq_2_array(cq: str) -> list[dict[str, dict[str, str]]]:
    """
    将CQCode格式的字符串转换为消息段数组。

    Args:
        cq (str): CQCode字符串。

    Returns:
        list[dict[str, dict[str, str]]]: 解析后的消息段数组。

    Raises:
        TypeError: 如果输入类型不是字符串。
        ValueError: 如果解析过程中遇到格式错误，包含错误位置信息。
    """
    if not isinstance(cq, str):
        raise TypeError("cq_2_array: 输入类型错误")

    cq_array = []
    now_state = 0  # 当前解析状态
    # 0: 不在CQ码内 (初始/普通文本)
    # 1: 在CQ码内，正在解析类型 (包括验证 [CQ: 前缀)
    # 2: 在CQ码内，正在解析参数键 (key)
    # 3: 在CQ码内，正在解析参数值 (value)

    segment_data = {"text": ""}  # 存储当前普通文本段
    current_cq_data = {}  # 存储当前 CQ 码的 data 部分
    now_key = ""
    now_value = ""  # 使用 now_value 暂存值，避免直接操作 current_cq_data[now_key]
    now_segment_type = ""  # 存储当前 CQ 码的完整类型部分 (包括 CQ:) 或处理后的类型
    cq_start_pos = -1  # 记录当前 CQ 码 '[' 的位置

    for i, c in enumerate(cq):
        error_context = f"在字符 {i} ('{c}') 附近"
        cq_error_context = f"在起始于字符 {cq_start_pos} 的 CQ 码中，{error_context}"

        if now_state == 0:  # 解析普通文本
            if cq_start_pos == -1:  # 文本块开始
                cq_start_pos = i
            if c == "[":
                # 遇到可能的 CQ 码开头，先保存之前的文本
                if len(segment_data["text"]):
                    cq_array.append({"type": "text", "data": {"text": cq_decode(segment_data["text"])}})
                    segment_data = {"text": ""}  # 重置文本段

                # 记录起始位置，进入状态 1
                cq_start_pos = i
                now_state = 1
                # 重置当前 CQ 码的临时变量
                now_segment_type = ""  # 开始累积类型部分
                current_cq_data = {}
                now_key = ""
                now_value = ""
            elif c == "]":
                raise ValueError(f"cq_2_array: {error_context}: 文本块中包含非法字符: ']'")
            else:
                segment_data["text"] += c  # 继续拼接普通文本

        elif now_state == 1:  # 解析类型 (包含 [CQ: 前缀)
            if c == ",":  # 类型解析结束，进入参数键解析
                if not now_segment_type.startswith("CQ:"):
                    raise ValueError(f"cq_2_array: {cq_error_context}: 期望 'CQ:' 前缀，但得到 '{now_segment_type}'")

                actual_type = now_segment_type[3:]
                if not actual_type:
                    raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码类型不能为空")

                now_segment_type = actual_type  # 保存处理后的类型名
                now_state = 2  # 进入参数键解析状态
                now_key = ""  # 准备解析第一个键
            elif c == "]":  # 类型解析结束，无参数 CQ 码结束
                if not now_segment_type.startswith("CQ:"):
                    # 如果不是 CQ: 开头，根据严格程度，可以报错或当作普通文本处理
                    # 这里我们严格处理，既然进入了状态1，就必须是 CQ: 开头
                    raise ValueError(f"cq_2_array: {cq_error_context}: 期望 'CQ:' 前缀，但得到 '{now_segment_type}'")

                actual_type = now_segment_type[3:]
                if not actual_type:
                    raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码类型不能为空")

                # 存入无参数的 CQ 码段
                cq_array.append({"type": actual_type, "data": {}})  # data 为空
                now_state = 0  # 回到初始状态
                cq_start_pos = -1  # 重置
            elif c == '[':  # 类型名中不应包含未转义的 '['
                raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码类型 '{now_segment_type}' 中包含非法字符 '['")
            else:
                # 继续拼接类型部分 (此时包含 CQ:)
                now_segment_type += c

        elif now_state == 2:  # 解析参数键 (key)
            if c == "=":  # 键名解析结束，进入值解析
                if not now_key:
                    raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码参数键不能为空")

                # 检查键名重复 (键名通常不解码，或按需解码)
                # decoded_key = cq_decode(now_key, in_cq=True) # 如果键名需要解码
                decoded_key = now_key  # 假设键名不解码
                if decoded_key in current_cq_data:
                    raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码参数键 '{decoded_key}' 重复")

                now_key = decoded_key  # 保存解码后（或原始）的键名
                now_state = 3  # 进入参数值解析状态
                now_value = ""  # 准备解析值
            elif c == "," or c == "]":  # 在键名后遇到逗号或方括号是错误的
                raise ValueError(f"cq_2_array: {cq_error_context}: 在参数键 '{now_key}' 后期望 '='，但遇到 '{c}'")
            elif c == '[':  # 键名中不应包含未转义的 '[' (根据规范，& 和 , 也应转义，但这里简化检查)
                raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码参数键 '{now_key}' 中包含非法字符 '['")
            else:
                now_key += c  # 继续拼接键名

        elif now_state == 3:  # 解析参数值 (value)
            if c == ",":  # 当前值结束，进入下一个键解析
                # 解码当前值并存入
                current_cq_data[now_key] = cq_decode(now_value, in_cq=True)
                now_state = 2  # 回到解析键的状态
                now_key = ""  # 重置键，准备解析下一个
                # now_value 不需要在这里重置，进入状态 2 后，遇到 = 进入状态 3 时会重置
            elif c == "]":  # 当前值结束，整个 CQ 码结束
                # 解码当前值并存入
                current_cq_data[now_key] = cq_decode(now_value, in_cq=True)
                # 存入带参数的 CQ 码段
                cq_array.append({"type": now_segment_type, "data": current_cq_data})
                now_state = 0  # 回到初始状态
                cq_start_pos = -1  # 重置
            elif c == '[':  # 值中不应出现未转义的 '['
                raise ValueError(f"cq_2_array: {cq_error_context}: CQ 码参数值 '{now_value}' 中包含非法字符 '['")
            else:
                now_value += c  # 继续拼接值 (转义由 cq_decode 处理)

    # --- 循环结束后检查 ---
    final_error_context = f"在字符串末尾"
    if now_state != 0:
        if cq_start_pos != -1:
            # 根据当前状态给出更具体的错误提示
            if now_state == 1:
                error_detail = f"类型部分 '{now_segment_type}' 未完成"
            elif now_state == 2:
                error_detail = f"参数键 '{now_key}' 未完成或缺少 '='"
            elif now_state == 3:
                error_detail = f"参数值 '{now_value}' 未结束"
            else:  # 理论上不会有其他状态
                error_detail = f"解析停留在未知状态 {now_state}"
            raise ValueError(
                f"cq_2_array: {final_error_context}，起始于字符 {cq_start_pos} 的 CQ 码未正确结束 ({error_detail})")
        else:
            # 如果 cq_start_pos 是 -1 但状态不是 0，说明逻辑可能出错了
            raise ValueError(f"cq_2_array: {final_error_context}，解析器状态异常 ({now_state}) 但未记录 CQ 码起始位置")

    # 处理末尾可能剩余的普通文本
    if len(segment_data["text"]):
        cq_array.append({"type": "text", "data": {"text": cq_decode(segment_data["text"])}})

    return cq_array


def array_2_cq(cq_array: list[dict[str, dict[str, str]]] | dict[str, dict[str, str]]) -> str:
    """
    array消息段转CQCode
    Args:
        cq_array: array消息段数组
    Returns:
        CQCode
    """
    # 特判
    if isinstance(cq_array, dict):
        cq_array = [cq_array]

    if not isinstance(cq_array, (list, tuple)):
        raise TypeError("array_2_cq: 输入类型错误")

    # 将json形式的富文本转换为CQ码
    text = ""
    for segment in cq_array:
        segment_type = segment.get("type")
        if not isinstance(segment_type, str):
            # 或者根据需求跳过这个 segment
            raise ValueError(f"array_2_cq: 消息段缺少有效的 'type': {segment}")

        # 文本
        if segment_type == "text":
            data = segment.get("data")
            if not isinstance(data, dict):
                raise ValueError(f"array_2_cq: 'text' 类型的消息段缺少有效的 'data' 字典: {segment}")
            text_content = data.get("text")
            if not isinstance(text_content, str):
                raise ValueError(f"array_2_cq: 'text' 类型的消息段 'data' 字典缺少有效的 'text' 字符串: {segment}")
            text += cq_encode(text_content)
        # CQ码
        else:
            cq_type_str = f"[CQ:{segment_type}"
            data = segment.get("data")
            if isinstance(data, dict) and data:  # data 存在且是包含内容的字典
                params = []
                for key, value in data.items():
                    if not isinstance(key, str):
                        raise ValueError(
                            f"array_2_cq: '{segment_type}' 类型的消息段 'data' 字典的键 '{key}' 不是字符串")
                    if value is None:
                        continue
                    if isinstance(value, bool):
                        value = "1" if value else "0"
                    if not isinstance(value, str):
                        try:
                            value = str(value)
                        except Exception as e:
                            raise ValueError(f"array_2_cq: '{segment_type}' 类型的消息段 "
                                             f"'data' 字典的键 '{key}' 的值 '{value}' 无法被转换: {repr(e)}")
                    params.append(f"{cq_encode(key, in_cq=True)}={cq_encode(value, in_cq=True)}")
                if params:
                    text += cq_type_str + "," + ",".join(params) + "]"
                else:  # 如果 data 非空但过滤后 params 为空（例如 data 里全是 None 值）
                    text += cq_type_str + "]"
            else:  # data 不存在、为 None 或为空字典 {}
                text += cq_type_str + "]"
    return text


def convert_to_fileurl(input_str: str) -> str:
    """
    自动将输入的路径转换成fileurl
    Args:
        input_str: 输入的路径

    Returns:
        转换后的 fileurl
    """
    # 检查是否已经是 file:// 格式
    if input_str.startswith("file://"):
        return input_str

    # 检查输入是否是有效的 URL
    parsed_url = urlparse(input_str)
    if parsed_url.scheme in ['http', 'https', 'ftp', 'file', 'data']:
        return input_str  # 已经是 URL 格式，直接返回

    # 检查输入是否是有效的本地文件路径
    if os.path.isfile(input_str):
        # 转换为 file:// 格式
        return f"file://{os.path.abspath(input_str)}"

    # 如果是相对路径或其他文件类型，则尝试转换
    if os.path.exists(input_str):
        return f"file://{os.path.abspath(input_str)}"

    raise ValueError("输入的路径无效，无法转换为 fileurl 格式")


segments = []
segments_map = {}


class SegmentMeta(type):
    """
    元类用于自动注册 Segment 子类到全局列表 segments 和映射 segments_map 中。
    """

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if 'Segment' in globals() and issubclass(cls, Segment):
            segments.append(cls)  # 将子类添加到全局列表中
            segments_map[cls.segment_type] = cls


class Segment(metaclass=SegmentMeta):
    """
    消息段
    """
    segment_type = None

    def __init__(self, cq: str | dict[str, dict[str, str]] | "Segment"):
        self.cq = cq
        if isinstance(cq, str):
            array = cq_2_array(cq)
            if len(self.array) != 1:
                raise ValueError("cq_2_array: 输入 CQ 码格式错误")
            self.array = array[0]
        elif isinstance(cq, dict):
            self.array = cq
        else:
            for segment in segments:
                if isinstance(cq, segment):
                    self.array = cq.array
                    break
            else:
                raise TypeError("Segment: 输入类型错误")
        self.type = self.array["type"]
        self.data = self.array.get("data", {})

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        self.cq = array_2_cq(self.array)
        return self.cq

    def __setitem__(self, key, value):
        self.array[key] = value

    def __getitem__(self, key):
        return self.array.get(key)

    def get(self, key, default=None):
        """
        获取消息段中的数据
        Args:
            key: key
            default: 默认值（默认为None）

        Returns:
            获取到的数据
        """
        return self.array.get(key, default)

    def __delitem__(self, key):
        del self.array[key]

    def __eq__(self, other):
        other = Segment(other)
        return self.array == other.array

    def __contains__(self, other):
        if isinstance(other, Segment):
            return all(item in self.array for item in other.array)
        else:
            try:
                return str(other) in str(self)
            except (TypeError, AttributeError):
                return False

    def render(self, group_id: int | None = None):
        """
        渲染消息段为字符串
        Args:
            group_id: 群号（选填）
        Returns:
            渲染完毕的消息段
        """
        return f"[{self.array.get('type', 'unknown')}: {self.cq}]"

    def set_data(self, k, v):
        """
        设置消息段的Data项
        Args:
            k: 要修改的key
            v: 要修改成的value
        """
        self.array["data"][k] = v


segments.append(Segment)


class Text(Segment):
    """
    文本消息段
    """
    segment_type = "text"

    def __init__(self, text):
        """
        Args:
            text: 文本
        """
        self.text = text
        super().__init__({"type": "text", "data": {"text": text}})

    def __add__(self, other):
        other = Text(other)
        return self.text + other.text

    def __eq__(self, other):
        other = Text(other)
        return self.text == other.text

    def __contains__(self, other):
        if isinstance(other, Text):
            return other.text in self.text
        else:
            try:
                return str(other) in str(self.text)
            except (TypeError, AttributeError):
                return False

    def set_text(self, text):
        """
        设置文本
        Args:
            text: 文本
        """
        self.text = text
        self["data"]["text"] = text

    def render(self, group_id: int | None = None):
        return self.text


class Face(Segment):
    """
    表情消息段
    """
    segment_type = "face"

    def __init__(self, id_):
        """
        Args:
            id_: 表情id
        """
        self.id_ = id_
        super().__init__({"type": "face", "data": {"id": str(id_)}})

    def set_id(self, id_):
        """
        设置表情id
        Args:
            id_: 表情id
        """
        self.id_ = id_
        self.array["data"]["id"] = str(id_)

    def render(self, group_id: int | None = None):
        return f"[表情: {self.id_}]"


class At(Segment):
    """
    At消息段
    """
    segment_type = "at"

    def __init__(self, qq):
        """
        Args:
            qq: qq号
        """
        self.qq = qq
        super().__init__({"type": "at", "data": {"qq": str(qq)}})

    def set_id(self, qq_id):
        """
        设置At的id
        Args:
            qq_id: qq号
        """
        self.qq = qq_id
        self.array["data"]["qq"] = str(qq_id)

    def render(self, group_id: int | None = None):
        if group_id:
            if str(self.qq) == "all" or str(self.qq) == "0":
                return f"@全体成员"
            return f"@{QQDataCacher.get_group_member_info(group_id, self.qq).get_nickname()}: {self.qq}"
        else:
            return f"@{QQDataCacher.get_user_info(self.qq).nickname}: {self.qq}"


class Image(Segment):
    """
    图片消息段
    """
    segment_type = "image"

    def __init__(self, file: str):
        """
        Args:
            file: 图片文件(url，对于文件使用file url格式)
        """
        file = convert_to_fileurl(file)
        self.file = file
        super().__init__({"type": "image", "data": {"file": str(file)}})

    def set_file(self, file: str):
        """
        设置图片文件
        Args:
            file: 图片文件
        """
        file = convert_to_fileurl(file)
        self.file = file
        self.array["data"]["file"] = str(file)

    def render(self, group_id: int | None = None):
        return "[图片: %s]" % self.file


class Record(Segment):
    """
    语音消息段
    """
    segment_type = "record"

    def __init__(self, file: str):
        """
        Args:
            file: 语音文件(url，对于文件使用file url格式)
        """
        file = convert_to_fileurl(file)
        self.file = file
        super().__init__({"type": "record", "data": {"file": str(file)}})

    def set_file(self, file: str):
        """
        设置语音文件
        Args:
            file: 语音文件(url，对于文件使用file url格式)
        """
        file = convert_to_fileurl(file)
        self.file = file
        self.array["data"]["file"] = str(file)

    def render(self, group_id: int | None = None):
        return "[语音: %s]" % self.file


class Video(Segment):
    """
    视频消息段
    """
    segment_type = "video"

    def __init__(self, file: str):
        """
        Args:
            file: 视频文件(url，对于文件使用file url格式)
        """
        file = convert_to_fileurl(file)
        self.file = file
        super().__init__({"type": "video", "data": {"file": str(file)}})

    def set_file(self, file: str):
        """
        设置视频文件
        Args:
            file: 视频文件(url，对于文件使用file url格式)
        """
        file = convert_to_fileurl(file)
        self.file = file
        self.array["data"]["file"] = str(file)

    def render(self, group_id: int | None = None):
        return f"[视频: {self.file}]"


class Rps(Segment):
    """
    猜拳消息段
    """
    segment_type = "rps"

    def __init__(self):
        super().__init__({"type": "rps", "data": {}})


class Dice(Segment):
    segment_type = "dice"

    def __init__(self):
        super().__init__({"type": "dice", "data": {}})


class Shake(Segment):
    """
    窗口抖动消息段
    (相当于戳一戳最基本类型的快捷方式。)
    """
    segment_type = "shake"

    def __init__(self):
        super().__init__({"type": "shake", "data": {}})


class Poke(Segment):
    """
    戳一戳消息段
    """
    segment_type = "poke"

    def __init__(self, type_, id_):
        """
        Args:
            type_: 见https://github.com/botuniverse/onebot-11/blob/master/message/segment.md#%E6%88%B3%E4%B8%80%E6%88%B3
            id_: 同上
        """
        self.type = type_
        self.id_ = id_
        super().__init__({"type": "poke", "data": {"type": str(self.type)}, "id": str(self.id_)})

    def set_type(self, type_):
        """
        设置戳一戳类型
        Args:
            type_: 见https://github.com/botuniverse/onebot-11/blob/master/message/segment.md#%E6%88%B3%E4%B8%80%E6%88%B3
        """
        self.type = type_
        self.array["data"]["type"] = str(type_)

    def set_id(self, id_):
        """
        设置戳一戳id
        Args:
            id_: 戳一戳id
        """
        self.id_ = id_
        self.array["data"]["id"] = str(id_)

    def render(self, group_id: int | None = None):
        return f"[戳一戳: {self.type}]"


class Anonymous(Segment):
    """
    匿名消息段
    """
    segment_type = "anonymous"

    def __init__(self, ignore=False):
        """
        Args:
            ignore: 是否忽略
        """
        self.ignore = 0 if ignore else 1
        super().__init__({"type": "anonymous", "data": {"ignore": str(self.ignore)}})

    def set_ignore(self, ignore):
        """
        设置是否忽略
        Args:
            ignore: 是否忽略
        """
        self.ignore = 0 if ignore else 1
        self.array["data"]["ignore"] = str(self.ignore)


class Share(Segment):
    """
    链接分享消息段
    """
    segment_type = "share"

    def __init__(self, url, title, content="", image=""):
        """
        Args:
            url: URL
            title: 标题
            content: 发送时可选，内容描述
            image: 发送时可选，图片 URL
        """
        self.url = url
        self.title = title
        self.content = content
        self.image = image
        super().__init__({"type": "share", "data": {"url": str(self.url), "title": str(self.title)}})

        if content != "":
            self.array["data"]["content"] = str(self.content)

        if image != "":
            self.array["data"]["image"] = str(self.image)

    def set_url(self, url):
        """
        设置URL
        Args:
            url: URL
        """
        self.array["data"]["url"] = str(url)
        self.url = url

    def set_title(self, title):
        """
        设置标题
        Args:
            title: 标题
        """
        self.title = title
        self.array["data"]["title"] = str(title)

    def set_content(self, content):
        """
        设置内容描述
        Args:
            content: 内容描述
        """
        self.content = content
        self.array["data"]["content"] = str(content)

    def set_image(self, image):
        """
        设置图片 URL
        Args:
            image: 图片 URL
        """
        self.image = image
        self.array["data"]["image"] = str(image)


class Contact(Segment):
    """
    推荐好友/推荐群
    """
    segment_type = "contact"

    def __init__(self, type_, id_):
        """
        Args:
            type_: 推荐的类型（friend/group）
            id_: 推荐的qqid
        """
        self.type = type_
        self.id = id_
        super().__init__({"type": "contact", "data": {"type": str(self.type), "id": str(self.id)}})

    def set_type(self, type_):
        """
        设置推荐类型
        Args:
            type_: 推荐的类型（friend/group）
        """
        self.type = type_
        self.array["data"]["type"] = str(type_)

    def set_id(self, id_):
        """
        设置推荐的qqid
        Args:
            id_: qqid
        """
        self.id = id_
        self.array["data"]["id"] = str(id_)


class Location(Segment):
    """
    位置消息段
    """
    segment_type = "location"

    def __init__(self, lat, lon, title="", content=""):
        """
        Args:
            lat: 纬度
            lon: 经度
            title: 发送时可选，标题
            content: 发送时可选，内容描述
        """
        self.lat = lat
        self.lon = lon
        self.title = title
        self.content = content
        super().__init__({"type": "location", "data": {"lat": str(self.lat), "lon": str(self.lon)}})

        if title != "":
            self.array["data"]["title"] = str(self.title)

        if content != "":
            self.array["data"]["content"] = str(self.content)

    def set_lat(self, lat):
        """
        设置纬度
        Args:
            lat: 纬度
        """
        self.lat = lat
        self.array["data"]["lat"] = str(lat)

    def set_lon(self, lon):
        """
        设置经度
        Args:
            lon: 经度
        """
        self.lon = lon
        self.array["data"]["lon"] = str(lon)

    def set_title(self, title):
        """
        设置标题
        Args:
            title: 标题
        """
        self.title = title
        self.array["data"]["title"] = str(title)

    def set_content(self, content):
        """
        设置内容描述
        Args:
            content: 内容描述
        """
        self.content = content
        self.array["data"]["content"] = str(content)


class Node(Segment):
    """
    合并转发消息节点
    接收时，此消息段不会直接出现在消息事件的 message 中，需通过 get_forward_msg API 获取。
    这是最阴间的消息段之一，tm的Onebot协议，各种转换的细节根本就没定义清楚，感觉CQ码的支持就像后加的，而且纯纯草台班子
    """
    segment_type = "node"

    def __init__(self, name: str, user_id: int, message, message_id: int = None):
        """
        Args:
            name: 发送者昵称
            user_id: 发送者 QQ 号
            message: 消息内容
            message_id: 消息 ID（选填，若设置，上面三者失效）
        """
        if message_id is None:
            self.name = name
            self.user_id = user_id
            self.message = QQRichText(message).get_array()
            super().__init__({"type": "node", "data": {"nickname": str(self.name), "user_id": str(self.user_id),
                                                       "content": self.message}})
        else:
            self.message_id = message_id
            super().__init__({"type": "node", "data": {"id": str(message_id)}})

    def set_message(self, message):
        """
        设置消息
        Args:
            message: 消息内容
        """
        self.message = QQRichText(message).get_array()
        self.array["data"]["content"] = self.message

    def set_name(self, name):
        """
        设置发送者昵称
        Args:
            name: 发送者昵称
        """
        self.name = name
        self.array["data"]["name"] = str(name)

    def set_user_id(self, user_id):
        """
        设置发送者 QQ 号
        Args:
            user_id: 发送者 QQ 号
        """
        self.user_id = user_id
        self.array["data"]["uin"] = str(user_id)

    def render(self, group_id: int | None = None):
        if self.message_id is not None:
            return f"[合并转发节点: {self.name}({self.user_id}): {self.message}]"
        else:
            return f"[合并转发节点: {self.message_id}]"

    def __repr__(self):
        """
        去tm的CQ码
        Raises:
            NotImplementedError: 暂不支持此方法
        """
        raise NotImplementedError("不支持将Node转成CQ码")


class Music(Segment):
    """
    音乐消息段
    """
    segment_type = "music"

    def __init__(self, type_, id_):
        """
        Args:
            type_: 音乐类型（可为qq 163 xm）
            id_: 音乐 ID
        """
        self.type = type_
        self.id = id_
        super().__init__({"type": "music", "data": {"type": str(self.type), "id": str(self.id)}})

    def set_type(self, type_):
        """
        设置音乐类型
        Args:
            type_: 音乐类型（qq 163 xm）
        """
        self.type = type_
        self.array["data"]["type"] = str(type_)

    def set_id(self, id_):
        """
        设置音乐 ID
        Args:
            id_: 音乐 ID
        """
        self.id = id_
        self.array["data"]["id"] = str(id_)


class CustomizeMusic(Segment):
    """
    自定义音乐消息段
    """
    segment_type = "music"

    def __init__(self, url, audio, image, title="", content=""):
        """
        Args:
            url: 点击后跳转目标 URL
            audio: 音乐 URL
            image: 标题
            title: 发送时可选，内容描述
            content: 发送时可选，图片 URL
        """
        self.url = url
        self.audio = audio
        self.image = image
        self.title = title
        self.content = content
        super().__init__({"type": "music", "data": {"type": "custom", "url": str(self.url), "audio": str(self.audio),
                                                    "image": str(self.image)}})
        if title != "":
            self.array["data"]["title"] = str(self.title)

        if content != "":
            self.array["data"]["content"] = str(self.content)

    def set_url(self, url):
        """
        设置 URL
        Args:
            url: 点击后跳转目标 URL
        """
        self.url = url
        self.array["data"]["url"] = str(url)

    def set_audio(self, audio):
        """
        设置音乐 URL
        Args:
            audio: 音乐 URL
        """
        self.audio = audio
        self.array["data"]["audio"] = str(audio)

    def set_image(self, image):
        """
        设置图片 URL
        Args:
            image: 图片 URL
        """
        self.image = image
        self.array["data"]["image"] = str(image)

    def set_title(self, title):
        """
        设置标题
        Args:
            title: 标题
        """
        self.title = title
        self.array["data"]["title"] = str(title)

    def set_content(self, content):
        """
        设置内容描述
        Args:
            content:
        """
        self.content = content
        self.array["data"]["content"] = str(content)


class Reply(Segment):
    """
    回复消息段
    """
    segment_type = "reply"

    def __init__(self, id_):
        """
        Args:
            id_: 回复消息 ID
        """
        self.id_ = id_
        super().__init__({"type": "reply", "data": {"id": str(self.id_)}})

    def set_id(self, id_):
        """
        设置消息 ID
        Args:
            id_: 消息 ID
        """
        self.id_ = id_
        self.array["data"]["id"] = str(self.id_)

    def render(self, group_id: int | None = None):
        return f"[回复: {self.id_}]"


class Forward(Segment):
    """
    合并转发消息段
    """
    segment_type = "forward"

    def __init__(self, id_):
        """
        Args:
            id_: 合并转发消息 ID
        """
        self.id_ = id_
        super().__init__({"type": "forward", "data": {"id": str(self.id_)}})

    def set_id(self, id_):
        """
        设置合并转发 ID
        Args:
            id_: 合并转发消息 ID
        """
        self.id_ = id_
        self.array["data"]["id"] = str(self.id_)

    def render(self, group_id: int | None = None):
        return f"[合并转发: {self.id_}]"


class XML(Segment):
    """
    XML消息段
    """
    segment_type = "xml"

    def __init__(self, data):
        self.xml_data = data
        super().__init__({"type": "xml", "data": {"data": str(self.xml_data)}})

    def set_xml_data(self, data):
        """
        设置xml数据
        Args:
            data: xml数据
        """
        self.xml_data = data
        self.array["data"]["data"] = str(self.xml_data)


class JSON(Segment):
    """
    JSON消息段
    """
    segment_type = "json"

    def __init__(self, data):
        """
        Args:
            data: JSON 内容
        """
        self.json_data = data
        super().__init__({"type": "json", "data": {"data": str(self.json_data)}})

    def set_json(self, data):
        """
        设置json数据
        Args:
            data: json 内容
        """
        self.json_data = data
        self.array["data"]["data"] = str(self.json_data)

    def get_json(self):
        """
        获取json数据（自动序列化）
        Returns:
            json: json数据
        """
        return json.loads(self.json_data)


def _create_segment_from_dict(segment_dict: dict) -> Segment:
    """从单个字典（array格式）创建Segment对象"""
    # 这个辅助函数和你代码中的对象化逻辑是一样的
    segment_type = segment_dict.get("type")
    if segment_type in segments_map:
        try:
            params = inspect.signature(segments_map[segment_type]).parameters
            kwargs = {}
            data = segment_dict.get("data", {})
            for param in params:
                if param in data:
                    kwargs[param] = data[param]
                elif param == "id_":
                    kwargs[param] = data.get("id")
                elif param == "type_":
                    kwargs[param] = data.get("type")
                elif params[param].default != params[param].empty:
                    kwargs[param] = params[param].default

            segment = segments_map[segment_type](**kwargs)

            for k, v in data.items():
                if k not in segment.data:
                    segment.set_data(k, v)
            return segment
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"转换{segment_dict}时失败")
            else:
                dump_path = None
            Logger.get_logger().warning(f"转换{segment_dict}时失败，报错信息: {repr(e)}"
                                        f"{f"\n已保存异常到 {dump_path}" if dump_path else ""}",
                                        exc_info=True)
            return Segment(segment_dict)
    return Segment(segment_dict)


class QQRichText:
    """
    QQ富文本
    """

    def __init__(
            self,
            *rich: dict[str, dict[str, str]] | str | Segment | "QQRichText" | list[
                dict[str, dict[str, str]] | str | Segment | "QQRichText"]
    ):
        """
        Args:
            *rich: 富文本内容，可为 str、dict、list、tuple、Segment、QQRichText
        """
        # __init__ 现在只做一件事：消费一个生成器来构建最终的列表
        self.rich_array: list[Segment] = list(self._iter_and_convert_segments(rich))

    def _iter_and_convert_segments(self, rich_items) -> Generator[Segment, None, None]:
        """
        核心优化：单遍处理所有输入，并直接 yield 最终的 Segment 对象。
        这完美实现了你“合并处理”的想法。
        """
        # 1. 扁平化初始输入
        if len(rich_items) == 1 and isinstance(rich_items[0], (list, tuple)):
            rich_items = rich_items[0]

        # 2. 单遍处理所有项目
        for item in rich_items:
            # 分类处理，直接生成并yield Segment对象
            if any(isinstance(item, segment) for segment in segments) and not isinstance(item, Segment):
                yield item
            elif isinstance(item, Segment):
                yield _create_segment_from_dict(item.array)
            elif isinstance(item, QQRichText):
                yield from item.rich_array
            elif isinstance(item, str):
                for arr in cq_2_array(item):
                    yield _create_segment_from_dict(arr)
            elif isinstance(item, dict):
                yield _create_segment_from_dict(item)
            elif isinstance(item, (list, tuple)):
                yield from self._iter_and_convert_segments(item)
            else:
                raise TypeError(f"QQRichText: 不支持的输入类型 {type(item)}")

    def render(self, group_id: int | None = None):
        """
        渲染消息（调用rich_array下所有消息段的render方法拼接）
        Args:
            group_id: 群号，选填，可优化效果
        """
        return "".join(rich.render(group_id=group_id) for rich in self.rich_array)

    def __str__(self):
        return array_2_cq(self.get_array())

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, index):
        return self.rich_array[index]

    def __add__(self, other):
        other = QQRichText(other)
        return QQRichText(self.rich_array + other.rich_array)

    def __eq__(self, other):
        other = QQRichText(other)

        return self.rich_array == other.rich_array

    def __contains__(self, other):
        if isinstance(other, QQRichText):
            return all(item in self.rich_array for item in other.rich_array)
        else:
            try:
                return str(other) in str(self)
            except (TypeError, AttributeError):
                return False

    def __bool__(self):
        return bool(self.rich_array)

    def get_array(self) -> list[dict[str, dict[str, str]]]:
        """
        获取rich_array的纯数组形式（用于序列化）
        Returns:
            rich_array
        """
        return [array.array for array in self.rich_array]

    def add(self, *segments):
        """
        添加消息段
        Args:
            *segments: 消息段

        Returns:
            self
        """
        res = QQRichText(self)
        for segment in segments:
            if isinstance(segment, Segment):
                res.rich_array.append(segment)
            else:
                res.rich_array += QQRichText(segment).rich_array
        return res

    def strip(self) -> QQRichText:
        """
        去除富文本开头和结尾如果是文本消息段包含的空格和换行，如果去除后没有内容自动删除该消息段，返回处理完成的新的QQRichText
        """
        res = QQRichText(self)
        if len(res.rich_array) == 0:
            return res

        index = 0
        for _ in range(2 if len(res.rich_array) else 1):
            if isinstance(res.rich_array[index], Text):
                res.rich_array[index].set_text(res.rich_array[index].text.strip())
                if not res.rich_array[index].text:
                    res.rich_array.pop(index)
                    if not res.rich_array:
                        break
            index = -1
        return res


# 使用示例
if __name__ == "__main__":
    # 测试CQ解码
    print(cq_decode(" - &#91;x&#93; 使用 `&amp;data` 获取地址"))

    # 测试CQ编码
    print(cq_encode(" - [x] 使用 `&data` 获取地址"))

    # 测试QQRichText
    rich = QQRichText(
        " [CQ:reply,id=123][CQ:share,title=标题,url=https://baidu.com] [CQ:at,qq=1919810,abc=123] -  &#91;x&#93; 使用 "
        " `&amp;data` 获取地址\n ")
    print(rich.get_array())

    print(rich)
    print("123" + str(rich.strip()) + "123")
    print(rich.render())

    print(QQRichText(rich))

    print(QQRichText(At(114514), At(1919810), "114514", Reply(133).array))
    print(Segment(At(1919810)))
    print(QQRichText([{"type": "text", "data": {"text": "1919810"}}]))
    print(QQRichText().add(At(114514)).add(Text("我吃柠檬")) + QQRichText(At(1919810)).rich_array)
    rich_array = [{'type': 'at', 'data': {'qq': '123'}}, {'type': 'text', 'data': {'text': '[期待]'}}]
    rich = QQRichText(rich_array)
    print(rich)
    print(rich.get_array())

    print("--- 正确示例 ---")
    print(cq_2_array("你好[CQ:face,id=123]世界[CQ:image,file=abc.jpg,url=http://a.com/b?c=1&d=2]"))
    print(cq_2_array("[CQ:shake]"))
    print(cq_2_array("只有文本"))
    print(cq_2_array("[CQ:at,qq=123][CQ:at,qq=456]"))

    print("\n--- 错误示例 ---")
    # 触发不同类型的 ValueError
    error_inputs = [
        "文本[CQ:face,id=123",  # 未闭合 (类型 3 结束)
        "文本[CQ:face,id]",  # 缺少=
        "文本[CQ:,id=123]",  # 类型为空
        "文本[NotCQ:face,id=123]",  # 非 CQ: 开头
        "文本[:face,id=123]",  # 非 CQ: 开头 (更具体)
        "文本[CQ:face,id=123,id=456]",  # 重复键
        "文本[CQ:face,,id=123]",  # 多余逗号 (会导致空键名错误)
        "文本[CQ:fa[ce,id=123]",  # 类型中非法字符 '['
        "文本[CQ:face,ke[y=value]",  # 键中非法字符 '['
        "文本[CQ:face,key=val]ue]",  # 文本中非法字符 ']'
        "[",  # 未闭合 (类型 1 结束)
        "[CQ",  # 未闭合 (类型 1 结束)
        "[CQ:",  # 未闭合 (类型 1 结束)
        "[CQ:type,",  # 未闭合 (类型 2 结束)
        "[CQ:type,key",  # 未闭合 (类型 2 结束)
        "[CQ:type,key=",  # 未闭合 (类型 3 结束)
        "[CQ:type,key=value"  # 未闭合 (类型 2 结束)
    ]
    for err_cq in error_inputs:
        try:
            print(f"\nTesting: {err_cq}")
            cq_2_array(err_cq)
        except ValueError as e:
            print(f"捕获到错误: {e}")
