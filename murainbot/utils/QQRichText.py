"""
QQ富文本
"""
from __future__ import annotations

import inspect
import json
import os
import re
from copy import deepcopy
from pathlib import Path, PureWindowsPath
from typing import Generator, Literal

from murainbot.common import save_exc_dump
from murainbot.core import ConfigManager
from murainbot.utils import QQDataCacher, Logger

logger = Logger.get_logger()

# URL正则，参考 RFC 3986
_URL_RE = re.compile(
    r'^'  # 行首
    r'([A-Za-z][A-Za-z0-9+.-]*)'  # scheme
    r':'  # 冒号
    r'(?:(//([^/?#\s]+)([^\s#]*))'  # 方案 A: '//' authority (必有 authority) + 可选 path
    r'|(?!//)([^\s#]*))'  # 方案 B: 没有 '//'，允许任意 path（但不能以 '//' 开头）
    r'(?:#\S*)?'  # 可选 fragment
    r'$'  # 行尾
)

_WINDOWS_DRIVE_RE = re.compile(r'^[A-Za-z]:[\\/]')

_UNC_RE = re.compile(r'^[\\/]{2}')


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


def convert_to_fileurl(input_str: str | os.PathLike) -> str:
    """
    自动将输入的路径转换成fileurl
    Args:
        input_str: 输入的路径

    Returns:
        转换后的 fileurl
    """
    # 支持 PathLike 和 str
    if not isinstance(input_str, (str, os.PathLike)):
        raise TypeError("input must be a str or os.PathLike")

    s = os.fspath(input_str).strip()

    # 如果显式是 Windows 驱动器路径或 UNC，即便当前平台不是 Windows，也当作文件路径处理
    if _WINDOWS_DRIVE_RE.match(s) or _UNC_RE.match(s):
        try:
            p = PureWindowsPath(s)
        except Exception:
            logger.exception("无效的路径输入")
            return s
        if not p.is_absolute():
            raise ValueError(f"输入的路径 {s} 不是绝对路径，请使用绝对路径")
        try:
            return p.as_uri()
        except Exception:
            logger.exception("路径转换为 URI 失败")
            return s

    # 当前平台感知的绝对路径优先
    if os.path.isabs(s):
        try:
            p = Path(s)
        except Exception:
            logger.exception("无效的路径输入")
            return s
        return p.as_uri()

    # 判断是否是 URL（更保守的判断）
    if _URL_RE.match(s):
        return s

    # 否则认为输入既不是绝对路径也不是可接受的 URL
    logger.warning(f"输入的路径 {s} 不是绝对路径，也不是被接受的 URL")
    return s


segments = []
segments_map: dict[str, type[Segment]] = {}


class SegmentMeta(type):
    """
    元类用于自动注册 Segment 子类到全局列表 segments 和映射 segments_map 中。
    """

    def __init__(cls: type[Segment], name, bases, dct):
        super().__init__(name, bases, dct)

        # 检查类是否想要被注册
        if getattr(cls, "_register", True):
            # 确保 'Segment' 已经定义，并且当前类是 Segment 的子类但不是 Segment 本身
            if 'Segment' in globals() and issubclass(cls, Segment) and cls is not Segment:
                if not cls.segment_type:
                    # 对于要注册的类，必须有一个有效的 segment_type
                    raise TypeError(f"无法注册类 {name}，因为它没有设置 segment_type 属性。")

                segments.append(cls)
                segments_map[cls.segment_type] = cls


class Segment(metaclass=SegmentMeta):
    """
    消息段
    """
    segment_type = None
    _register = True

    def __init__(self, cq: str | dict[str, dict[str, str]] | Segment):
        # 统一处理输入，最终得到 _seg_dict
        if isinstance(cq, str):
            array = cq_2_array(cq)
            if len(array) != 1:
                raise ValueError("cq_2_array: 输入 CQ 码格式错误")
            self._seg_dict = array[0]
        elif isinstance(cq, dict):
            # 进行深拷贝，防止外部修改传入的字典影响到对象内部状态
            self._seg_dict = deepcopy(cq)
        elif isinstance(cq, Segment):
            # 访问seg_dict，创建一个完全独立的Segment副本
            self._seg_dict = cq.seg_dict
        else:
            raise TypeError("Segment: 输入类型错误")

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Segment:
        """
        从seg_dict创建一个Segment对象，由子类实现
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Segment对象
        """
        raise NotImplementedError("Segment: creat_from_seg_dict 方法未实现")

    @property
    def type(self) -> str:
        """获取消息段类型，直接从底层字典读取。"""
        return self.get("type")

    @type.setter
    def type(self, value: str):
        """设置消息段类型，直接修改底层字典。"""
        self["type"] = value

    @property
    def data(self) -> dict:
        """
        获取data字典。
        直接返回底层字典中的data字典的引用。
        如果data不存在，则创建并返回一个空字典。
        """
        return self._seg_dict.setdefault("data", {})

    @data.setter
    def data(self, value: dict):
        """设置data字典，直接修改底层字典。"""
        if not isinstance(value, dict):
            raise TypeError("data 必须是一个字典")
        self._seg_dict["data"] = value

    @property
    def seg_dict(self) -> dict:
        """获取当前Segment的字典的拷贝。"""
        return deepcopy(self._seg_dict)

    def __str__(self):
        return array_2_cq(self._seg_dict)

    def __repr__(self):
        return f"Segment({self._seg_dict!r})"  # repr应该更明确

    def __eq__(self, other):
        if not isinstance(other, Segment):
            try:
                other = Segment(other)
            except (TypeError, ValueError):
                return NotImplemented
        return self._seg_dict == other._seg_dict

    def get(self, key, default=None):
        return self._seg_dict.get(key, default)

    def __getitem__(self, key):
        return self._seg_dict[key]

    def __setitem__(self, key, value):
        self._seg_dict[key] = value

    def __delitem__(self, key):
        del self._seg_dict[key]

    def set_data(self, key, value):
        """设置消息段的Data项。"""
        self.data[key] = value

    def get_data(self, key, default=None):
        """获取消息段的Data项。"""
        return self.data.get(key, default)

    def copy(self):
        """
        复制消息段，深拷贝
        Returns:
            新的Segment对象
        """
        return Segment(self)

    def render(self, group_id: int | None = None):
        """
        渲染消息段为字符串
        Args:
            group_id: 群号（选填）
        Returns:
            渲染完毕的消息段
        """
        return f"[{self.type}: {self}]"


segments.append(Segment)


class Text(Segment):
    """
    文本
    """
    segment_type = "text"

    def __init__(self, text: str):
        super().__init__({"type": self.segment_type, "data": {"text": str(text)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Text:
        """
        从seg_dict创建一个Text对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Text对象
        """
        return cls(text=seg_dict.get("data", {}).get("text", ""))

    @property
    def text(self) -> str:
        return self.data.get("text", "")

    @text.setter
    def text(self, value: str):
        self.data["text"] = str(value)

    def __bool__(self):
        return bool(self.text)

    def render(self, group_id: int | None = None) -> str:
        return self.text


class Face(Segment):
    """
    表情
    """
    segment_type = "face"

    def __init__(self, id_: int | str):
        super().__init__({"type": self.segment_type, "data": {"id": str(id_)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Face:
        """
        从seg_dict创建一个Face对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Face对象
        """
        return cls(id_=seg_dict.get("data", {}).get("id"))

    @property
    def id(self) -> str:
        return self.data.get("id")

    @id.setter
    def id(self, value: int | str):
        self.data["id"] = str(value)

    def render(self, group_id: int | None = None) -> str:
        return f"[表情: {self.id}]"


class At(Segment):
    """
    At
    """
    segment_type = "at"

    def __init__(self, qq: int | str):
        super().__init__({"type": self.segment_type, "data": {"qq": str(qq)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> At:
        """
        从seg_dict创建一个At对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            At对象
        """
        return cls(qq=seg_dict.get("data", {}).get("qq"))

    @property
    def qq(self) -> str:
        return self.data.get("qq")

    @qq.setter
    def qq(self, value: int | str):
        self.data["qq"] = str(value)

    def render(self, group_id: int | None = None) -> str:
        if self.qq in ["all", "0"]:
            return "@全体成员"
        try:
            qq = int(self.qq)
        except ValueError:
            return f"@{self.qq}"
        if group_id:
            return f"@{QQDataCacher.get_group_member_info(group_id, qq).get_nickname()}: {self.qq}"
        else:
            return f"@{QQDataCacher.get_user_info(qq).get_nickname()}: {self.qq}"


class Image(Segment):
    """
    图片
    """
    segment_type = "image"

    def __init__(self, file: str):
        super().__init__({"type": self.segment_type, "data": {"file": convert_to_fileurl(file)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Image:
        """
        从seg_dict创建一个Image对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Image对象
        """
        # __init__会处理convert_to_fileurl，直接传递参数即可
        return cls(file=seg_dict.get("data", {}).get("url", seg_dict.get("data", {}).get("file", "")))

    @property
    def file(self) -> str:
        return self.data.get("file")

    @file.setter
    def file(self, value: str):
        self.data["file"] = convert_to_fileurl(value)

    def render(self, group_id: int | None = None) -> str:
        return f"[图片: {self.file}]"


class Record(Segment):
    """
    语音
    """
    segment_type = "record"

    def __init__(self, file: str):
        super().__init__({"type": self.segment_type, "data": {"file": convert_to_fileurl(file)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Record:
        """
        从seg_dict创建一个Record对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Record对象
        """
        return cls(file=seg_dict.get("data", {}).get("url", seg_dict.get("data", {}).get("file", "")))

    @property
    def file(self) -> str:
        return self.data.get("file")

    @file.setter
    def file(self, value: str):
        self.data["file"] = convert_to_fileurl(value)

    def render(self, group_id: int | None = None) -> str:
        return f"[语音: {self.file}]"


class Video(Segment):
    """
    视频
    """
    segment_type = "video"

    def __init__(self, file: str):
        super().__init__({"type": self.segment_type, "data": {"file": convert_to_fileurl(file)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Video:
        """
        从seg_dict创建一个Video对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Video对象
        """
        return cls(file=seg_dict.get("data", {}).get("url", seg_dict.get("data", {}).get("file", "")))

    @property
    def file(self) -> str:
        return self.data.get("file")

    @file.setter
    def file(self, value: str):
        self.data["file"] = convert_to_fileurl(value)

    def render(self, group_id: int | None = None) -> str:
        return f"[视频: {self.file}]"


class Rps(Segment):
    """
    猜拳魔法表情
    """
    segment_type = "rps"

    def __init__(self):
        super().__init__({"type": self.segment_type, "data": {}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Rps:
        """
        从seg_dict创建一个Rps对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Rps对象
        """
        return cls()


class Dice(Segment):
    """
    掷骰子魔法表情
    """
    segment_type = "dice"

    def __init__(self):
        super().__init__({"type": self.segment_type, "data": {}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Dice:
        """
        从seg_dict创建一个Dice对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Dice对象
        """
        return cls()


class Shake(Segment):
    """
    窗口抖动
    (相当于戳一戳最基本类型的快捷方式。)
    """
    segment_type = "shake"

    def __init__(self):
        super().__init__({"type": self.segment_type, "data": {}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Shake:
        """
        从seg_dict创建一个Shake对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Shake对象
        """
        return cls()


class Poke(Segment):
    """
    戳一戳
    """
    segment_type = "poke"

    def __init__(self, type_: str | int, id_: str | int):
        super().__init__({"type": self.segment_type, "data": {"type": str(type_), "id": str(id_)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Poke:
        """
        从seg_dict创建一个Poke对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Poke对象
        """
        data = seg_dict.get("data", {})
        return cls(type_=data.get("type"), id_=data.get("id"))

    @property
    def poke_type(self) -> str:
        return self.data.get("type")

    @poke_type.setter
    def poke_type(self, value: str | int):
        self.data["type"] = str(value)

    @property
    def id(self) -> str:
        return self.data.get("id")

    @id.setter
    def id(self, value: str | int):
        self.data["id"] = str(value)

    def render(self, group_id: int | None = None) -> str:
        return f"[戳一戳: type={self.poke_type}, id={self.id}]"


class Anonymous(Segment):
    """
    匿名消息
    """
    segment_type = "anonymous"

    def __init__(self, ignore: bool = False):
        super().__init__({"type": self.segment_type, "data": {"ignore": "0" if ignore else "1"}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Anonymous:
        """
        从seg_dict创建一个Anonymous对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Anonymous对象
        """
        # __init__中的逻辑是反的：ignore=True 存 "0"，ignore=False 存 "1"
        # 因此这里也需要反向转换
        ignore_val = seg_dict.get("data", {}).get("ignore")
        return cls(ignore=(ignore_val == "0"))

    @property
    def ignore(self) -> bool:
        return self.data.get("ignore", "0") != "0"

    @ignore.setter
    def ignore(self, value: bool):
        self.data["ignore"] = "0" if value else "1"


class Share(Segment):
    """
    链接分享
    """
    segment_type = "share"

    def __init__(self, url: str, title: str, content: str = "", image: str = ""):
        data = {"url": str(url), "title": str(title)}
        if content:
            data["content"] = str(content)
        if image:
            data["image"] = str(image)
        super().__init__({"type": self.segment_type, "data": data})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Share:
        """
        从seg_dict创建一个Share对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Share对象
        """
        data = seg_dict.get("data", {})
        return cls(
            url=data.get("url"),
            title=data.get("title"),
            content=data.get("content", ""),
            image=data.get("image", "")
        )

    @property
    def url(self) -> str:
        return self.data.get("url")

    @url.setter
    def url(self, value: str):
        self.data["url"] = str(value)

    @property
    def title(self) -> str:
        return self.data.get("title")

    @title.setter
    def title(self, value: str):
        self.data["title"] = str(value)

    @property
    def content(self) -> str:
        return self.data.get("content")

    @content.setter
    def content(self, value: str):
        self.data["content"] = str(value)

    @property
    def image(self) -> str:
        return self.data.get("image")

    @image.setter
    def image(self, value: str):
        self.data["image"] = str(value)


class Contact(Segment):
    """
    推荐好友/推荐群
    """
    segment_type = "contact"

    def __init__(self, type_: str, id_: str | int):
        super().__init__({"type": self.segment_type, "data": {"type": str(type_), "id": str(id_)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Contact:
        """
        从seg_dict创建一个Contact对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Contact对象
        """
        data = seg_dict.get("data", {})
        return cls(type_=data.get("type"), id_=data.get("id"))

    @property
    def contact_type(self) -> str: return self.data.get("type")

    @contact_type.setter
    def contact_type(self, value: str): self.data["type"] = str(value)

    @property
    def id(self) -> str: return self.data.get("id")

    @id.setter
    def id(self, value: str | int): self.data["id"] = str(value)


class Location(Segment):
    segment_type = "location"

    def __init__(self, lat: float | str, lon: float | str, title: str = "", content: str = ""):
        data = {"lat": str(lat), "lon": str(lon)}
        if title:
            data["title"] = str(title)
        if content:
            data["content"] = str(content)
        super().__init__({"type": self.segment_type, "data": data})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Location:
        """
        从seg_dict创建一个Location对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Location对象
        """
        data = seg_dict.get("data", {})
        return cls(
            lat=data.get("lat"),
            lon=data.get("lon"),
            title=data.get("title", ""),
            content=data.get("content", "")
        )

    @property
    def lat(self) -> str:
        return self.data.get("lat")

    @lat.setter
    def lat(self, value: float | str):
        self.data["lat"] = str(value)

    @property
    def lon(self) -> str:
        return self.data.get("lon")

    @lon.setter
    def lon(self, value: float | str):
        self.data["lon"] = str(value)

    @property
    def title(self) -> str:
        return self.data.get("title")

    @title.setter
    def title(self, value: str):
        self.data["title"] = str(value)

    @property
    def content(self) -> str:
        return self.data.get("content")

    @content.setter
    def content(self, value: str):
        self.data["content"] = str(value)


class Node(Segment):
    """
    合并转发消息节点
    ***此消息段不可被放入QQRichText内***
    接收时，此消息段不会直接出现在消息事件的 message 中，需通过 get_forward_msg API 获取。
    这是最阴间的消息段之一，tm的Onebot协议，各种转换的细节根本就没定义清楚，感觉CQ码的支持就像后加的，而且纯纯草台班子
    """
    segment_type = "node"
    _register = False  # 防止被注册

    def __init__(self, nickname: str = None, user_id: int = None, content: QQRichText | list[dict | Segment] = None,
                 message_id: int = None):
        """
        Args:
            nickname: 发送者昵称
            user_id: 发送者 QQ 号
            content: 消息内容
            message_id: 消息 ID（选填，若设置，上面三者失效）
        """
        if message_id is None:
            if not isinstance(content, QQRichText):
                content = QQRichText(content)
            super().__init__({"type": self.segment_type, "data": {"nickname": str(nickname), "user_id": str(user_id),
                                                                  "content": content.get_array()}})
        else:
            self.message_id = message_id
            super().__init__({"type": self.segment_type, "data": {"id": str(message_id)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Node:
        """
        从seg_dict创建一个Node对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Node对象
        """
        data = seg_dict.get("data", {})
        if "id" in data:
            return cls(message_id=data.get("id"))
        else:
            return cls(
                nickname=data.get("nickname"),
                user_id=data.get("user_id"),
                content=data.get("content")
            )

    @property
    def id(self) -> int:
        return self.data.get("id")

    @id.setter
    def id(self, value: int):
        self.data["id"] = str(value)

    @property
    def nickname(self) -> str:
        return self.data.get("nickname")

    @nickname.setter
    def nickname(self, value: str):
        self.data["nickname"] = str(value)

    @property
    def user_id(self) -> int:
        return self.data.get("user_id")

    @user_id.setter
    def user_id(self, value: int):
        self.data["user_id"] = str(value)

    @property
    def content(self) -> QQRichText:
        return self.data.get("content")

    @content.setter
    def content(self, value: QQRichText):
        self.data["content"] = value.get_array()

    def get_content(self) -> QQRichText:
        return QQRichText(self.data.get("content"))

    def render(self, group_id: int | None = None):
        if self.message_id is not None:
            return f"[合并转发节点: {self.nickname}({self.user_id}): {self.get_content()}]"
        else:
            return f"[合并转发节点: {self.id}]"

    def __str__(self):
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

    def __init__(self, type_: Literal["qq", "163", "xm"], id_):
        """
        Args:
            type_: 音乐类型（可为qq 163 xm）
            id_: 音乐 ID
        """
        super().__init__({"type": self.segment_type, "data": {"type": str(type_), "id": str(id_)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Music:
        """
        从seg_dict创建一个Music对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Music对象
        """
        data = seg_dict.get("data", {})
        # 对于自定义音乐类型，应使用CustomizeMusic类
        if data.get("type") == "custom":
            return CustomizeMusic.creat_from_seg_dict(seg_dict)
        return cls(type_=data.get("type"), id_=data.get("id"))

    @property
    def type(self) -> str:
        return self.data.get("type")

    @type.setter
    def type(self, value: str):
        self.data["type"] = str(value)

    @property
    def id(self) -> str:
        return self.data.get("id")

    @id.setter
    def id(self, value: str):
        self.data["id"] = str(value)


class CustomizeMusic(Segment):
    """
    自定义音乐消息段
    """
    segment_type = "music"

    def __init__(self, url: str, audio: str, title: str, image: str = "", content: str = ""):
        """
        Args:
            url: 点击后跳转目标 URL
            audio: 音乐 URL
            title: 标题
            image: 发送时可选，图片 URL
            content: 发送时可选，内容描述
        """
        super().__init__(
            {
                "type": self.segment_type,
                "data": {
                    "type": "custom",
                    "url": str(url),
                    "title": str(title),
                    "audio": str(audio),
                }
            }
        )
        if image != "":
            self.data["image"] = str(image)

        if content != "":
            self.data["content"] = str(content)

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> CustomizeMusic:
        """
        从seg_dict创建一个CustomizeMusic对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            CustomizeMusic对象
        """
        data = seg_dict.get("data", {})
        return cls(
            url=data.get("url"),
            audio=data.get("audio"),
            title=data.get("title"),
            image=data.get("image", ""),
            content=data.get("content", "")
        )

    @property
    def url(self) -> str:
        return self.data.get("url")

    @url.setter
    def url(self, value: str):
        self.data["url"] = str(value)

    @property
    def title(self) -> str:
        return self.data.get("title")

    @title.setter
    def title(self, value: str):
        self.data["title"] = str(value)

    @property
    def audio(self) -> str:
        return self.data.get("audio")

    @audio.setter
    def audio(self, value: str):
        self.data["audio"] = str(value)

    @property
    def image(self) -> str:
        return self.data.get("image")

    @image.setter
    def image(self, value: str):
        self.data["image"] = str(value)

    @property
    def content(self) -> str:
        return self.data.get("content")

    @content.setter
    def content(self, value: str):
        self.data["content"] = str(value)


class Reply(Segment):
    """
    回复
    """
    segment_type = "reply"

    def __init__(self, id_: int | str):
        """
                Args:
                    id_: 回复消息 ID
                """
        super().__init__({"type": self.segment_type, "data": {"id": str(id_)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Reply:
        """
        从seg_dict创建一个Reply对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Reply对象
        """
        return cls(id_=seg_dict.get("data", {}).get("id"))

    @property
    def id(self):
        return self.data.get("id")

    @id.setter
    def id(self, value: int):
        self.data["id"] = value

    def render(self, group_id: int | None = None):
        return f"[回复: {self.id}]"


class Forward(Segment):
    """
    合并转发
    """
    segment_type = "forward"

    def __init__(self, id_: str):
        """
                Args:
                    id_: 合并转发消息 ID
                """
        super().__init__({"type": self.segment_type, "data": {"id": str(id_)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> Forward:
        """
        从seg_dict创建一个Forward对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            Forward对象
        """
        return cls(id_=seg_dict.get("data", {}).get("id"))

    @property
    def id(self):
        return self.data.get("id")

    @id.setter
    def id(self, value: int):
        self.data["id"] = value

    def render(self, group_id: int | None = None):
        return f"[合并转发: {self.id}]"


class XML(Segment):
    """
    XML消息段
    """
    segment_type = "xml"

    def __init__(self, data: str):
        super().__init__({"type": self.segment_type, "data": {"data": str(data)}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> XML:
        """
        从seg_dict创建一个XML对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            XML对象
        """
        return cls(data=seg_dict.get("data", {}).get("data"))

    @property
    def xml(self):
        return self.data.get("data")

    @xml.setter
    def xml(self, value):
        self.data["data"] = str(value)


class JSON(Segment):
    """
    JSON消息段
    """
    segment_type = "json"

    def __init__(self, data: str | dict | list):
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        super().__init__({"type": self.segment_type, "data": {"data": data}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> JSON:
        """
        从seg_dict创建一个JSON对象
        Args:
            seg_dict: 输入的seg_dict

        Returns:
            JSON对象
        """
        return cls(data=seg_dict.get("data", {}).get("data"))

    @property
    def json(self) -> str:
        """
        获取json数据（未序列化）
        Returns:
            str: json数据
        """
        return self.data.get("data")

    @json.setter
    def json(self, value: str | dict | list):
        self.data["data"] = value

    def get_json(self):
        """
        获取json数据（自动序列化）
        Returns:
            json: json数据
        """
        return json.loads(self.data["data"])


def _create_segment_from_dict(segment_dict: dict) -> Segment:
    """从单个字典（array格式）创建Segment对象"""
    # 这个辅助函数和你代码中的对象化逻辑是一样的
    segment_type = segment_dict.get("type")
    data = segment_dict.get("data", {})

    # 特别处理自定义音乐
    if segment_type == "music" and data.get("type") == "custom":
        return CustomizeMusic.creat_from_seg_dict(segment_dict)

    if segment_type in segments_map:
        try:
            try:
                segment = segments_map[segment_type].creat_from_seg_dict(segment_dict)
            except NotImplementedError:
                logger.warning(
                    f"{segments_map[segment_type]}的creat_from_seg_dict方法未实现，回退到__init__自动匹配初始化")

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

            # 为了兼容性，添加一下不包含的键
            for k, v in data.items():
                if k not in segment.data:
                    segment.set_data(k, v)

            return segment
        except Exception as e:
            if ConfigManager.GlobalConfig().debug.save_dump:
                dump_path = save_exc_dump(f"转换 {segment_dict} 到 {segments_map[segment_type]} 时失败")
            else:
                dump_path = None
            logger.warning(f"转换 {segment_dict} 到 {segments_map[segment_type]} 时失败，报错信息: {repr(e)}"
                           f"{f'\n已保存异常到 {dump_path}' if dump_path else ''}",
                           exc_info=True)
            return Segment(segment_dict)
    return Segment(segment_dict)


class QQRichText:
    """
    QQ富文本
    """

    def __init__(
            self,
            *rich: dict[str, dict[str, str]] | str | Segment | QQRichText | list[
                dict[str, dict[str, str]] | str | Segment | QQRichText]
    ):
        """
        Args:
            *rich: 富文本内容，可为 str、dict、list、tuple、Segment、QQRichText
        """
        # 消费一个生成器来构建最终的列表
        self.rich_array: list[Segment] = list(self._iter_and_convert_segments(rich))

    def _iter_and_convert_segments(self, rich_items) -> Generator[Segment, None, None]:
        """
        单遍处理所有输入，并直接 yield 最终的 Segment 对象。
        """
        # 1. 扁平化初始输入
        if len(rich_items) == 1 and isinstance(rich_items[0], (list, tuple)):
            rich_items = rich_items[0]

        # 2. 单遍处理所有项目
        for item in rich_items:
            # 分类处理，直接生成并yield Segment对象
            if isinstance(item, Segment):
                yield _create_segment_from_dict(item.seg_dict)
            elif any(isinstance(item, segment) for segment in segments):
                yield item
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
        if not isinstance(other, QQRichText):
            other = QQRichText(other)
        return QQRichText(self.rich_array + other.rich_array)

    def __eq__(self, other):
        if not isinstance(other, QQRichText):
            other = QQRichText(other)

        return self.rich_array == other.rich_array

    def __contains__(self, other):
        if not isinstance(other, QQRichText):
            other = QQRichText(other)

        n = len(other.rich_array)
        m = len(self.rich_array)
        if n > m:
            return False
        # 只需要遍历到 self.rich_array 的倒数第 n 个元素即可
        for i in range(m - n + 1):
            # 如果从 i 开始的切片与 other.rich_array 相等，则找到
            if self.rich_array[i:i + n] == other.rich_array:
                return True
        return False

    def __bool__(self):
        return bool(self.rich_array)

    def get_array(self) -> list[dict[str, dict[str, str]]]:
        """
        获取rich_array的纯数组形式（用于序列化）
        Returns:
            rich_array
        """
        return [array.seg_dict for array in self.rich_array]

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

        for index in [0, -1] if res.rich_array else [0]:
            if isinstance(res.rich_array[index], Text):
                res.rich_array[index].text = res.rich_array[index].text.strip()
                if not res.rich_array[index].text:
                    res.rich_array.pop(index)
                    if not res.rich_array:
                        break
        return res

    def copy(self):
        """
        复制一份新的QQRichText，会从array开始全部重新创建，所以是深拷贝
        Returns:
            QQRichText
        """
        return QQRichText(self)


# 使用示例
if __name__ == "__main__":
    # 测试CQ解码
    print(cq_decode(" - &#91;x&#93; 使用 `&amp;data` 获取地址"))

    # 测试CQ编码
    print(cq_encode(" - [x] 使用 `&data` 获取地址"))

    # 测试QQRichText
    rich = QQRichText(
        " [CQ:reply,id=123,abc=321][CQ:share,title=标题,url=https://baidu.com] -  &#91;x&#93; 使用 "
        " `&amp;data` 获取地址\n ")
    print(rich.get_array())

    # 测试新的 creat_from_seg_dict 方法
    at_dict = {'type': 'at', 'data': {'qq': '12345'}}
    at_segment = At.creat_from_seg_dict(at_dict)
    print(f"从字典创建的At对象: {at_segment}, 类型: {type(at_segment)}")

    text_dict = {'type': 'text', 'data': {'text': 'Hello World'}}
    text_segment = QQRichText(text_dict)[0]  # 通过QQRichText的构造逻辑调用
    print(f"从字典创建的Text对象: {text_segment}, 类型: {type(text_segment)}")

    print(rich)
    print("123" + str(rich.strip()) + "123")
    print(rich.render())

    print(QQRichText(rich))

    print(QQRichText(At(114514), At(1919810), "114514", Reply(133).seg_dict))
    print(Segment(At(1919810)))
    print(QQRichText([{"type": "text", "data": {"text": "1919810"}}]))
    print(QQRichText().add(At(114514)).add(Text("我吃柠檬")) + QQRichText(At(1919810)).rich_array)
    rich_array = [{'type': 'at', 'data': {'qq': '123'}}, {'type': 'text', 'data': {'text': '[期待]'}}]
    rich = QQRichText(rich_array)
    print(rich)
    print(rich.get_array())

    print("--- 正确示例 ---")
    print(cq_2_array("你好[CQ:face,id=123]世界[CQ:image,file=abc.jpg,url=https://a.com/b?c=1&d=2]"))
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
