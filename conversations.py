import logging
import threading
import enum

all = {}
lock = threading.Lock()
logger = logging.getLogger("conversations")


class Conversation(object):
    # States should typically transition as per the listed order
    # STICKER may hijack the order if the user sends a new sticker
    #   and cancels the previous chain.
    # LABEL may repeat if user replies negatively to confirmation
    class State(enum.Enum):
        IDLE = 0
        STICKER = 1
        LABEL = 2
        CONFIRMED = 3

    def __init__(self, user):
        self.user = user
        self.state = Conversation.State.IDLE
        self.lock = threading.Lock()
        self._future = None

    def state_complete(self, state):
        if not self._future:
            return False

        return self.state == state and self._future.done()

    def is_idle(self):
        return self.state == Conversation.State.IDLE

    def reset_state(self):
        self.state = Conversation.State.IDLE
        self._future = None

    def __change_state(self, new_state, future):
        self.state = new_state
        self._future.cancel()
        self._future = future

    def change_state(self, new_state, future=None, force=False):
        if force:
            self.__change_state(new_state, future)

        # Block until previous state's action is complete
        elif self._future:
            while not self._future.done():
                pass

        # Enforce state transition order
        if new_state == Conversation.State.STICKER:
            assert self.state == Conversation.State.IDLE
        elif new_state == Conversation.State.LABEL:
            assert (self.state == Conversation.State.STICKER or
                    self.state == Conversation.State.LABEL)
        elif new_state == Conversation.State.CONFIRMED:
            assert self.state == Conversation.State.LABEL

        logger = logging.getLogger("conversation." + str(self.user.id))
        logger.debug("Transiting from " + str(self.state) +
                     " to " + str(new_state))

        self.__change_state(new_state, future)

    def get_future_result(self):
        return self._future.result()


def get_or_create(telegram_user, get_only=False):
    conversation = None
    user_id = telegram_user.id

    with lock:
        logger.debug("Acquired conversations lock")
        if user_id in all:
            logger.debug("User " + str(user_id) + "found")
            conversation = all[user_id]
        elif not get_only:
            logger.debug("Creating new conversation")
            conversation = Conversation(telegram_user)
            all[user_id] = conversation

    return conversation
