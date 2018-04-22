from unittest import mock

import pytest

from stickertaggerbot import message
from stickertaggerbot.handlers import start
from tests import telegram_factories
from tests.misc import outgoing_message_patches, assert_sent_message_once, \
    run_handler

base_patch_path = "stickertaggerbot.handlers.start"


class TestStartCommandHandler(object):
    @pytest.fixture(autouse=True)
    def patches(self):
        patches = [
            mock.patch(base_patch_path + ".models.User.add_to_database",
                       mock.MagicMock(autospec=True)),
            mock.patch(base_patch_path + ".models.database.session.commit",
                       mock.MagicMock(autospec=True)),
            mock.patch(base_patch_path + ".models.User.get",
                       mock.MagicMock(autospec=True, return_value=None))]

        patches.extend(outgoing_message_patches(base_patch_path))

        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    def test_new_user(self):
        update = telegram_factories.CommandUpdateFactory(
            message__command="start")
        user_id = update.effective_user.id

        run_handler(start.create_command_start_handler, update)

        start.models.User.get.assert_called_once_with(user_id)
        start.models.User.add_to_database.assert_called_once_with()
        assert_sent_message_once(message.Text.Instruction.START)
