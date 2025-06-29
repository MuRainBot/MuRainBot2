import shutil
from pathlib import Path
import typer
from typing_extensions import Annotated
from rich import print

app = typer.Typer(
    add_completion=False,
    help="""
    MuRainBot2 命令行工具

    一个用于创建、管理和运行 MuRainBot 实例的强大工具。
    """
)

from ._defaults import DEFAULT_CONFIG

# --- 默认 .gitignore 文件内容 ---
DEFAULT_GITIGNORE_CONTENT = """
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env

# MuRainBot
/data/
/logs/
/exc_dumps/
*.db
*.db-journal
"""


# --- `init` 命令 ---
@app.command(
    name="init",
    help="🚀 初始化一个新的 MuRainBot 项目。"
)
def init_project(
        project_name: Annotated[str, typer.Argument(
            help="新机器人项目的文件夹名称。",
            show_default=False,
        )],
):
    """
    创建一个包含标准目录结构和默认配置的全新 MuRainBot 项目。
    """
    project_path = Path(project_name).resolve()  # 使用 resolve 获取绝对路径

    # 检查目录是否已存在
    if project_path.exists():
        print(f"[bold red]❌ 错误: 目录 '{project_path.name}' 已存在。[/bold red]")
        raise typer.Exit(code=1)

    print(f"✨ 正在 '{project_path.parent}' 目录下创建新项目: [bold cyan]{project_path.name}[/bold cyan]")

    try:
        # --- 创建目录结构 ---
        project_path.mkdir()
        (project_path / "plugins").mkdir()
        (project_path / "data").mkdir()
        (project_path / "logs").mkdir()
        (project_path / "plugin_configs").mkdir()
        (project_path / "exc_dumps").mkdir()
        print("    - 📂 目录结构创建成功。")

        # --- 复制内置插件 ---
        dest_plugins_path = project_path / "plugins"
        # 找到打包在框架内的源插件目录
        source_plugins_path = Path(__file__).parent / "templates" / "plugins"

        if source_plugins_path.is_dir():
            shutil.copytree(source_plugins_path, dest_plugins_path, dirs_exist_ok=True)
            print("    - 🧩 内置插件 (Helper, LagrangeExtension) 安装成功。")

        # --- 创建默认文件 ---
        (project_path / "config.yml").write_text(DEFAULT_CONFIG.strip(), encoding="utf-8")
        print("    - 📄 默认 `config.yml` 创建成功。")

        (project_path / ".gitignore").write_text(DEFAULT_GITIGNORE_CONTENT.strip(), encoding="utf-8")
        print("    - 🕶️ 默认 `.gitignore` 创建成功。")

    except Exception as e:
        print(f"\n❌ [red bold]创建项目时发生错误: {e}[/red bold]")
        # 如果出错，尝试清理已创建的目录
        if project_path.exists():
            shutil.rmtree(project_path)
            print(f"[yellow]已清理不完整的项目目录 '{project_path.name}'。[/yellow]")
        raise typer.Exit(code=1)

    # --- 成功提示 ---
    success_message = f"""
[bold green]🎉 项目 '{project_path.name}' 创建成功! 🎉[/bold green]

接下来，请执行以下步骤:

1. [bold]进入项目目录:[/bold]
   [cyan]cd {project_name}[/cyan]

2. [bold]编辑配置文件:[/bold]
   打开 [yellow]config.yml[/yellow] 文件，根据你的需求进行修改。

3. [bold]启动你的机器人:[/bold]
   [cyan]murainbot run[/cyan]
"""
    print(success_message)


# --- `run` 命令 ---
@app.command(
    name="run",
    help="▶️ 运行当前目录下的 MuRainBot 实例。"
)
def run_bot():
    """
    加载当前目录的配置和插件，并启动机器人服务。
    """
    # 检查是否在项目目录中
    config_path = Path("plugins")
    if not config_path.is_dir():
        print("[red bold]❌ 错误: 未找到 `plugins` 目录。[/red bold]")
        print("请确保你在一个由 `murainbot init` 创建的项目目录中运行此命令。")
        raise typer.Exit(code=1)

    work_path = Path.cwd()

    print(f"✅ [green]找到 `plugins` 目录，工作目录 {work_path}，准备启动...[/green]")

    try:
        from murainbot.main import start
        start(work_path)

    except ImportError as e:
        print(f"❌ [red]启动失败: 无法导入核心模块 - {repr(e)}[/red]")
        print("这可能是一个安装问题。请尝试重新安装 `murainbot`。")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"\n❌ [red bold]机器人启动时发生致命错误: {repr(e)}[/red bold]")
        raise typer.Exit(code=1)


# --- CLI 主入口 ---
def main():
    app()


if __name__ == "__main__":
    main()
