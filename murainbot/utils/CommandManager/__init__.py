"""
命令管理器
"""
import ast
from typing import Any

from murainbot.utils import QQRichText, Logger

arg_map = {}
logger = Logger.get_logger()


def _split_remaining_cmd(remaining_cmd: QQRichText.QQRichText) -> \
        tuple[QQRichText.Segment | None, QQRichText.QQRichText | None]:
    remaining_cmd = remaining_cmd.strip()
    if len(remaining_cmd.rich_array) == 0:
        return None, None
    else:
        if remaining_cmd.rich_array[0].type == "text":
            cmd = remaining_cmd.rich_array[0].data.get("text", "").split(" ", 1)
            if len(cmd) != 1:
                cmd, remaining_cmd_str = cmd
                cmd = cmd.strip()
                return (QQRichText.Text(cmd),
                        QQRichText.QQRichText(QQRichText.Text(remaining_cmd_str), *remaining_cmd.rich_array[1:]))
            else:
                return QQRichText.Text(cmd[0].strip()), QQRichText.QQRichText(*remaining_cmd.rich_array[1:])
        else:
            return remaining_cmd.rich_array[0], QQRichText.QQRichText(*remaining_cmd.rich_array[1:])


def encode_arg(arg: str):
    """
    编码参数
    Args:
        arg: 参数

    Returns:
        编码后的参数
    """
    return (arg.replace("%", "%25").replace("<", "%3C").replace("[", "%5B")
            .replace(">", "%3E").replace("]", "%5D").replace(",", "%2C"))


def decode_arg(arg: str):
    """
    解码参数
    Args:
        arg: 参数

    Returns:
        解码后的参数
    """
    return (arg.replace("%3C", "<").replace("%5B", "[").replace("%3E", ">")
            .replace("%5D", "]").replace("%2C", ",").replace("%25", "%"))


class NotMatchCommandError(Exception):
    """
    没有匹配的命令
    """


class CommandMatchError(Exception):
    """
    命令匹配时出现问题
    """

    def __init__(self, message: str, command: "BaseArg"):
        super().__init__(message)
        self.command = command


class ArgMeta(type):
    """
    元类用于自动注册 Arg 子类到全局映射 arg_map 中。
    """

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        try:
            BaseArg
        except NameError:
            return
        if issubclass(cls, BaseArg):
            arg_map[f"{cls.__module__}.{cls.__name__}"] = cls


class BaseArg(metaclass=ArgMeta):
    """
    基础命令参数类，请勿直接使用
    """

    def __init__(self, arg_name: str, next_arg_list=None):
        self.arg_name = arg_name
        if next_arg_list is None:
            next_arg_list = []
        self.next_arg_list = next_arg_list

    def __str__(self):
        return f"<{self.arg_name}: {self.__class__.__module__}.{self.__class__.__name__}{self.config_str(", ")}>"

    def __repr__(self):
        return "\n".join(self._generate_repr_lines())

    def node_str(self):
        """
        生成该节点的字符串形式
        """
        return f"{self.__class__.__name__}({self.arg_name!r}{self.config_str(", ", encode=False)})"

    def config_str(self, prefix: str = "", encode: bool = True):
        """
        生成当前节点配置文件的字符串形式
        """
        if encode:
            res = ", ".join(f"{k}={encode_arg(repr(v))}" for k, v in self.get_config().items())
        else:
            res = ", ".join(f"{k}={repr(v)}" for k, v in self.get_config().items())
        if res:
            res = prefix + res
        return res

    def _generate_repr_lines(self, prefix="", is_last=True):
        """
        一个递归的辅助函数，用于生成漂亮的树状结构。

        Args:
            prefix (str): 当前层级的前缀（包含空格和连接符）。
            is_last (bool): 当前节点是否是其父节点的最后一个子节点。
        """
        # 1. 生成当前节点的行
        # 使用 └─ 表示最后一个节点，├─ 表示中间节点
        connector = "└─ " if is_last else "├─ "
        connector = connector if prefix else ""
        # 简化节点自身的表示，只包含类名和参数名
        yield prefix + connector + self.node_str()

        # 2. 准备下一层级的前缀
        # 如果是最后一个节点，其子节点的前缀应该是空的；否则应该是 '│  '
        next_prefix = prefix + ("    " if is_last else "│   ")

        # 3. 递归处理子节点
        child_count = len(self.next_arg_list)
        for i, child in enumerate(self.next_arg_list):
            is_child_last = (i == child_count - 1)
            # 使用 yield from 将子生成器的所有结果逐一产出
            yield from child._generate_repr_lines(next_prefix, is_child_last)

    def matcher(self, remaining_cmd: QQRichText.QQRichText) -> bool:
        """
        匹配剩余命令
        Args:
            remaining_cmd: 剩余命令

        Returns:
            是否匹配
        """
        return True

    def handler(self, remaining_cmd: QQRichText.QQRichText) -> tuple[dict[str, Any], QQRichText.QQRichText | None]:
        """
        参数处理函数
        Args:
            remaining_cmd: 剩余未匹配的命令

        Returns:
            匹配到的参数，剩余交给下一个匹配器的参数(没有则为None)

        Raises:
            ValueError: 参数处理失败（格式不对）
        """
        match_parameters, remaining_cmd = _split_remaining_cmd(remaining_cmd)
        return self._handler(match_parameters), remaining_cmd

    def _handler(self, match_parameters: QQRichText.Segment) -> dict[str, Any]:
        """
        参数处理函数（内部实现）
        Args:
            match_parameters: 当前需要处理的参数

        Returns:
            处理结果

        Raises:
            ValueError: 参数处理失败（格式不对）
        """
        return {}

    def add_next_arg(self, arg):
        """
        添加下一参数
        Args:
            arg: 参数

        Returns:
            self

        """
        self.next_arg_list.append(arg)
        return self

    def get_last_arg(self):
        """
        获取当前参数的下一个参数，如果没有则返回自己，如果当前参数的下个参数不止一个，则会报错
        Returns:
            参数
        """
        if len(self.next_arg_list) == 0:
            return self
        elif len(self.next_arg_list) > 1:
            raise ValueError(f"当前参数的下个参数不止一个")
        return self.next_arg_list[0].get_last_arg()

    def get_config(self) -> dict:
        """
        获取当前实例的配置
        """
        return {}

    @classmethod
    def get_instance_from_config(cls, arg_name: str, config: dict[str, str]) -> "BaseArg":
        """
        从配置中创建实例
        Args:
            arg_name: 参数名称
            config: 配置

        Returns:
            创建好的实例
        """
        config = {
            k: ast.literal_eval(v)
            for k, v in config.items()
        }
        return cls(arg_name, **config)


def parsing_command_def(command_def: str) -> BaseArg:
    """
    字符串命令转命令树
    Args:
        command_def: 字符串格式的命令定义

    Returns:
        命令树
    """
    is_in_arg = False
    is_in_arg_config = False
    arg_config = ""
    arg_configs = {}
    is_in_optional = False
    arg_name = ""
    command_tree = None
    for char in command_def:
        # print(char, is_in_arg, is_in_arg_config, arg_config, arg_configs, is_in_optional, arg_name)
        if (char == "<" or char == "[") and not is_in_arg_config:
            arg_name = arg_name.strip()
            if arg_name:
                if is_in_optional and char == "<":
                    raise ValueError("参数定义错误: 必要参数必须放在可选参数之前")
                if command_tree is not None:
                    command_tree.get_last_arg().add_next_arg(Literal(arg_name))
                else:
                    command_tree = Literal(arg_name)
            arg_name = ""
            if not is_in_arg:
                is_in_arg = True
            else:
                raise ValueError("参数定义错误")
        elif char == ",":
            if is_in_arg:
                if not is_in_arg_config:
                    is_in_arg_config = True
                else:
                    try:
                        k, v = arg_config.strip().split("=", 1)
                    except ValueError:
                        raise ValueError("参数定义错误")
                    v = decode_arg(v)
                    # print(k, v)
                    arg_configs[k] = v
                    arg_config = ""
            else:
                raise ValueError("参数定义错误")
        elif char == ">":
            if is_in_arg:
                if is_in_optional:
                    raise ValueError("参数定义错误: 必要参数必须放在可选参数之前")
                if is_in_arg_config:
                    try:
                        k, v = arg_config.strip().split("=", 1)
                    except ValueError:
                        raise ValueError("参数定义错误")
                    v = decode_arg(v)
                    # print(k, v)
                    arg_configs[k] = v
                is_in_arg = False
                is_in_arg_config = False
                arg_name, arg_type = arg_name.split(":", 1)
                arg_name, arg_type = arg_name.strip(), arg_type.strip()
                arg = arg_map[arg_type].get_instance_from_config(arg_name, arg_configs)
                if arg_type in arg_map:
                    if command_tree is not None:
                        command_tree.get_last_arg().add_next_arg(arg)
                    else:
                        command_tree = arg
                    arg_name = ""
                    arg_configs = {}
                else:
                    raise ValueError(f"参数定义错误: 未知的参数类型 {arg_type}")
            else:
                raise ValueError("参数定义错误")
        elif char == "]":
            if is_in_arg:
                if is_in_arg_config:
                    try:
                        k, v = arg_config.strip().split("=", 1)
                    except ValueError:
                        raise ValueError("参数定义错误")
                    v = decode_arg(v)
                    # print(k, v)
                    arg_configs[k] = v
                is_in_optional = True
                is_in_arg = False
                is_in_arg_config = False
                arg_name, arg_type = arg_name.split(":", 1)
                arg_type, arg_default = arg_type.split("=", 1)
                arg_name, arg_type, arg_default = arg_name.strip(), arg_type.strip(), arg_default.strip()
                arg_default = ast.literal_eval(arg_default)
                arg = OptionalArg(arg_map[arg_type].get_instance_from_config(arg_name, arg_configs), arg_default)
                if arg_type in arg_map:
                    if command_tree is not None:
                        command_tree.get_last_arg().add_next_arg(arg)
                    else:
                        command_tree = arg
                    arg_name = ""
                    arg_configs = {}
                else:
                    raise ValueError(f"参数定义错误: 未知的参数类型 {arg_type}")
            else:
                raise ValueError("参数定义错误")
        elif is_in_arg_config:
            arg_config += char
        else:
            arg_name += char

    arg_name = arg_name.strip()
    if arg_name:
        if is_in_optional:
            raise ValueError("参数定义错误: 必要参数必须放在可选参数之前")
        if command_tree is not None:
            command_tree.get_last_arg().add_next_arg(Literal(arg_name))
        else:
            # 处理整个命令只有一个 Literal 的情况
            command_tree = Literal(arg_name)

    return command_tree


from murainbot.utils.CommandManager.args import *


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    计算两个字符串之间的莱文斯坦距离（编辑距离）。
    使用动态规划算法。

    Args:
        s1: 第一个字符串。
        s2: 第二个字符串。

    Returns:
        两个字符串之间的编辑距离。
    """
    m, n = len(s1), len(s2)

    # 创建一个 (m+1) x (n+1) 的矩阵来存储距离
    # dp[i][j] 表示 s1 的前 i 个字符和 s2 的前 j 个字符之间的编辑距离
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 初始化矩阵的第一行和第一列
    # 从空字符串转换到 s2 的前 j 个字符需要 j 次插入
    for j in range(n + 1):
        dp[0][j] = j
    # 从 s1 的前 i 个字符转换到空字符串需要 i 次删除
    for i in range(m + 1):
        dp[i][0] = i

    # 填充矩阵的其余部分
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # 如果 s1[i-1] 和 s2[j-1] 字符相同，则替换成本为 0，否则为 1
            substitution_cost = 0 if s1[i - 1] == s2[j - 1] else 1

            # dp[i][j] 的值是以下三者中的最小值：
            # 1. dp[i-1][j] + 1  (删除 s1 的第 i 个字符)
            # 2. dp[i][j-1] + 1  (在 s1 中插入 s2 的第 j 个字符)
            # 3. dp[i-1][j-1] + substitution_cost (替换 s1 的第 i 个字符为 s2 的第 j 个字符)
            dp[i][j] = min(dp[i - 1][j] + 1,  # Deletion
                           dp[i][j - 1] + 1,  # Insertion
                           dp[i - 1][j - 1] + substitution_cost)  # Substitution

    # 最终结果位于矩阵的右下角
    return dp[m][n]


def get_all_optional_args_recursive(start_node: BaseArg):
    """
    一个独立的递归生成器，用于获取所有可选参数。
    """
    for child in start_node.next_arg_list:
        if isinstance(child, OptionalArg):
            yield child
            yield from get_all_optional_args_recursive(child.wrapped_arg)
        else:
            yield from get_all_optional_args_recursive(child)


class CommandManager:
    """
    命令管理器
    """

    def __init__(self):
        self.command_list: list[BaseArg] = []

    def register_command(self, command: BaseArg):
        """
        注册命令
        Args:
            command: 注册命令的命令树

        Returns:
            self
        """
        # if callback_func is not None:
        #     command.get_last_arg().callback_func = callback_func
        self.command_list.append(command)

        return self

    def run_command(self, command: QQRichText.QQRichText):
        """
        执行命令
        Args:
            command: 输入命令

        Returns:
            命令参数, 匹配的命令
        """
        kwargs = {}
        command = command.strip()
        # 先对command_list重排序，第一个是literal的放前面，然后再根据literal的长度排序
        self.command_list.sort(
            key=lambda x: max(len(c) for c in x.command_list) if isinstance(x, Literal) else 0, reverse=True
        )
        for command_def in self.command_list:
            if command_def.matcher(command):
                now_command_def = command_def
                break
        else:
            literals = [_.arg_name for _ in self.command_list if isinstance(_, Literal)]
            user_input = command.rich_array[0]
            if user_input.type == "text":
                user_input = user_input.data.get("text")
                if len(literals) == 1:
                    raise NotMatchCommandError(f'命令不匹配任何命令定义: '
                                               f'{", ".join([str(_) for _ in self.command_list])}'
                                               f'你的意思是: {literals[0]}？')
                elif literals:
                    closest_command = None
                    min_dist = float('inf')

                    for command in literals:
                        dist = levenshtein_distance(user_input, command)

                        if dist < min_dist and dist <= 3:
                            min_dist = dist
                            closest_command = command
                    if closest_command:
                        raise NotMatchCommandError(f'命令不匹配任何命令定义: '
                                                   f'{", ".join([str(_) for _ in self.command_list])}\n'
                                                   f'你的意思是: {closest_command}？')
            raise NotMatchCommandError(f'命令不匹配任何命令定义: '
                                       f'{", ".join([str(_) for _ in self.command_list])}')
        try:
            new_kwargs, command = now_command_def.handler(command)
        except ValueError as e:
            raise CommandMatchError(f'命令参数匹配错误: {e}', command_def)
        kwargs.update(new_kwargs)

        while True:
            # print(command)
            if command is None or not (command := command.strip()):
                must_args = [_ for _ in now_command_def.next_arg_list if not isinstance(_, OptionalArg)]
                if must_args:
                    raise CommandMatchError(f'命令已被匹配完成但仍有剩余必要参数未被匹配: '
                                            f'{", ".join([str(_) for _ in must_args])}', command_def)
                optional_args = get_all_optional_args_recursive(now_command_def)
                for optional_arg in optional_args:
                    if optional_arg.arg_name not in kwargs:
                        kwargs[optional_arg.arg_name] = optional_arg.default
                break

            if not now_command_def.next_arg_list:
                raise CommandMatchError(f'命令参数均已匹配，但仍剩余命令: "{command}"', command_def)

            for next_command in now_command_def.next_arg_list:
                if next_command.matcher(command):
                    now_command_def = next_command
                    break
            else:
                raise CommandMatchError(f'剩余命令: "{command}" 不匹配任何命令定义: '
                                        f'{", ".join([str(_) for _ in now_command_def.next_arg_list])}', command_def)

            try:
                new_kwargs, command = now_command_def.handler(command)
            except ValueError as e:
                raise CommandMatchError(f'命令参数匹配错误: {e}', command_def)
            kwargs.update(new_kwargs)

        return kwargs, command_def, now_command_def


from murainbot.utils.CommandManager.matcher import *

if __name__ == '__main__':
    print(arg_map)
    test_command_manager = CommandManager()
    languages = [Literal("python", {"py"})]
    cmd = (f"codeshare "
           f"{SkipOptionalArg(EnumArg("language", languages), "guess")}")
    print(cmd)
    print(repr(parsing_command_def(cmd)))
    cmd = (f"codeshare "
           f"{OptionalArg(SkipOptionalArg(EnumArg("language", languages)), "guess")}"
           f"{OptionalArg(GreedySegments("code"))}")
    print(cmd)
    print(repr(parsing_command_def(cmd)))
    test_command_manager.register_command(
        parsing_command_def(f"/email send {IntArg("email_id")} {GreedySegments("message")}"))
    test_command_manager.register_command(
        parsing_command_def(f"/email get {OptionalArg(IntArg("email_id"))} {OptionalArg(EnumArg("color", [
            Literal("red"), Literal("green"), Literal("blue")
        ]), "red")}"))
    test_command_manager.register_command(
        parsing_command_def(f"/email set image {IntArg("email_id")} {ImageSegmentArg("image")}"))
    test_command_manager.register_command(
        Literal(
            '/git', next_arg_list=[
                Literal(
                    'push', next_arg_list=[
                        TextArg(
                            'remote', [
                                TextArg('branch')
                            ]
                        )
                    ]
                ),
                Literal(
                    'pull', next_arg_list=[
                        TextArg(
                            'remote', [
                                TextArg('branch')
                            ]
                        )
                    ]
                )
            ]
        )
    )
    print("\n".join([repr(_) for _ in test_command_manager.command_list]))
    print(test_command_manager.run_command(QQRichText.QQRichText(QQRichText.Text("/git push origin master")))[0])
    print(test_command_manager.run_command(QQRichText.QQRichText(QQRichText.Text("/email send 123 abc ded 213")))[0])
    print(test_command_manager.run_command(QQRichText.QQRichText(QQRichText.Text("/email get")))[0])
    print(test_command_manager.run_command(QQRichText.QQRichText(QQRichText.Text("/email get 123")))[0])
    print(test_command_manager.run_command(QQRichText.QQRichText(QQRichText.Text("/email get 123 red")))[0])
    print(test_command_manager.run_command(
        QQRichText.QQRichText(
            QQRichText.Text("/email set image 123456"),
            QQRichText.Image("file://123")
        )
    )[0])
    print(test_command_manager.run_command(QQRichText.QQRichText(QQRichText.Text("/email sne")))[0])
