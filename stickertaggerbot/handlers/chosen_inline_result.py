from telegram.ext import run_async

from stickertaggerbot import logging, models, StickerResult


# TODO: Consider adding soft labels – labels in the query that aren't yet
#       associated with the sticker
def create_chosen_inline_result_handler(app):
    @run_async
    def chosen_inline_result_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_CHOSEN_INLINE_RESULT,
                                   update.update_id)
        logger.log_start()

        user = update.effective_user
        chosen_inline_result = update.chosen_inline_result
        sticker_id = StickerResult.unwrap(chosen_inline_result.result_id)
        labels = chosen_inline_result.query.split()

        logger.debug("Query: " + chosen_inline_result.query)
        logger.debug("Labels: " + str(labels))

        models.Association.increment_usage(user.id, sticker_id, labels)

        logger.debug("Incremented usage for user " + str(user.id) +
                     "'s sticker " + str(sticker_id))

    return chosen_inline_result_handler
