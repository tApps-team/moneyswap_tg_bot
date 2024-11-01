from aiogram.fsm.state import StatesGroup, State


class SwiftSepaStates(StatesGroup):
    request_type = State()
    country = State()
    amount = State()
    task_text = State()


class FeedbackFormStates(StatesGroup):
    reason = State()
    description = State()
    contact = State()
    username = State()