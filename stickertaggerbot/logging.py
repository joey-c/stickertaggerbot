import logging
import os
from enum import Enum

logging.basicConfig(filename=os.environ["LOG_LOCATION"],
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - '
                           '%(message)s',
                    datefmt='%d/%m/%Y %I:%M:%S %p')


class Type(Enum):
    APP = "app"
    DATABASE_ADD_STICKER = "database.add_sticker"

    HANDLER_START = "handler.start"
    HANDLER_STICKER = "handler.sticker"
    HANDLER_LABELS = "handler.label"
    HANDLER_CALLBACK_QUERY = "handler.callback_query"
    HANDLER_CALLBACK_QUERY_LABELS = "handler.callback_query.labels"
    HANDLER_INLINE_QUERY = "handler.inline_query"
    HANDLER_CHOSEN_INLINE_RESULT = "handler.chosen_inline_result"
    HANDLER_HELP = "handler.help"


def get_logger(logger_type, update_id=None):
    if update_id:
        return logging.getLogger(logger_type.value + "." + str(update_id))
    else:
        return logging.getLogger(logger_type.value)


class Logger(logging.getLoggerClass()):
    def __init__(self, name):
        super().__init__(name)

    def log_start(self):
        self.debug("Handling update")

    def log_failed_to_change_conversation_state(self, original_state,
                                                target_state):
        self.debug("Failed to enter " + original_state.name +
                   " from " + target_state.name)

    def log_conversation_not_found(self, user_id):
        self.debug("Conversation for user " + str(user_id) + " not found")

    def log_sent_message(self, message_string):
        self.debug("Sent: " + message_string)

    def log_sent_sticker(self, sticker_id):
        self.debug("Sent sticker: " + str(sticker_id))


logging.setLoggerClass(Logger)
