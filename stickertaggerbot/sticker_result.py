import telegram


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
