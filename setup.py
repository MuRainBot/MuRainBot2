import os
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

# --- 自定义构建逻辑 ---

DEFAULT_PLUGINS = [
    'LagrangeExtension',
    'Helper.py',
]

SOURCE_DIR = 'plugins'
DEST_DIR_IN_PACKAGE = os.path.join('murainbot', 'templates', 'plugins')


class CustomBuildPy(build_py):
    """自定义的构建类，在构建时精确复制指定的默认插件"""

    def run(self):
        # 首先运行标准的构建过程
        super().run()

        # --- 开始我们的自定义复制逻辑 ---
        if not os.path.isdir(SOURCE_DIR):
            print(f"Warning: Source directory '{SOURCE_DIR}' not found, skipping plugin copy.")
            return

        # 计算目标路径
        target_dir = os.path.join(self.build_lib, DEST_DIR_IN_PACKAGE)
        print(f"--- Running custom build step: Copying default plugins to {target_dir} ---")

        # 确保目标目录存在，如果已存在则先清空，保证是干净的复制
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir)

        # 定义要忽略的文件/目录模式
        ignore_patterns = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.DS_Store')

        # 循环遍历我们定义的插件列表，并精确复制
        for plugin_name in DEFAULT_PLUGINS:
            source_path = os.path.join(SOURCE_DIR, plugin_name)
            dest_path = os.path.join(target_dir, plugin_name)

            if not os.path.exists(source_path):
                print(f"Warning: Plugin '{plugin_name}' not found at '{source_path}', skipping.")
                continue

            if os.path.isdir(source_path):
                # 如果是目录，使用 copytree 并传入忽略模式
                shutil.copytree(source_path, dest_path, ignore=ignore_patterns)
                print(f"Copied directory: {plugin_name}")
            elif os.path.isfile(source_path):
                # 如果是文件，直接复制
                shutil.copy2(source_path, dest_path)
                print(f"Copied file: {plugin_name}")


setup(
    cmdclass={
        'build_py': CustomBuildPy
    }
)
