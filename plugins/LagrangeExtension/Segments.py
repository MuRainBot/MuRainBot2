"""
Lagrange的拓展消息段
"""

from murainbot import QQRichText


class MFace(QQRichText.Segment):
    """
    商城表情消息段
    """

    segment_type = "mface"

    def __init__(self, emoji_package_id: int, emoji_id: int, key: str, summary: str, url: str = None):
        """
        Args:
            emoji_package_id: 表情包 ID
            emoji_id: 表情 ID
            key: 表情 Key
            summary: 表情说明
            url: 表情 Url(可选)
        """
        self.emoji_package_id = emoji_package_id
        self.emoji_id = emoji_id
        self.key = key
        self.summary = summary
        super().__init__({"type": "mface", "data": {"emoji_package_id": emoji_package_id, "emoji_id": emoji_id,
                                                    "key": key, "summary": summary}})
        if url:
            self.url = url
            self.array["data"]["url"] = url

    def set_url(self, url: str):
        """
        设置表情 Url
        Args:
            url: 表情 Url
        Returns:
            None
        """
        self.url = url
        self.data["data"]["url"] = url

    def set_emoji_id(self, emoji_id: int):
        """
        设置表情 ID
        Args:
            emoji_id: 表情 ID
        Returns:
            None
        """
        self.emoji_id = emoji_id
        self.data["data"]["emoji_id"] = emoji_id

    def set_emoji_package_id(self, emoji_package_id: int):
        """
        设置表情包 ID
        Args:
            emoji_package_id: 表情包 ID
        Returns:
            None
        """
        self.emoji_package_id = emoji_package_id
        self.data["data"]["emoji_package_id"] = emoji_package_id

    def set_key(self, key: str):
        """
        设置表情 Key
        Args:
            key: 表情 Key
        Returns:
            None
        """
        self.key = key
        self.data["data"]["key"] = key

    def render(self, group_id: int | None = None):
        return f"[mface: {self.summary}({self.emoji_package_id}:{self.emoji_id}:{self.key}):{self.url}]"


class File(QQRichText.Segment):
    """
    文件消息段
    """

    segment_type = "file"

    def __init__(self, file_name: str, file_id: str, file_hash: int, url: str):
        """
        Args:
            file_name: 文件名
            file_id: 文件 ID
            file_hash: 文件 Hash
            url: 下载链接
        """
        self.file_name = file_name
        self.file_id = file_id
        self.file_hash = file_hash
        self.url = url

        super().__init__({"type": "file", "data": {"file_name": file_name, "file_id": file_id, "file_hash": file_hash,
                                                   "url": url}})

    def set_file_name(self, file_name: str):
        """
        设置文件名
        Args:
            file_name: 文件名
        Returns:
            None
        """
        self.file_name = file_name
        self.data["data"]["file_name"] = file_name

    def set_file_id(self, file_id: str):
        """
        设置文件 ID
        Args:
            file_id: 文件 ID
        Returns:
            None
        """
        self.file_id = file_id
        self.data["data"]["file_id"] = file_id

    def set_file_hash(self, file_hash: int):
        """
        设置文件 Hash
        Args:
            file_hash: 文件 Hash
        Returns:
            None
        """
        self.file_hash = file_hash
        self.data["data"]["file_hash"] = file_hash

    def set_url(self, url: str):
        """
        设置下载链接
        Args:
            url: 下载链接
        Returns:
            None
        """
        self.url = url
        self.data["data"]["url"] = url

    def render(self, group_id: int | None = None):
        return f"[file: {self.file_name}({self.file_id}:{self.file_hash}):{self.url}]"
