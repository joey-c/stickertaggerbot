import concurrent.futures
import logging
from enum import Enum

import telegram.ext
from telegram.ext.dispatcher import run_async

from Text2StickerBot import conversations, models

pool = concurrent.futures.ThreadPoolExecutor()


class Message(object):
    class Instruction(Enum):
        START = ""
        LABEL = ""
        RE_LABEL = ""
        CONFIRM = ""

    class Error(Enum):
        NOT_STARTED = ""
        STICKER_EXISTS = ""
        UNKNOWN = ""
        RESTART = ""  # TODO Prompt to cancel or resume previous chain
        LABEL_MISSING = ""

    class Other(Enum):
        SUCCESS = ""


# Add user to database if user is new
def create_command_start_handler(app):
    @run_async
    def command_start_handler(bot, update):
        logger = logging.getLogger("handler.start")
        logger.debug("Handling start")

        with app.app_context():
            user = models.User.get(update.effective_user.id)
            if not user:
                chat_id = update.effective_chat.id
                user = models.User.from_telegram_user(update.effective_user,
                                                      chat_id)
            models.database.session.commit()
            bot.send_message(user.chat_id, Message.Instruction.START.value)

        logger.debug("Sent instructions")

    return command_start_handler


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
        logger = logging.getLogger("handler.sticker")
        logger.debug("Handling sticker")

        user = update.effective_user
        sticker = update.effective_message.sticker
        chat_id = update.effective_chat.id

        conversation = conversations.get_or_create(user)

        with conversation.lock:
            changed = False
            if conversation.is_idle():
                changed = conversation.change_state(
                    conversations.Conversation.State.STICKER,
                    pool.submit(sticker_is_new, app, user, sticker))

            if not changed:
                # TODO Ask user if they want to cancel previous conversation
                logger.debug("Conversation is not idle")
                bot.send_message(chat_id, Message.Error.RESTART.value)
                return

        new_sticker = conversation.get_future_result()

        if new_sticker:
            bot.send_message(chat_id, Message.Instruction.LABEL.value)
            with conversation.lock:
                conversation.sticker = sticker
        elif new_sticker is False:
            logger.debug("Sticker exists")
            bot.send_message(chat_id, Message.Error.STICKER_EXISTS.value)
            # TODO Ask user if they meant to change the sticker's labels
            conversation.rollback_state()
        else:
            logger.debug("Future timed out")
            bot.send_message(chat_id, Message.Error.UNKNOWN.value)
            conversation.rollback_state()

    return sticker_handler


def get_labels(update):
    raw_text = update.effective_message.text
    labels = raw_text.split()
    return labels


def create_labels_handler(app):
    @run_async
    def labels_handler(bot, update):
        # TODO Make callback_data class
        def callback_data_generator(button_text):
            state = conversations.Conversation.State.LABEL
            bases = [state.name, sticker.file_id, button_text]
            return "+".join(bases)

        logger = logging.getLogger("handler.labels")
        logger.debug("Handling labels")

        user = update.effective_user
        chat_id = update.effective_chat.id

        conversation = conversations.get_or_create(user, get_only=True)
        if not conversation:
            bot.send_message(chat_id, Message.Error.NOT_STARTED.value)
            return

        try:
            with conversation.lock:
                changed = conversation.change_state(
                    conversations.Conversation.State.LABEL)
        except ValueError:  # State transition error
            bot.send_message(chat_id, Message.Error.RESTART.value)
            return

        if not changed:
            bot.send_message(chat_id, Message.Error.UNKNOWN.value)
            return

        sticker = conversation.sticker

        new_labels = get_labels(update)
        if not new_labels:
            bot.send_message(chat_id, Message.Error.LABEL_MISSING.value)
            return

        with conversation.lock:
            conversation.labels = new_labels
        # TODO Include existing labels
        if len(new_labels) > 1:
            message_labels = "/n".join(new_labels)
        else:
            message_labels = new_labels[0]

        message_text = Message.Instruction.CONFIRM.value + message_labels

        inline_keyboard_markup = generate_inline_keyboard_markup(
            callback_data_generator, [["confirm", "cancel"]])  # TODO Re-label

        bot.send_sticker(chat_id, sticker)
        bot.send_message(chat_id,
                         message_text,
                         reply_markup=inline_keyboard_markup)

    return labels_handler


# state: (state_type, identifier)
# button_texts: [[row1_text1, row1_text2, ...],
#           [row2_text1, row2_text2, ...]]
# Returns [[row1_callback1, row1_callback2, ...],
#          [row2_callback1, row2_callback2, ...]]
#         corresponds to buttons
def generate_inline_keyboard_markup(callback_data_generator, button_texts):
    buttons = []

    for row in button_texts:
        button_row = []
        for button_text in row:
            button = telegram.InlineKeyboardButton(
                button_text,
                callback_data=callback_data_generator(button_text))
            button_row.append(button)
        buttons.append(button_row)

    return telegram.InlineKeyboardMarkup(buttons)


def create_callback_handler(app):
    def callback_handler(bot, update):
        pass

    return callback_handler


def add_sticker(bot, update, conversation):
    user = update.effective_user

    # TODO Add sticker

    bot.send_message(user.chat_id, Message.Other.SUCCESS.value)

    # TODO Change conversation state to IDLE


def create_inline_query_handler(app):
    @run_async
    def inline_query_handler(bot, update):
        pass

    return inline_query_handler


# TODO Handle unrecognized commands
def register_handlers(dispatcher, app):
    dispatcher.add_handler(
        telegram.ext.CommandHandler("start",
                                    create_command_start_handler(app)))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.sticker,
                                    create_sticker_handler(app)))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    create_labels_handler(app)))

    dispatcher.add_handler(
        telegram.ext.CallbackQueryHandler(create_callback_handler(app)))

    dispatcher.add_handler(
        telegram.ext.InlineQueryHandler(create_inline_query_handler(app)))
