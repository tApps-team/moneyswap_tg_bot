from aiogram import Router, types
from aiogram.filters import Command

from sqlalchemy.orm import Session

from keyboards import create_start_keyboard

from db.base import Base


main_router = Router()

@main_router.message(Command('start'))
async def start(message: types.Message,
                session: Session):
    Users = Base.classes.partners_direction
    res = session.query(Users).all()
    print('id', message.from_user.id)
    print('name', message.from_user.username)
    for r in res:
        print(r.__dict__)
    # print(res)
    start_kb = create_start_keyboard()
    await message.answer('💱 Добро пожаловать в виртуальный обменник! 💵  Настоящая версия: MVP v.0.5 (beta 0.1). Доступен архив:',
                         reply_markup=start_kb.as_markup())
    await message.delete()