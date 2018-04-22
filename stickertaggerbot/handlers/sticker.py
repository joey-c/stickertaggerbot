from telegram.ext import run_async

from stickertaggerbot import models, logging, message, conversations
from stickertaggerbot.handlers.handlers import pool


def sticker_is_new(app, user, sticker):
    with app.app_context():
        subquery = models.Association.query.filter_by(
            user_id=user.id, sticker_id=sticker.file_id)
        count = subquery.count()
    return count == 0


# Create a conversation upon receiving a sticker,
# or prompt to cancel previous conversations
def create_sticker_handler(app):
    @run_async
    def sticker_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_STICKER,
                                   update.update_id)
        logger.log_start()

        user = update.effective_user
        sticker = update.effective_message.sticker
        chat_id = update.effective_chat.id

        response = message.Message(bot, update, logger, chat_id)

        conversation = conversations.get_or_create(user,
                                                   chat=update.effective_chat)

        try:
            conversation.change_state(
                conversations.Conversation.State.STICKER,
                pool.submit(sticker_is_new, app, user, sticker), force=True)
        except ValueError as e:
            # TODO Ask user if they want to cancel previous conversation
            # Currently should not enter this branch
            state, = e.args
            logger.log_failed_to_change_conversation_state(
                state, conversations.Conversation.State.STICKER)

            response_content = message.Text.Error.RESTART
            response.set_content(response_content).send()
            return

        logger.debug("Entered STICKER state")
        new_sticker = conversation.get_future_result()

        if new_sticker:
            response_content = message.Text.Instruction.LABEL
            response.set_content(response_content).send()
            conversation.sticker = sticker
        elif new_sticker is False:
            logger.debug("Sticker exists")
            response_content = message.Text.Error.STICKER_EXISTS
            response.set_content(response_content).send()
            # TODO Ask user if they meant to change the sticker's labels
            conversation.rollback_state()
        else:
            logger.debug("Future timed out")
            response_content = message.Text.Error.UNKNOWN
            response.set_content(response_content).send()
            conversation.rollback_state()

    return sticker_handler
