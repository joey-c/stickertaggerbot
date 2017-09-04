import logging

import flask_sqlalchemy as fsa
from sqlalchemy import literal
from sqlalchemy.sql.functions import func

# NOTE: All Models flush the session upon creation

MAX_STRING_SIZE = 80
database = fsa.SQLAlchemy()

sqlalchemy_loggers = ["sqlalchemy.engine",
                      "sqlalchemy.dialects",
                      "sqlalchemy.pool",
                      "sqlalchemy.orm"]


def sqlalchemy_logging(log=False, level=logging.DEBUG):
    if log:
        for logger in sqlalchemy_loggers:
            logging.getLogger(logger).setLevel(level)


class ModelMixin(object):
    @classmethod
    def get(cls, class_id):
        return cls.query.get(class_id)

    @classmethod
    def id_exists(cls, class_id):
        subquery = cls.query.filter_by(id=class_id)
        boolean = database.session.query(literal(True))
        result = boolean.filter(subquery.exists()).scalar()  # True or None
        return result == True

    # Returns number of records where field_string == value, or
    # returns number of records
    @classmethod
    def count(cls, field_string=None, value=None):
        if field_string and value:
            field = getattr(cls, field_string)
            return cls.query.filter(field == value).count()
        elif field_string:
            field = getattr(cls, field_string)
            return database.session.query(func.count(field)).scalar()
        else:
            return database.session.query(func.count(cls.id)).scalar()

    def add_to_database(self):
        database.session.add(self)
        database.session.flush()


class User(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)
    chat_id = database.Column(database.Integer)

    # Length derived from
    # https://core.telegram.org/method/account.checkUsername
    username = database.Column(database.String(32), unique=True)

    first_name = database.Column(database.String(MAX_STRING_SIZE))
    last_name = database.Column(database.String(MAX_STRING_SIZE))

    # Length derived from
    # https://stackoverflow.com/questions/17848070/what-data-type-should-i-use-for-ietf-language-codes
    language = database.Column(database.String(35))

    def __init__(self, user_id, chat_id, first_name, last_name=None,
                 username=None, language=None):
        self.id = user_id
        self.chat_id = chat_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.language = language
        self.add_to_database()

    # If not present, optional fields (last_name, username, and language_code)
    # are None
    @classmethod
    def from_telegram_user(cls, telegram_user, chat_id):
        return cls(telegram_user.id,
                   chat_id,
                   telegram_user.first_name,
                   telegram_user.last_name,
                   telegram_user.username,
                   telegram_user.language_code)

    def __str__(self):
        return "ID: " + str(self.id) + \
               ", Username: " + str(self.username) + \
               ", Name: " + str(self.name)


class Sticker(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)

    # Length derived from
    # http://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html#telegram.Bot.create_new_sticker_set
    set = database.Column(database.String(64))

    def __init__(self, sticker_id, set_name=None):
        self.id = sticker_id
        self.set = set_name
        self.add_to_database()

    @classmethod
    def from_telegram_sticker(cls, telegram_sticker):
        return cls(telegram_sticker.file_id,
                   telegram_sticker.set_name)

    def __str__(self):
        return "ID: " + str(self.id)


class Label(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)
    text = database.Column(database.String(MAX_STRING_SIZE))

    def __init__(self, text):
        self.text = text
        self.add_to_database()

    def __str__(self):
        return "ID: " + str(self.id) + \
               ", Text: " + str(self.text)


class Association(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)

    user_id = database.Column(database.Integer,
                              database.ForeignKey("user.id"))

    sticker_id = database.Column(database.Integer,
                                 database.ForeignKey("sticker.id"))

    label_id = database.Column(database.Integer,
                               database.ForeignKey("label.id"))

    __table_args__ = (database.UniqueConstraint("user_id",
                                                "sticker_id",
                                                "label_id"),)

    database.relationship("User", backref="associations", lazy="dynamic")
    database.relationship("Sticker", backref="associations", lazy="dynamic")
    database.relationship("Label", backref="associations", lazy="dynamic")

    def __init__(self, user, sticker, label):
        self.user_id = user.id
        self.sticker_id = sticker.id
        self.label_id = label.id
        self.add_to_database()

    def __str__(self):
        return "User: " + str(self.user_id) + \
               ", Sticker: " + str(self.sticker_id) + \
               ", Label: " + str(self.label_id)
