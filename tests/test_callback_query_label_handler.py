import time
from unittest import mock

import pytest

import stickertaggerbot.callback_data
from stickertaggerbot import message
from stickertaggerbot.handlers import callbacks
from tests import telegram_factories
from tests.misc import clear_all_tables, get_or_create, conversation, \
    outgoing_message_patches, assert_sent_message_once, run_handler

base_patch_path = "stickertaggerbot.handlers.callbacks"
base_patch_path_labels = base_patch_path + ".labels_callback.models"
States = stickertaggerbot.conversations.Conversation.State


class TestCallbackQueryHandlerInLabelState(object):
    @pytest.fixture(autouse=True)
    def patch(self):
        patches = outgoing_message_patches(base_patch_path)
        # patches.extend(outgoing_message_patches(base_patch_path_labels))
        database_commit = base_patch_path_labels + ".database.session.commit"
        patches.append(mock.patch(database_commit))

        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    @pytest.fixture()
    def sticker(self):
        return telegram_factories.StickerFactory()

    @pytest.fixture()
    def callback_query_update(self):
        def update_maker(conversation, button_text):
            callback_data = stickertaggerbot.callback_data.CallbackData(
                States.LABEL, conversation.sticker.file_id)
            callback_data_text = callback_data.generator(button_text)

            update = telegram_factories.CallbackQueryUpdateFactory(
                callback_query__from_user=conversation.user,
                callback_query__data=callback_data_text,
                callback_query__chat_instance=str(conversation.chat.id))

            return update

        return update_maker

    def test_confirm(self, conversation, sticker, callback_query_update):
        conversation.sticker = sticker
        conversation.labels = ["label1", "label2", "label3"]
        conversation.change_state = mock.MagicMock(autospec=True,
                                                   return_value=True)
        update = callback_query_update(
            conversation,
            stickertaggerbot.callback_data.CallbackData.ButtonText.CONFIRM)

        with mock.patch(base_patch_path_labels + ".User.id_exists",
                        mock.MagicMock(return_value=False)):
            database_user = \
                callbacks.labels_callback.models.User.from_telegram_user(
                    conversation.user, conversation.chat.id)

        # TODO: Use a more elegant way to do this
        with mock.patch(base_patch_path_labels + ".User.get",
                        mock.MagicMock(autospec=True,
                                       return_value=database_user)), \
             mock.patch(*get_or_create(conversation)), \
             mock.patch(base_patch_path_labels + ".Association",
                        mock.MagicMock(autospec=True)), \
             mock.patch(base_patch_path_labels + ".database.session.commit",
                        mock.MagicMock(autospec=True)):
            run_handler(callbacks.create_callback_handler, update)

        time.sleep(2)
        clear_all_tables()

        assert_sent_message_once(message.Text.Other.SUCCESS)

    def test_cancel(self, conversation, sticker, callback_query_update):
        conversation.sticker = sticker

        update = callback_query_update(
            conversation,
            stickertaggerbot.callback_data.CallbackData.ButtonText.CANCEL)

        with mock.patch(*get_or_create(conversation)):
            run_handler(callbacks.create_callback_handler, update)

        assert_sent_message_once(message.Text.Instruction.RE_LABEL)
