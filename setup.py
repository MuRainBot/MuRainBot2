import os
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

# --- 自定义构建逻辑 ---

SOURCE_DIR = 'plugins'
DEST_DIR_IN_PACKAGE = os.path.join('murainbot', 'templates')


class CustomBuildPy(build_py):
    """自定义的构建类，在构建时复制 plugins 文件夹"""

    def run(self):
        super().run()

        if os.path.isdir(SOURCE_DIR):
            target_dir = os.path.join(self.build_lib, DEST_DIR_IN_PACKAGE)
            dest_path = os.path.join(target_dir, 'plugins')

            print(f"--- Running custom build step: Copying {SOURCE_DIR} to {dest_path} ---")

            os.makedirs(target_dir, exist_ok=True)
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(SOURCE_DIR, dest_path)
        else:
            print(f"Warning: Source directory '{SOURCE_DIR}' not found, skipping copy.")

setup(
    cmdclass={
        'build_py': CustomBuildPy,
    }
)