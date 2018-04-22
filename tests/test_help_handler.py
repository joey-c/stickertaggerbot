import pytest

from stickertaggerbot import message
from stickertaggerbot.handlers import start
from tests import telegram_factories
from tests.misc import outgoing_message_patches, assert_sent_message_once, \
    run_handler

base_patch_path = "stickertaggerbot.handlers.help"


class TestHelpHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        patches = outgoing_message_patches(base_patch_path)

        for patch in patches:
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    def test_help(self):
        update = telegram_factories.CommandUpdateFactory(
            message__command="help")

        run_handler(start.create_command_start_handler, update)
        assert_sent_message_once(message.Text.Instruction.HELP)
