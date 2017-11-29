import pytest
from sqlite3 import IntegrityError

from stickertaggerbot import models
from tests import telegram_factories, model_factories
from tests.misc import clear_all_tables, app_for_testing

models.sqlalchemy_logging(True)


class TestInsertion(object):
    def test_insertion_basic(self):
        with app_for_testing.app_context():
            clear_all_tables()

            user = model_factories.UserFactory()
            sticker = model_factories.StickerFactory()
            label = model_factories.LabelFactory()
            association = model_factories.AssociationFactory(
                user=user, sticker=sticker, label=label)

            assert models.User.id_exists(user.id)
            assert models.User.count() == 1

            assert models.Sticker.id_exists(sticker.id)
            assert models.Sticker.count() == 1

            assert models.Label.id_exists(label.id)
            assert models.Label.count() == 1

            assert models.Association.id_exists(association.id)
            assert models.Association.count() == 1

    def test_insertion_overlapping(self):
        with app_for_testing.app_context():
            clear_all_tables()

            user = model_factories.UserFactory()
            sticker = model_factories.StickerFactory()
            label_a = model_factories.LabelFactory()
            association_a = models.Association(
                user=user, sticker=sticker, label=label_a)

            label_b = model_factories.LabelFactory()
            association_b = models.Association(
                user=user, sticker=sticker, label=label_b)

            assert models.User.id_exists(user.id)
            assert models.User.count() == 1

            assert models.Sticker.id_exists(sticker.id)
            assert models.Sticker.count() == 1

            assert models.Label.id_exists(label_a.id)
            assert models.Label.id_exists(label_b.id)
            assert models.Label.count() == 2

            assert models.Association.id_exists(association_a.id)
            assert models.Association.id_exists(association_b.id)
            assert models.Association.count() == 2

            assert models.Association.count("user_id", user.id) == 2
            assert models.Association.count("sticker_id", sticker.id) == 2
            assert models.Association.count("label_id") == 2

    def test_duplicates(self):
        with app_for_testing.app_context():
            clear_all_tables()

            user = model_factories.UserFactory()
            sticker = model_factories.StickerFactory()
            label = model_factories.LabelFactory()
            association = model_factories.AssociationFactory(
                user=user, sticker=sticker, label=label)

            with pytest.raises(IntegrityError):
                user_duplicate = model_factories.UserFactory(user_id=user.id)

            with pytest.raises(IntegrityError):
                sticker_duplicate = model_factories.StickerFactory(
                    sticker_id=sticker.id)

            with pytest.raises(IntegrityError):
                label_duplicate = model_factories.LabelFactory(
                    text=label.text)

            with pytest.raises(IntegrityError):
                association_duplicate = model_factories.AssociationFactory(
                    user=user, sticker=sticker, label=label)

            assert models.User.count() == 1
            assert models.Sticker.count() == 1
            assert models.Label.count() == 1
            assert models.Association.count() == 1


class TestRetrieval(object):
    def test_label_get(self):
        with app_for_testing.app_context():
            clear_all_tables()

            label = model_factories.LabelFactory()
            retrieved_label = models.Label.get_or_create(label.text)
            assert label == retrieved_label

            # TODO
            # label_ids = models.Label.get_ids(label_texts[1:])
            # assert set(label_ids) == {2, 3}


# 3 variables: user, sticker, and label.
# Test cases are designed by considering combinations of the variations.
# 3/3 different: implicitly tested with other_irrelevant_associations
# 2/3 different: implicitly tested with irrelevant_associations_with_*
# 1/3 different: explicitly tested with methods
# 0/3 different: not tested as duplicate rows are not allowed.
class TestRetrieveStickerByLabel(object):
    # raw_associations: [(user, sticker, label)]
    def populate_associations(self, raw_associations):
        associations = [model_factories.AssociationFactory(
            user=models.database.session.merge(self.users[u], load=False),
            sticker=models.database.session.merge(self.stickers[s],
                                                  load=False),
            label=models.database.session.merge(self.labels[l],
                                                load=False))
            for u, s, l in raw_associations]

        return associations

    @classmethod
    def setup_class(cls):
        cls.context = app_for_testing.app_context()
        cls.context.push()

        clear_all_tables()

        cls.users = model_factories.UserFactory.build_batch(3)
        cls.labels = model_factories.LabelFactory.build_batch(3)
        cls.stickers = model_factories.StickerFactory.build_batch(3)

        # Populate database with extra rows
        irrelevant_associations_with_users = [
            association for user in cls.users
            for association in
            model_factories.AssociationFactory.build_batch(3, user=user)]
        irrelevant_associations_with_labels = [
            association for label in cls.labels
            for association in
            model_factories.AssociationFactory.build_batch(3, label=label)]
        irrelevant_associations_with_stickers = [
            association for sticker in cls.stickers
            for association in
            model_factories.AssociationFactory.build_batch(3,
                                                           sticker=sticker)]
        other_irrelevant_associations = \
            model_factories.AssociationFactory.build_batch(5)

        cls.irrelevant_associations = sum(
            [irrelevant_associations_with_users,
             irrelevant_associations_with_labels,
             irrelevant_associations_with_stickers,
             other_irrelevant_associations], [])

    @classmethod
    def teardown_class(cls):
        clear_all_tables()
        cls.context.pop()

    def test_different_users_same_stickers_same_labels(self):
        # [(user, sticker, label)]
        raw_associations = [(0, 2, 0),
                            (1, 2, 0)]
        associations = self.populate_associations(raw_associations)

        sticker_ids = models.Association.get_sticker_ids(
            self.users[0].id, [self.labels[0].text])
        assert len(sticker_ids) == 1
        assert sticker_ids[0] == self.stickers[2].id

    def test_same_users_different_stickers_same_labels(self):
        # [(user, sticker, label)]
        raw_associations = [(0, 0, 1),
                            (0, 1, 1)]
        associations = self.populate_associations(raw_associations)

        sticker_ids = models.Association.get_sticker_ids(
            self.users[0].id, [self.labels[1].text])
        assert len(sticker_ids) == 2
        assert set(sticker_ids) == {self.stickers[0].id,
                                    self.stickers[1].id}

    def test_same_users_same_stickers_different_labels(self):
        raw_associations = [(2, 2, 1),
                            (2, 2, 2)]
        associations = self.populate_associations(raw_associations)

        sticker_id = self.stickers[2].id
        sticker_ids = models.Association.get_sticker_ids(
            self.users[2].id, [self.labels[1].text, self.labels[2].text])
        assert len(sticker_ids) == 2
        assert sticker_ids == [sticker_id, sticker_id]

        sticker_ids_unique = models.Association.get_sticker_ids(
            self.users[2].id, [self.labels[1].text, self.labels[2].text],
            unique=True)
        assert len(sticker_ids_unique) == 1
        assert sticker_ids_unique[0] == sticker_id
