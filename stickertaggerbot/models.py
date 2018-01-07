import logging

import flask_sqlalchemy as fsa
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


class ObjectAlreadyExistsError(Exception):
    pass


class ModelMixin(object):
    @classmethod
    def get(cls, class_id):
        return cls.query.get(class_id)

    @classmethod
    def id_exists(cls, class_id):
        query = cls.query.filter_by(id=class_id)
        return query.count() > 0

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
        if User.id_exists(user_id):
            raise ObjectAlreadyExistsError("User exists")

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
    id = database.Column(database.String(MAX_STRING_SIZE), primary_key=True)

    # Length derived from
    # http://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html#telegram.Bot.create_new_sticker_set
    set = database.Column(database.String(64))

    def __init__(self, sticker_id, set_name=None):
        if Sticker.id_exists(sticker_id):
            raise ObjectAlreadyExistsError("Sticker exists")

        self.id = sticker_id
        self.set = set_name
        self.add_to_database()

    def __str__(self):
        return "ID: " + str(self.id)

    @classmethod
    def from_telegram_sticker(cls, telegram_sticker):
        return cls(telegram_sticker.file_id,
                   telegram_sticker.set_name)

    @classmethod
    def get_or_create(cls, telegram_sticker, get_only=False):
        sticker = cls.get(telegram_sticker.file_id)
        if sticker:
            return sticker
        else:
            return cls.from_telegram_sticker(telegram_sticker)


class Label(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)
    text = database.Column(database.String(MAX_STRING_SIZE),
                           unique=True)

    def __init__(self, text):
        if Label.exists(text):
            raise ObjectAlreadyExistsError("Label exists")

        self.text = text
        self.add_to_database()

    def __str__(self):
        return "ID: " + str(self.id) + \
               ", Text: " + str(self.text)

    @classmethod
    def get_or_create(cls, text, get_only=False):
        query = cls.query.filter_by(text=text)

        if query.count() == 0:
            if not get_only:
                return cls(text)
            else:
                return None
        elif query.count() == 1:
            return query.first()

    @classmethod
    def exists(cls, text):
        query = cls.query.filter_by(text=text)
        return query.count() > 0

    @classmethod
    def query_get_ids(cls, texts):
        select_ids = cls.query.with_entities(cls.id)
        any_texts = cls.text.in_(texts)
        return select_ids.filter(any_texts)

    @classmethod
    def get_ids(cls, texts):
        label_ids = cls.query_get_ids(texts).all()
        return [label_id for label_id, in label_ids]


class Association(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)

    user_id = database.Column(database.Integer,
                              database.ForeignKey("user.id"))

    sticker_id = database.Column(database.String(MAX_STRING_SIZE),
                                 database.ForeignKey("sticker.id"))

    label_id = database.Column(database.Integer,
                               database.ForeignKey("label.id"))

    uses = database.Column(database.Integer)

    __table_args__ = (database.UniqueConstraint("user_id",
                                                "sticker_id",
                                                "label_id"),)

    database.relationship("User", backref="associations", lazy="dynamic")
    database.relationship("Sticker", backref="associations", lazy="dynamic")
    database.relationship("Label", backref="associations", lazy="dynamic")

    def __init__(self, user, sticker, label):
        if Association.exists(user, sticker, label):
            raise ObjectAlreadyExistsError("Association exists")
        self.user_id = user.id
        self.sticker_id = sticker.id
        self.label_id = label.id
        self.uses = 0
        self.add_to_database()

    def __str__(self):
        return "User: " + str(self.user_id) + \
               ", Sticker: " + str(self.sticker_id) + \
               ", Label: " + str(self.label_id) + \
               ", Uses: " + str(self.uses)

    @classmethod
    def exists(cls, user, sticker, label):
        query = cls.query.filter_by(user_id=user.id,
                                    sticker_id=sticker.id,
                                    label_id=label.id)
        return query.count() > 0

    @classmethod
    def query_get_sticker_ids(cls, user_id, labels, unique=False):
        label_ids = Label.get_ids(labels)
        select_sticker_ids = cls.query.with_entities(cls.sticker_id)
        any_labels = cls.label_id.in_(label_ids)
        query = select_sticker_ids.filter_by(user_id=user_id).filter(
            any_labels)

        if unique:
            query = query.distinct()

        return query

    @classmethod
    def get_sticker_ids(cls, user_id, labels, unique=False):
        sticker_ids = cls.query_get_sticker_ids(user_id, labels, unique).all()
        return [sticker_id for sticker_id, in sticker_ids]

    @classmethod
    def increment_usage(cls, user_id, sticker_id, labels):
        by_user_and_sticker = cls.query.filter_by(user_id=user_id,
                                                  sticker_id=sticker_id)
        label_ids = Label.query_get_ids(labels)
        any_labels = cls.label_id.in_(label_ids)

        associations = by_user_and_sticker.filter(any_labels)

        associations.update({'uses': Association.uses + 1},
                            synchronize_session='fetch')  # Hence not flushing

    # Fails silently if no such association exists
    @classmethod
    def get_usage_count(cls, sticker_id, label, user_id=None):
        uses = 0

        label_id = Label.get_ids([label])
        if not label_id:
            return uses
        label_id, = label_id

        if user_id is None:
            query = Association.query.filter_by(sticker_id=sticker_id,
                                                label_id=label_id)
            uses = query.with_entities(func.sum(Association.uses)).scalar()
        else:
            select_uses = Association.query.with_entities(Association.uses)
            query = select_uses.filter_by(
                user_id=user_id, sticker_id=sticker_id, label_id=label_id)
            result = query.first()
            if result:
                uses, = result

        return uses
