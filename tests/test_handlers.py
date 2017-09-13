import time
import pytest
from unittest import mock

from Text2StickerBot import handlers, conversations

from tests import telegram_factories
from tests.misc import app_for_testing, clear_all_tables

bot = app_for_testing.bot
States = conversations.Conversation.State


# Returns a new mock Conversation instance, and mocks the class
@pytest.fixture()
def conversation():
    handlers.conversations.Conversation = mock.MagicMock(
        spec=handlers.conversations.Conversation)

    user = telegram_factories.UserFactory()
    chat = telegram_factories.ChatFactory()
    mock_conversation = handlers.conversations.Conversation(user, chat)
    mock_conversation.user = user
    mock_conversation.chat = chat

    return mock_conversation


def run_handler(handler_creator, update):
    handler = handler_creator(app_for_testing)
    handler.__wrapped__(bot, update)  # run without async


class TestStartCommandHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        bot.send_message = mock.Mock()

    def patch_database(self):
        handlers.models.User.add_to_database = mock.Mock(autospec=True)
        handlers.models.database.session.commit = mock.Mock(autospec=True)

    def test_new_user(self):
        self.patch_database()

        handlers.models.User.get = mock.Mock(autospec=True,
                                             return_value=None)

        update = telegram_factories.CommandUpdateFactory(
            message__command="start")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        run_handler(handlers.create_command_start_handler, update)

        handlers.models.User.get.assert_called_once_with(user_id)
        handlers.models.User.add_to_database.assert_called_once_with()

        bot.send_message.assert_called_once_with(
            chat_id,
            handlers.Message.Instruction.START.value)


class TestStickerHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        bot.send_message = mock.Mock()

    @pytest.fixture
    def update(self):
        return telegram_factories.StickerUpdateFactory()

    def test_new_sticker(self, update, conversation):
        handlers.sticker_is_new = mock.Mock(autospec=True, return_value=True)

        run_handler(handlers.create_sticker_handler, update)

        assert conversation.sticker == update.effective_message.sticker
        conversation.change_state.assert_called_once()
        assert conversation.rollback_state.call_args is None

        bot.send_message.assert_called_once_with(
            update.effective_chat.id,
            handlers.Message.Instruction.LABEL.value)

    def test_interrupted_conversation(self, update, conversation):
        conversation.change_state = mock.Mock(
            autospec=True, side_effect=ValueError(States.IDLE))

        run_handler(handlers.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        assert conversation.rollback_state.call_args is None
        bot.send_message.assert_called_once_with(
            update.effective_chat.id,
            handlers.Message.Error.RESTART.value)

    def test_sticker_exists(self, update, conversation):
        conversation.get_future_result = mock.Mock(return_value=False)

        run_handler(handlers.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        conversation.rollback_state.assert_called_once()
        bot.send_message.assert_called_once_with(
            update.effective_chat.id,
            handlers.Message.Error.STICKER_EXISTS.value)

    def test_future_timed_out(self, update, conversation):
        conversation.get_future_result = mock.Mock(autospec=True,
                                                   return_value=None)

        run_handler(handlers.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        conversation.rollback_state.assert_called_once()
        bot.send_message.assert_called_once_with(
            update.effective_chat.id,
            handlers.Message.Error.UNKNOWN.value)


class TestLabelsHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        bot.send_message = mock.Mock()
        bot.send_sticker = mock.Mock()

    def test_no_conversation(self):
        handlers.conversations.get_or_create = mock.Mock(autospec=True,
                                                         return_value=None)

        update = telegram_factories.MessageUpdateFactory(
            message__text="message")
        chat_id = update.effective_chat.id

        run_handler(handlers.create_labels_handler, update)

        bot.send_message.assert_called_once_with(
            chat_id,
            handlers.Message.Error.NOT_STARTED.value)

    def test_interrupted_conversation(self, conversation):
        conversation.change_state = mock.Mock(
            autospec=True, side_effect=ValueError(States.IDLE))
        update = telegram_factories.MessageUpdateFactory(
            message__from_user=conversation.user)
        chat_id = update.effective_chat.id
        handlers.conversations.get_or_create = mock.Mock(
            autospec=True, return_value=conversation)

        run_handler(handlers.create_labels_handler, update)

        bot.send_message.assert_called_once_with(
            chat_id, handlers.Message.Error.RESTART.value)

    def test_empty_labels(self, conversation):
        conversation.labels = None
        handlers.conversations.get_or_create = mock.Mock(
            autospec=True, return_value=conversation)

        update = telegram_factories.MessageUpdateFactory(message__text="")
        chat_id = update.effective_chat.id

        run_handler(handlers.create_labels_handler, update)

        bot.send_message.assert_called_once_with(
            chat_id,
            handlers.Message.Error.LABEL_MISSING.value)

    def test_one_label(self, conversation):
        label = "label"

        sticker = telegram_factories.StickerFactory()
        conversation.sticker = sticker

        user = telegram_factories.UserFactory()
        conversation.user = user

        handlers.conversations.get_or_create = mock.Mock(
            autospec=True, return_value=conversation)
        handlers.conversations.Conversation.State.LABEL = States.LABEL
        update = telegram_factories.MessageUpdateFactory(
            message__text=label,
            message__from_user=user)
        chat_id = update.effective_chat.id

        run_handler(handlers.create_labels_handler, update)

        bot.send_sticker.assert_called_once_with(chat_id, sticker)
        bot.send_message.assert_called_once()

    # TODO Distinguish test from test_one_label
    def test_multiple_labels(self, conversation):
        sticker = telegram_factories.StickerFactory()
        conversation.sticker = sticker

        user = telegram_factories.UserFactory()
        conversation.user = user

        handlers.conversations.get_or_create = mock.Mock(
            autospec=True, return_value=conversation)
        handlers.conversations.Conversation.State.LABEL = States.LABEL

        update = telegram_factories.MessageUpdateFactory(
            message__text="label1 label2 label3")
        chat_id = update.effective_chat.id

        run_handler(handlers.create_labels_handler, update)

        bot.send_sticker.assert_called_once_with(chat_id, sticker)
        bot.send_message.assert_called_once()


class TestCallbackQueryHandlerInLabelState(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        bot.send_message = mock.Mock()

    @pytest.fixture(autouse=True)
    def patch_database(self):
        handlers.models.database.session.commit = mock.MagicMock()

    @pytest.fixture()
    def sticker(self):
        return telegram_factories.StickerFactory()

    @pytest.fixture()
    def callback_query_update(self):
        def update_maker(conversation, button_text):
            callback_data = handlers.CallbackData(
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
        handlers.conversations.get_or_create = mock.MagicMock(
            autospec=True,
            return_value=conversation)

        handlers.models.User.id_exists = mock.MagicMock(return_value=False)
        with app_for_testing.app_context():
            database_user = handlers.models.User.from_telegram_user(
                conversation.user, conversation.chat.id)
        handlers.models.User.get = mock.MagicMock(autospec=True,
                                                  return_value=database_user)

        handlers.models.Association.exists = mock.MagicMock(return_value=False)

        update = callback_query_update(
            conversation, handlers.CallbackData.ButtonText.CONFIRM)

        run_handler(handlers.create_callback_handler, update)

        time.sleep(2)

        with app_for_testing.app_context():
            clear_all_tables()

        bot.send_message.assert_called_once_with(
            conversation.chat.id, handlers.Message.Other.SUCCESS.value)

        assert handlers.models.Association.exists.call_count == len(
            conversation.labels)

    def test_cancel(self, conversation, sticker, callback_query_update):
        conversation.sticker = sticker
        handlers.conversations.get_or_create = mock.MagicMock(
            autospec=True,
            return_value=conversation)

        update = callback_query_update(
            conversation, handlers.CallbackData.ButtonText.CANCEL)

        run_handler(handlers.create_callback_handler, update)

        bot.send_message.assert_called_once_with(
            conversation.chat.id, handlers.Message.Instruction.RE_LABEL.value)


class TestInlineQueryHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        bot.answer_inline_query = mock.Mock()

    def patch_user_association(self, result):
        filter_return = mock.MagicMock()
        filter_return.count = mock.MagicMock(return_value=result)
        query = mock.MagicMock()
        query.filter_by = mock.MagicMock(autospec=True,
                                         return_value=filter_return)
        handlers.models.Association.query = query

    def test_new_user(self):
        self.patch_user_association(0)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        run_handler(handlers.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id,
            is_personal=True,
            switch_pm_text=handlers.Message.Error.NOT_STARTED.value)

    def test_no_stickers(self):
        self.patch_user_association(1)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        handlers.models.Association.get_sticker_ids = mock.MagicMock(
            autospec=True, return_value=[])

        run_handler(handlers.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id,
            is_personal=True,
            switch_pm_text=handlers.Message.Error.NO_MATCHES.value)

    def test_one_label(self):
        self.patch_user_association(1)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        sticker_id = telegram_factories.StickerFactory().file_id
        handlers.models.Association.get_sticker_ids = mock.MagicMock(
            autospec=True, return_value=[sticker_id])

        sticker_result = handlers.StickerResult(sticker_id)
        handlers.StickerResult = mock.MagicMock(return_value=sticker_result)

        run_handler(handlers.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id, [sticker_result], is_personal=True)

    # Sort stickers by number of matching labels
    def test_multiple_labels(self):
        pass

    # Sort stickers by number of matching labels, then by frequency of usage
    def test_multiple_labels_with_usage_frequency(self):
        pass

    def test_pagination(self):
        pass
