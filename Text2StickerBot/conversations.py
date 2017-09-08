import logging
import threading
import enum
import concurrent.futures

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

    def __init__(self, user, chat):
        self.user = user
        self.chat = chat
        self.state = Conversation.State.IDLE
        self.lock = threading.Lock()
        self.sticker = None
        self.labels = None
        self._future = None

    # Returns True if state is None and self.state is IDLE
    #                 state is None and future is done
    #                 state is None and there is no future
    #                 state matches and future is done
    #                 state matches and there is no future
    def state_complete(self, state=None):
        if state and self.state != state:
            return False

        if self._future:
            return self._future.done()

        return True

    def is_idle(self):
        return self.state == Conversation.State.IDLE

    def reset_state(self):
        self.state = Conversation.State.IDLE
        if self._future:
            self._future.cancel()
        self._future = None

    def __change_state(self, new_state, future):
        self.state = new_state
        if self._future:
            self._future.cancel()
        self._future = future

    # Change state to typical previous state, unless otherwise specified
    # If specifying future, state must also be specified
    def rollback_state(self, state=None, future=None):
        if future and not state:
            raise ValueError()

        if state:
            if self.state == Conversation.State.STICKER:
                self.sticker = None
            elif self.state == Conversation.State.LABEL:
                self.labels = None
            self.state = state

        if future:
            self._future = future

        if state is None and future is None:
            if self._future:
                self._future.cancel()

            if self.state == Conversation.State.STICKER:
                self.sticker = None
            elif self.state == Conversation.State.LABEL:
                self.labels = None

            if self.state != Conversation.State.IDLE:
                self.state = Conversation.State(self.state.value - 1)

    def change_state(self, new_state, future=None, force=False):
        if force:
            self.__change_state(new_state, future)
            return True

        # Block until previous state's action is complete
        elif self._future:
            while not self._future.done():
                pass

        # Enforce state transition order
        try:
            if new_state == Conversation.State.STICKER:
                assert self.state == Conversation.State.IDLE
            elif new_state == Conversation.State.LABEL:
                assert (self.state == Conversation.State.STICKER or
                        self.state == Conversation.State.LABEL)
            elif new_state == Conversation.State.CONFIRMED:
                assert self.state == Conversation.State.LABEL
        except AssertionError:
            raise ValueError("Cannot transit to " + new_state.name +
                             " from " + self.state.name)

        logger = logging.getLogger("conversation." + str(self.user.id))
        logger.debug("Transiting from " + str(self.state) +
                     " to " + str(new_state))

        self.__change_state(new_state, future)

        return True

    def update_future(self, new_future, force=False):
        if force:
            if self._future:
                self._future.cancel()
            self._future = new_future

        if not force:
            if self._future:
                while not self._future.done():
                    pass
            self._future = new_future

    # timeout in seconds
    def get_future_result(self, timeout=3):
        if not self._future:
            raise ValueError("Conversation has no future.")
        try:
            return self._future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None


def get_or_create(telegram_user, get_only=False, chat=None):
    conversation = None
    user_id = telegram_user.id

    if not (get_only or chat):
        raise ValueError("Pass in chat or get_only=True")

    with lock:
        logger.debug("Acquired conversations lock")
        if user_id in all:
            logger.debug("User " + str(user_id) + "found")
            conversation = all[user_id]
        elif not get_only:
            logger.debug("Creating new conversation")
            conversation = Conversation(telegram_user, chat)
            all[user_id] = conversation

    return conversation
