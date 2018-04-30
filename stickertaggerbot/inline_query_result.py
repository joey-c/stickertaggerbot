import telegram


# TODO Consider other implementations of result_id
class Sticker(telegram.InlineQueryResultCachedSticker):
    def __init__(self, sticker_id):
        super().__init__(Sticker.generate_result_id(sticker_id),
                         sticker_id)

    @classmethod
    def generate_result_id(cls, sticker_id):
        return sticker_id

    @classmethod
    def unwrap(cls, result_id):
        return result_id


class Text(telegram.InlineQueryResultArticle):
    def __init__(self, update_id, text, subtitle):
        message_content = telegram.InputTextMessageContent(subtitle)
        super().__init__(id=update_id,
                         title=text,
                         input_message_content=message_content)
