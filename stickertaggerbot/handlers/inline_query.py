from telegram.ext import run_async

from stickertaggerbot import models, message, StickerResult


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
            query.answer(is_personal=True,
                         switch_pm_text=message.Text.Error.NOT_STARTED.value)
            return

        with app.app_context():
            stickers = models.Association.get_sticker_ids(
                user_id, labels, unique=True)

        if not stickers:
            query.answer(is_personal=True,
                         switch_pm_text=message.Text.Error.NO_MATCHES.value)
            return

        sticker_results = [StickerResult(sticker) for sticker in stickers]
        query.answer(sticker_results, is_personal=True)

    return inline_query_handler
