from stickertaggerbot import logging, conversations, message, models, \
    CallbackData


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
