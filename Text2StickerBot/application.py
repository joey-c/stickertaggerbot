import logging
import os

import flask
import telegram

from Text2StickerBot import config, flask_app

logging.basicConfig(filename=os.environ["LOG_LOCATION"],
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - '
                           '%(message)s',
                    datefmt='%d/%m/%Y %I:%M:%S %p')

application = flask_app.Application()
application.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URI
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

@application.route("/" + config.TELEGRAM_TOKEN, methods=['POST'])
def route_update():
    update_json = flask.request.get_json()
    update = telegram.Update.de_json(update_json, application.bot)
    application.update_queue.put(update)
    return ""
