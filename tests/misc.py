import flask
import telegram

from stickertaggerbot import flask_app, models, config

app_config = {"SQLALCHEMY_DATABASE_URI": config.DATABASE_URI,
              "SQLALCHEMY_TRACK_MODIFICATIONS": False}

app_for_testing = flask_app.Application(app_config, testing=True)


@app_for_testing.route("/" + config.TELEGRAM_TOKEN, methods=['POST'])
def route_update():
    update_json = flask.request.get_json()
    update = telegram.Update.de_json(update_json, app_for_testing.bot)
    app_for_testing.update_queue.put(update)
    return ""


tables = [models.User,
          models.Sticker,
          models.Label,
          models.Association]


def clear_all_tables():
    for table in tables:
        models.database.session.query(table).delete()

    models.database.session.flush()
