from unittest import mock

import handlers

from tests import telegram_factories
from tests.misc import app_for_testing

bot = app_for_testing.bot


def patch_telegram():
    def return_update(chat_id, text):
        return telegram_factories.MessageFactory(text=text,
                                                 chat__id=chat_id)

    bot.send_message = mock.Mock(side_effect=return_update)


def patch_database():
    handlers.models.User.add_to_database = mock.Mock(autospec=True,
                                                     return_value=None)
    handlers.models.database.session.commit = mock.Mock(autospec=True,
                                                        return_value=None)


class TestStartCommand(object):
    def test_new_user(self):
        patch_telegram()
        patch_database()

        handlers.models.User.get = mock.Mock(autospec=True, return_value=None)

        update = telegram_factories.CommandUpdateFactory(
            message__command="start")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        with app_for_testing.app_context():
            handlers.command_start_handler(bot, update)

        handlers.models.User.get.assert_called_once_with(user_id)
        handlers.models.User.add_to_database.assert_called_once_with()

        bot.send_message.assert_called_once_with(
            chat_id,
            handlers.Message.Instruction.START.value)
