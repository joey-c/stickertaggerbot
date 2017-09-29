import time
import pytest
from unittest import mock

from Text2StickerBot import config, models, conversations, handlers

from tests import telegram_factories
from tests.misc import app_for_testing as app


route = "/" + config.TELEGRAM_TOKEN


def post(update):
    with app.test_client() as app_client:
        return app_client.post(route,
                           data=update.to_json(),
                           content_type="application/json")


@pytest.mark.incremental
class TestNormalUsage(object):
    user = telegram_factories.UserFactory()
    chat = telegram_factories.ChatFactory(username=user.username,
                                          first_name=user.first_name,
                                          last_name=user.last_name)
    sticker = telegram_factories.StickerFactory()
    labels = ["label1", "label2", "label3"]

    @pytest.yield_fixture(autouse=True)
    def patch_telegram(self):
        patches = []
        patches.append(mock.patch.object(app.bot, "send_message"))
        patches.append(mock.patch.object(app.bot, "answer_inline_query"))
        patches.append(mock.patch.object(app.bot, "send_sticker"))

        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    def test_start(self):
        with app.app_context():
            existing_users = models.User.query.all()
        assert len(existing_users) == 0

        update = telegram_factories.CommandUpdateFactory(
            command="/start",
            message__from_user=self.user,
            message__chat=self.chat)

        response = post(update)
        time.sleep(2)

        with app.app_context():
            database_user = models.User.get(update.effective_user.id)

        assert database_user is not None

        app.bot.send_message.assert_called_once_with(
            self.chat.id, handlers.Message.Instruction.START.value)

    def test_new_sticker(self):
        update = telegram_factories.StickerUpdateFactory(
            message__sticker=self.sticker,
            message__from_user=self.user,
            message__chat=self.chat)
        response = post(update)
        time.sleep(2)

        conversation = conversations.all[self.user.id]
        assert conversation.sticker == self.sticker

        app.bot.send_message.assert_called_once_with(
            self.chat.id, handlers.Message.Instruction.LABEL.value)

    def test_label(self):
        update = telegram_factories.MessageUpdateFactory(
            message__text=" ".join(self.labels),
            message__from_user=self.user,
            message__chat=self.chat)
        response = post(update)
        time.sleep(2)

        conversation = conversations.all[self.user.id]
        assert conversation.labels == self.labels

        app.bot.send_sticker.assert_called_once_with(
            self.chat.id, self.sticker)

    def test_confirm(self):
        callback_data = handlers.CallbackData(
            conversations.Conversation.State.LABEL, self.sticker.file_id)
        callback_data_text = callback_data.generator(
            handlers.CallbackData.ButtonText.CONFIRM)

        update = telegram_factories.CallbackQueryUpdateFactory(
            callback_query__from_user=self.user,
            callback_query__data=callback_data_text,
            callback_query__chat_instance=str(self.chat.id))
        response = post(update)
        time.sleep(2)

        with app.app_context():
            sticker_ids = models.Association.get_sticker_ids(
                self.user.id, self.labels)

        assert len(sticker_ids) == 3
        assert len(set(sticker_ids)) == 1
        assert sticker_ids[0] == self.sticker.file_id

        app.bot.send_message.assert_called_once_with(
            self.chat.id, handlers.Message.Other.SUCCESS.value)

    def test_retrieve(self):
        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query=self.labels[0],
            inline_query__bot=app.bot,
            inline_query__from_user=self.user)

        post(update)
        time.sleep(2)

        result = [handlers.StickerResult(self.sticker.file_id)]
        app.bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id, result, is_personal=True)
