from Text2StickerBot import flask_app, models

app_for_testing = flask_app.Application(testing=True)

tables = [models.User,
          models.Sticker,
          models.Label,
          models.Association]


def clear_all_tables():
    for table in tables:
        models.database.session.query(table).delete()

    models.database.session.flush()
