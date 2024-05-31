from aiogram import Router, types
from aiogram.filters import Command

from sqlalchemy.orm import Session
from sqlalchemy import insert

from keyboards import create_start_keyboard

from db.base import Base


main_router = Router()

start_text = '''
💱 <b>Добро пожаловать в MoneySwap!</b><br>

Наш бот поможет найти лучшую сделку под вашу задачу 💸<br>

👉🏻 <b>Чтобы начать поиск</b>, выберите категорию “безналичные”, “наличные” или “Swift/Sepa” и нажмите на нужную кнопку ниже.<br>

Если есть какие-то вопросы, обращайтесь [поддержка]. Мы всегда готовы вам помочь!
'''

@main_router.message(Command('start'))
async def start(message: types.Message,
                session: Session):
    Guest = Base.classes.general_models_guest
    username = message.from_user.username
    tg_id = message.from_user.id
    guest = session.query(Guest).where(Guest.tg_id == tg_id).all()
    # print(guest)
    if not guest:
        session.execute(insert(Guest).values(username=username,
                                              tg_id=tg_id))
        session.commit()
    start_kb = create_start_keyboard()
    await message.answer(start_text,
                         parse_mode='html',
                        reply_markup=start_kb.as_markup(resize_keyboard=True,
                                                        is_persistent=True))
    await message.delete()