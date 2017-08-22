import queue
import threading

import flask
import telegram
import telegram.ext

import tokens
import handlers


class Application(flask.Flask):
    def __init__(self):
        super().__init__(__name__)
        self.debug = True
        self.bot = None
        self.update_queue = None
        self.dispatcher = None
        self.dispatcher_thread = None
        self.setup_telegram()

    def setup_telegram(self):
        self.bot = telegram.Bot(token=tokens.TELEGRAM)
        self.update_queue = queue.Queue()
        self.dispatcher = telegram.ext.Dispatcher(self.bot, self.update_queue)
        handlers.register_handlers(self.dispatcher)
        self.dispatcher_thread = threading.Thread(target=self.dispatcher.start,
                                                  name="dispatcher")
        self.dispatcher_thread.start()

