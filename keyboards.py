from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types.web_app_info import WebAppInfo
from config import WEBAPP_URL_ONE, WEBAPP_URL_TWO, WEBAPP_URL_THREE



def create_start_keyboard(user_id: int):
    start_kb = ReplyKeyboardBuilder()
    
    start_kb.add(types.KeyboardButton(text='Безналичные',
                                      web_app=WebAppInfo(url=f'https://www.bestexchanges.world/?direction=noncash?user_id={user_id}')))
    start_kb.add(types.KeyboardButton(text='Наличные',
                                      web_app=WebAppInfo(url=f'https://www.bestexchanges.world/?direction=cash?user_id={user_id}')))
    start_kb.row(types.KeyboardButton(text='Swift/Sepa'))
    
    return start_kb
