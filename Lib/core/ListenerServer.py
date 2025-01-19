from ..utils import Logger
from .ConfigManager import GlobalConfig
from Lib.core import EventManager

from concurrent.futures import ThreadPoolExecutor
from wsgiref.simple_server import WSGIServer

from flask import Flask, request
from werkzeug.serving import WSGIRequestHandler


logger = Logger.get_logger()
app = Flask(__name__)


class EscalationEvent(EventManager.Event):
    def __init__(self, event_data):
        self.event_data = event_data


@app.route("/", methods=["POST"])
def post_data():
    data = request.get_json()
    logger.debug("收到上报: %s" % data)
    if "self" in data and GlobalConfig().account.user_id != 0 and data.get("self") != GlobalConfig().account.user_id:
        logger.warning(f"收到来自其他bot的消息，忽略: {data}")
        return "ok", 204
    EscalationEvent(data).call_async()

    return "ok", 204


class ThreadPoolWSGIServer(WSGIServer):
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
        request, client_address = self.get_request()
        if self.verify_request(request, client_address):
            self.executor.submit(self.process_request, request, client_address)

    def serve_forever(self):
        logger.info("监听服务器启动成功！")
        while True:
            self.handle_request()


class ThreadPoolWSGIRequestHandler(WSGIRequestHandler):
    def handle(self):
        super().handle()


config = GlobalConfig()
server = ThreadPoolWSGIServer((config.server.host, config.server.port),
                              app=app,
                              max_workers=config.server.max_works)
server.RequestHandlerClass = ThreadPoolWSGIRequestHandler
