from aiogram import Router, types
from aiogram.filters import Command

from keyboards import create_start_keyboard


main_router = Router()

@main_router.message(Command('start'))
async def start(message: types.Message):
    start_kb = create_start_keyboard()
    await message.answer('💱 Добро пожаловать в виртуальный обменник! 💵  Настоящая версия: MVP v.0.5 (beta 0.1). Доступен архив:',
                         reply_markup=start_kb.as_markup())
    await message.delete()