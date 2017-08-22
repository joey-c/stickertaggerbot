import flask_sqlalchemy as fsa

# NOTE: All Models flush the session upon creation

MAX_STRING_SIZE = 80
database = fsa.SQLAlchemy()


class User(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    username = database.Column(database.String(MAX_STRING_SIZE), unique=True)
    name = database.Column(database.String(MAX_STRING_SIZE))

    def __init__(self, user_id, username, name):
        self.id = user_id
        self.username = username
        self.name = name
        database.session.add(self)
        database.session.flush()

    def __str__(self):
        return "ID: " + str(self.id) + \
               ", Username: " + str(self.username) + \
               ", Name: " + str(self.name)


class Sticker(database.Model):
    id = database.Column(database.Integer, primary_key=True)

    def __init__(self, sticker_id):
        self.id = sticker_id
        database.session.add(self)
        database.session.flush()


class Label(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    text = database.Column(database.String(MAX_STRING_SIZE))

    def __init__(self, text):
        self.text = text
        database.session.add(self)
        database.session.flush()


class Association(database.Model):
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
        database.session.add(self)
        database.session.flush()

    def __str__(self):
        return "User: " + str(self.user_id) + \
               ", Sticker: " + str(self.sticker_id) + \
               ", Label: " + str(self.label_id)
