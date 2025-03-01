"""
QQ富文本
"""
import inspect
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

from Lib.utils import QQDataCacher, Logger


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


def cq_2_array(cq: str) -> list[dict[str, dict[str, Any]]]:
    """
    CQCode转array消息段数组
    Args:
        cq: CQCode
    Returns:
        array消息段
    """
    if not isinstance(cq, str):
        raise TypeError("cq_2_array: 输入类型错误")

    cq_array = []
    now_state = 0  # 0: 不在cq码内；1: 在CQ码的类型内；2: 在CQ码的参数的键内；3: 在CQ码的参数的值内
    segment_data = {"text": ""}
    now_key = ""
    now_segment_type = ""
    for c in cq:
        if now_state == 0:
            if c == "[":
                now_state = 1
                if len(segment_data["text"]):
                    cq_array.append({"type": "text", "data": {"text": cq_decode(segment_data["text"])}})
                segment_data = {}
            else:
                segment_data["text"] += c
        elif now_state == 1:
            if c == ",":
                now_state = 2
                now_segment_type = now_segment_type[3:]
            else:
                now_segment_type += c
        elif now_state == 2:
            if c == "=":
                now_state = 3
                now_key = cq_decode(now_key, in_cq=True)
                if now_key not in segment_data:
                    segment_data[now_key] = ""
                else:
                    raise ValueError("cq_2_array: CQ码键名称重复")
            else:
                now_key += c
        elif now_state == 3:
            if c == "]":
                now_state = 0
                segment_data[now_key] = cq_decode(segment_data[now_key], in_cq=True)
                cq_array.append({"type": now_segment_type, "data": segment_data})
                segment_data = {"text": ""}
                now_segment_type = ""
                now_key = ""
            elif c == ",":
                segment_data[now_key] = cq_decode(segment_data[now_key], in_cq=True)
                now_state = 2
                now_key = ""
            else:
                segment_data[now_key] += c

    if len(segment_data["text"]):
        cq_array.append({"type": "text", "data": {"text": segment_data["text"]}})

    return cq_array


def array_2_cq(cq_array: list | dict) -> str:
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
        # 纯文本
        if segment.get("type") == "text":
            text += cq_encode(segment.get("data").get("text"))
        # CQ码
        else:
            if segment.get("data"):  # 特判
                text += f"[CQ:{segment.get('type')}," + ",".join(
                    [cq_encode(x, in_cq=True) + "=" + cq_encode(segment.get("data")[x], in_cq=True)
                     for x in segment.get("data").keys()]) + "]"
            else:
                text += f"[CQ:{segment.get('type')}]"
    return text


def convert_to_fileurl(input_str):
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

    def __init__(self, cq):
        self.cq = cq
        if isinstance(cq, str):
            self.array = cq_2_array(cq)[0]
            self.type, self.data = list(self.array.values())
        elif isinstance(cq, dict):
            self.array = cq
            self.cq = array_2_cq(self.array)
            self.type, self.data = list(self.array.values())
        else:
            for segment in segments:
                if isinstance(cq, segment):
                    self.array = cq.array
                    self.cq = str(self.cq)
                    # print(self.array.values(), list(self.array.values()))
                    self.type, self.data = list(self.array.values())
                    break
            else:
                # print(cq, str(cq), type(cq))
                raise TypeError("Segment: 输入类型错误")

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
        super().__init__(text)
        self.text = self["data"]["text"] = text

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

    def __init__(self, face_id):
        """
        Args:
            face_id: 表情id
        """
        self.face_id = face_id
        super().__init__({"type": "face", "data": {"id": str(face_id)}})

    def set_id(self, face_id):
        """
        设置表情id
        Args:
            face_id: 表情id
        """
        self.face_id = face_id
        self.array["data"]["id"] = str(face_id)

    def render(self, group_id: int | None = None):
        return "[表情: %s]" % self.face_id


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
            return f"@{QQDataCacher.qq_data_cache.get_group_member_info(group_id, self.qq).get_nickname()}: {self.qq}"
        else:
            return f"@{QQDataCacher.qq_data_cache.get_user_info(self.qq).nickname}: {self.qq}"


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
        super().__init__({"type": "rps"})


class Dice(Segment):
    segment_type = "dice"

    def __init__(self):
        super().__init__({"type": "dice"})


class Shake(Segment):
    """
    窗口抖动消息段
    (相当于戳一戳最基本类型的快捷方式。)
    """
    segment_type = "shake"

    def __init__(self):
        super().__init__({"type": "shake"})


class Poke(Segment):
    """
    戳一戳消息段
    """
    segment_type = "poke"

    def __init__(self, type_, poke_id):
        """
        Args:
            type_: 见https://github.com/botuniverse/onebot-11/blob/master/message/segment.md#%E6%88%B3%E4%B8%80%E6%88%B3
            poke_id: 同上
        """
        self.type = type_
        self.poke_id = poke_id
        super().__init__({"type": "poke", "data": {"type": str(self.type)}, "id": str(self.poke_id)})

    def set_type(self, qq_type):
        """
        设置戳一戳类型
        Args:
            qq_type: qq类型
        """
        self.type = qq_type
        self.array["data"]["type"] = str(qq_type)

    def set_id(self, poke_id):
        """
        设置戳一戳id
        Args:
            poke_id: 戳一戳id
        """
        self.poke_id = poke_id
        self.array["data"]["id"] = str(poke_id)

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

    def __init__(self, message_id):
        """
        Args:
            message_id: 回复消息 ID
        """
        self.message_id = message_id
        super().__init__({"type": "reply", "data": {"id": str(self.message_id)}})

    def set_message_id(self, message_id):
        """
        设置消息 ID
        Args:
            message_id: 消息 ID
        """
        self.message_id = message_id
        self.array["data"]["id"] = str(self.message_id)

    def render(self, group_id: int | None = None):
        return f"[回复: {self.message_id}]"


class Forward(Segment):
    """
    合并转发消息段
    """
    segment_type = "forward"

    def __init__(self, forward_id):
        """
        Args:
            forward_id: 合并转发消息 ID
        """
        self.forward_id = forward_id
        super().__init__({"type": "forward", "data": {"id": str(self.forward_id)}})

    def set_forward_id(self, forward_id):
        """
        设置合并转发消息 ID
        Args:
            forward_id: 合并转发消息 ID
        """
        self.forward_id = forward_id
        self.array["data"]["id"] = str(self.forward_id)

    def render(self, group_id: int | None = None):
        return f"[合并转发: {self.forward_id}]"


class XML(Segment):
    """
    XML消息段
    """
    segment_type = "xml"

    def __init__(self, data):
        self.data = data
        super().__init__({"type": "xml", "data": {"data": str(self.data)}})

    def set_xml_data(self, data):
        """
        设置xml数据
        Args:
            data: xml数据
        """
        self.data = data
        self.array["data"]["data"] = str(self.data)


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
        self.data = data
        super().__init__({"type": "json", "data": {"data": str(self.data)}})

    def set_json(self, data):
        """
        设置json数据
        Args:
            data: json 内容
        """
        self.data = data
        self.array["data"]["data"] = str(self.data)

    def get_json(self):
        """
        获取json数据（自动序列化）
        Returns:
            json: json数据
        """
        return json.loads(self.data)


class QQRichText:
    """
    QQ富文本
    """
    def __init__(self, *rich: str | dict | list | tuple | Segment):
        """
        Args:
            *rich: 富文本内容，可为 str、dict、list、tuple、Segment、QQRichText
        """

        # 特判
        self.rich_array: list[Segment] = []
        if len(rich) == 1:
            rich = rich[0]

        # 识别输入的是CQCode or json形式的富文本
        # 如果输入的是CQCode，则转换为json形式的富文本

        # 处理CQCode
        if isinstance(rich, str):
            rich_string = rich
            rich = cq_2_array(rich_string)

        elif isinstance(rich, dict):
            rich = [rich]
        elif isinstance(rich, (list, tuple)):
            array = []
            for item in rich:
                if isinstance(item, dict):
                    array.append(item)
                elif isinstance(item, str):
                    array += cq_2_array(item)
                else:
                    for segment in segments:
                        if isinstance(item, segment):
                            array.append(item.array)
                            break
                    else:
                        if isinstance(rich, QQRichText):
                            array += rich.rich_array
                        else:
                            raise TypeError("QQRichText: 输入类型错误")
            rich = array
        else:
            for segment in segments:
                if isinstance(rich, segment):
                    rich = [rich.array]
                    break
            else:
                if isinstance(rich, QQRichText):
                    rich = rich.rich_array
                else:
                    raise TypeError("QQRichText: 输入类型错误")

        # 将rich转换为的Segment
        for _ in range(len(rich)):
            if rich[_]["type"] in segments_map:
                try:
                    params = inspect.signature(segments_map[rich[_]["type"]]).parameters
                    kwargs = {}
                    for param in params:
                        if param in rich[_]["data"]:
                            kwargs[param] = rich[_]["data"][param]
                        else:
                            if rich[_]["type"] == "reply" and param == "message_id":
                                kwargs[param] = rich[_]["data"].get("id")
                            elif rich[_]["type"] == "face" and param == "face_id":
                                kwargs[param] = rich[_]["data"].get("id")
                            elif rich[_]["type"] == "forward" and param == "forward_id":
                                kwargs[param] = rich[_]["data"].get("id")
                            elif rich[_]["type"] == "poke" and param == "poke_id":
                                kwargs[param] = rich[_]["data"].get("id")
                            elif param == "id_":
                                kwargs[param] = rich[_]["data"].get("id")
                            elif param == "type_":
                                kwargs[param] = rich[_]["data"].get("type")
                            else:
                                if params[param].default != params[param].empty:
                                    kwargs[param] = params[param].default
                    segment = segments_map[rich[_]["type"]](**kwargs)
                    # 检查原cq中是否含有不在segment的data中的参数
                    for k, v in rich[_]["data"].items():
                        if k not in segment["data"]:
                            segment.set_data(k, v)
                    rich[_] = segment
                except Exception as e:
                    Logger.logger.warning(f"转换{rich[_]}时失败，报错信息: {repr(e)}")
                    rich[_] = Segment(rich[_])
            else:
                rich[_] = Segment(rich[_])

        self.rich_array: list[Segment] = rich

    def render(self, group_id: int | None = None):
        """
        渲染消息（调用rich_array下所有消息段的render方法拼接）
        Args:
            group_id: 群号，选填，可优化效果
        """
        text = ""
        for rich in self.rich_array:
            text += rich.render(group_id=group_id)
        return text

    def __str__(self):
        self.rich_string = array_2_cq(self.rich_array)
        return self.rich_string

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

    def get_array(self):
        """
        获取rich_array（非抽象类，可用于API调用等）
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
        for segment in segments:
            if isinstance(segment, Segment):
                self.rich_array.append(segment)
            else:
                self.rich_array += QQRichText(segment).rich_array
        return self


# 使用示例
if __name__ == "__main__":
    # 测试CQ解码
    print(cq_decode(" - &#91;x&#93; 使用 `&amp;data` 获取地址"))

    # 测试CQ编码
    print(cq_encode(" - [x] 使用 `&data` 获取地址"))

    # 测试QQRichText
    rich = QQRichText(
        "[CQ:reply,id=123][CQ:share,title=标题,url=https://baidu.com] [CQ:at,qq=1919810,abc=123] -  &#91;x&#93; 使用 "
        " `&amp;data` 获取地址")
    print(rich.get_array())
    print(rich)
    print(rich.render())

    print(QQRichText(At(114514)))
    print(Segment(At(1919810)))
    print(QQRichText([{"type": "text", "data": {"text": "1919810"}}]))
    print(QQRichText().add(At(114514)).add(Text("我吃柠檬"))+QQRichText(At(1919810)).rich_array)
