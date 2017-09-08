import pytest
from unittest import mock

from Text2StickerBot import handlers, conversations

from tests import telegram_factories
from tests.misc import app_for_testing

bot = app_for_testing.bot
States = conversations.Conversation.State




# Returns a new mock Conversation instance, and mocks the class
@pytest.fixture()
def conversation():
    handlers.conversations.Conversation = mock.MagicMock(
        spec=handlers.conversations.Conversation)
    mock_conversation = handlers.conversations.Conversation(
        telegram_factories.UserFactory(),
        telegram_factories.ChatFactory())

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
        conversation.is_idle = mock.Mock(autospec=True, return_value=False)

        run_handler(handlers.create_sticker_handler, update)

        assert conversation.change_state.call_args is None
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
            autospec=True, return_value=False)
        update = telegram_factories.MessageUpdateFactory(
            message__from_user=conversation.user)
        chat_id = update.effective_chat.id
        handlers.conversations.get_or_create = mock.Mock(
            autospec=True, return_value=conversation)

        run_handler(handlers.create_labels_handler, update)

        bot.send_message.assert_called_once_with(
            chat_id, handlers.Message.Error.RESTART.value)

    def test_empty_labels(self):
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
