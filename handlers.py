import telegram.ext


def inline_query_handler(bot, update):
    pass


def register_handlers(dispatcher):
    dispatcher.add_handler(
        telegram.ext.InlineQueryHandler(inline_query_handler))
