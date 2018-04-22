from unittest import mock

import pytest

import stickertaggerbot.handlers
from stickertaggerbot import message
from tests import telegram_factories
from tests.misc import conversation, get_or_create, outgoing_message_patches, \
    assert_sent_message_once, run_handler

base_patch_path = "stickertaggerbot.handlers.sticker"
States = stickertaggerbot.conversations.Conversation.State


class TestStickerHandler(object):
    @pytest.yield_fixture(autouse=True)
    def patches(self):
        patches = outgoing_message_patches(base_patch_path)

        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    @pytest.fixture
    def update_maker(self):
        def maker(conversation):
            update = telegram_factories.StickerUpdateFactory(
                message__from_user=conversation.user,
                message_chat=conversation.chat)
            return update

        return maker

    @mock.patch(base_patch_path + ".sticker_is_new",
                mock.MagicMock(autospec=True, return_value=True))
    def test_new_sticker(self, update_maker, conversation):
        update = update_maker(conversation)

        with mock.patch(*get_or_create(conversation)):
            run_handler(
                stickertaggerbot.handlers.sticker.create_sticker_handler, update)

        assert conversation.sticker == update.effective_message.sticker
        conversation.change_state.assert_called_once()
        assert conversation.rollback_state.call_args is None
        assert_sent_message_once(message.Text.Instruction.LABEL)

    def test_interrupted_conversation(self, update_maker, conversation):
        update = update_maker(conversation)

        conversation.change_state = mock.MagicMock(
            autospec=True, side_effect=ValueError(States.IDLE))

        with mock.patch(*get_or_create(conversation)):
            run_handler(
                stickertaggerbot.handlers.sticker.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        assert conversation.rollback_state.call_args is None
        assert_sent_message_once(message.Text.Error.RESTART)

    def test_sticker_exists(self, update_maker, conversation):
        update = update_maker(conversation)

        conversation.get_future_result = mock.MagicMock(return_value=False)

        with mock.patch(*get_or_create(conversation)):
            run_handler(
                stickertaggerbot.handlers.sticker.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        conversation.rollback_state.assert_called_once()
        assert_sent_message_once(message.Text.Error.STICKER_EXISTS)

    def test_future_timed_out(self, update_maker, conversation):
        update = update_maker(conversation)
        conversation.get_future_result = mock.MagicMock(autospec=True,
                                                        return_value=None)

        with mock.patch(*get_or_create(conversation)):
            run_handler(
                stickertaggerbot.handlers.sticker.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        conversation.rollback_state.assert_called_once()
        assert_sent_message_once(message.Text.Error.UNKNOWN)