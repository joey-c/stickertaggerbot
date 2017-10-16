import logging
import os

logging.basicConfig(filename=os.environ["LOG_LOCATION"],
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - '
                           '%(message)s',
                    datefmt='%d/%m/%Y %I:%M:%S %p')

APP = logging.getLogger("app")

HANDLER_START = logging.getLogger("handler.start")
HANDLER_STICKER = logging.getLogger("handler.sticker")
HANDLER_LABELS = logging.getLogger("handler.label")
HANDLER_CALLBACK_QUERY = logging.getLogger("handler.callback_query")
HANDLER_CALLBACK_QUERY_LABELS = logging.getLogger(
    "handler.callback_query.labels")
HANDLER_INLINE_QUERY = logging.getLogger("handler.inline_query")

DATABASE_ADD_STICKER = logging.getLogger("database.add_sticker")


def update_prefix(update):
    return "Update " + str(update.update_id) + ": "


def logger_start(logger, update_id):
    logger.debug("Handling update " + str(update_id))


def log_failed_to_change_conversation_state(logger, prefix, original_state,
                                            target_state):
    logger.debug(prefix + "Failed to enter " + original_state.name +
                 " from " + target_state.name)


def log_conversation_not_found(logger, prefix, user_id):
    logger.debug(prefix +
                 "Conversation for user " + str(user_id) + " not found")


def log_sent_message(logger, prefix, message):
    logger.debug(prefix + "Sent " + message.name + " message")
