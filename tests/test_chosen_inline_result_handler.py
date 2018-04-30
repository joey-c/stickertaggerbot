from unittest import mock

import pytest

from stickertaggerbot.handlers import chosen_inline_result
from stickertaggerbot.inline_query_result import Sticker
from tests import telegram_factories
from tests.misc import run_handler

base_patch_path = "stickertaggerbot.handlers.chosen_inline_result"


class TestChosenInlineResultHandler(object):
    @pytest.fixture(autouse=True)
    def patch_telegram(self):
        patch = mock.patch(
            base_patch_path + ".models.Association.increment_usage",
            new_callable=mock.MagicMock(autospec=True))
        patch.start()
        yield
        patch.stop()

    def test_single_label(self):
        query_string = "label_0"
        sticker_id = "sticker_0"

        result_id = Sticker.generate_result_id(sticker_id)
        update = telegram_factories.ChosenInlineResultUpdateFactory(
            chosen_inline_result__query=query_string,
            chosen_inline_result__result_id=result_id)

        run_handler(chosen_inline_result.create_chosen_inline_result_handler,
                    update)

        user_id = update.effective_user.id
        chosen_inline_result.models.Association.increment_usage.assert_called_once_with(
            user_id, sticker_id, [query_string])

    def test_multiple_labels(self):
        labels = ["label_0", "label_1", "label_2"]
        sticker_id = "sticker_0"

        query_string = " ".join(labels)
        result_id = Sticker.generate_result_id(sticker_id)
        update = telegram_factories.ChosenInlineResultUpdateFactory(
            chosen_inline_result__query=query_string,
            chosen_inline_result__result_id=result_id)

        run_handler(chosen_inline_result.create_chosen_inline_result_handler,
                    update)

        user_id = update.effective_user.id
        chosen_inline_result.models.Association.increment_usage.assert_called_once_with(
            user_id, sticker_id, labels)

    # TODO: Flesh out when soft labels are implemented.
    # Nonexistent labels are currently ignored at increment_usage
    def test_nonexistent_labels(self):
        pass
