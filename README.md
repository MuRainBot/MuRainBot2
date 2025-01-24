<h1 align="center">MuRain Bot2(MRB2)</h1>
<p align="center" class="shields">
    <a href="https://github.com/MuRainBot/MuRainBot2/issues" style="text-decoration:none">
        <img src="https://img.shields.io/github/issues/MuRainBot/MuRainBot2.svg?style=for-the-badge" alt="GitHub issues"/>
    </a>
    <a href="https://github.com/MuRainBot/MuRainBot2/stargazers" style="text-decoration:none" >
        <img src="https://img.shields.io/github/stars/MuRainBot/MuRainBot2.svg?style=for-the-badge" alt="GitHub stars"/>
    </a>
    <a href="https://github.com/MuRainBot/MuRainBot2/forks" style="text-decoration:none" >
        <img src="https://img.shields.io/github/forks/MuRainBot/MuRainBot2.svg?style=for-the-badge" alt="GitHub forks"/>
    </a>
    <!--
    <a href="https://github.com/MuRainBot/MuRainBot2/actions">
        <img src="https://img.shields.io/github/actions/workflow/status/MuRainBot/MuRainBot2/vuepress-deploy.yml?style=for-the-badge">
    </a>
    -->
    <a href="https://github.com/MuRainBot/MuRainBot2/blob/master/LICENSE" style="text-decoration:none" >
        <img src="https://img.shields.io/static/v1?label=LICENSE&message=GPL-3.0&color=lightrey&style=for-the-badge" alt="GitHub license"/>
    </a>
    <a href="https://github.com/botuniverse/onebot" style="text-decoration:none">
        <img src="https://img.shields.io/badge/OneBot-11-black?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHAAAABwCAMAAADxPgR5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAxQTFRF////29vbr6+vAAAAk1hCcwAAAAR0Uk5T////AEAqqfQAAAKcSURBVHja7NrbctswDATQXfD//zlpO7FlmwAWIOnOtNaTM5JwDMa8E+PNFz7g3waJ24fviyDPgfhz8fHP39cBcBL9KoJbQUxjA2iYqHL3FAnvzhL4GtVNUcoSZe6eSHizBcK5LL7dBr2AUZlev1ARRHCljzRALIEog6H3U6bCIyqIZdAT0eBuJYaGiJaHSjmkYIZd+qSGWAQnIaz2OArVnX6vrItQvbhZJtVGB5qX9wKqCMkb9W7aexfCO/rwQRBzsDIsYx4AOz0nhAtWu7bqkEQBO0Pr+Ftjt5fFCUEbm0Sbgdu8WSgJ5NgH2iu46R/o1UcBXJsFusWF/QUaz3RwJMEgngfaGGdSxJkE/Yg4lOBryBiMwvAhZrVMUUvwqU7F05b5WLaUIN4M4hRocQQRnEedgsn7TZB3UCpRrIJwQfqvGwsg18EnI2uSVNC8t+0QmMXogvbPg/xk+Mnw/6kW/rraUlvqgmFreAA09xW5t0AFlHrQZ3CsgvZm0FbHNKyBmheBKIF2cCA8A600aHPmFtRB1XvMsJAiza7LpPog0UJwccKdzw8rdf8MyN2ePYF896LC5hTzdZqxb6VNXInaupARLDNBWgI8spq4T0Qb5H4vWfPmHo8OyB1ito+AysNNz0oglj1U955sjUN9d41LnrX2D/u7eRwxyOaOpfyevCWbTgDEoilsOnu7zsKhjRCsnD/QzhdkYLBLXjiK4f3UWmcx2M7PO21CKVTH84638NTplt6JIQH0ZwCNuiWAfvuLhdrcOYPVO9eW3A67l7hZtgaY9GZo9AFc6cryjoeFBIWeU+npnk/nLE0OxCHL1eQsc1IciehjpJv5mqCsjeopaH6r15/MrxNnVhu7tmcslay2gO2Z1QfcfX0JMACG41/u0RrI9QAAAABJRU5ErkJggg==" alt="Badge">
    </a>
    <br>
    <a href="https://github.com/MuRainBot/MuRainBot2">
        <img src="https://counter.seku.su/cmoe?name=murainbot2&theme=rule34" alt=""/>
    </a>
</p>


## 🤔概述

### 这是什么？

#### 这是一个基于python适配onebot11协议的轻量级QQBot框架

切记！
MRB2本身**不具备任何**实际功能
具体的功能（如通过关键词回复特定消息等）都需要插件来实现，有任何功能的需要可以自行阅读文档编写

~~作者自己写着用的，有一些写的不好的地方还请见谅（不过估计也没人会用我这个项目吧）~~

~~*什么？你问我为什么要叫MRB2，因为这个框架最初是给我的一个叫做沐雨的qqbot写的，然后之前还有[一个写的很垃圾](https://github.com/xiaosuyyds/PyQQbot)的版本，所以就叫做MRB2*~~


### 关于本Readme以及MRB2文档的一些术语
#### 首先推荐在阅读本Readme以及MRB2文档中先了解Onebot的一些基本属于以方便理解[我是链接](https://12.onebot.dev/glossary)
(上述的术语表中是Onebot12的定义，对于Onebot11可能略有偏差但是大体相通)
* MRB2：MuRainBot2，缩写MRB2
* onebot11协议：[OneBot v11](https://11.onebot.dev/)，一个用于QQ机器人的协议，本项目就是基于此协议开发的框架
* 框架：根据[onebot12的定义](https://12.onebot.dev/glossary/#onebot-sdk)(~~我也不知道为什么，但是onebot11就是没有定义什么是框架和sdk之类乱七八糟的术语表~~)
MRB2就是这样一个SDK，可以让插件不需要自行实现http通讯和事件、操作、消息等内容的事件分发与解析，同时将实际的功能分为一个一个插件，方便管理，所以也称为框架
* 插件：MRB2本身不具备任何实际上的功能，一切都需要编写插件来实现功能；
MRB2的插件，统一放在`plugins`文件夹中，每个插件都是一个python文件，也可以是一个文件夹，文件夹中必须包含一个`__init__.py`文件用于初始化插件

### 关于一些提醒

本项目在2024年12月4日在dev分支对框架进行了重构，主要重构了目录结构与一些Lib的实现，不支持过去的插件，如果你有旧版本的插件，可以尝试使用新的框架的文档来进行适配（放心，差别不会很大）。

目前重构尚未完成，请勿现在在将框架用于实际部署。

---

如果使用时遇到问题，请将 `config.yml` 的`debug.enable`设置为`true`，然后复现 bug，
并检查该问题是否是你使用的 Onebot 实现端的问题（可查看实现端的日志检查是否有异常）

如果是，请自行在你使用的 Onebot 实现端进行反馈。

如果不是，将完整 完整 完整的将日志信息（部分对于问题排查不重要的敏感信息（如 QQ 群号、 QQ 号等）可自行遮挡） 和错误描述发到 [issues](https://github.com/MuRainBot/MuRainBot2/issues/new/choose)。

### 目录结构


<details>
<summary>查看基本看目录结构</summary>

```
├─ data                MRB2及插件的临时/缓存文件
│   ├─ ...
├─ Lagrange.Onebot     Onebot实现端，此处以Lagrange.Onebot例
├─ Lib                 MRB2的Lib库，插件和MRB2均需要依赖此Lib
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


## 💻如何部署？
**作者在python3.12编写，由于使用了一些高版本python添加的特性
（例如[PEP701中取消部分f-string语法限制（这真的超方便的好不好(）](https://docs.python.org/zh-cn/3.13/whatsnew/3.12.html#whatsnew312-pep701)），
推荐在3.12.X或以上版本部署和运行**

### 具体可查看本项目的[`文档`](https://mrb2.xiaosu.icu)

## 📕关于版本
* 目前MRB2版本为2.0.0-dev

~~*你问我为什么第一个版本就是2.0.0?因为这是MRB2嘛自然就是2.0.0开始的咯*~~
* 关于版本号的说明：
   * 版本号格式为`<主版本>.<次版本>.<修订版本>-<特殊提醒/版本(如果有)>` 例如`2.0.0`
   * 测试版版本号后统一添加`-dev`后缀 例如`2.0.0-dev`

## ❤️鸣谢❤️

### 请勿直接提交到[`master`](https://github.com/MuRainBot/MuRainBot2)分支，请先提交到[`dev`](https://github.com/MuRainBot/MuRainBot2/tree/dev)分支，每隔一段时间我们会合并到[`master`](https://github.com/MuRainBot/MuRainBot2)分支

### 感谢所有为此项目做出贡献的大大，你们的存在，让社区变得更加美好~！
<a href="https://github.com/MuRainBot/MuRainBot2/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MuRainBot/MuRainBot2&max=999" alt=感谢他们（鼓掌）！>
</a>

### 以及特别鸣谢[HarcicYang](https://github.com/HarcicYang)和[kaokao221](https://github.com/kaokao221)为此项目提供了许多的帮助~


## ⭐StarHistory⭐

[![](https://api.star-history.com/svg?repos=MuRainBot/MuRainBot2&type=Date)](https://github.com/MuRainBot/MuRainBot2/stargazers)
