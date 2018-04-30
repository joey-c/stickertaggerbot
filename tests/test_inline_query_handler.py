from unittest import mock

import pytest

from stickertaggerbot import message
from stickertaggerbot.handlers import inline_query
import stickertaggerbot.inline_query_result as inline_query_result
from tests import telegram_factories
from tests.misc import run_handler, bot

base_patch_path = "stickertaggerbot.handlers.inline_query"



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

        patch = mock.patch(base_patch_path + ".models.Association.query",
                           query)
        patch.start()

        yield
        patch.stop()

    def set_user_association(self, result):
        inline_query.models.Association.query.filter_by.return_value.count.return_value = result

    def test_new_user(self):
        self.set_user_association(0)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        result = inline_query_result.Text(
            update.update_id,
            message.Text.Inline.NOT_STARTED.value,
            message.Text.Inline.CHAT_TO_START.value)

        with mock.patch(base_patch_path + ".inline_query_result.Text",
                        mock.MagicMock(autospec=True, return_value=result)):
            run_handler(inline_query.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id,
            results=[result],
            cache_time=2,
            is_personal=True,
            switch_pm_text=message.Text.Inline.START_BUTTON.value)

    @mock.patch(base_patch_path + ".models.Association.get_sticker_ids",
                mock.MagicMock(autospec=True, return_value=[]))
    def test_no_stickers(self):
        self.set_user_association(1)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        result = inline_query_result.Text(
            update.update_id,
            message.Text.Inline.NO_RESULTS.value,
            message.Text.Inline.CHAT_TO_LABEL.value)

        with mock.patch(base_patch_path + ".inline_query_result.Text",
                        mock.MagicMock(autospec=True, return_value=result)):
            run_handler(inline_query.create_inline_query_handler, update)

        bot.answer_inline_query.assert_called_once_with(
            update.inline_query.id,
            results=[result],
            cache_time=2,
            is_personal=True)

    def test_one_label(self):
        self.set_user_association(1)

        update = telegram_factories.InlineQueryUpdateFactory(
            inline_query__query="label",
            inline_query__bot=bot)

        sticker_id = telegram_factories.StickerFactory().file_id
        sticker_result = inline_query_result.Sticker(sticker_id)

        with mock.patch(
                base_patch_path + ".models.Association.get_sticker_ids",
                mock.MagicMock(autospec=True, return_value=[sticker_id])), \
             mock.patch(base_patch_path + ".inline_query_result.Sticker",
                        mock.MagicMock(return_value=sticker_result)):
            run_handler(inline_query.create_inline_query_handler, update)

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
