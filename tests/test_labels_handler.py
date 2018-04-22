from unittest import mock

import pytest

import stickertaggerbot.handlers
from stickertaggerbot import message
from tests import telegram_factories
from tests.misc import conversation, get_or_create, outgoing_message_patches, \
    assert_sent_message_once, run_handler

base_patch_path = "stickertaggerbot.handlers.labels"
States = stickertaggerbot.conversations.Conversation.State


class TestLabelsHandler(object):
    @pytest.yield_fixture(autouse=True)
    def patches(self):
        patches = outgoing_message_patches(base_patch_path)

        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    def test_no_conversation(self):
        update = telegram_factories.MessageUpdateFactory(
            message__text="message")

        with mock.patch(*get_or_create(None)):
            run_handler(stickertaggerbot.handlers.labels.create_labels_handler,
                        update)

        assert_sent_message_once(message.Text.Error.NOT_STARTED)

    def test_interrupted_conversation(self, conversation):
        conversation.change_state = mock.Mock(
            autospec=True, side_effect=ValueError(States.IDLE))
        update = telegram_factories.MessageUpdateFactory(
            message__from_user=conversation.user)

        with mock.patch(*get_or_create(conversation)):
            run_handler(stickertaggerbot.handlers.labels.create_labels_handler,
                        update)

        assert_sent_message_once(message.Text.Error.RESTART)

    def test_empty_labels(self, conversation):
        conversation.labels = None
        update = telegram_factories.MessageUpdateFactory(message__text="")

        with mock.patch(*get_or_create(conversation)):
            run_handler(stickertaggerbot.handlers.labels.create_labels_handler,
                        update)

        assert_sent_message_once(message.Text.Error.LABEL_MISSING)

    def test_one_label(self, conversation):
        label = "label"

        sticker = telegram_factories.StickerFactory()
        conversation.sticker = sticker

        user = telegram_factories.UserFactory()
        conversation.user = user

        update = telegram_factories.MessageUpdateFactory(
            message__text=label,
            message__from_user=user)

        with mock.patch(*get_or_create(conversation)):
            run_handler(stickertaggerbot.handlers.labels.create_labels_handler,
                        update)

        assert message.Message.set_content.call_count == 2
        assert message.Message.send.call_count == 2

        first_call_contents, second_call_contents = \
            message.Message.set_content.call_args_list
        assert first_call_contents[0][1] == sticker
        assert second_call_contents[0][1] == \
               message.Text.Instruction.CONFIRM.value + label

    # TODO Distinguish test from test_one_label
    def test_multiple_labels(self, conversation):
        labels = ["label1", "label2", "label3"]

        sticker = telegram_factories.StickerFactory()
        conversation.sticker = sticker

        user = telegram_factories.UserFactory()
        conversation.user = user

        update = telegram_factories.MessageUpdateFactory(
            message__text=" ".join(labels))

        with mock.patch(*get_or_create(conversation)):
            run_handler(stickertaggerbot.handlers.labels.create_labels_handler,
                        update)

        assert message.Message.set_content.call_count == 2
        assert message.Message.send.call_count == 2

        first_call_contents, second_call_contents = \
            message.Message.set_content.call_args_list
        assert first_call_contents[0][1] == sticker
        assert second_call_contents[0][1] == \
               message.Text.Instruction.CONFIRM.value + "\n".join(labels)
