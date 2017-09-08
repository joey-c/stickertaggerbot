from Text2StickerBot import models
from tests.misc import clear_all_tables, app_for_testing

models.sqlalchemy_logging(True)


class TestInsertion(object):
    def test_insertion_basic(self):
        with app_for_testing.app_context():
            user_id = 123
            sticker_id = 456
            user = models.User(user_id, "username", "name")
            sticker = models.Sticker(sticker_id)
            label = models.Label("label")
            association = models.Association(user, sticker, label)

            assert models.User.id_exists(user_id)
            assert models.User.count() == 1

            assert models.Sticker.id_exists(sticker_id)
            assert models.Sticker.count() == 1

            assert models.Label.id_exists(1)
            assert models.Label.count() == 1

            assert models.Association.id_exists(1)
            assert models.Association.count() == 1

            clear_all_tables()

    def test_insertion_overlapping(self):
        with app_for_testing.app_context():
            user_id = 123
            sticker_id = 456
            user = models.User(user_id, "username", "name")
            sticker = models.Sticker(sticker_id)
            label_a = models.Label("label a")
            association_a = models.Association(user, sticker, label_a)

            label_b = models.Label("label b")
            association_b = models.Association(user, sticker, label_b)

            assert models.User.id_exists(user_id)
            assert models.User.count() == 1

            assert models.Sticker.id_exists(sticker_id)
            assert models.Sticker.count() == 1

            assert models.Label.id_exists(1)
            assert models.Label.id_exists(2)
            assert models.Label.count() == 2

            assert models.Association.id_exists(1)
            assert models.Association.id_exists(2)
            assert models.Association.count() == 2

            assert models.Association.count("user_id", user_id) == 2
            assert models.Association.count("sticker_id", sticker_id) == 2
            assert models.Association.count("label_id") == 2

            clear_all_tables()

    def test_duplicates(self):
        with app_for_testing.app_context():
            user_id = 123
            sticker_id = 456
            user = models.User(user_id, "username", "name")
            sticker = models.Sticker(sticker_id)
            label = models.Label("label")
            association_a = models.Association(user, sticker, label)

            models.database.session.add(user)
            models.database.session.add(sticker)
            models.database.session.add(label)
            models.database.session.add(association_a)

            assert models.User.count() == 1
            assert models.Sticker.count() == 1
            assert models.Label.count() == 1
            assert models.Association.count() == 1

            clear_all_tables()
