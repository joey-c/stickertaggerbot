import factory

from stickertaggerbot import models
from tests.misc import app_for_testing


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.User
        sqlalchemy_session = app_for_testing.database.session

    # Required arguments
    user_id = factory.Sequence(lambda n: n)
    chat_id = factory.Sequence(lambda n: n)
    first_name = factory.Sequence(lambda n: "firstname_" + str(n))

    # Optional arguments
    last_name = factory.Sequence(lambda n: "lastname_" + str(n))
    username = factory.Sequence(lambda n: "username_" + str(n))
    language = None


class StickerFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Sticker
        sqlalchemy_session = app_for_testing.database.session

    # Required arguments
    sticker_id = factory.Sequence(lambda n: "id_" + str(n))

    # Optional arguments
    set_name = None


class LabelFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Label
        sqlalchemy_session = app_for_testing.database.session

    # Required arguments
    text = factory.Sequence(lambda n: "label_" + str(n))


class AssociationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Association
        sqlalchemy_session = app_for_testing.database.session

    # Required arguments
    user = factory.SubFactory(UserFactory)
    sticker = factory.SubFactory(StickerFactory)
    label = factory.SubFactory(LabelFactory)
