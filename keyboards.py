from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types.web_app_info import WebAppInfo
from config import WEBAPP_URL_ONE, WEBAPP_URL_TWO, WEBAPP_URL_THREE, FEEDBACK_REASON_PREFIX



reason_list = (
    ('Ошибка', 'error'),
    ('Проблемма с обменником', 'exchange_problem'),
    ('Сотрудничество', 'cooperation'),
    ('Другое', 'other'),
)

reason_dict = {
    'error': 'Ошибка',
    'exchange_problem': 'Проблемма с обменником',
    'cooperation': 'Сотрудничество',
    'other': 'Другое',

}


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


def create_swift_sepa_kb():
    swift_sepa_kb = InlineKeyboardBuilder()
    swift_sepa_kb.add(types.InlineKeyboardButton(text='Оплатить инвойс',
                                                 callback_data='start_swift_sepa'))
    swift_sepa_kb.row(types.InlineKeyboardButton(text='Условия - Телеграф',
                                                 callback_data='conditions'))     ###   !!!!

    return swift_sepa_kb


def create_feedback_form_reasons_kb():
    reason_kb = InlineKeyboardBuilder()

    # for reason, data in reason_list:
    for data, reason in reason_dict.items():
        reason_kb.row(types.InlineKeyboardButton(text=reason,
                                                 callback_data=f'{FEEDBACK_REASON_PREFIX}__{data}'))
        
    return reason_kb


def create_feedback_confirm_kb():
    feedback_confirm_kb = InlineKeyboardBuilder()

    feedback_confirm_kb.add(types.InlineKeyboardButton(text='Отправить',
                                                       callback_data='feedback_form_send'))
    
    return feedback_confirm_kb


def create_support_kb():
    support_kb = InlineKeyboardBuilder()
    support_kb.add(types.InlineKeyboardButton(text='Заполнить форму',
                                              callback_data='feedback_form'))

    return support_kb


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