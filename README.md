<div align="center">

![MuRainBot2](https://socialify.git.ci/MuRainBot/MuRainBot2/image?custom_description=%E5%9F%BA%E4%BA%8Epython%E9%80%82%E9%85%8Donebot11%E5%8D%8F%E8%AE%AE%E7%9A%84%E8%BD%BB%E9%87%8F%E7%BA%A7OnebotBot%E6%A1%86%E6%9E%B6&description=1&forks=1&issues=1&logo=https%3A%2F%2Fgithub.com%2FMuRainBot%2FMuRainBot2Doc%2Fblob%2Fmaster%2Fdocs%2Fpublic%2Ficon.png%3Fraw%3Dtrue&name=1&pattern=Overlapping+Hexagons&pulls=1&stargazers=1&theme=Auto)
    <a href="https://github.com/MuRainBot/MuRainBot2/blob/master/LICENSE" style="text-decoration:none" >
        <img src="https://img.shields.io/static/v1?label=LICENSE&message=LGPL-2.1&color=lightgrey&style=for-the-badge" alt="GitHub license"/>
    </a>
    <a href="https://python.org/">
        <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=edb641&style=for-the-badge" alt="python">
    </a>
    <a href="https://11.onebot.dev/" style="text-decoration:none">
        <img src="https://img.shields.io/badge/OneBot-11-black?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHAAAABwCAMAAADxPgR5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAxQTFRF////29vbr6+vAAAAk1hCcwAAAAR0Uk5T////AEAqqfQAAAKcSURBVHja7NrbctswDATQXfD//zlpO7FlmwAWIOnOtNaTM5JwDMa8E+PNFz7g3waJ24fviyDPgfhz8fHP39cBcBL9KoJbQUxjA2iYqHL3FAnvzhL4GtVNUcoSZe6eSHizBcK5LL7dBr2AUZlev1ARRHCljzRALIEog6H3U6bCIyqIZdAT0eBuJYaGiJaHSjmkYIZd+qSGWAQnIaz2OArVnX6vrItQvbhZJtVGB5qX9wKqCMkb9W7aexfCO/rwQRBzsDIsYx4AOz0nhAtWu7bqkEQBO0Pr+Ftjt5fFCUEbm0Sbgdu8WSgJ5NgH2iu46R/o1UcBXJsFusWF/QUaz3RwJMEgngfaGGdSxJkE/Yg4lOBryBiMwvAhZrVMUUvwqU7F05b5WLaUIN4M4hRocQQRnEedgsn7TZB3UCpRrIJwQfqvGwsg18EnI2uSVNC8t+0QmMXogvbPg/xk+Mnw/6kW/rraUlvqgmFreAA09xW5t0AFlHrQZ3CsgvZm0FbHNKyBmheBKIF2cCA8A600aHPmFtRB1XvMsJAiza7LpPog0UJwccKdzw8rdf8MyN2ePYF896LC5hTzdZqxb6VNXInaupARLDNBWgI8spq4T0Qb5H4vWfPmHo8OyB1ito+AysNNz0oglj1U955sjUN9d41LnrX2D/u7eRwxyOaOpfyevCWbTgDEoilsOnu7zsKhjRCsnD/QzhdkYLBLXjiK4f3UWmcx2M7PO21CKVTH84638NTplt6JIQH0ZwCNuiWAfvuLhdrcOYPVO9eW3A67l7hZtgaY9GZo9AFc6cryjoeFBIWeU+npnk/nLE0OxCHL1eQsc1IciehjpJv5mqCsjeopaH6r15/MrxNnVhu7tmcslay2gO2Z1QfcfX0JMACG41/u0RrI9QAAAABJRU5ErkJggg==" alt="OneBot v11">
    </a>
    <br>
    <a href="https://github.com/MuRainBot/MuRainBot2">
        <img src="https://counter.seku.su/cmoe?name=murainbot2&theme=moebooru" alt="visitor counter"/>
    </a>
</div>

## 🤔 概述

MuRainBot2 (MRB2) 是一个基于 Python、适配 OneBot v11 协议的轻量级开发框架。

它专注于提供稳定高效的核心事件处理与 API 调用能力，所有具体功能（如关键词回复、群管理等）均通过插件实现，赋予开发者高度的灵活性。

对于具体的操作（如监听消息、发送消息、批准加群请求等）请先明确：

 - 什么是[OneBot11协议](https://11.onebot.dev)；
 - 什么是Onebot实现端，什么是Onebot开发框架；
 - Onebot实现端具有哪些功能

## ✨ 核心特性

*   **🪶 轻量高效：** 没有太多冗杂的功能，使用简单，内存占用较低。
*   **🧩 轻松扩展：** 灵活的插件系统，让您能够轻松、快速地添加、移除或定制所需功能。
*   **🔁 基于线程池：** 基于内置线程池实现并发处理，没有异步的较为复杂的语法，直接编写同步代码，且如果你使用nogil版本的python解释器可以获得更高的性能。
*   **🤖 命令解析：** 命令系统吸收了像 FastAPI 一样现代 Web 框架的优点，为开发者带来简洁、高效的插件编写体验。

## 🚨 重要提醒：关于重构与兼容性

> [!CAUTION]
> **请注意：** 本项目在 2025/6/29 进行了一次巨大修改&更新，修改了目录结构和包名，如果您是旧版本用户或拥有旧插件，请修改插件以进行适配。

> [!CAUTION]
> **请注意：** 本项目在 2024 年底至 2025 年初进行了一次 **彻底的重构**（主要涉及 `dev` 分支并在 2025年1月29日 合并至 `master`）。
>
> **当前的 MRB2 版本与重构前的旧版本插件完全不兼容。** 如果您是旧版本用户或拥有旧插件，请参考 **[最新文档](https://mrb2.xiaosu.icu)** 进行适配迁移。

## 📖 背景与术语

*   **MRB2：** MuRainBot2 的缩写。
*   **OneBot v11 协议：** 一个广泛应用于即时通讯软件中的聊天机器人的应用层协议标准，本项目基于此标准开发。详情请见 [OneBot v11](https://11.onebot.dev/)。
*   **框架：** MRB2 作为一个 OneBot 开发框架，负责处理与 OneBot 实现端的通信、事件分发、API 调用封装等底层工作，以及提供插件系统，让开发者可以专注于插件功能的实现。更多通用术语可参考 [OneBot v12 术语表](https://12.onebot.dev/glossary/) (v11 与 v12 大体相通)。
*   **插件：** MRB2 的所有功能都由插件提供。插件通常是放置在 `plugins` 目录下的 Python 文件或包含 `__init__.py` 的 Python 包。

~~*什么？你问我为什么要叫MRB2，因为这个框架最初是给我的一个叫做沐雨的bot写的，然后之前还有[一个写的很垃圾](https://github.com/xiaosuyyds/PyQQbot)的版本，所以就叫做MRB2*~~

## 🐛 问题反馈

如果使用时遇到问题，请按以下步骤操作：

1.  将框架版本更新到 [`dev`](https://github.com/MuRainBot/MuRainBot2/tree/dev) 分支（可选，但推荐）
2.  将 `config.yml` 中的 `debug.enable` 设置为 `true`。
3.  复现您遇到的 Bug。
4.  **检查 Onebot 实现端的日志**，确认问题是否源于实现端本身。如果是，请向您使用的实现端反馈。
5.  如果问题确认在 MRB2 框架：
    *   请准备**完整**的 MRB2 日志文件 (`logs` 目录下)。您可以自行遮挡日志中的 QQ 号、群号等敏感信息。
    *   提供清晰的错误描述、复现步骤。
    *   如果开启了 `save_dump` 且生成了 dump 文件，可以一并提供。（不强制，但是推荐提供，不过需要注意可以检查一下是否包含apikey等敏感信息）
    *   将当前使用的MRB2版本、日志、错误描述、复现步骤，以及dump文件（可选），提交到项目的 [**Issues**](https://github.com/MuRainBot/MuRainBot2/issues/new/choose) 页面。

如果不遵守以上要求，您的问题可能会被关闭或无视。

## 📁 目录结构

<details>
<summary>查看基本目录结构</summary>

```
├─ data                MRB2及插件的临时/缓存文件
│   ├─ ...
├─ murainbot                 MRB2的Lib库，插件和MRB2均需要依赖此Lib
│   ├─ __init__.py     MRB2Lib的初始化文件
│   ├─ core            核心模块，负责配置文件读取、与实现端通信、插件加载等
│   |   ├─ ...
│   ├─ utils           工具模块，实现一些偏工具类的功能，例如QQ信息缓存、日志记录、事件分类等
│   |   ├─ ...
│   ...
├─ logs
│   ├─ latest.log      当日的日志
│   ├─ xxxx-xx-xx.log  以往的日志
│   ...
├─ plugins
│   ├─ xxx.py           xxx插件代码
│   ├─ yyy.py           yyy插件代码
│   ...
├─ plugin_configs
│   ├─ xxx.yml          xxx插件的配置文件
│   ├─ yyy.yml          yyy插件的配置文件
│   ...
├─ config.yml           MRB2配置文件
├─ main.py              MRB2的入口文件
└─ README.md            这个文件就不用解释了吧（？）
```

</details>

## 💻 如何部署？

**本项目使用 Python 3.12+ 开发，并利用了其部分新特性 (如 [PEP 701](https://docs.python.org/zh-cn/3/whatsnew/3.12.html#whatsnew312-pep701))。推荐使用 Python 3.12 或更高版本运行，如果使用 Python 3.12 以下版本，由于未经测试，可能会导致部分代码出现问题。**

~~详细~~的部署步骤、配置说明和插件开发指南，请查阅：

### ➡️ [**MRB2 官方文档**](https://mrb2.xiaosu.icu)

#### 快速部署指南

- 安装murainbot2
  ```bash
  pip install murainbot
  ```
- 创建项目
  ```bash
  murainbot init
  ```
- 启动项目
  ```bash
  murainbot run
  ```

## 📕 关于版本

* 目前项目仍在开发中，属于测试版，未来还可能会有一些不兼容更改和新功能添加，也欢迎各位提供宝贵的建设性的意见。

## ❤️ 鸣谢 ❤️

**贡献指南：** 我们欢迎各种形式的贡献！包括 Issues 和 Pull Request，您可以向我们反馈 bug 提供建议，请求一些新功能，也可以通过 PR 直接帮我们编写代码来实现功能或者修复bug。请将您的 Pull Request 提交到 `dev` 分支。我们会定期将 `dev` 分支的稳定更新合并到 `master` 分支。

**感谢所有为 MRB2 付出努力的贡献者！**

<a href="https://github.com/MuRainBot/MuRainBot2/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MuRainBot/MuRainBot2&max=999" alt="Contributors">
</a>

**特别感谢 [HarcicYang](https://github.com/HarcicYang)、[kaokao221](https://github.com/kaokao221) 和 [BigCookie233](https://github.com/BigCookie233) 在项目开发过程中提供的宝贵帮助！**

## ⭐ Star History ⭐

[![](https://api.star-history.com/svg?repos=MuRainBot/MuRainBot2&type=Date)](https://github.com/MuRainBot/MuRainBot2/stargazers)


## 🚀 关于性能

本项目在正常使用，默认配置，多群聊，6-8个中等复杂度（如签到、图片绘制（如视频信息展示等）、AI聊天（基于API接口调用的））的插件情况下内存占用稳定在 100-160MB 左右
（具体取决于插件和群聊数量以及配置文件，也可能超过这个范围）

仅安装默认插件，默认配置，情况下内存占用稳定在 40MB-60MB 左右

如果实在内存不够用可调小缓存（配置文件中的 `qq_data_cache.max_cache_size`）（尽管这个也占不了多少内存）
