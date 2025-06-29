"""
默认常量
"""

DEFAULT_CONFIG = """# MuRainBot2配置文件
account:  # 账号相关
  user_id: 0  # QQ账号（留空则自动获取）
  nick_name: ""  # 昵称（留空则自动获取）
  bot_admin: []

api:  # Api设置(Onebot HTTP通信)
  host: '127.0.0.1'
  port: 5700
  access_token: ""  # HTTP的Access Token，为空则不使用（详见https://github.com/botuniverse/onebot-11/blob/master/communication/authorization.md#http-%E5%92%8C%E6%AD%A3%E5%90%91-websocket）

server:  # 监听服务器设置（Onebot HTTP POST通信）
  host: '127.0.0.1'
  port: 5701
  server: 'werkzeug'  # 使用的服务器（werkzeug或waitress，使用waitress需先pip install waitress）
  max_works: 4  # 最大工作线程数
  secret: ""  # 上报数据签名密钥（详见https://github.com/botuniverse/onebot-11/blob/master/communication/http-post.md#%E7%AD%BE%E5%90%8D）

thread_pool:  # 线程池相关
  max_workers: 10  # 线程池最大线程数

qq_data_cache:  # QQ数据缓存设置
  enable: true  # 是否启用缓存（非常不推荐关闭缓存，对于对于需要无缓存的场景，推荐在插件内自行调用api来获取而非关闭此配置项）
  expire_time: 300  # 缓存过期时间（秒）
  max_cache_size: 500  # 最大缓存数量（设置过大可能会导致报错）

debug:  # 调试模式，若启用框架的日志等级将被设置为debug，不建议在生产环境开启
  enable: false  # 是否启用调试模式
  save_dump: true  # 是否在发生异常的同时保存一个dump错误文件（不受debug.enable约束，独立开关，若要使用请先安装coredumpy库，不使用可不安装）

auto_restart_onebot:  # 在Onebot实现端状态异常时自动重启Onebot实现端（需开启心跳包）
  enable: true  # 是否启用自动重启

command:  # 命令相关
  command_start: ["/"]  # 命令起始符
"""
