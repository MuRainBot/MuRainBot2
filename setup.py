import os
import shutil
from setuptools import setup, find_packages

PACKAGE_NAME = "murainbot"
TEMPLATE_PLUGINS_DIR = "templates/plugins"
TARGET_DIR = os.path.join(PACKAGE_NAME, TEMPLATE_PLUGINS_DIR)
SOURCE_PLUGINS_DIR = "plugins"

# --- 构建前的清理和准备工作 ---
# 如果目标目录存在，先删除，确保是干净的构建
if os.path.exists(TARGET_DIR):
    shutil.rmtree(TARGET_DIR)
# 创建目标目录树
os.makedirs(TARGET_DIR)

# --- 定义要打包的内置插件 ---
bundled_plugins = ["LagrangeExtension", "Helper.py"]

# --- 复制插件到包内临时位置 ---
print(f"Copying bundled plugins to {TARGET_DIR}...")
for plugin_name in bundled_plugins:
    source_path = os.path.join(SOURCE_PLUGINS_DIR, plugin_name)
    if os.path.isdir(source_path):
        shutil.copytree(source_path, os.path.join(TARGET_DIR, plugin_name), ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
        print(f"  - Copied {plugin_name}")
    elif os.path.isfile(source_path):
        shutil.copy(source_path, os.path.join(TARGET_DIR, plugin_name))
        print(f"  - Copied {plugin_name}")
    else:
        print(f"  - {plugin_name} not found")

# --- Setuptools 的 setup() 函数 ---
setup(
    # 元数据会自动从 pyproject.toml 读取，这里不需要重复
    packages=find_packages(exclude=["plugins*"]),
    # 关键：告诉 setuptools 包含我们刚刚复制过来的所有文件
    include_package_data=True,
    package_data={
        PACKAGE_NAME: [f"{TEMPLATE_PLUGINS_DIR}/**/*"],
    }
)