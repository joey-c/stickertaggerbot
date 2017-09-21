import datetime

import factory
import telegram

from Text2StickerBot import config


class BotFactory(factory.Factory):
    class Meta:
        model = telegram.Bot

    token = config.TELEGRAM_TOKEN


class UserFactory(factory.Factory):
    class Meta:
        model = telegram.User

    # Required arguments
    id = factory.Sequence(lambda n: n)
    first_name = "First"
    is_bot = False

    # Optional arguments
    last_name = "Last"
    username = factory.Sequence(lambda n: "username_" + str(n))
    language_code = None
    bot = factory.SubFactory(BotFactory)


class ChatFactory(factory.Factory):
    class Meta:
        model = telegram.Chat

    # Required arguments
    id = factory.Sequence(lambda n: n)
    type = telegram.Chat.PRIVATE

    # Optional arguments
    username = None
    first_name = None
    last_name = None


class MessageFactory(factory.Factory):
    class Meta:
        model = telegram.Message

    # Required arguments
    message_id = factory.Sequence(lambda n: n)
    from_user = factory.SubFactory(UserFactory)
    date = datetime.datetime.now()
    chat = factory.SubFactory(
        ChatFactory,
        username=factory.LazyAttribute(
            lambda chat: chat.factory_parent.from_user.username),
        first_name=factory.LazyAttribute(
            lambda chat: chat.factory_parent.from_user.first_name),
        last_name=factory.LazyAttribute(
            lambda chat: chat.factory_parent.from_user.last_name))

    # Optional arguments
    text = None
    chat_id = factory.LazyAttribute(lambda self: self.chat.id)
    sticker = None
    bot = factory.SubFactory(BotFactory)
    entities = None


class MessageEntity(factory.Factory):
    class Meta:
        model = telegram.MessageEntity

    # Required arguments
    type = None
    length = None
    offset = 0


class CommandMessageFactory(MessageFactory):
    class Params:
        command = "/command"

    entities = factory.List([factory.SubFactory(
        MessageEntity,
        type=telegram.MessageEntity.BOT_COMMAND,
        length=factory.LazyAttribute(
            lambda entity: len(
                entity.factory_parent.factory_parent.command)))])

    text = factory.LazyAttribute(lambda self: self.command)


class StickerFactory(factory.Factory):
    class Meta:
        model = telegram.Sticker

    # Required arguments
    file_id = factory.Sequence(lambda n: "sticker_" + str(n))
    width = 150
    height = 150

    # Optional arguments
    set_name = None


class StickerMessageFactory(MessageFactory):
    sticker = factory.SubFactory(StickerFactory)


class CallbackQueryFactory(factory.Factory):
    class Meta:
        model = telegram.CallbackQuery

    # Required arguments
    id = factory.Sequence(lambda n: "cq_" + str(n))
    from_user = factory.SubFactory(UserFactory)
    chat_instance = factory.Sequence(lambda n: str(n))
    data = None
    message = factory.SubFactory(
        MessageFactory,
        user=factory.SubFactory(BotFactory),
        chat__id=factory.LazyAttribute(
            lambda chat: int(
                chat.factory_parent.factory_parent.chat_instance)))


class InlineQueryFactory(factory.Factory):
    class Meta:
        model = telegram.InlineQuery

    # Required arguments
    id = factory.sequence(lambda n: "iq_" + str(n))
    from_user = factory.SubFactory(UserFactory)
    query = ""
    offset = ""


class UpdateFactory(factory.Factory):
    class Meta:
        model = telegram.Update

    # Required arguments
    update_id = factory.Sequence(lambda n: n)

    # Optional arguments
    message = None
    inline_query = None
    chosen_inline_result = None


class MessageUpdateFactory(UpdateFactory):
    message = factory.SubFactory(MessageFactory)


class StickerUpdateFactory(UpdateFactory):
    message = factory.SubFactory(StickerMessageFactory)


class CommandUpdateFactory(UpdateFactory):
    class Params:
        command = "/command"

    message = factory.SubFactory(
        CommandMessageFactory,
        command=factory.LazyAttribute(
            lambda message: message.factory_parent.command))


class InlineQueryUpdateFactory(UpdateFactory):
    inline_query = factory.SubFactory(InlineQueryFactory)


class CallbackQueryUpdateFactory(UpdateFactory):
    callback_query = factory.SubFactory(CallbackQueryFactory)
