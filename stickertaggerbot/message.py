from enum import Enum

import telegram.error


# For outgoing messages via bot

class Text(object):
    class Instruction(Enum):
        START = "Hi! I can remember stickers and your labels for them. " + \
                "You can easily search and send your stickers with me. " + \
                "Try it now! Send me a sticker you want to label."
        LABEL = "Great! Now, send me label(s). " + \
                "Labels must be separated by spaces."
        RE_LABEL = "Please send your label(s) again."
        CONFIRM = "Label(s) received:\n"
        HELP = START

    class Error(Enum):
        NOT_STARTED = "Please send a sticker to start labelling."
        STICKER_EXISTS = "This sticker has already been labelled. " + \
                         "Please label another sticker. " + \
                         "Editing and viewing of labels are not yet supported."
        UNKNOWN = "An unknown error has occurred. Please try again later."
        RESTART = ""  # TODO Prompt to cancel or resume previous chain
        LABEL_MISSING = "No labels were detected. Please send again. " + \
                        "Labels must be separated by spaces, tabs or line breaks."
        NO_MATCHES = "No stickers were found. " + \
                     "Send me a sticker to start labelling it!"

    class Other(Enum):
        SUCCESS = "Your sticker is labelled! " + \
                  "You can now use @stickertaggerbot <label> to find it"

    class Inline(Enum):
        NOT_STARTED = "You have not labelled any stickers."
        START_BUTTON = "Start"
        NO_RESULTS = "No results found."
        CHAT_TO_START = "Chat with me to start labelling!"
        CHAT_TO_LABEL = "Chat with me to label stickers!"

    types = (Instruction, Error, Other)


class Message(object):
    class Type(Enum):
        TEXT = 0
        STICKER = 1

    def __init__(self, bot, update, logger, chat_id, content=None):
        self.bot = bot
        self.update = update
        self.logger = logger
        self.chat_id = chat_id

        if content:
            self.set_content(content)

    def set_content(self, content):
        if isinstance(content, Text.types):
            self.type = Message.Type.TEXT
            self.content = content.value
        elif isinstance(content, telegram.Sticker):
            self.type = Message.Type.STICKER
            self.content = content
        elif isinstance(content, str):
            self.type = Message.Type.TEXT
            self.content = content

        return self  # allows for chaining with send

    def send(self, *args, **kwargs):  # TODO chat_id
        try:
            if self.type == Message.Type.TEXT:
                self.bot.send_message(self.chat_id, self.content,
                                      *args, **kwargs)
                self.logger.log_sent_message(self.content)

            elif self.type == Message.Type.STICKER:
                self.bot.send_sticker(self.chat_id, self.content,
                                      *args, **kwargs)
                self.logger.log_sent_sticker(self.content.file_id)

        except telegram.error.BadRequest as e:
            self.logger.error(e)
        except telegram.error.InvalidToken as e:
            self.logger.error(e)
        except telegram.error.TimedOut as e:
            self.logger.error(e)
        except telegram.error.NetworkError as e:
            self.logger.error(e)
        except telegram.error.RetryAfter as e:
            self.logger.error(e)
        except telegram.error.Unauthorized as e:
            self.logger.error(e)
        except telegram.error.ChatMigrated as e:
            self.logger.error(e)
        except telegram.error.TelegramError as e:  # generic Telegram error
            self.logger.error(e)
        except Exception as e:  # generic error
            self.logger.error(e)
