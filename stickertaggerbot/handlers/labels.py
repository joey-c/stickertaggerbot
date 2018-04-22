from telegram.ext import run_async
import telegram

from stickertaggerbot import logging, message, conversations, CallbackData


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
                button_text.value,
                callback_data=callback_data_generator(button_text))
            button_row.append(button)
        buttons.append(button_row)

    return telegram.InlineKeyboardMarkup(buttons)
