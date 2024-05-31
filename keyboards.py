from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardBuilder
from aiogram.types.web_app_info import WebAppInfo
from config import WEBAPP_URL_ONE, WEBAPP_URL_TWO, WEBAPP_URL_THREE



def create_start_keyboard():
    start_kb = KeyboardBuilder()
    # start_kb = InlineKeyboardBuilder()
    start_kb.add(types.KeyboardButton(text='Наличные',
                                      web_app=WebAppInfo(url='https://www.bestexchanges.world/')))

    start_kb.add(types.KeyboardButton(text='Безналичные',
                                      web_app=WebAppInfo(url='https://www.bestexchanges.world/')))

    start_kb.row(types.KeyboardButton(text='Swift/Sepa'))

    # start_kb.add(types.InlineKeyboardButton(text='Наличные',
    #                                         web_app=WebAppInfo(url='https://www.bestexchanges.world/')))
    # start_kb.add(types.InlineKeyboardButton(text='Безналичные',
    #                                         web_app=WebAppInfo(url='https://www.bestexchanges.world/')))
    # start_kb.row(types.InlineKeyboardButton(text='Swift/Sepa',
    #                                         callback_data='3'))
    
    return start_kb
