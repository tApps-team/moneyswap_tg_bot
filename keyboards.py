from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types.web_app_info import WebAppInfo
from config import WEBAPP_URL_ONE, WEBAPP_URL_TWO, WEBAPP_URL_THREE



def create_start_keyboard(user_id: int):
    start_kb = ReplyKeyboardBuilder()
    
    start_kb.add(types.KeyboardButton(text='Безналичные',
                                      web_app=WebAppInfo(url=f'https://www.bestexchanges.world/?direction=noncash&user_id={user_id}')))
    start_kb.add(types.KeyboardButton(text='Наличные',
                                      web_app=WebAppInfo(url=f'https://www.bestexchanges.world/?direction=cash&user_id={user_id}')))
    # start_kb.row(types.KeyboardButton(text='Swift/Sepa'))
    
    return start_kb


def create_start_inline_keyboard(user_id: int):
    start_kb = InlineKeyboardBuilder()

    start_kb.add(types.InlineKeyboardButton(text='Безналичные',
                                            web_app=WebAppInfo(url=f'https://www.bestexchanges.world/?direction=noncash&user_id={user_id}')))
    start_kb.add(types.InlineKeyboardButton(text='Наличные',
                                            web_app=WebAppInfo(url=f'https://www.bestexchanges.world/?direction=cash&user_id={user_id}')))
    start_kb.row(types.InlineKeyboardButton(text='Инвойсы Swift/Sepa',
                                            callback_data='invoice_swift/sepa'))
    start_kb.row(types.InlineKeyboardButton(text='О MoneySwap',
                                            callback_data='about'))
    start_kb.add(types.InlineKeyboardButton(text='Поддержка',
                                            callback_data='support'))
    
    return start_kb


def create_swift_start_kb():
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='Оплатить платеж',
                                      callback_data='pay_payment'))
    kb.add(types.InlineKeyboardButton(text='Принять платеж',
                                      callback_data='access_payment'))
    
    return kb


def add_cancel_btn_to_kb(kb: InlineKeyboardBuilder = None):
    if kb is None:
        kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text='Отменить',
                                      callback_data='cancel'))
    
    return kb
    

def create_kb_to_main():
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='На главную',
                                      callback_data='to_main'))
    kb.add(types.InlineKeyboardButton(text='Отправить заявку',
                                      callback_data='send_app'))
    
    return kb