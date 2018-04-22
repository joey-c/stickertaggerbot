from telegram.ext import run_async

from stickertaggerbot import logging, message, models


# Catch errors when sending messages
# TODO Handle deep-linking parameters
# Add user to database if user is new
def create_command_start_handler(app):
    @run_async
    def command_start_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_START,
                                   update.update_id)
        logger.log_start()

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        response = message.Message(bot, update, logger, chat_id)

        with app.app_context():
            user = models.User.get(user_id)
            if not user:
                logger.debug("User " + str(user_id) + " not found")
                user = models.User.from_telegram_user(update.effective_user,
                                                      chat_id)
                models.database.session.commit()
                logger.debug("Created user " + str(user_id))

        response_content = message.Text.Instruction.START
        response.set_content(response_content).send()

    return command_start_handler
