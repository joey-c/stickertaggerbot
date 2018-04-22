from telegram.ext import run_async

from stickertaggerbot import logging, message, conversations, CallbackData
from stickertaggerbot.handlers import labels_callback


def create_callback_handler(app):
    @run_async
    def callback_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_CALLBACK_QUERY,
                                   update.update_id)
        logger.log_start()

        callback_data = CallbackData.unwrap(update.callback_query.data)
        user = update.effective_user
        chat_id = update.effective_chat.id

        response = message.Message(bot, update, logger, chat_id)

        conversation = conversations.get_or_create(user, get_only=True)
        if not conversation:
            logger.log_conversation_not_found(user.id)
            response_content = message.Text.Error.UNKNOWN
            response.set_content(response_content).send()
            return

        if callback_data.state == conversations.Conversation.State.LABEL:
            labels_callback.handle_callback_for_labels(app, bot, update)

    return callback_handler
