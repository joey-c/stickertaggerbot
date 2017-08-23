import flask_sqlalchemy as fsa
from sqlalchemy import literal
from sqlalchemy.sql.functions import func

# NOTE: All Models flush the session upon creation

MAX_STRING_SIZE = 80
database = fsa.SQLAlchemy()


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
    username = database.Column(database.String(MAX_STRING_SIZE), unique=True)
    name = database.Column(database.String(MAX_STRING_SIZE))

    def __init__(self, user_id, username, name):
        self.id = user_id
        self.username = username
        self.name = name
        self.add_to_database()

    def __str__(self):
        return "ID: " + str(self.id) + \
               ", Username: " + str(self.username) + \
               ", Name: " + str(self.name)


class Sticker(database.Model, ModelMixin):
    id = database.Column(database.Integer, primary_key=True)

    def __init__(self, sticker_id):
        self.id = sticker_id
        self.add_to_database()

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
    user_id = database.Column(database.Integer,
                              database.ForeignKey("user.id"),
                              primary_key=True)

    sticker_id = database.Column(database.Integer,
                                 database.ForeignKey("sticker.id"),
                                 primary_key=True)

    label_id = database.Column(database.Integer,
                               database.ForeignKey("label.id"),
                               primary_key=True)

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
