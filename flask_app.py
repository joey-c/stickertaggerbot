import queue
import threading

import flask
import telegram
import telegram.ext

import tokens
import handlers
import models


class Application(flask.Flask):
    def __init__(self):
        super().__init__(__name__)
        self.debug = True
        self.bot = None
        self.update_queue = None
        self.dispatcher = None
        self.dispatcher_thread = None
        self.setup_telegram()
        self.database = None
        self.setup_database()

    def setup_telegram(self):
        self.bot = telegram.Bot(token=tokens.TELEGRAM)
        self.update_queue = queue.Queue()
        self.dispatcher = telegram.ext.Dispatcher(self.bot, self.update_queue)
        handlers.register_handlers(self.dispatcher)
        self.dispatcher_thread = threading.Thread(target=self.dispatcher.start,
                                                  name="dispatcher")
        self.dispatcher_thread.start()

    def setup_database(self):
        self.database = models.database
        self.database.init_app(self)
        with self.app_context():
            self.database.create_all()