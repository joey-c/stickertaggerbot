import logging
import concurrent.futures

import telegram.ext
from telegram.ext.dispatcher import run_async

import conversations

pool = concurrent.futures.ThreadPoolExecutor


def command_start_handler(bot, update):
    pass


# Only create a conversation upon /newsticker.
@run_async
def command_new_sticker_handler(bot, update):
    logger = logging.getLogger("handler.command_new_sticker")
    logger.debug("Handling /newsticker")

    user = update.effective_user

    conversation = None
    with conversations.lock:
        logger.debug("Acquired conversations lock")
        if user in conversations.all:
            conversation = conversations.all[user.id]
        else:
            logger.debug("Creating new conversation")
            conversation = conversations.Conversation(user)
            conversations.all[user.id] = conversation

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

    # TODO Handle case where this update arrives before /newsticker
    if user not in conversations.all:
        return

    conversation = conversations.all[user.id]
    with conversation.lock:
        conversation.change_state(conversations.Conversation.State.STICKER,
                                  pool.submit(check_sticker, user, sticker))

    sticker_is_new = conversation.get_future_result()
    if sticker_is_new:
        # TODO Send message to user to continue
        pass
    else:
        # TODO Send error message to user
        # TODO Ask user if they meant to change the sticker's labels
        pass


def check_sticker(user, sticker):
    pass


@run_async
def sticker_name_handler(bot, update):
    user = update.effective_user

    if user not in conversations.all:
        # TODO Send error message
        return

    conversation = conversations.all[user.id]
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

    if user not in conversations.all:
        # TODO Send error message
        return

    text = update.effective_message.text.lower()
    if text == "yes" or text == "y":
        conversation = conversations.all[user.id]
        with conversation.lock:
            conversation.change_state(
                conversations.Conversation.State.LABEL,
                pool.submit(add_sticker, bot, update, conversation))
    else:
        # TODO Send message to label again
        pass


def add_sticker(bot, update, conversation):
    # TODO Add sticker
    # TODO Send success message
    # TODO Change conversation state to IDLE
    pass


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
