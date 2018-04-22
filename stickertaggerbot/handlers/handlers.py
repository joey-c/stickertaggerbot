import concurrent.futures

import telegram.ext

from stickertaggerbot import handlers, config


# TODO Add EDIT
# TODO Add DELETE
# TODO Add CHECK - what labels does a sticker already have?
# TODO Consider moving classes into another file
# TODO Handle unrecognized commands
def register_handlers(dispatcher, app):
    dispatcher.add_handler(
        telegram.ext.CommandHandler(
            "start", handlers.create_command_start_handler(app)))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.sticker,
                                    handlers.create_sticker_handler(app)))

    dispatcher.add_handler(
        telegram.ext.MessageHandler(telegram.ext.Filters.text,
                                    handlers.create_labels_handler(app)))

    dispatcher.add_handler(
        telegram.ext.CallbackQueryHandler(
            handlers.create_callback_handler(app)))

    dispatcher.add_handler(
        telegram.ext.InlineQueryHandler(
            handlers.create_inline_query_handler(app)))

    dispatcher.add_handler(
        telegram.ext.CommandHandler(
            "help", handlers.create_command_start_handler(app)))


pool = concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS)