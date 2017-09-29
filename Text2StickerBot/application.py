import flask
import telegram

from Text2StickerBot import config, flask_app, loggers



application = flask_app.Application()
application.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URI
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

@application.route("/" + config.TELEGRAM_TOKEN, methods=['POST'])
def route_update():
    update_json = flask.request.get_json()
    update = telegram.Update.de_json(update_json, application.bot)
    application.update_queue.put(update)
    loggers.APP.info("Received update " + str(update.update_id))
    return ""
