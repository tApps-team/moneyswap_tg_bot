from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types.web_app_info import WebAppInfo

from config import WEBAPP_URL_ONE, WEBAPP_URL_TWO, WEBAPP_URL_THREE, FEEDBACK_REASON_PREFIX

from utils.multilanguage import (start_text_dict,
                                 start_kb_text,
                                 start_swift_sepa_text)


reason_list = (
    (('Ошибка', 'Error'), 'error'),
    (('Проблема с обменником', 'Issue with the Exchanger'), 'exchange_problem'),
    (('Сотрудничество', 'Partnership'), 'cooperation'),
    (('Другое', 'Other'), 'other'),
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
                                      web_app=WebAppInfo(url=f'https://app.moneyswap.online/?direction=noncash&user_id={user_id}')))
    start_kb.add(types.KeyboardButton(text='Наличные',
                                      web_app=WebAppInfo(url=f'https://app.moneyswap.online/?direction=cash&user_id={user_id}')))
    # start_kb.row(types.KeyboardButton(text='Swift/Sepa'))
    
    return start_kb


# def create_start_inline_keyboard(user_id: int,
#                                  language_code: str):
#     if language_code == 'ru':
#         tuple_text = start_kb_text.get('ru')
#         telegraf_link = 'https://telegra.ph/O-MoneySwap-11-21'
#     else:
#         tuple_text = start_kb_text.get('en')
#         telegraf_link = ' https://telegra.ph/About-MoneySwap-02-06'

#     start_kb = InlineKeyboardBuilder()

#     start_kb.add(types.InlineKeyboardButton(text='Безналичные',
#                                             web_app=WebAppInfo(url=f'https://app.moneyswap.online/?direction=noncash&user_id={user_id}')))
#     start_kb.add(types.InlineKeyboardButton(text='Наличные',
#                                             web_app=WebAppInfo(url=f'https://app.moneyswap.online/?direction=cash&user_id={user_id}')))
#     start_kb.row(types.InlineKeyboardButton(text='Инвойсы Swift/Sepa',
#                                             callback_data='invoice_swift/sepa'))
#     start_kb.row(types.InlineKeyboardButton(text='О MoneySwap',
#                                             url='https://telegra.ph/O-MoneySwap-11-21'))
#     start_kb.add(types.InlineKeyboardButton(text='Поддержка',
#                                             callback_data='support'))
    
#     return start_kb


def create_start_inline_keyboard(user_id: int,
                                 language_code: str):
    if language_code == 'ru':
        tuple_text = start_kb_text.get('ru')
        telegraf_link = 'https://telegra.ph/O-MoneySwap-11-21'
    else:
        tuple_text = start_kb_text.get('en')
        telegraf_link = 'https://telegra.ph/About-MoneySwap-02-06'

    start_kb = InlineKeyboardBuilder()

    start_kb.add(types.InlineKeyboardButton(text=tuple_text[0],
                                            web_app=WebAppInfo(url=f'https://app.moneyswap.online/?direction=noncash&user_id={user_id}&user_lang={language_code}')))
    start_kb.add(types.InlineKeyboardButton(text=tuple_text[1],
                                            web_app=WebAppInfo(url=f'https://app.moneyswap.online/?direction=cash&user_id={user_id}&user_lang={language_code}')))
    start_kb.row(types.InlineKeyboardButton(text=tuple_text[2],
                                            callback_data='invoice_swift/sepa'))
    start_kb.row(types.InlineKeyboardButton(text=tuple_text[3],
                                            url=telegraf_link))
    start_kb.add(types.InlineKeyboardButton(text=tuple_text[4],
                                            callback_data='support'))
    
    return start_kb


def create_swift_sepa_kb():
    swift_sepa_kb = InlineKeyboardBuilder()
    swift_sepa_kb.add(types.InlineKeyboardButton(text='Оплатить инвойс',
                                                 callback_data='start_swift_sepa'))
    swift_sepa_kb.row(types.InlineKeyboardButton(text='Условия',
                                                 url='https://telegra.ph/Usloviya-obmena-SWIFTSEPA-s-MoneySwap-11-21'))   ###   !!!!

    return swift_sepa_kb


def create_condition_kb():
    condition_kb = InlineKeyboardBuilder()
    condition_kb.add(types.InlineKeyboardButton(text='Назад',
                                                 callback_data='back_to_swift/sepa'))
    
    return condition_kb


def create_feedback_form_reasons_kb(language_code: str):
    reason_kb = InlineKeyboardBuilder()

    # for reason, data in reason_list:
    # for data, reason in reason_dict.items():
    for reason, data in reason_list:
        _text = reason[0] if language_code == 'ru' else reason[-1]
        reason_kb.row(types.InlineKeyboardButton(text=_text,
                                                 callback_data=f'{FEEDBACK_REASON_PREFIX}__{data}'))
        
    return reason_kb


def create_feedback_confirm_kb(language_code: str):
    feedback_confirm_kb = InlineKeyboardBuilder()

    _text = 'Отправить' if language_code == 'ru' else 'Send'

    feedback_confirm_kb.add(types.InlineKeyboardButton(text=_text,
                                                       callback_data='feedback_form_send'))
    
    return feedback_confirm_kb


def create_support_kb():
    support_kb = InlineKeyboardBuilder()
    support_kb.add(types.InlineKeyboardButton(text='Заполнить форму',
                                              callback_data='feedback_form'))

    return support_kb



def create_swift_start_kb(language_code: str):
    if language_code == 'ru':
        swift_sepa_tuple = start_swift_sepa_text.get('ru')
        telegraf_url = 'https://telegra.ph/Usloviya-obmena-SWIFTSEPA-s-MoneySwap-11-21'
    else:
        swift_sepa_tuple = start_swift_sepa_text.get('en')
        telegraf_url = 'https://telegra.ph/SWIFTSEPA-Exchange-Terms-with-MoneySwap-02-06'  

    # swift_sepa_tuple = start_swift_sepa_text.get('ru') if language_code == 'ru' \
    #                     else start_swift_sepa_text.get('en')
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text=swift_sepa_tuple[0],
                                      callback_data='pay_payment'))
    kb.add(types.InlineKeyboardButton(text=swift_sepa_tuple[1],
                                      callback_data='access_payment'))
    
    kb.row(types.InlineKeyboardButton(text=swift_sepa_tuple[2],
                                      url=telegraf_url))

    return kb


def create_swift_condition_kb(language_code: str):
    if language_code == 'ru':
        swift_sepa_tuple = start_swift_sepa_text.get('ru')
        telegraf_url = 'https://telegra.ph/Usloviya-obmena-SWIFTSEPA-s-MoneySwap-11-21'
    else:
        swift_sepa_tuple = start_swift_sepa_text.get('en')
        telegraf_url = 'https://telegra.ph/SWIFTSEPA-Exchange-Terms-with-MoneySwap-02-06'  

    # swift_sepa_tuple = start_swift_sepa_text.get('ru') if language_code == 'ru' \
    #                     else start_swift_sepa_text.get('en')
    kb = InlineKeyboardBuilder()
    # kb.add(types.InlineKeyboardButton(text=swift_sepa_tuple[0],
    #                                   callback_data='pay_payment'))
    # kb.add(types.InlineKeyboardButton(text=swift_sepa_tuple[1],
    #                                   callback_data='access_payment'))
    
    kb.row(types.InlineKeyboardButton(text=swift_sepa_tuple[2],
                                      url=telegraf_url))

    return kb


def add_cancel_btn_to_kb(language_code: str,
                         kb: InlineKeyboardBuilder = None):
    if language_code == 'ru':
        _text = 'Отменить'
    else:
        _text = 'Cancel'
    if kb is None:
        kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text=_text,
                                      callback_data='cancel'))
    
    return kb
    

def create_kb_to_main(language_code: str):
    if language_code == 'ru':
        _tuple_text = ('На главную', 'Отправить заявку')
    else:
        _tuple_text = ('Back to main', 'Send request')

    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text=_tuple_text[0],
                                      callback_data='to_main'))
    kb.add(types.InlineKeyboardButton(text=_tuple_text[1],
                                      callback_data='send_app'))
    
    return kb


def add_switch_language_btn(_kb: InlineKeyboardBuilder,
                            select_language: str):
    if select_language == 'ru':
        _text = 'Switch language to 🇺🇸'
        _callback_data = 'lang_to_en'
    else:
        _text = 'Сменить язык на 🇷🇺'
        _callback_data = 'lang_to_ru'

    _kb.row(types.InlineKeyboardButton(text=_text,
                                       callback_data=_callback_data))

    return _kb