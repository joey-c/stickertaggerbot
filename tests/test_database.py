import pytest
from sqlite3 import IntegrityError

from stickertaggerbot import models
from tests import model_factories
from tests.misc import clear_all_tables

models.sqlalchemy_logging(True)


@pytest.fixture(scope="class", autouse=True)
def clear_tables_before_and_after_each_test_class():
    clear_all_tables()
    yield
    clear_all_tables()


class TestInsertion(object):
    @pytest.fixture(scope="function", autouse=True)
    def clear_tables_before_each_test_function(self):
        clear_all_tables()

    def test_insertion_basic(self):
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

    # Default setup_class runs before the clear_tables fixture.
    # This is a fixture so that it will run after the other fixture.
    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class_after_clearing_tables(cls):
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


@pytest.mark.incremental
class TestAssociationUsage(object):
    def test_get_usage_count(self):
        user = model_factories.UserFactory()
        sticker = model_factories.StickerFactory()
        label = model_factories.LabelFactory()
        association = model_factories.AssociationFactory(
            user=user, sticker=sticker, label=label)

        usage = models.Association.get_usage_count(
            sticker.id, label.text, user.id)
        assert usage == 0

        new_usage = 5
        association.uses = new_usage
        usage = models.Association.get_usage_count(
            sticker.id, label.text, user.id)
        assert usage == new_usage

    def test_get_usage_count_for_nonexistent_association(self):
        nonexistent_sticker_id = "0"
        nonexistent_label = "label"
        nonexistent_user_id = 0

        nonexistent_without_user_id = models.Association.get_usage_count(
            nonexistent_sticker_id, nonexistent_label)
        assert nonexistent_without_user_id == 0

        nonexistent_with_user_id = models.Association.get_usage_count(
            nonexistent_sticker_id, nonexistent_label, nonexistent_user_id)
        assert nonexistent_with_user_id == 0

        valid_label = model_factories.LabelFactory().text
        valid_sticker_id = model_factories.StickerFactory().id
        valid_user_id = model_factories.UserFactory().id

        nonexistent_sticker_count = models.Association.get_usage_count(
            nonexistent_sticker_id, valid_label, valid_user_id)
        assert nonexistent_sticker_count == 0

        nonexistent_label_count = models.Association.get_usage_count(
            valid_sticker_id, nonexistent_label, valid_user_id)
        assert nonexistent_label_count == 0

        nonexistent_user_count = models.Association.get_usage_count(
            valid_sticker_id, valid_label, nonexistent_user_id)
        assert nonexistent_user_count == 0

    def test_get_usage_count_across_users(self):
        sticker = model_factories.StickerFactory()
        label = model_factories.LabelFactory()
        associations = model_factories.AssociationFactory.build_batch(
            3, sticker=sticker, label=label)

        associations_unique = \
            model_factories.AssociationFactory.build_batch(5)

        for association in associations + associations_unique:
            association.uses = 1
        models.database.session.flush()

        count = models.Association.get_usage_count(sticker.id, label.text)
        assert count == len(associations)

    def test_increment_usage(self):
        label = model_factories.LabelFactory()
        association = model_factories.AssociationFactory(label=label)
        assert association.uses == 0

        models.Association.increment_usage(
            association.user_id, association.sticker_id, [label.text])
        assert association.uses == 1

    # Incrementing should fail silently
    def test_increment_usage_for_nonexistent_association(self):
        models.Association.increment_usage(0, "0", ["label"])

    def test_increment_same_users_same_stickers_different_labels(self):
        users = model_factories.UserFactory.build_batch(2)
        stickers = model_factories.StickerFactory.build_batch(2)
        labels = model_factories.LabelFactory.build_batch(2)

        # user, sticker, label
        association_groups = [(0, 0, 0),
                              (1, 0, 0),
                              (0, 1, 0),
                              (0, 0, 1)]

        associations = [model_factories.AssociationFactory(
            user=users[u], sticker=stickers[s], label=labels[l])
            for u, s, l in association_groups]

        relevant_indices = [0, 3]
        relevant_association_groups = [association_groups[i]
                                       for i in relevant_indices]

        current_uses = [models.Association.get_usage_count(
            stickers[s].id, labels[l].text, users[u].id)
            for u, s, l in relevant_association_groups]

        relevant_labels = [label.text for label in labels[:2]]
        models.Association.increment_usage(
            users[0].id, stickers[0].id, relevant_labels)

        new_uses = [models.Association.get_usage_count(
            stickers[s].id, labels[l].text, users[u].id)
            for u, s, l in relevant_association_groups]

        incremented_uses = [use + 1 for use in current_uses]

        assert new_uses == incremented_uses
