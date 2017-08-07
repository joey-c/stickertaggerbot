import logging
import os

import flask
import telegram

import flask_app
import tokens

logging.basicConfig(filename=os.environ["LOG_LOCATION"],
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - '
                           '%(message)s',
                    datefmt='%d/%m/%Y %I:%M:%S %p')

application = flask_app.create_app()


@application.route("/" + tokens.TELEGRAM, methods=['POST'])
def route_update():
    update_json = flask.request.get_json()
    update = telegram.Update.de_json(update_json, application.bot)
    application.update_queue.put(update)
    return "put an update"
