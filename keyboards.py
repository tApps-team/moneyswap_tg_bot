from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import WEBAPP_URL_ONE, WEBAPP_URL_TWO, WEBAPP_URL_THREE



def create_start_keyboard():
    start_kb = InlineKeyboardBuilder()
    start_kb.add(types.InlineKeyboardButton(text='prototype 💸',
                                            web_app=types.WebAppInfo(url=WEBAPP_URL_ONE)))
    start_kb.add(types.InlineKeyboardButton(text='alpha v.0.1 💰',
                                            web_app=types.WebAppInfo(url=WEBAPP_URL_TWO)))
    start_kb.row(types.InlineKeyboardButton(text='IONIX UX+UI 📱',
                                            web_app=types.WebAppInfo(url=WEBAPP_URL_THREE)))
    
    return start_kb
