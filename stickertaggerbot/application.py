import flask
import telegram

from stickertaggerbot import config, flask_app, loggers

app_config = {"SQLALCHEMY_DATABASE_URI": config.DATABASE_URI,
              "SQLALCHEMY_TRACK_MODIFICATIONS": False}

application = flask_app.Application(app_config)


@application.route("/" + config.TELEGRAM_TOKEN, methods=['POST'])
def route_update():
    update_json = flask.request.get_json()
    update = telegram.Update.de_json(update_json, application.bot)
    application.update_queue.put(update)
    loggers.APP.info("Received update " + str(update.update_id))
    return ""
