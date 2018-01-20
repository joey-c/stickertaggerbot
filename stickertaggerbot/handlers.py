import concurrent.futures
from enum import Enum

import telegram.ext
from telegram.ext.dispatcher import run_async

from stickertaggerbot import conversations, models, config, logging, message

pool = concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS)


# TODO Consider moving classes into another file

class CallbackData(object):
    class ButtonText(Enum):
        CONFIRM = "confirm"
        CANCEL = "cancel"

    SEPARATOR = "+"

    # Strings
    def __init__(self, state, state_identifier, button_text=None):
        self.state = state
        self.state_identifier = state_identifier
        self.button_text = button_text

    def generator(self, button_text):
        return CallbackData.SEPARATOR.join([button_text.value,
                                            self.state.name,
                                            self.state_identifier])

    @classmethod
    def unwrap(cls, callback_string):
        button_text_value, state_name, state_identifier \
            = callback_string.split(cls.SEPARATOR)

        state = getattr(conversations.Conversation.State, state_name)
        button_text = CallbackData.ButtonText(button_text_value)

        return cls(state, state_identifier, button_text)


# TODO Consider other implementations of result_id
class StickerResult(telegram.InlineQueryResultCachedSticker):
    def __init__(self, sticker_id):
        super().__init__(StickerResult.generate_result_id(sticker_id),
                         sticker_id)

    @classmethod
    def generate_result_id(cls, sticker_id):
        return sticker_id

    @classmethod
    def unwrap(cls, result_id):
        return result_id


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
                pool.submit(sticker_is_new, app, user, sticker))
        except ValueError as e:
            # TODO Ask user if they want to cancel previous conversation
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


def get_labels(update):
    raw_text = update.effective_message.text
    labels = raw_text.split()
    return labels


def create_labels_handler(app):
    @run_async
    def labels_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_LABELS,
                                    update.update_id)
        logger.log_start()

        user = update.effective_user
        chat_id = update.effective_chat.id

        response = message.Message(bot, update, logger, chat_id)

        conversation = conversations.get_or_create(user, get_only=True)
        if not conversation:
            logger.log_conversation_not_found(user.id)
            response_content = message.Text.Error.NOT_STARTED
            response.set_content(response_content).send()
            return

        try:
            conversation.change_state(
                conversations.Conversation.State.LABEL)
        except ValueError as e:
            state, = e.args
            logger.log_failed_to_change_conversation_state(
                state, conversations.Conversation.State.LABEL)
            response_content = message.Text.Error.RESTART
            response.set_content(response_content).send()
            return

        sticker = conversation.sticker

        new_labels = get_labels(update)
        if not new_labels:
            logger.debug("No new labels found. Message: " +
                         update.message.text)

            response_content = message.Text.Error.LABEL_MISSING
            response.set_content(response_content).send()

            conversation.rollback_state()
            return

        conversation.labels = new_labels
        # TODO Include existing labels
        if len(new_labels) > 1:
            message_labels = "\n".join(new_labels)
        else:
            message_labels = new_labels[0]

        message_text = message.Text.Instruction.CONFIRM.value + message_labels

        buttons = [[CallbackData.ButtonText.CONFIRM,
                    CallbackData.ButtonText.CANCEL]]
        generator = CallbackData(conversations.Conversation.State.LABEL,
                                 sticker.file_id).generator
        inline_keyboard_markup = generate_inline_keyboard_markup(
            generator, buttons)  # TODO Add re-label

        response_content = sticker
        response.set_content(response_content).send()

        response_confirmation = message.Message(bot, update, logger, chat_id,
                                                content=message_text)
        response_confirmation.send(reply_markup=inline_keyboard_markup)
        logger.debug("Sent sticker with confirmation message")

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
            handle_callback_for_labels(app, bot, update)

    return callback_handler


def handle_callback_for_labels(app, bot, update):
    logger = logging.get_logger(logging.Type.HANDLER_CALLBACK_QUERY_LABELS,
                                update.update_id)
    logger.log_start()

    callback_data = CallbackData.unwrap(update.callback_query.data)
    chat_id = update.effective_chat.id
    conversation = conversations.get_or_create(
        update.effective_user, get_only=True)

    response = message.Message(bot, update, logger, chat_id)

    if not conversation:
        logger.log_conversation_not_found(update.effective_user.id)
        response_content = message.Text.Error.UNKNOWN
        response.set_content(response_content).send()
        return

    if callback_data.button_text == CallbackData.ButtonText.CONFIRM:
        logger.debug("Button – confirm")
        try:
            conversation.change_state(
                conversations.Conversation.State.CONFIRMED)
        except ValueError as e:
            state, = e.args
            logger.log_failed_to_change_conversation_state(
                state, conversations.Conversation.State.CONFIRMED)

            response_content = message.Text.Error.UNKNOWN
            response.set_content(response_content).send()
            return

        added = add_sticker(app, bot, update, conversation)
        if not added:
            response_content = message.Text.Error.UNKNOWN
            response.set_content(response_content).send()
            conversation.rollback_state()
            return

        response_content = message.Text.Other.SUCCESS
        response.set_content(response_content).send()

        try:
            conversation.change_state(conversations.Conversation.State.IDLE)
        except ValueError as e:
            state, = e.args
            logger.log_failed_to_change_conversation_state(
                state, conversations.Conversation.State.IDLE)

            return

    elif callback_data.button_text == CallbackData.ButtonText.CANCEL:
        # TODO Rollback state after pending conversation state is introduced
        conversation.labels = None
        response_content = message.Text.Instruction.RE_LABEL
        response.set_content(response_content).send()


def add_sticker(app, bot, update, conversation):
    logger = logging.get_logger(logging.Type.DATABASE_ADD_STICKER,
                                update.update_id)

    user = update.effective_user
    chat_id = update.effective_chat.id
    sticker = conversation.sticker

    with app.app_context():
        try:
            database_user = models.User.get(user.id)
            database_sticker = models.Sticker.get_or_create(sticker)

            for label in conversation.labels:
                database_label = models.Label.get_or_create(label)

                # TODO Work with existing labels
                association = models.Association(
                    database_user, database_sticker, database_label)

            models.database.session.commit()
        except Exception as e:
            response = message.Message(bot, update, logger, chat_id)
            response_content = message.Text.Error.UNKNOWN
            response.set_content(response_content).send()

            models.database.session.rollback()
            conversation.rollback_state()
            return False

    return True


# TODO Add deep-linking parameters
# TODO Support pagination
def create_inline_query_handler(app):
    @run_async
    def inline_query_handler(bot, update):
        query = update.inline_query
        user_id = update.effective_user.id
        labels = query.query.split()

        with app.app_context():
            user_associations = models.Association.query.filter_by(
                user_id=user_id)

        if user_associations.count() == 0:
            query.answer(is_personal=True,
                         switch_pm_text=message.Text.Error.NOT_STARTED.value)
            return

        with app.app_context():
            stickers = models.Association.get_sticker_ids(
                user_id, labels, unique=True)

        if not stickers:
            query.answer(is_personal=True,
                         switch_pm_text=message.Text.Error.NO_MATCHES.value)
            return

        sticker_results = [StickerResult(sticker) for sticker in stickers]
        query.answer(sticker_results, is_personal=True)

    return inline_query_handler


# TODO: Consider adding soft labels – labels in the query that aren't yet
#       associated with the sticker
def create_chosen_inline_result_handler(app):
    @run_async
    def chosen_inline_result_handler(bot, update):
        logger = logging.get_logger(logging.Type.HANDLER_CHOSEN_INLINE_RESULT,
                                    update.update_id)
        logger.log_start()

        user = update.effective_user
        chosen_inline_result = update.chosen_inline_result
        sticker_id = StickerResult.unwrap(chosen_inline_result.result_id)
        labels = chosen_inline_result.query.split()

        logger.debug("Query: " + chosen_inline_result.query)
        logger.debug("Labels: " + str(labels))

        models.Association.increment_usage(user.id, sticker_id, labels)

        logger.debug("Incremented usage for user " + str(user.id) +
                     "'s sticker " + str(sticker_id))

    return chosen_inline_result_handler


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
