import time
import concurrent.futures
import pytest
from unittest import mock

from Text2StickerBot import conversations
from tests import telegram_factories

States = conversations.Conversation.State


@pytest.fixture()
def incomplete_future():
    future = concurrent.futures.Future()

    # set running, since it cannot have been cancelled already
    future.set_running_or_notify_cancel()

    return future


@pytest.fixture()
def completed_future():
    future = concurrent.futures.Future()
    future.set_result(True)
    return future


pool = concurrent.futures.ThreadPoolExecutor()


@pytest.fixture()
def blocking_future():
    def block():
        time.sleep(3)

    return pool.submit(block)


@pytest.fixture()
def conversation():
    return conversations.Conversation(telegram_factories.UserFactory(),
                                      telegram_factories.ChatFactory())


class TestStateComplete(object):
    def test_init(self, conversation):
        assert conversation.state_complete()
        assert conversation.state_complete(States.IDLE)

    def test_changed_state(self, conversation):
        conversation.state = States.STICKER
        assert conversation.state_complete()
        assert conversation.state_complete(States.STICKER)
        assert not conversation.state_complete(States.LABEL)

    def test_changed_state_with_completed_future(self, conversation,
                                                 completed_future):
        conversation.state = States.STICKER
        conversation._future = completed_future
        assert conversation.state_complete()
        assert conversation.state_complete(States.STICKER)
        assert not conversation.state_complete(States.LABEL)

    def test_changed_state_with_incomplete_future(self, conversation,
                                                  incomplete_future):
        conversation.state = States.STICKER
        conversation._future = incomplete_future
        assert not conversation.state_complete()
        assert not conversation.state_complete(States.STICKER)
        assert not conversation.state_complete(States.LABEL)


class TestIsIdle(object):
    def test_init(self, conversation):
        assert conversation.is_idle()

    def test_other_states(self, conversation):
        conversation.state = States.LABEL
        assert not conversation.is_idle()

        conversation.state = States.STICKER
        assert not conversation.is_idle()

        conversation.state = States.CONFIRMED
        assert not conversation.is_idle()


class TestResetState(object):
    def test_other_state(self, conversation):
        conversation.state = States.STICKER

        conversation.reset_state()
        assert conversation.state == States.IDLE

    def test_other_state_with_completed_future(self, conversation,
                                               completed_future):
        conversation.state = States.STICKER
        conversation._future = completed_future

        conversation.reset_state()
        assert conversation.state == States.IDLE
        assert conversation._future is None

    def test_other_state_with_incomplete_future(self, conversation,
                                                incomplete_future):
        conversation.state = States.STICKER
        conversation._future = incomplete_future

        conversation.reset_state()
        assert conversation.state == States.IDLE
        assert conversation._future is None


class TestRollback(object):
    def test_init(self, conversation):
        conversation.rollback_state()
        assert conversation.state == States.IDLE

    def test_other_state(self, conversation):
        conversation.state = States.STICKER
        conversation.rollback_state()
        assert conversation.state == States.IDLE

    def test_error(self, conversation, completed_future):
        with pytest.raises(ValueError) as error:
            conversation.rollback_state(future=completed_future)


class TestChangeState(object):
    def test_force(self, conversation):
        conversation.change_state(States.STICKER, force=True)

        assert conversation.state == States.STICKER

    def test_force_with_blocking_future(self, conversation, blocking_future):
        blocking_future.cancel = mock.Mock()
        conversation.state = States.STICKER
        conversation._future = blocking_future

        conversation.change_state(States.LABEL, force=True)

        blocking_future.cancel.assert_called_once()
        assert conversation.state == States.LABEL
        assert conversation._future is None

    def test_blocked(self, conversation, blocking_future):
        blocking_future.cancel = mock.Mock()
        conversation._future = blocking_future
        conversation.change_state(States.STICKER)

        blocking_future.cancel.assert_called_once()
        assert conversation.state == States.STICKER
        assert conversation._future is None

    def test_wrong_transition_order(self, conversation):
        with pytest.raises(ValueError):
            conversation.change_state(States.LABEL)

    def test_normal(self, conversation, incomplete_future):
        conversation.change_state(States.STICKER, future=incomplete_future)

        assert conversation.state == States.STICKER
        assert conversation._future == incomplete_future


class TestUpdateFuture(object):
    def test_force(self, conversation, incomplete_future, completed_future):
        conversation._future = incomplete_future
        conversation.update_future(completed_future, force=True)
        assert conversation._future == completed_future

    def test_normal(self, conversation, completed_future, incomplete_future):
        conversation._future = completed_future
        conversation.update_future(incomplete_future)
        assert conversation._future == incomplete_future


class TestGetFutureResult(object):
    def test_incomplete_future(self, conversation, incomplete_future):
        conversation._future = incomplete_future

        assert conversation.get_future_result() is None

    def test_no_future(self, conversation):
        with pytest.raises(ValueError):
            conversation.get_future_result()

    def test_completed_future(self, conversation, completed_future):
        conversation._future = completed_future

        assert conversation.get_future_result()


class TestGetOrCreate(object):
    def test_get(self, conversation):
        conversations.all[conversation.user.id] = conversation

        retrieved_conversation = conversations.get_or_create(
            conversation.user, get_only=True)
        assert retrieved_conversation == conversation

    def test_create(self):
        original_size = len(conversations.all)
        conversation = conversations.get_or_create(
            telegram_factories.UserFactory(),
            chat=telegram_factories.ChatFactory())
        current_size = len(conversations.all)

        assert current_size == original_size + 1
