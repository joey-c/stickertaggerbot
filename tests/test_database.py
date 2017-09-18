import pytest
from sqlite3 import IntegrityError

from Text2StickerBot import models
from tests import telegram_factories
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
            username = "username"
            name = "name"
            user = models.User(user_id, username, name)

            sticker_id = 456
            sticker = models.Sticker(sticker_id)

            label_text = "label"
            label = models.Label(label_text)

            association = models.Association(user, sticker, label)

            with pytest.raises(IntegrityError):
                user_duplicate = models.User(user_id, username, name)

            with pytest.raises(IntegrityError):
                sticker_duplicate = models.Sticker(sticker_id)

            with pytest.raises(IntegrityError):
                label_duplicate = models.Label("label")

            with pytest.raises(IntegrityError):
                association_duplicate = models.Association(user, sticker,
                                                           label)

            assert models.User.count() == 1
            assert models.Sticker.count() == 1
            assert models.Label.count() == 1
            assert models.Association.count() == 1

            clear_all_tables()


class TestRetrieval(object):
    def test_label_get(self):
        label_text = "label"

        with app_for_testing.app_context():
            label = models.Label(label_text)
            retrieved_label = models.Label.get_or_create(label_text)
            assert label == retrieved_label

            clear_all_tables()

    # TODO: Test more exhaustively
    def test_retrieve_sticker_by_label(self):
        telegram_users = [telegram_factories.UserFactory(id=n) for n in
                          range(1, 4)]
        raw_sticker_ids = [("sticker_" + str(n)) for n in range(1, 4)]
        label_texts = [("label_" + str(n)) for n in range(1, 4)]

        with app_for_testing.app_context():
            labels = [models.Label(text) for text in label_texts]

            stickers = [models.Sticker(sticker_id) for sticker_id in
                        raw_sticker_ids]

            users = [models.User.from_telegram_user(
                user, telegram_factories.ChatFactory().id)
                for user in telegram_users]

            models.Association(users[0], stickers[0], labels[0])
            models.Association(users[0], stickers[0], labels[1])
            models.Association(users[0], stickers[1], labels[1])

            models.Association(users[1], stickers[0], labels[0])
            models.Association(users[1], stickers[0], labels[1])
            models.Association(users[1], stickers[1], labels[0])

            models.Association(users[2], stickers[2], labels[0])
            models.Association(users[2], stickers[2], labels[1])
            models.Association(users[2], stickers[2], labels[2])

            label_ids = models.Label.get_ids(label_texts[1:])
            assert set(label_ids) == {2, 3}

            sticker_ids = models.Association.get_sticker_ids(
                users[1].id, label_texts[1:])
            assert sticker_ids == [raw_sticker_ids[0]]

            clear_all_tables()
