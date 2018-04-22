from telegram.ext import run_async

from stickertaggerbot import logging, message


def create_help_handler(app):
    @run_async
    def help_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_HELP,
                                   update.update_id)
        logger.log_start()

        chat_id = update.effective_chat.id

        response = message.Message(bot, update, logger, chat_id)
        response_content = message.Text.Instruction.HELP
        response.set_content(response_content).send()

    return help_handler
