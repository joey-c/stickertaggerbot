from unittest import mock

import flask
import pytest
import telegram

from stickertaggerbot import flask_app, models, config, message
from tests import telegram_factories

app_config = {"SQLALCHEMY_DATABASE_URI": config.DATABASE_URI,
              "SQLALCHEMY_TRACK_MODIFICATIONS": False}

app_for_testing = flask_app.Application(app_config, testing=True)
bot = app_for_testing.bot


@app_for_testing.route("/" + config.TELEGRAM_TOKEN, methods=['POST'])
def route_update():
    update_json = flask.request.get_json()
    update = telegram.Update.de_json(update_json, app_for_testing.bot)
    app_for_testing.update_queue.put(update)
    return ""


tables = [models.Association,
          models.User,
          models.Sticker,
          models.Label]


def clear_all_tables():
    for table in tables:
        models.database.session.query(table).delete()

    models.database.session.flush()


# Returns a new mock Conversation instance
@mock.patch("stickertaggerbot.conversations.Conversation")
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


def outgoing_message_patches(base_patch_path):
    return [mock.patch(base_patch_path + ".message.Message.set_content",
                       autospec=True,
                       side_effect=lambda self, content: self),
            mock.patch(base_patch_path + ".message.Message.send",
                       autospec=True)]


def assert_sent_message_once(message_content=None):
    message.Message.set_content.assert_called_once()

    # call_args: ((self, content), kwargs)
    if message_content:
        assert message.Message.set_content.call_args[0][1] == message_content

    message.Message.send.assert_called_once()


def run_handler(handler_creator, update):
    handler = handler_creator(app_for_testing)
    handler.__wrapped__(bot, update)  # run without async
