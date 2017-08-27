import logging
import threading
import enum

all = {}
lock = threading.Lock()
logger = logging.getLogger("conversations")


class Conversation(object):
    # States should transition as per the listed order, and loop back such that
    # IDLE should precede NEW_STICKER
    class State(enum.Enum):
        NEW_STICKER = 0
        STICKER = 1
        LABEL = 2
        CONFIRMED = 3
        IDLE = 4

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

    def change_state(self, new_state, future=None):
        # Block until previous state 's action is complete
        if self._future:
            while not self._future.done():
                pass

        # Enforce state transition order
        if new_state == Conversation.State.NEW_STICKER:
            assert self.state == Conversation.State.IDLE
        else:
            assert self.state.value == new_state.value - 1

        logger = logging.getLogger("conversation." + str(self.user.id))
        logger.debug("Transiting from " + str(self.state) +
                     " to " + str(new_state))

        self.state = new_state
        self._future = future

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
