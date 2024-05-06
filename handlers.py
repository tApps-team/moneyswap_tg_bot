from aiogram import Router, types
from aiogram.filters import Command

from sqlalchemy.orm import Session
from sqlalchemy import insert

from keyboards import create_start_keyboard

from db.base import Base


main_router = Router()

@main_router.message(Command('start'))
async def start(message: types.Message,
                session: Session):
    Guests = Base.classes.general_models_guest
    username = message.from_user.username
    tg_id = message.from_user.id
    try:
        session.execute(insert(Guests).values(username=username,
                                            tg_id=tg_id))
    except Exception:
        pass
    finally:
        start_kb = create_start_keyboard()
        await message.answer('💱 Добро пожаловать в виртуальный обменник! 💵  Настоящая версия: MVP v.0.5 (beta 0.1). Доступен архив:',
                            reply_markup=start_kb.as_markup())
        await message.delete()