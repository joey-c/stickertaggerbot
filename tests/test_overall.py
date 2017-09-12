import time
import pytest
from unittest import mock

from Text2StickerBot import tokens, models, conversations
from Text2StickerBot.application import application as app

from tests import telegram_factories

app_client = app.test_client()
route = "/" + tokens.TELEGRAM


def post(update):
    return app_client.post(route,
                           data=update.to_json(),
                           content_type="application/json")


@pytest.mark.incremental
class TestNormalUsage(object):
    user = telegram_factories.UserFactory()
    sticker = telegram_factories.StickerFactory()

    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        app.bot.send_message = mock.MagicMock()

    def test_start(self):
        update = telegram_factories.CommandUpdateFactory(
            command="/start",
            message__from_user=self.user)
        response = post(update)
        time.sleep(2)

        with app.app_context():
            database_user = models.User.get(
                update.effective_user.id)

        assert database_user is not None

    def test_new_sticker(self):
        update = telegram_factories.StickerUpdateFactory(
            message__from_user=self.user,
            message__sticker=self.sticker)
        response = post(update)

        time.sleep(2)
        conversation = conversations.all[self.user.id]
        assert conversation.sticker == self.sticker
