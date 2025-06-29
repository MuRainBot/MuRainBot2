"""
监听服务器
"""

from ..utils import Logger
from .ConfigManager import GlobalConfig
from murainbot.core import EventManager

from concurrent.futures import ThreadPoolExecutor
from wsgiref.simple_server import WSGIServer

from flask import Flask, request
import hmac

logger = Logger.get_logger()
app = Flask(__name__)


class EscalationEvent(EventManager.Event):
    """
    上报事件
    """

    def __init__(self, event_data):
        self.event_data = event_data


@app.route("/", methods=["POST"])
def post_data():
    """
    上报处理
    """
    if GlobalConfig().server.secret:
        sig = hmac.new(GlobalConfig().server.secret.encode("utf-8"), request.get_data(), 'sha1').hexdigest()
        try:
            received_sig = request.headers['X-Signature'][len('sha1='):]
        except KeyError:
            logger.warning("收到非法请求(缺少签名)，拒绝访问")
            return "", 401
        if sig != received_sig:
            logger.warning("收到非法请求(签名不匹配)，拒绝访问")
            return "", 401
    data = request.get_json()
    logger.debug("收到上报: %s" % data)
    if "self" in data and GlobalConfig().account.user_id != 0 and data.get("self") != GlobalConfig().account.user_id:
        logger.warning(f"收到来自其他bot的消息，忽略: {data}")
        return "ok", 204
    EscalationEvent(data).call_async()

    return "ok", 204


config = GlobalConfig()
if config.server.server == "werkzeug":
    # 使用werkzeug服务器
    from werkzeug.serving import WSGIRequestHandler


    class ThreadPoolWSGIServer(WSGIServer):
        """
        线程池WSGI服务器
        """

        def __init__(self, server_address, app=None, max_workers=10, passthrough_errors=False,
                     handler_class=WSGIRequestHandler, **kwargs):
            super().__init__(server_address, handler_class, **kwargs)
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
            self.app = app
            self.ssl_context = None
            self.multithread = True
            self.multiprocess = False
            self.threaded = True
            self.passthrough_errors = passthrough_errors

        def handle_request(self):
            """
            处理请求
            """
            request, client_address = self.get_request()
            if self.verify_request(request, client_address):
                self.executor.submit(self.process_request, request, client_address)

        def serve_forever(self):
            """
            启动服务器
            """
            while True:
                self.handle_request()


    class ThreadPoolWSGIRequestHandler(WSGIRequestHandler):
        def handle(self):
            super().handle()


    server = ThreadPoolWSGIServer((config.server.host, config.server.port),
                                  app=app,
                                  max_workers=config.server.max_works)
    server.RequestHandlerClass = ThreadPoolWSGIRequestHandler
    start_server = lambda: server.serve_forever()
elif config.server.server == "waitress":
    # 使用waitress服务器
    from waitress import serve

    start_server = lambda: serve(app, host=config.server.host, port=config.server.port, threads=config.server.max_works)
else:
    raise ValueError("服务器类型错误: 未知服务器类型")
