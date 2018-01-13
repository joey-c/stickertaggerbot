import time
from unittest import mock

import pytest

from stickertaggerbot import handlers, conversations, message
from tests import telegram_factories
from tests.misc import app_for_testing, clear_all_tables

bot = app_for_testing.bot
States = conversations.Conversation.State


# TODO test Message separately and patch Message instead of the bot here

# Returns a new mock Conversation instance
@mock.patch("stickertaggerbot.handlers.conversations.Conversation")
@pytest.fixture()
def conversation(Conversation):
    user = telegram_factories.UserFactory()
    chat = telegram_factories.ChatFactory()
    mock_conversation = Conversation(user, chat)
    mock_conversation.user = user
    mock_conversation.chat = chat

    return mock_conversation


# Use with mock.patch
def get_or_create(conversation):
    args = ("stickertaggerbot.conversations.get_or_create",
            mock.MagicMock(autospec=True, return_value=conversation))
    return args


def run_handler(handler_creator, update):
    handler = handler_creator(app_for_testing)
    handler.__wrapped__(bot, update)  # run without async


class TestSendMessage(object):
    pass


class TestStartCommandHandler(object):
    @mock.patch.object(bot, "send_message", mock.MagicMock(autospec=True))
    @mock.patch("stickertaggerbot.handlers.models.User.add_to_database",
                mock.MagicMock(autospec=True))
    @mock.patch("stickertaggerbot.handlers.models.database.session.commit",
                mock.MagicMock(autospec=True))
    @mock.patch("stickertaggerbot.handlers.models.User.get",
                mock.MagicMock(autospec=True, return_value=None))
    def test_new_user(self):
        update = telegram_factories.CommandUpdateFactory(
            message__command="start")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        run_handler(handlers.create_command_start_handler, update)

        handlers.models.User.get.assert_called_once_with(user_id)
        handlers.models.User.add_to_database.assert_called_once_with()

        bot.send_message.assert_called_once_with(
            chat_id, message.Text.Instruction.START.value)


class TestStickerHandler(object):
    @pytest.yield_fixture(autouse=True)
    def patch_telegram(self):
        patch = mock.patch.object(bot, "send_message")
        patch.start()
        yield
        patch.stop()

    @pytest.fixture
    def update_maker(self):
        def maker(conversation):
            update = telegram_factories.StickerUpdateFactory(
                message__from_user=conversation.user,
                message_chat=conversation.chat)
            return update

        return maker

    @mock.patch("stickertaggerbot.handlers.sticker_is_new",
                mock.MagicMock(autospec=True, return_value=True))
    def test_new_sticker(self, update_maker, conversation):
        update = update_maker(conversation)

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_sticker_handler, update)

        assert conversation.sticker == update.effective_message.sticker
        conversation.change_state.assert_called_once()
        assert conversation.rollback_state.call_args is None

        bot.send_message.assert_called_once_with(
            update.effective_chat.id, message.Text.Instruction.LABEL.value)

    def test_interrupted_conversation(self, update_maker, conversation):
        update = update_maker(conversation)

        conversation.change_state = mock.MagicMock(
            autospec=True, side_effect=ValueError(States.IDLE))

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        assert conversation.rollback_state.call_args is None
        bot.send_message.assert_called_once_with(
            update.effective_chat.id, message.Text.Error.RESTART.value)

    def test_sticker_exists(self, update_maker, conversation):
        update = update_maker(conversation)

        conversation.get_future_result = mock.MagicMock(return_value=False)

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        conversation.rollback_state.assert_called_once()
        bot.send_message.assert_called_once_with(
            update.effective_chat.id, message.Text.Error.STICKER_EXISTS.value)

    def test_future_timed_out(self, update_maker, conversation):
        update = update_maker(conversation)
        conversation.get_future_result = mock.MagicMock(autospec=True,
                                                        return_value=None)

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_sticker_handler, update)

        conversation.change_state.assert_called_once()
        conversation.rollback_state.assert_called_once()
        bot.send_message.assert_called_once_with(
            update.effective_chat.id, message.Text.Error.UNKNOWN.value)


class TestLabelsHandler(object):
    @pytest.yield_fixture(autouse=True)
    def patch_telegram(self):
        patches = []
        patches.append(mock.patch.object(bot, "send_message"))
        patches.append(mock.patch.object(bot, "send_sticker"))
        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    def test_no_conversation(self):
        update = telegram_factories.MessageUpdateFactory(
            message__text="message")
        chat_id = update.effective_chat.id

        with mock.patch(*get_or_create(None)):
            run_handler(handlers.create_labels_handler, update)

        bot.send_message.assert_called_once_with(
            chat_id, message.Text.Error.NOT_STARTED.value)

    def test_interrupted_conversation(self, conversation):
        conversation.change_state = mock.Mock(
            autospec=True, side_effect=ValueError(States.IDLE))
        update = telegram_factories.MessageUpdateFactory(
            message__from_user=conversation.user)

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_labels_handler, update)

        chat_id = update.effective_chat.id
        bot.send_message.assert_called_once_with(
            chat_id, message.Text.Error.RESTART.value)

    def test_empty_labels(self, conversation):
        conversation.labels = None
        update = telegram_factories.MessageUpdateFactory(message__text="")

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_labels_handler, update)

        chat_id = update.effective_chat.id
        bot.send_message.assert_called_once_with(
            chat_id, message.Text.Error.LABEL_MISSING.value)

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
            run_handler(handlers.create_labels_handler, update)

        chat_id = update.effective_chat.id
        bot.send_sticker.assert_called_once_with(chat_id, sticker)
        bot.send_message.assert_called_once()

    # TODO Distinguish test from test_one_label
    def test_multiple_labels(self, conversation):
        sticker = telegram_factories.StickerFactory()
        conversation.sticker = sticker

        user = telegram_factories.UserFactory()
        conversation.user = user

        update = telegram_factories.MessageUpdateFactory(
            message__text="label1 label2 label3")
        chat_id = update.effective_chat.id

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_labels_handler, update)

        bot.send_sticker.assert_called_once_with(chat_id, sticker)
        bot.send_message.assert_called_once()


class TestCallbackQueryHandlerInLabelState(object):
    @pytest.fixture(autouse=True)
    def patch(self):
        patches = []
        patches.append(mock.patch.object(bot, "send_message"))
        patches.append(mock.patch(
            "stickertaggerbot.handlers.models.database.session.commit"))
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
        update = callback_query_update(
            conversation, handlers.CallbackData.ButtonText.CONFIRM)

        with mock.patch("stickertaggerbot.handlers.models.User.id_exists",
                        mock.MagicMock(return_value=False)):
            database_user = handlers.models.User.from_telegram_user(
                conversation.user, conversation.chat.id)

        # TODO: Use a more elegant way to do this
        with mock.patch("stickertaggerbot.handlers.models.User.get",
                        mock.MagicMock(autospec=True,
                                       return_value=database_user)), \
             mock.patch(*get_or_create(conversation)), \
             mock.patch("stickertaggerbot.handlers.models.Association",
                        mock.MagicMock(autospec=True)), \
             mock.patch(
                 "stickertaggerbot.handlers.models.database.session.commit",
                 mock.MagicMock(autospec=True)):
            run_handler(handlers.create_callback_handler, update)

        time.sleep(2)
        clear_all_tables()

        bot.send_message.assert_called_once_with(
            conversation.chat.id, message.Text.Other.SUCCESS.value)

    def test_cancel(self, conversation, sticker, callback_query_update):
        conversation.sticker = sticker

        update = callback_query_update(
            conversation, handlers.CallbackData.ButtonText.CANCEL)

        with mock.patch(*get_or_create(conversation)):
            run_handler(handlers.create_callback_handler, update)

        bot.send_message.assert_called_once_with(
            conversation.chat.id, message.Text.Instruction.RE_LABEL.value)


class TestInlineQueryHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        patch = mock.patch.object(bot, "answer_inline_query")
        patch.start()
        yield
        patch.stop()

    @pytest.yield_fixture(autouse=True)
    def patch_user_association(self):
        filter_return = mock.MagicMock()
        filter_return.count = mock.MagicMock()
        query = mock.MagicMock()
        query.filter_by = mock.MagicMock(autospec=True,
                                         return_value=filter_return)

        patch = mock.patch(
            "stickertaggerbot.handlers.models.Association.query", query)
        patch.start()

        yield
        patch.stop()

    def set_user_association(self, result):
        handlers.models.Association.query.filter_by.return_value.count.return_value = result

    def test_new_user(self):
        self.set_user_association(0)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        run_handler(handlers.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id,
            is_personal=True,
            switch_pm_text=message.Text.Error.NOT_STARTED.value)

    @mock.patch("stickertaggerbot.handlers.models.Association.get_sticker_ids",
                mock.MagicMock(autospec=True, return_value=[]))
    def test_no_stickers(self):
        self.set_user_association(1)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        run_handler(handlers.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id,
            is_personal=True,
            switch_pm_text=message.Text.Error.NO_MATCHES.value)

    def test_one_label(self):
        self.set_user_association(1)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        sticker_id = telegram_factories.StickerFactory().file_id
        sticker_result = handlers.StickerResult(sticker_id)

        with mock.patch(
                "stickertaggerbot.handlers.models.Association.get_sticker_ids",
                mock.MagicMock(autospec=True, return_value=[sticker_id])), \
             mock.patch("stickertaggerbot.handlers.StickerResult",
                        mock.MagicMock(return_value=sticker_result)):
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


class TestChosenInlineResultHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        patch = mock.patch(
            "stickertaggerbot.handlers.models.Association.increment_usage",
            new_callable=mock.MagicMock(autospec=True))
        patch.start()
        yield
        patch.stop()

    def test_single_label(self):
        query_string = "label_0"
        sticker_id = "sticker_0"

        result_id = handlers.StickerResult.generate_result_id(sticker_id)
        update = telegram_factories.ChosenInlineResultUpdateFactory(
            chosen_inline_result__query=query_string,
            chosen_inline_result__result_id=result_id)

        run_handler(handlers.create_chosen_inline_result_handler, update)

        user_id = update.effective_user.id
        handlers.models.Association.increment_usage.assert_called_once_with(
            user_id, sticker_id, [query_string])

    def test_multiple_labels(self):
        labels = ["label_0", "label_1", "label_2"]
        sticker_id = "sticker_0"

        query_string = " ".join(labels)
        result_id = handlers.StickerResult.generate_result_id(sticker_id)
        update = telegram_factories.ChosenInlineResultUpdateFactory(
            chosen_inline_result__query=query_string,
            chosen_inline_result__result_id=result_id)

        run_handler(handlers.create_chosen_inline_result_handler, update)

        user_id = update.effective_user.id
        handlers.models.Association.increment_usage.assert_called_once_with(
            user_id, sticker_id, labels)

    # TODO: Flesh out when soft labels are implemented.
    # Nonexistent labels are currently ignored at increment_usage
    def test_nonexistent_labels(self):
        pass
