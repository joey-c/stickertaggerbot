from telegram.ext import run_async

from stickertaggerbot import models, message
import stickertaggerbot.inline_query_result as inline_query_result


# TODO Add deep-linking parameters
# TODO Support pagination
def create_inline_query_handler(app):
    @run_async
    def inline_query_handler(bot, update):
        query = update.inline_query
        user_id = update.effective_user.id
        labels = query.query.split()

        with app.app_context():
            user_associations = models.Association.query.filter_by(
                user_id=user_id)

        if user_associations.count() == 0:
            result = inline_query_result.Text(
                update.update_id,
                message.Text.Inline.NOT_STARTED.value,
                message.Text.Inline.CHAT_TO_START.value)
            query.answer(results=[result],
                         is_personal=True,
                         cache_time=2,
                         switch_pm_text=message.Text.Inline.START_BUTTON.value)
            return

        with app.app_context():
            stickers = models.Association.get_sticker_ids(
                user_id, labels, unique=True)

        if not stickers:
            result = inline_query_result.Text(
                update.update_id,
                message.Text.Inline.NO_RESULTS.value,
                message.Text.Inline.CHAT_TO_LABEL.value)
            query.answer(results=[result],
                         is_personal=True,
                         cache_time=2)
            return

        sticker_results = [inline_query_result.Sticker(sticker)
                           for sticker in stickers]
        query.answer(sticker_results, is_personal=True)

    return inline_query_handler
