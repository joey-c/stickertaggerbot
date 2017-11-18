import queue
import threading

import flask
import telegram
import telegram.ext

from stickertaggerbot import config, handlers, models


class Application(flask.Flask):
    def __init__(self, config=None, testing=False, sqlalchemy_logging=False):
        super().__init__(__name__)
        self.apply_config(config)
        self.testing = testing
        self.debug = True

        self.bot = None
        self.update_queue = None
        self.dispatcher = None
        self.dispatcher_thread = None
        self.setup_telegram()

        self.database = None
        self.setup_database(sqlalchemy_logging)

    def apply_config(self, config):
        if not config:
            return
        
        for key, value in config.items():
            self.config[key] = value

    def setup_telegram(self):
        self.bot = telegram.Bot(token=config.TELEGRAM_TOKEN)
        self.update_queue = queue.Queue()
        self.dispatcher = telegram.ext.Dispatcher(self.bot, self.update_queue)
        handlers.register_handlers(self.dispatcher, self)
        self.dispatcher_thread = threading.Thread(target=self.dispatcher.start,
                                                  name="dispatcher")
        self.dispatcher_thread.start()

    def setup_database(self, sqlalchemy_logging):
        self.database = models.database
        self.database.init_app(self)
        with self.app_context():
            self.database.create_all()
        models.sqlalchemy_logging(log=sqlalchemy_logging)
