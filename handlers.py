import concurrent.futures
import logging
from enum import Enum

import telegram.ext
from telegram.ext.dispatcher import run_async

import conversations
import models

pool = concurrent.futures.ThreadPoolExecutor


class Message(object):
    class Instruction(Enum):
        START = ""
        LABEL = ""
        RE_LABEL = ""
        CONFIRM = ""

    class Error(Enum):
        NOT_STARTED = ""
        STICKER_EXISTS = ""

    class Other(Enum):
        SUCCESS = ""


# Add user to database if user is new
def command_start_handler(bot, update):
    user = models.User.get(update.effective_user.id)
    if not user:
        chat_id = update.effective_chat.id
        user = models.User.from_telegram_user(update.effective_user, chat_id)
    models.database.session.commit()

    bot.send_message(user.chat_id, Message.Instruction.START.value)


# Create a conversation upon /newsticker.
@run_async
def command_new_sticker_handler(bot, update):
    logger = logging.getLogger("handler.command_new_sticker")
    logger.debug("Handling /newsticker")

    conversation = conversations.get_or_create(update.effective_user)
    with conversation.lock:
        if conversation.is_idle():
            conversation.change_state(
                conversations.Conversation.State.NEW_STICKER)
        else:
            pass  # TODO Handle interruption of previous chain


@run_async
def new_sticker_handler(bot, update):
    user = update.effective_user
    sticker = update.effective_message.sticker

    conversation = conversations.get_or_create(user, get_only=True)

    # TODO Handle edge case where this update arrives before /newsticker
    if not conversation:
        return

    with conversation.lock:
        conversation.change_state(conversations.Conversation.State.STICKER,
                                  pool.submit(check_sticker, user, sticker))

    sticker_is_new = conversation.get_future_result()
    if sticker_is_new:
        bot.send_message(user.chat_id, Message.Instruction.LABEL)
    else:
        bot.send_message(user.chat_id, Message.Error.STICKER_EXISTS)
        # TODO Ask user if they meant to change the sticker's labels


def check_sticker(user, sticker):
    pass


@run_async
def sticker_name_handler(bot, update):
    user = update.effective_user

    conversation = conversations.get_or_create(user, get_only=True)

    if not conversation:
        bot.send_message(user.chat_id, Message.Error.NOT_STARTED)
        return

    with conversation.lock:
        conversation.change_state(
            conversations.Conversation.State.LABEL,
            pool.submit(confirm_sticker_name, bot, update))


def confirm_sticker_name(bot, update):
    # TODO Send confirmation message to user with sticker and labels
    pass


@run_async
def confirmation_handler(bot, update):
    user = update.effective_user

    conversation = conversations.get_or_create(user, get_only=True)

    if not conversation:
        bot.send_message(user.chat_id, Message.Error.NOT_STARTED)
        return

    text = update.effective_message.text.lower()
    if text == "yes" or text == "y":
        conversation = conversations.all[user.id]
        with conversation.lock:
            conversation.change_state(
                conversations.Conversation.State.LABEL,
                pool.submit(add_sticker, bot, update, conversation))
    else:
        bot.send_message(user.chat_id, Message.Instruction.RE_LABEL)


def add_sticker(bot, update, conversation):
    user = update.effective_user

    # TODO Add sticker

    bot.send_message(user.chat_id, Message.Other.SUCCESS)

    # TODO Change conversation state to IDLE


def inline_query_handler(bot, update):
    pass


def register_handlers(dispatcher):
    dispatcher.add_handler(
        telegram.ext.CommandHandler("start", command_start_handler))

    dispatcher.add_handler(
        telegram.ext.CommandHandler("newsticker",
                                    command_new_sticker_handler))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.sticker,
                                    new_sticker_handler))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    sticker_name_handler))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    confirmation_handler))

    dispatcher.add_handler(
        telegram.ext.InlineQueryHandler(inline_query_handler))
