"""
Lagrange的拓展消息段
"""

from murainbot import QQRichText


class MFace(QQRichText.Segment):
    """
    商城表情消息段
    """

    segment_type = "mface"

    def __init__(self, emoji_package_id: int | str, emoji_id: int | str, key: str, summary: str, url: str = None):
        """
        Args:
            emoji_package_id: 表情包 ID
            emoji_id: 表情 ID
            key: 表情 Key
            summary: 表情说明
            url: 表情 Url(可选)
        """
        super().__init__({"type": "mface", "data": {"emoji_package_id": str(emoji_package_id),
                                                    "emoji_id": str(emoji_id),
                                                    "key": key, "summary": summary}})
        if url:
            self.data["url"] = url

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> "MFace":
        return cls(
            seg_dict["data"]["emoji_package_id"],
            seg_dict["data"]["emoji_id"],
            seg_dict["data"]["key"],
            seg_dict["data"]["summary"],
            seg_dict["data"]["url"]
        )

    @property
    def summary(self):
        return self.data["summary"]

    @summary.setter
    def summary(self, summary: str):
        self.data["summary"] = summary

    @property
    def emoji_package_id(self):
        return self.data["emoji_package_id"]

    @emoji_package_id.setter
    def emoji_package_id(self, emoji_package_id: int):
        self.data["emoji_package_id"] = emoji_package_id

    @property
    def emoji_id(self):
        return self.data["emoji_id"]

    @emoji_id.setter
    def emoji_id(self, emoji_id: int):
        self.data["emoji_id"] = emoji_id

    @property
    def key(self):
        return self.data["key"]

    @key.setter
    def key(self, key: str):
        self.data["key"] = key

    @property
    def url(self):
        return self.data["url"]

    @url.setter
    def url(self, url: str):
        self.data["url"] = url

    def render(self, group_id: int | None = None):
        return f"[mface: {self.summary}({self.emoji_package_id}:{self.emoji_id}:{self.key}):{self.url}]"


class File(QQRichText.Segment):
    """
    文件消息段
    """

    segment_type = "file"

    def __init__(self, file_name: str, file_id: str, file_hash: int | str, url: str):
        """
        Args:
            file_name: 文件名
            file_id: 文件 ID
            file_hash: 文件 Hash
            url: 下载链接
        """
        super().__init__({"type": "file", "data": {"file_name": file_name, "file_id": file_id, "file_hash": file_hash,
                                                   "url": url}})

    @classmethod
    def creat_from_seg_dict(cls, seg_dict: dict[str, dict[str, str]]) -> "File":
        return cls(
            seg_dict["data"]["file_name"],
            seg_dict["data"]["file_id"],
            seg_dict["data"]["file_hash"],
            seg_dict["data"]["url"]
        )

    @property
    def file_name(self):
        return self.data["file_name"]

    @file_name.setter
    def file_name(self, file_name: str):
        self.data["file_name"] = file_name

    @property
    def file_id(self):
        return self.data["file_id"]

    @file_id.setter
    def file_id(self, file_id: str):
        self.data["file_id"] = file_id

    @property
    def file_hash(self):
        return self.data["file_hash"]

    @file_hash.setter
    def file_hash(self, file_hash: int):
        self.data["file_hash"] = file_hash

    @property
    def url(self):
        return self.data["url"]

    @url.setter
    def url(self, url: str):
        self.data["url"] = url

    def render(self, group_id: int | None = None):
        return f"[file: {self.file_name}({self.file_id}:{self.file_hash}):{self.url}]"
