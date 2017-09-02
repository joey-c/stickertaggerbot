import concurrent.futures
import pytest

import conversations
from tests import telegram_factories

States = conversations.Conversation.State


@pytest.fixture()
def user():
    return telegram_factories.UserFactory()


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


@pytest.fixture()
def conversation(user):
    return conversations.Conversation(user)


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


class TestChangeState(object):
    def test_force(self, conversation):
        pass

    def test_blocked(self, conversation):
        pass

    def test_wrong_transition_order(self, conversation):
        pass

    def test_normal(self, conversation):
        pass

    def test_idle(self, conversation):
        pass


class TestGetFutureResult(object):
    def test_incomplete_future(self, conversation, incomplete_future):
        pass

    def test_no_future(self, conversation):
        pass

    def test_completed_future(self, conversation, completed_future):
        pass


class TestGetOrCreate(object):
    def test_get(self, conversation):
        pass

    def test_create(self):
        pass
