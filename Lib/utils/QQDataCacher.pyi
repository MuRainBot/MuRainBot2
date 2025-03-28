NotFetched = type("NotFetched", (), {"__getattr__": lambda _, __: NotFetched,
                                     "__repr__": lambda _: "NotFetched",
                                     "__bool__": lambda _: False})


class QQDataItem:
    def __init__(self):
        self._data: dict | NotFetched = NotFetched  # 数据
        self.last_update: float = None  # 最后刷新时间
        self.last_use: float = None

    def refresh_cache(self):
        self.last_update = None

class UserData(QQDataItem):
    def __init__(
            self,
            user_id: int,
            nickname: str = NotFetched,
            sex: str = NotFetched,
            age: int = NotFetched,
            is_friend: bool = NotFetched,
            remark: str | None = NotFetched  # 此值仅在是好友的时候会存在
    ) -> None:
        self._data = None
        self._user_id = None

    def refresh_cache(self) -> None: ...

    def get_nickname(self) -> str: ...

    @property
    def data(self) -> dict: ...

    @property
    def user_id(self) -> int: ...

    @property
    def nickname(self) -> str: ...

    @property
    def sex(self) -> str: ...

    @property
    def age(self) -> int: ...

    @property
    def is_friend(self) -> bool: ...

    @property
    def remark(self) -> str: ...


class GroupMemberData(QQDataItem):
    def __init__(
            self,
            group_id: int,
            user_id: int,
            nickname: str = NotFetched,
            card: str = NotFetched,
            sex: str = NotFetched,
            age: int = NotFetched,
            area: str = NotFetched,
            join_time: int = NotFetched,
            last_sent_time: int = NotFetched,
            level: str = NotFetched,
            role: str = NotFetched,
            unfriendly: bool = NotFetched,
            title: str = NotFetched,
            title_expire_time: int = NotFetched,
            card_changeable: bool = NotFetched,
    ):
        self._data = None
        self._user_id = None
        self._group_id = None

    def refresh_cache(self) -> None: ...

    def get_nickname(self) -> str: ...

    @property
    def data(self): ...

    @property
    def group_id(self): ...
    @property
    def user_id(self): ...

    @property
    def nickname(self) -> str: ...

    @property
    def card(self) -> str: ...

    @property
    def sex(self) -> str: ...

    @property
    def age(self) -> int: ...

    @property
    def area(self) -> str: ...

    @property
    def join_time(self) -> int: ...

    @property
    def last_sent_time(self) -> int: ...

    @property
    def level(self) -> str: ...

    @property
    def role(self) -> str: ...

    @property
    def unfriendly(self) -> bool: ...

    @property
    def title(self) -> str: ...

    @property
    def title_expire_time(self) -> int: ...

    @property
    def card_changeable(self) -> bool: ...


class GroupData(QQDataItem):
    def __init__(
            self,
            group_id: int,
            group_name: str = NotFetched,
            member_count: int = NotFetched,
            max_member_count: int = NotFetched
    ) -> None:
        super().__init__()
        self._group_id = None
        self._data = None

    def refresh_cache(self) -> None: ...

    @property
    def data(self): ...

    @property
    def group_id(self): ...

    @property
    def group_name(self) -> str: ...

    @property
    def member_count(self) -> int: ...

    @property
    def max_member_count(self) -> int: ...

    @property
    def group_member_list(self) -> list[GroupMemberData]: ...



group_info: dict = None
group_member_info: dict =  None
user_info: dict =  None
max_cache_size: int =  None
expire_time: int =  None

def get_group_info(group_id: int, *args, **kwargs) -> GroupData: ...

def get_group_member_info(group_id: int, user_id: int, *args, **kwargs) -> GroupMemberData: ...

def get_user_info(user_id: int, *args, **kwargs) -> UserData: ...

def garbage_collection() -> int: ...

def scheduled_garbage_collection() -> None: ...
