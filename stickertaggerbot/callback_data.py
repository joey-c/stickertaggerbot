from enum import Enum

from stickertaggerbot import conversations


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
