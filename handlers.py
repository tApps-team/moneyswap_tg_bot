import os
import json
import time

from asyncio import sleep

from datetime import datetime, timedelta

import aiohttp

from aiogram import Router, types, Bot, F
from aiogram.types import BufferedInputFile, URLInputFile
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError

from pyrogram import Client

from sqlalchemy.orm import Session, joinedload, sessionmaker
from sqlalchemy import insert, select, update, and_

from config import BEARER_TOKEN, FEEDBACK_REASON_PREFIX

from keyboards import (create_add_review_kb, create_start_keyboard,
                       create_start_inline_keyboard, create_swift_condition_kb,
                       create_swift_start_kb,
                       add_cancel_btn_to_kb,
                       create_kb_to_main,
                       create_swift_sepa_kb,
                       create_support_kb,
                       create_feedback_form_reasons_kb,
                       reason_dict,
                       create_feedback_confirm_kb,
                       create_condition_kb,
                       add_switch_language_btn)

from states import SwiftSepaStates, FeedbackFormStates

from utils.handlers import get_exchange_name, try_add_file_ids_to_db, try_add_file_ids, swift_sepa_data, validate_amount
from utils.multilanguage import start_text_dict

from db.base import Base


main_router = Router()

start_text = '💱<b>Добро пожаловать в MoneySwap!</b>\n\nНаш бот поможет найти лучшую сделку под вашу задачу 💸\n\n👉🏻 <b>Чтобы начать поиск</b>, выберите категорию “безналичные”, “наличные” или “Swift/Sepa” и нажмите на нужную кнопку ниже.\n\nЕсли есть какие-то вопросы, обращайтесь <a href="https://t.me/MoneySwap_support">Support</a> или <a href="https://t.me/moneyswap_admin">Admin</a>. Мы всегда готовы вам помочь!'

about_text = '''
<b>MoneySwap — ваш проводник в мире обмена , переводов и платежных решений</b>\n
MoneySwap — это удобный агрегатор обменников, который упрощает процесс обмена криптовалют, электронных денег и переводов. Мы помогаем частным лицам и бизнесу быстро находить выгодные условия для обменов и переводов — все в одном месте.

MoneySwap — это и сайт, и Telegram-бот: можно подобрать обменник прямо с телефона или ноутбука.\n
<b>Преимущества работы с MoneySwap</b>\n
<i>1. Доступ к проверенным обменникам</i>\r
Мы работаем только с обменниками с хорошей репутацией, чтобы минимизировать все возможные риски. Вы выбираете из списка надежных вариантов — каждый обменник прошел нашу проверку на безопасность и прозрачность.

<i>2. Быстрые сделки и выгодные курсы</i>\r
MoneySwap помогает вам быстро найти лучшие курсы. Мы отслеживаем предложения разных обменников в реальном времени, чтобы вы могли сразу увидеть, где самые выгодные условия для вашей сделки.

<i>3. Решения без ограничений</i>\r
Для пользователей из России это особенно важно: никаких ограничений по типам обменов и переводов. Наличные, безналичные, SWIFT/SEPA — вы выбираете удобный способ, а мы помогаем быстро найти подходящий обменник.

<i>4. Прозрачность и безопасность</i>\r
Мы заботимся о прозрачности каждой сделки. Вам не нужно беспокоиться о скрытых условиях — вы видите все детали и работаете только с проверенными обменниками.

<b>Как начать обмен с MoneySwap?</b>

Просто запустите наш Telegram-бот или зайдите на сайт. Выберите тип обмена:\r

<i>Наличные</i>\r
Укажите cтрану, город. Выберите что отдаете и получаете. Ниже вы увидите список доступных обменников и их курсы обмена.

<i>Безналичные переводы</i>\r
Выберите, что отдаете и что хотите получить, а бот подберет для вас лучшие варианты с надежными условиями.

<b>Важно: MoneySwap не занимается обменами и переводами напрямую. Мы помогаем вам найти проверенные обменники и провайдеров, чтобы решить ваши финансовые вопросы безопасно и удобно.</b>

<b>SWIFT/SEPA переводы, решения для бизнеса</b>

Если нужен международный перевод, выберите этот тип и отправьте запрос. Мы обработаем его и свяжем вас с проверенным провайдером для безопасной сделки.

MoneySwap — это простой способ безопасно обменять криптовалюту и другие активы. Проводите обмены по всему миру с MoneySwap!
'''

condition_text = '''
<b>Условия обмена SWIFT/SEPA с MoneySwap</b>

Если вам нужно отправить или принять платеж через SWIFT/SEPA, MoneySwap сделает этот процесс простым и удобным. Все, что нужно — оставить заявку, а наши менеджеры подберут для вас лучшие решения.

<b>Как это работает?</b>

\t1. Оставьте заявку в Telegram-боте или на сайте MoneySwap.\r
\t2. Мы обработаем ваш запрос и предложим проверенных провайдеров, которые смогут выполнить ваш перевод.\r
\t3. Выберите подходящий вариант, свяжитесь с провайдером и согласуйте детали.\r

<b>Условия</b>

	•	Минимальная сумма: от $3 000 в эквиваленте.
	•	Максимальная сумма: до $500 000 в эквиваленте.

<b>Что можно оплатить?</b>

MoneySwap помогает найти решения для самых разных задач:

	•	Оплата товаров за рубежом (популярные направления: Гонконг, Китай, Европа, ОАЭ, Таиланд, Турция).
	•	Оплата инвойсов за покупку автомобилей (Япония, Корея, Китай и другие).
	•	Покупка недвижимости (Европа, Азия, ОАЭ).
	•	Оплата обучения за границей (Англия, Европа, США и другие страны).
	•	И многое другое — почти любой запрос может быть обработан.

<b>Важно!</b>
MoneySwap не проводит обмены или переводы напрямую, мы предлагаем проверенных провайдеров, которые выполнят ваш запрос быстро, безопасно и надежно.
Оставьте заявку, и мы найдем для вас оптимальное решение!
'''

# @main_router.message(Command('start'))
# async def start(message: types.Message | types.CallbackQuery,
#                 session: Session,
#                 state: FSMContext,
#                 bot: Bot,
#                 text_msg: str = None):
#     is_callback = isinstance(message, types.CallbackQuery)

#     data = await state.get_data()
#     main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     # if main_menu_msg:
#     #     chat_id, message_id = main_menu_msg

#     _start_text = start_text
#     utm_source = None

#     if isinstance(message, types.Message):
#         query_param = message.text.split()

#         if len(query_param) > 1:
#             utm_source = query_param[-1]

#     with session as session:
#         Guest = Base.classes.general_models_guest

#         tg_id = message.from_user.id
#         guest = session.query(Guest)\
#                         .where(Guest.tg_id == tg_id)\
#                         .first()
    
#         if isinstance(message, types.CallbackQuery):
#             message = message.message

#         chat_link = None

#         if not guest:
#             value_dict = {
#                 'username': message.from_user.username,
#                 'tg_id': tg_id,
#                 'first_name': message.from_user.first_name,
#                 'last_name': message.from_user.last_name,
#                 'language_code': message.from_user.language_code,
#                 'is_premium': bool(message.from_user.is_premium),
#                 'is_active': True,
#             }

#             if utm_source:
#                 value_dict.update(
#                     {
#                         'utm_source': utm_source,
#                     }
#                 )
#             session.execute(insert(Guest).values(**value_dict))
#             session.commit()
#         else:
#             chat_link  = guest.chat_link

#     start_kb = create_start_inline_keyboard(tg_id)

#     if chat_link:
#         chat_link_text = f'Cсылка на чата по Вашим обращениям -> {chat_link}'
#         _start_text += f'\n\n{chat_link_text}'

#     if not is_callback:
#         main_menu_msg: types.Message = await message.answer(text=_start_text,
#                                                             reply_markup=start_kb.as_markup(),
#                                                             disable_web_page_preview=True,
#                                                             disable_notification=True)
#         try:
#             chat_id, message_id = main_menu_msg
#             await bot.delete_message(chat_id=chat_id,
#                                      message_id=message_id)
#         except Exception:
#             pass
#     else:
#         try:
#             chat_id, message_id = main_menu_msg

#             main_menu_msg: types.Message = await bot.edit_message_text(text=_start_text,
#                                                                         chat_id=chat_id,
#                                                                         message_id=message_id,
#                                                                         reply_markup=start_kb.as_markup(),
#                                                                         disable_web_page_preview=True)
#         except Exception as ex:
#             print(ex)
#             main_menu_msg: types.Message = await bot.send_message(chat_id=message.chat.id,
#                                                                   text=_start_text,
#                                                                   reply_markup=start_kb.as_markup(),
#                                                                   disable_web_page_preview=True,
#                                                                   disable_notification=True)


#     # if not is_callback:
#     #     try:
#     #         await bot.delete_message(chat_id=chat_id,
#     #                                  message_id=message_id)
#     #     except Exception:
#     #         pass

#     msg_data = (main_menu_msg.chat.id, main_menu_msg.message_id)

#     await state.update_data(main_menu_msg=msg_data)
    
#     # if main_menu_msg:
#     #     try:
#     #         await main_menu_msg.delete()
#     #     except Exception:
#     #         pass
#     # await state.update_data(start_msg=start_msg.message_id)
#     # await state.update_data(username=message.from_user.username)
#     # try:
#     #     await bot.delete_message(message.chat.id,
#     #                             prev_start_msg)
#     # except Exception:
#     #     pass
#     try:
#         await message.delete()
#     except Exception:
#         pass


@main_router.message(Command('start'))
async def start(message: types.Message | types.CallbackQuery,
                session: Session,
                state: FSMContext,
                bot: Bot,
                text_msg: str = None):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        # print('TEST LANGUAGE', type(select_language), select_language)
        select_language = 'ru'
        await state.update_data(select_language=select_language)

    # language_code = message.from_user.language_code
    # print(language_code)
    review_msg_dict = None

    is_callback = isinstance(message, types.CallbackQuery)

    # _start_text = start_text
    _start_text = start_text_dict.get('ru') if select_language == 'ru'\
          else start_text_dict.get('en')
    
    utm_source = None

    if isinstance(message, types.Message):
        query_param = message.text.split()

        if len(query_param) > 1:
            utm_source = query_param[-1]

            if utm_source.startswith('review'):
                params = utm_source.split('_')
                
                review_msg_dict = {
                    'marker': params[1],
                    'exchange_id': params[-1],
                }

                utm_source = 'from_site'
            
    with session as session:
        Guest = Base.classes.general_models_guest

        tg_id = message.from_user.id
        guest = session.query(Guest)\
                        .where(Guest.tg_id == tg_id)\
                        .first()
    
        if isinstance(message, types.CallbackQuery):
            message = message.message

        chat_link = None

        if not guest:
            value_dict = {
                'username': message.from_user.username,
                'tg_id': tg_id,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name,
                'language_code': message.from_user.language_code,
                'select_language': 'ru',
                'is_premium': bool(message.from_user.is_premium),
                'time_create': datetime.now(),
                'is_active': True,
            }

            if utm_source:
                value_dict.update(
                    {
                        'utm_source': utm_source,
                    }
                )
            session.execute(insert(Guest).values(**value_dict))
            session.commit()
        else:
            chat_link  = guest.chat_link

    has_pinned_message = message.chat.pinned_message.text

    if review_msg_dict and has_pinned_message:
        exchange_name = get_exchange_name(review_msg_dict,
                                          session)
        if exchange_name is not None:
            _kb = create_add_review_kb(review_msg_dict,
                                       select_language)
            # _text = f'Оставить отзыв на обменник {exchange_name}'
            if select_language == 'ru':
                _text = f'Оставить отзыв на обменник {exchange_name}'
            else:
                _text = f'Add review to exchanger {exchange_name}'
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для отзыва'
            else:
                _text = 'Exchanger to add review not found'

        await bot.send_message(chat_id=message.from_user.id,
                               text=_text,
                               reply_markup=_kb.as_markup())
            
        return

    start_kb = create_start_inline_keyboard(tg_id,
                                            select_language)
    start_kb = add_switch_language_btn(start_kb,
                                       select_language)

    if chat_link:
        if select_language == 'ru':
            chat_link_text = f'Cсылка на чата по Вашим обращениям -> {chat_link}'
        else:
            chat_link_text = f'Link to chat for your requests -> {chat_link}'
        
        _start_text += f'\n\n{chat_link_text}'

    if not is_callback:
        try:
            _msg = await message.answer(text=_start_text,
                                reply_markup=start_kb.as_markup(),
                                disable_web_page_preview=True,
                                disable_notification=True)
        except TelegramForbiddenError:
            return

        try:
            await bot.unpin_all_chat_messages(chat_id=message.chat.id)
        except Exception as ex:
            print('unpin error', ex)
        await bot.pin_chat_message(message.chat.id,
                                    message_id=_msg.message_id)
        try:
            await message.delete()
        except Exception:
            pass
    else:
        try:
            _msg = await bot.send_message(chat_id=message.chat.id,
                                text=_start_text,
                                reply_markup=start_kb.as_markup(),
                                disable_web_page_preview=True,
                                disable_notification=True)
        except TelegramForbiddenError:
            return
        try:
            await bot.unpin_all_chat_messages(chat_id=message.chat.id)
        except Exception as ex:
            print('unpin error', ex)
        await bot.pin_chat_message(message.chat.id,
                                    message_id=_msg.message_id)
        try:
            await message.delete()
        except Exception:
            pass
    if review_msg_dict:
        exchange_name = get_exchange_name(review_msg_dict,
                                          session)
        if exchange_name is not None:
            _kb = create_add_review_kb(review_msg_dict)
            await bot.send_message(chat_id=message.from_user.id,
                                text=f'Оставить отзыв на обменник {exchange_name}',
                                reply_markup=_kb.as_markup())


@main_router.callback_query(F.data.startswith('lang'))
async def request_type_state(callback: types.CallbackQuery,
                             session: Session,
                             state: FSMContext,
                             bot: Bot):
    callback_data = callback.data.split('_')[-1]

    if callback_data == 'ru':
        select_language = 'ru'
    else:
        select_language = 'en'
    
    await state.update_data(select_language=select_language)

    await start(callback,
                session,
                state,
                bot,
                text_msg='Главное меню')
    
    await callback.answer()


# @main_router.message(F.text == 'Swift/Sepa')
# async def start_swift_sepa(message: types.Message,
#                            state: FSMContext,
#                            bot: Bot):
#     data = await state.get_data()
#     await state.set_state(SwiftSepaStates.request_type)
#     await state.update_data(order=dict())

#     swift_start_kb = create_swift_start_kb()
#     kb = add_cancel_btn_to_kb(swift_start_kb)

#     main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     # print('has_main_menu_msg?', bool(main_menu_msg))

#     if main_menu_msg:
#         try:
#             await bot.delete_message(*main_menu_msg)
#             # await main_menu_msg.delete()
#         except Exception:
#             pass

#     state_msg = await message.answer('<b>Выберите тип заявки</b>',
#                          reply_markup=kb.as_markup())
    
#     state_data_message = (state_msg.chat.id, state_msg.message_id)
    
#     await state.update_data(state_msg=state_data_message)
#     # await state.update_data(username=message.from_user.username)
#     await message.delete()


@main_router.callback_query(F.data.in_(('cancel', 'to_main')))
async def back_to_main(callback: types.CallbackQuery,
                       state: FSMContext,
                       session: Session,
                       bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # start_msg = state_data.get('start_msg')
    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')
    # chat_link_msg: tuple[str,str] = data.get('chat_link_msg')

    await state.clear()

    if select_language:
        await state.update_data(select_language=select_language)
    # if main_menu_msg:
    #     await state.update_data(main_menu_msg=main_menu_msg)

    # if chat_link_msg:
    #     await state.update_data(chat_link_msg=chat_link_msg)

    await start(callback,
                session,
                state,
                bot,
                text_msg='Главное меню')
    try:
        await callback.answer()
        # await callback.message.delete()
    except Exception:
        pass


# @main_router.callback_query(F.data == 'invoice_swift/sepa')
# async def invoice_swift_sepa(callback: types.CallbackQuery,
#                             session: Session,
#                             state: FSMContext,
#                             bot: Bot,
#                             api_client: Client):
#     data = await state.get_data()

#     main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     chat_id, message_id = main_menu_msg
#     # chat_id = callback.message.chat.id
#     # message_id = callback.message.message_id

#     swift_sepa_kb = create_swift_sepa_kb()
#     swift_sepa_kb = add_cancel_btn_to_kb(swift_sepa_kb)

#     # await state.update_data(action='swift/sepa')

#     await bot.edit_message_text(text='Выберите действие',
#                                 chat_id=chat_id,
#                                 message_id=message_id,
#                                 reply_markup=swift_sepa_kb.as_markup())
    
#     # await bot.edit_message_reply_markup(chat_id=chat_id,
#     #                                     message_id=message_id,
#     #                                     reply_markup=swift_sepa_kb.as_markup())
    
#     await callback.answer()

@main_router.callback_query(F.data == 'invoice_swift/sepa')
async def invoice_swift_sepa(callback: types.CallbackQuery,
                            session: Session,
                            state: FSMContext,
                            bot: Bot,
                            api_client: Client):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = callback.from_user.language_code

    _text = 'Выберите действие' if select_language == 'ru' else 'Choose an action'
    # _text = '<b>Введите сумму и валюту платежа</b>\n\n⚠️ <u>Внимание: минимальная сумма платежа составляет 3000$.</u>' if select_language == 'ru'\
    #              else '<b>Input payment and valute amount</b>\n\n⚠️ <u>Please note: the minimum payment amount is 3000$</u>'

    # data = await state.get_data()

    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

    await state.set_state(SwiftSepaStates.request_type)
    # await state.set_state(SwiftSepaStates.amount)


    # chat_id, message_id = main_menu_msg
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    await state.update_data(order=dict(),
                            state_msg=(chat_id, message_id))
    # swift_sepa_kb = create_swift_sepa_kb()
    swift_sepa_kb = create_swift_start_kb(select_language)
    # swift_sepa_kb = create_swift_condition_kb(select_language)
    swift_sepa_kb = add_cancel_btn_to_kb(select_language,
                                         swift_sepa_kb)

    # await state.update_data(action='swift/sepa')
    try:
        await bot.edit_message_text(text=_text,
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=swift_sepa_kb.as_markup())
    except TelegramForbiddenError:
        return
    # await bot.edit_message_reply_markup(chat_id=chat_id,
    #                                     message_id=message_id,
    #                                     reply_markup=swift_sepa_kb.as_markup())
    
    await callback.answer()

    

# @main_router.callback_query(F.data == 'start_swift_sepa')
# async def start_swift_sepa(callback: types.CallbackQuery,
#                             session: Session,
#                             state: FSMContext,
#                             bot: Bot,
#                             api_client: Client):
#     # await callback.answer(text='Находится в разработке',
#     #                       show_alert=True)
#     data = await state.get_data()

#     # if not data.get('action'):
#     #     await callback.answer(text='Что то пошло не так, попробуйте еще раз.')
#     #     await state.clear()

#     #     await start(callback,
#     #                 session,
#     #                 state,
#     #                 bot,
#     #                 text_msg='Главное меню')
#     #     return
    
#     await state.set_state(SwiftSepaStates.request_type)
#     await state.update_data(order=dict())

#     swift_start_kb = create_swift_start_kb()
#     kb = add_cancel_btn_to_kb(swift_start_kb)

#     main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     chat_id, message_id = main_menu_msg
#     # chat_id = callback.message.chat.id
#     # message_id = callback.message.message_id


#     # print('has_main_menu_msg?', bool(main_menu_msg))

#     # if main_menu_msg:
#     #     try:
#     #         await bot.delete_message(*main_menu_msg)
#     #         # await main_menu_msg.delete()
#     #     except Exception:
#     #         pass

#     # state_msg = await message.answer('<b>Выберите тип заявки</b>',
#     #                      reply_markup=kb.as_markup())
#     await bot.edit_message_text(text='<b>Выберите тип заявки</b>',
#                                 chat_id=chat_id,
#                                 message_id=message_id,
#                                 reply_markup=kb.as_markup())
    
#     try:
#         await callback.answer()
#     except Exception:
#         pass
    
#     # state_data_message = (state_msg.chat.id, state_msg.message_id)
    
#     # await state.update_data(state_msg=state_data_message)
#     # # await state.update_data(username=message.from_user.username)
#     # await message.delete()

@main_router.callback_query(F.data == 'start_swift_sepa')
async def start_swift_sepa(callback: types.CallbackQuery,
                            session: Session,
                            state: FSMContext,
                            bot: Bot,
                            api_client: Client):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = callback.from_user.language_code
    # data = await state.get_data()

    # if not data.get('action'):
    #     await callback.answer(text='Что то пошло не так, попробуйте еще раз.')
    #     await state.clear()

    #     await start(callback,
    #                 session,
    #                 state,
    #                 bot,
    #                 text_msg='Главное меню')
    #     return
    
    await state.set_state(SwiftSepaStates.request_type)
    await state.update_data(order=dict())

    swift_start_kb = create_swift_start_kb(select_language)
    kb = add_cancel_btn_to_kb(select_language,
                              swift_start_kb)

    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

    # chat_id, message_id = main_menu_msg
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    try:
        await bot.edit_message_text(text='<b>Выберите тип заявки</b>',
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=kb.as_markup())
    except TelegramForbiddenError:
        return
    try:
        await callback.answer()
    except Exception:
        pass


@main_router.callback_query(F.data == 'conditions')
async def get_conditions(callback: types.CallbackQuery,
                        session: Session,
                        state: FSMContext,
                        bot: Bot,
                        api_client: Client):
    # await callback.answer(text='Находится в разработке',
    #                       show_alert=True)
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    condition_kb = create_condition_kb()

    await bot.edit_message_text(text=condition_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=condition_kb.as_markup())
    try:
        await callback.answer()
    except Exception:
        pass


@main_router.callback_query(F.data == 'about')
async def get_about(callback: types.CallbackQuery,
                    session: Session,
                    state: FSMContext,
                    bot: Bot,
                    api_client: Client):
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    kb = add_cancel_btn_to_kb()

    await bot.edit_message_text(text=about_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    
    try:
        await callback.answer()
    except Exception:
        pass
    
    # await callback.answer(text='Находится в разработке',
    #                       show_alert=True)


@main_router.callback_query(F.data == 'back_to_swift/sepa')
async def start_support(callback: types.CallbackQuery,
                        session: Session,
                        state: FSMContext,
                        bot: Bot,
                        api_client: Client):
    await invoice_swift_sepa(callback,
                             session,
                             state,
                             bot,
                             api_client)
    try:
        await callback.answer()
        # await callback.message.delete()
    except Exception:
        pass
    


@main_router.callback_query(F.data == 'support')
async def start_support(callback: types.CallbackQuery,
                        session: Session,
                        state: FSMContext,
                        bot: Bot,
                        api_client: Client):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = callback.from_user.language_code
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    await state.set_state(FeedbackFormStates.reason)

    await state.update_data(feedback_form=dict())

    reason_kb = create_feedback_form_reasons_kb(select_language)

    reason_kb = add_cancel_btn_to_kb(select_language,
                                     reason_kb)
    
    if select_language == 'ru':
        _text = '<b>Выберите причину обращения</b>\n\nЕсли есть вопросы, Вы можете обратиться напрямую в <a href="https://t.me/MoneySwap_support">Support</a> или <a href="https://t.me/moneyswap_admin">Admin</a>.\nМы всегда готовы Вам помочь!'
    else:
        _text = '<b>Select the reason for your inquiry</b>\n\nIf you have any questions, you can contact <a href="https://t.me/MoneySwap_support">Support</a> or <a href="https://t.me/moneyswap_admin">Admin</a> directly. We are always ready to help!'

    try:
        await bot.edit_message_text(text=_text,
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    disable_web_page_preview=True,
                                    reply_markup=reason_kb.as_markup())
    except TelegramForbiddenError:
        return
    except Exception:
        try:
            await bot.send_message(text=_text,
                                chat_id=chat_id,
                                disable_web_page_preview=True,
                                reply_markup=reason_kb.as_markup())
        except TelegramForbiddenError:
            return
        

    # await bot.edit_message_reply_markup(reply_markup=reason_kb.as_markup(),
    #                                     chat_id=chat_id,
    #                                     message_id=message_id)
    
    await callback.answer()

    # data = await state.get_data()

    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

    # chat_id, message_id = main_menu_msg
    # chat_id = callback.message.chat.id
    # message_id = callback.message.message_id

    # support_kb = create_support_kb()
    # support_kb = add_cancel_btn_to_kb(support_kb)

    # await bot.edit_message_text(text='Выберите действие',
    #                             chat_id=chat_id,
    #                             message_id=message_id,
    #                             reply_markup=support_kb.as_markup())
    
    # # await bot.edit_message_reply_markup(chat_id=chat_id,
    # #                                     message_id=message_id,
    # #                                     reply_markup=support_kb.as_markup())
    
    # await callback.answer()
    

# @main_router.callback_query(F.data == 'feedback_form')
# async def start_support(callback: types.CallbackQuery,
#                         session: Session,
#                         state: FSMContext,
#                         bot: Bot,
#                         api_client: Client):
#     # data = await state.get_data()

#     # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     # chat_id, message_id = main_menu_msg
#     chat_id = callback.message.chat.id
#     message_id = callback.message.message_id

#     await state.set_state(FeedbackFormStates.reason)

#     await state.update_data(feedback_form=dict())

#     reason_kb = create_feedback_form_reasons_kb()

#     reason_kb = add_cancel_btn_to_kb(reason_kb)

#     await bot.edit_message_text(text='Выберите причину обращения',
#                                 chat_id=chat_id,
#                                 message_id=message_id,
#                                 reply_markup=reason_kb.as_markup())

#     # await bot.edit_message_reply_markup(reply_markup=reason_kb.as_markup(),
#     #                                     chat_id=chat_id,
#     #                                     message_id=message_id)
    
#     await callback.answer()


@main_router.callback_query(F.data == 'feedback_form_send')
async def feedback_form_send(callback: types.CallbackQuery,
                            session: Session,
                            state: FSMContext,
                            bot: Bot,
                            api_client: Client):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

    # chat_id, message_id = main_menu_msg

    feedback_form = data.get('feedback_form')

    feedback_values = {
        'reasons': reason_dict.get(feedback_form['reason']),
        'username': feedback_form['username'],
        'email': feedback_form['contact'],
        'description': feedback_form['description'],
        'time_create': datetime.now(),
    }

    FeedbackForm = Base.classes.general_models_feedbackform


    with session as _session:
        check_datetime = datetime.now() - timedelta(minutes=2)
        check_feedback_query = (
            select(
                FeedbackForm.id
            )\
            .where(
                and_(
                    FeedbackForm.reasons == reason_dict.get(feedback_form['reason']),
                    FeedbackForm.username == feedback_form['username'],
                    FeedbackForm.email == feedback_form['contact'],
                    FeedbackForm.time_create >= check_datetime,
                )
            )
        )
        check_feedback = _session.execute(check_feedback_query)
        check_feedback = check_feedback.scalar_one_or_none()

        if check_feedback:
            _text = 'Обращение уже было отправлено или Вы пытаетесь отправить одно и то же обращение, ожидайте с Вами свяжутся'
            await callback.answer(text=_text,
                                  show_alert=True)
        
            await start(callback,
                        session,
                        state,
                        bot,
                        text_msg='Главное меню')
            return

        _feedback_form = FeedbackForm(**feedback_values)
        _session.add(_feedback_form)

    #     new_order = Order(**order)  # предполагая, что order — это словарь
    #     session.add(new_order)


    # print(new_order.__dict__)

    # user_id = new_order.guest_id
    # order_id = new_order.id
    # marker = 'swift/sepa'

        # session.execute(insert(FeedbackForm).values(feedback_values))
        try:
    #     session.refresh(new_order)
            _session.commit()
            _session.refresh(_feedback_form)

            user_id = callback.from_user.id
            marker = 'feedback_form'
            order_id = _feedback_form.id

            _text = 'Обращение успешно отправлено!' if select_language == 'ru'\
                    else 'Request has been send successfully!'
        except Exception as ex:
            print(ex)
            _session.rollback()
            _text = 'Что то пошло не так, попробуйте повторить позже' if select_language == 'ru'\
                    else 'Something wrong, try repeat later'

        # else:
        #     _url = f'https://api.moneyswap.online/send_to_tg_group?user_id={user_id}&order_id={order_id}&marker={marker}'
        #     timeout = aiohttp.ClientTimeout(total=5)
        #     async with aiohttp.ClientSession() as session:
        #         async with session.get(_url,
        #                             timeout=timeout) as response:
        #             pass

        # finally:
        await callback.answer(text=_text,
                            show_alert=True)
        
        await start(callback,
                    session,
                    state,
                    bot,
                    text_msg='Главное меню')

        try:
            _url = f'https://api.moneyswap.online/send_to_tg_group?user_id={user_id}&order_id={order_id}&marker={marker}'
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession() as aiosession:
                async with aiosession.get(_url,
                                        timeout=timeout) as response:
                    pass
        except Exception as ex:
            print(ex)
            pass


    
@main_router.callback_query(F.data.startswith(FEEDBACK_REASON_PREFIX))
async def request_type_state(callback: types.CallbackQuery,
                             session: Session,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    
    reason = callback.data.split('__')[-1]

    # data = await state.get_data()

    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

    # chat_id, message_id = main_menu_msg
    # language_code = callback.from_user.language_code
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    feedback_form = data.get('feedback_form')

    feedback_form['reason'] = reason

    await state.update_data(feedback_form=feedback_form)
    await state.update_data(state_msg=(chat_id, message_id))

    await state.set_state(FeedbackFormStates.description)

    kb = add_cancel_btn_to_kb(select_language)

    _text = '<b>Опишите проблему, если это нужно</b>\nЕсли нет напишите "Нет"' if select_language == 'ru'\
                else '<b>Describe the issue if necessary</b>\nIf not, type “No”'

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    

    # await bot.edit_message_reply_markup(chat_id=chat_id,
    #                                     message_id=message_id,
    #                                     reply_markup=kb.as_markup())
    
    await callback.answer()


@main_router.message(FeedbackFormStates.description)
async def request_type_state(message: types.Message,
                             session: Session,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = message.from_user.language_code

    # reason = callback.data.split('__')[-1]
    description = message.text

    # data = await state.get_data()

    state_msg: tuple[str,str] = data.get('state_msg')

    chat_id, message_id = state_msg

    feedback_form = data.get('feedback_form')

    feedback_form['description'] = description

    await state.update_data(feedback_form=feedback_form)

    await state.set_state(FeedbackFormStates.contact)
    
    kb = add_cancel_btn_to_kb(select_language)

    if select_language == 'ru':
        _text = '<b>Укажите контактные данные, по которым мы сможем с Вами связаться</b>\n(E-mail, ссылка на Телеграм или что то другое)'
    else:
        _text = '<b>Provide contact details where we can contact you</b>\n(E-mail, Telegram link or something else)'

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    

    # await bot.edit_message_reply_markup(chat_id=chat_id,
    #                                     message_id=message_id,
    #                                     reply_markup=kb.as_markup())
    
    await message.delete()
    

@main_router.message(FeedbackFormStates.contact)
async def country_state(message: types.Message,
                        session: Session,
                        state: FSMContext,
                        bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = message.from_user.language_code
    contact = message.text

    # data = await state.get_data()

    state_msg: tuple[str,str] = data.get('state_msg')

    chat_id, message_id = state_msg

    feedback_form = data.get('feedback_form')

    feedback_form['contact'] = contact

    await state.update_data(feedback_form=feedback_form)

    await state.set_state(FeedbackFormStates.username)

    kb = add_cancel_btn_to_kb(select_language)

    _text = 'Укажите имя, чтобы мы знали как к Вам обращаться' if select_language == 'ru'\
                else 'Please provide your name so we know how to call you'

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    

    # await bot.edit_message_reply_markup(chat_id=chat_id,
    #                                     message_id=message_id,
    #                                     reply_markup=kb.as_markup())

    await message.delete()
    


@main_router.message(FeedbackFormStates.username)
async def country_state(message: types.Message,
                        session: Session,
                        state: FSMContext,
                        bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = message.from_user.language_code
    username = message.text

    # data = await state.get_data()

    state_msg: tuple[str,str] = data.get('state_msg')

    chat_id, message_id = state_msg

    feedback_form = data.get('feedback_form')

    feedback_form['username'] = username

    await state.update_data(feedback_form=feedback_form)

    feedback_confirm_kb = create_feedback_confirm_kb(select_language)

    feedback_confirm_kb = add_cancel_btn_to_kb(select_language,
                                               feedback_confirm_kb)
    
    _text = 'Заполнение завершено\nВыберите действие' if select_language == 'ru'\
            else 'Request is done\nChoose an action'

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=feedback_confirm_kb.as_markup())

    # await bot.edit_message_reply_markup(chat_id=chat_id,
    #                                     message_id=message_id,
    #                                     reply_markup=feedback_confirm_kb.as_markup())

    await message.delete()

    # feedback_values = {
    #     'reasons': reason_dict.get(feedback_form['reason']),
    #     'username': username,
    #     'email': feedback_form['contact'],
    #     'description': feedback_form['description'],
    #     'time_create': datetime.now(),
    # }

    # FeedbackForm = Base.classes.general_models_feedbackform

    # session.execute(insert(FeedbackForm).values(feedback_values))
    # try:
    #     session.commit()

    #     tx = ''
    # except Exception as ex:
    #     print(ex)


# @main_router.message(FeedbackFormStates.username)
# async def country_state(message: types.Message,
#                         session: Session,
#                         state: FSMContext,
#                         bot: Bot):
#     username = message.text

#     data = await state.get_data()

#     main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     chat_id, message_id = main_menu_msg

#     feedback_form = data.get('feedback_form')

#     feedback_form['username'] = username

#     feedback_values = {
#         'reasons': reason_dict.get(feedback_form['reason']),
#         'username': username,
#         'email': feedback_form['contact'],
#         'description': feedback_form['description'],
#         'time_create': datetime.now(),
#     }

#     FeedbackForm = Base.classes.general_models_feedbackform

#     session.execute(insert(FeedbackForm).values(feedback_values))
#     try:
#         session.commit()

#         tx = ''
#     except Exception as ex:
#         print(ex)


    # await state.update_data(feedback_form=feedback_form)

    # await state.set_state(FeedbackFormStates.username)

    # await bot.edit_message_text(text='Укажите имя, чтобы мы знали как к Вам обращаться',
    #                             chat_id=chat_id,
    #                             message_id=message_id)






@main_router.callback_query(F.data == 'send_app')
async def send_order(callback: types.CallbackQuery,
                   session: Session,
                   state: FSMContext,
                   bot: Bot,
                   api_client: Client):
    
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    order: dict = data.get('order')
    time_create = datetime.now()
    order.update({'guest_id': callback.from_user.id,
                  'time_create': time_create,
                  'moderation': False,
                  'status': 'Модерация'})
    # if order:
    print('order', order)

    # state_process = data.get('state_process')
    # state_msg: tuple[str, str] = data.get('state_msg')
    # state_msg: types.Message = data.get('state_msg')
    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')
    # chat_id, message_id = main_menu_msg

    await state.update_data(state_msg=None)

    # username = callback.message.from_user.username
    # username_from_callback = callback.from_user.username

    # kb = create_start_keyboard(callback.from_user.id)

    Order = Base.classes.general_models_customorder

    # session.execute(insert(Order).values(order))
    # session.commit()

    with session as session:

        new_order = Order(**order)  # предполагая, что order — это словарь
        session.add(new_order)
        session.commit()

        session.refresh(new_order)

    print(new_order.__dict__)

    user_id = new_order.guest_id
    order_id = new_order.id
    marker = 'swift/sepa'

    # _text = 'Ваша заявка успешно отправлена!' if select_language == 'ru'\
    #              else 'your request has been sent successfully!'
    if select_language == 'ru':
        _text = '⏳ Ваша заявка успешно принята. При положительном решении Вам будет отправлена ссылка на вступление в чат с персональным менеджером от нашей партнерской компании, который будет сопровождать ваш перевод'
    else:
        _text = '⏳ Your request has been successfully accepted. If the decision is positive, you will be sent a link to join the chat with a personal manager from our partner company, who will accompany your transfer'

    await callback.answer(text=_text,
                          show_alert=True)
    
    await start(callback,
                session,
                state,
                bot,
                text_msg='Главное меню')

    _url = f'https://api.moneyswap.online/send_to_tg_group?user_id={user_id}&order_id={order_id}&marker={marker}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                               timeout=timeout) as response:
            pass




# @main_router.callback_query(F.data == 'start_swift_sepa')
# async def start_swift_sepa(callback: types.CallbackQuery,
#                            state: FSMContext,
#                            bot: Bot):
#     data = await state.get_data()
#     await state.set_state(SwiftSepaStates.request_type)
#     await state.update_data(order=dict())

#     swift_start_kb = create_swift_start_kb()
#     kb = add_cancel_btn_to_kb(swift_start_kb)

#     main_menu_msg: tuple[str,str] = data.get('main_menu_msg')

#     # print('has_main_menu_msg?', bool(main_menu_msg))

#     # if main_menu_msg:
#     #     try:
#     #         await bot.delete_message(*main_menu_msg)
#     #         # await main_menu_msg.delete()
#     #     except Exception:
#     #         pass

#     # state_msg = await message.answer('<b>Выберите тип заявки</b>',
#     #                      reply_markup=kb.as_markup())
#     await bot.edit_message_text(text='<b>Выберите тип заявки</b>',
#                                 reply_markup=kb.as_markup())
    
#     # state_data_message = (state_msg.chat.id, state_msg.message_id)
    
#     # await state.update_data(state_msg=state_data_message)
#     # # await state.update_data(username=message.from_user.username)
#     # await message.delete()



@main_router.callback_query(F.data.in_(('pay_payment', 'access_payment')))
async def request_type_state(callback: types.CallbackQuery,
                             session: Session,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()

    # state_process = data.get('state_process')
    state_msg = data.get('state_msg')
    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    # language_code = callback.from_user.language_code
    # data = await state.get_data()

    # if not data.get('order'):
    #     await callback.answer(text='Что то пошло не так, попробуйте еще раз.')
    #     await state.clear()

    #     await start(callback,
    #                 session,
    #                 state,
    #                 bot,
    #                 text_msg='Главное меню')
    #     return

    # state_msg: tuple[str, str] = data.get('state_msg')
    # chat_id, message_id = state_msg
    # state_msg: types.Message = data.get('state_msg')
    # main_menu_msg: tuple[str,str] = data.get('main_menu_msg')
    # chat_id, message_id = main_menu_msg
    # chat_id = callback.message.chat.id
    # message_id = callback.message.message_id
    chat_id, message_id = state_msg

    request_type = 'Оплатить платеж' if callback.data == 'pay_payment' else 'Принять платеж'
    # _text = '<b>Введите сумму и валюту платежа</b>\n\n⚠️ <u>Внимание: минимальная сумма платежа составляет 3000$.</u>' if select_language == 'ru'\
    #              else '<b>Input payment and valute amount</b>\n\n⚠️ <u>Please note: the minimum payment amount is 3000$</u>'

    if select_language == 'ru':
        state_process = f'\nТип заявки: {request_type}'
        # _text = f'{state_process}\n\n<b>Подробно опишите перевод</b>\n\n<u>Укажите все необходимые детали: из какой страны и в какую осуществляется перевод, назначение платежа и любые другие значимые детали.</u>'
        _text = f'{state_process}\n\n<b>Введите сумму и валюту платежа</b>\n\n⚠️ <u>Внимание: минимальная сумма платежа составляет 3000$.</u>'
    else:
        request_dict = {
            'Оплатить платеж': 'Make a Payment',
            'Принять платеж': 'Receive a Payment',
        }
        state_process = f'\nRequest Type: {request_dict.get(request_type)}'
        # _text = f'{state_process}\n\n<b>Describe your request in detail</b>\n\n<u>Please provide all necessary details: from and to which country the transfer is made, the purpose of the payment and any other significant details.</u>'
        _text = f'{state_process}\n\n<b>Input payment and valute amount</b>\n\n⚠️ <u>Please note: the minimum payment amount is 3000$</u>'
    #
    order = data.get('order')
    order['request_type'] = request_type

    await state.update_data(order=order,
                            state_process=state_process,
                            request_type=callback.data)
    # await state.update_data(state_process=state_process)
    # await state.update_data(request_type=callback.data)
    # await state.update_data(state_msg=(chat_id, message_id))
    #
    # username_from_state = data.get('username')
    # print(username_from_state)
    # #
    # print(callback.message.from_user.username)
    # print(callback.from_user.username)
    # await state.update_data(username=callback.message.from_user.username)
    #
    # print(state_msg)

    # await state.update_data(proccess_msg=(chat_id, message_id))

    # await state.set_state(SwiftSepaStates.country)
    await state.set_state(SwiftSepaStates.amount)

    kb = add_cancel_btn_to_kb(select_language)

    #
    # await bot.edit_message_text(f'{state_process}\n<b>Введите страну...</b>',
    #                             chat_id=chat_id,
    #                             message_id=message_id,
    #                             reply_markup=kb.as_markup())
    #

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())

    # await state_msg.edit_text(f'{state_process}\n<b>Введите страну...</b>',
    #                           reply_markup=kb.as_markup())
    try:
        await callback.answer()
    except Exception:
        pass
    # await callback.message.answer('Введите страну...')

    # await callback.message.delete()


@main_router.message(SwiftSepaStates.country)
async def country_state(message: types.Message,
                        session: Session,
                        state: FSMContext,
                        bot: Bot):
    language_code = message.from_user.language_code
    data = await state.get_data()

    # if not data.get('order') or not data.get('proccess_msg'):
    #     await message.answer(text='Что то пошло не так, попробуйте еще раз.')
    #     await state.clear()

    #     await start(message,
    #                 session,
    #                 state,
    #                 bot,
    #                 text_msg='Главное меню')
    #     return
    # state_msg: tuple[str, str] = data.get('state_msg')
    # chat_id, message_id = state_msg
    state_msg: tuple[str,str] = data.get('state_msg')
    chat_id, message_id = state_msg

    # state_msg: types.Message = data.get('state_msg')
    await state.update_data(country=message.text)

    #
    order = data.get('order')
    order['country'] = message.text
    await state.update_data(order=order)
    #

    state_process = data.get('state_process')
    state_process += f'\nСтрана: {message.text}'
    await state.update_data(state_process=state_process)

    await state.set_state(SwiftSepaStates.amount)

    kb = add_cancel_btn_to_kb(language_code)

    #
    await bot.edit_message_text(f'{state_process}\n<b>Введите сумму...</b>',
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    #

    # await state_msg.edit_text(f'{state_process}\n<b>Введите сумму...</b>',
    #                           reply_markup=kb.as_markup())
    # await message.answer('Введите сумму...')

    await message.delete()


@main_router.message(SwiftSepaStates.amount)
async def amount_state(message: types.Message,
                       session: Session,
                       state: FSMContext,
                       bot: Bot):
    # language_code = message.from_user.language_code
    
    data = await state.get_data()
    
    select_language = data.get('select_language')
    state_msg: tuple[str,str] = data.get('state_msg')
    state_process: tuple[str,str] = data.get('state_process')
    chat_id, message_id = state_msg

    #validation
    amount_text = message.text.strip()

    if not validate_amount(amount_text):
        await state.set_state(SwiftSepaStates.amount)

        if select_language == 'ru':
            validation_text = f'\n\n❗️Некорректные данные (передано - {amount_text})\n\nВведите корректное значение (Пример формата: 3000$, $3000, 3000 $, 3000 usd, 3000 долларов)'
        else:
            validation_text = f'\n\n❗️Incorrect data (send - {amount_text})\n\nPlease enter a correct value (Example format: 3000$, $3000, 3000 $, 3000 usd, 3000 dollars)'
        # await state.update_data(validation_text=validation_text)
        _text = state_process + f'<b>{validation_text}</b>'
        
        kb = add_cancel_btn_to_kb(select_language)
        
        try:
            await bot.edit_message_text(text=_text,
                                            chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=kb.as_markup())
        except Exception as ex:
            print(ex)
            pass
        try:
            await message.delete()
        except Exception as ex:
            print(ex)
        
        return
        # возвращаемся к этому же шагу

    if select_language == 'ru':
        state_process += f'\nСумма: {message.text}'
        # _text = f'{state_process}\n\n<b>Выберите тип заявки</b>'
        _text = f'{state_process}\n\n<b>Подробно опишите перевод</b>\n\n<u>Укажите все необходимые детали: из какой страны и в какую осуществляется перевод, назначение платежа и любые другие значимые детали.</u>'
    else:
        # request_dict = {
        #     'Оплатить платеж': 'Make a Payment',
        #     'Принять платеж': 'Receive a Payment',
        # }
        state_process += f'\nAmount: {message.text}'
        # _text = f'{state_process}\n\n<b>Choose request type</b>'
        _text = f'{state_process}\n\n<b>Describe your request in detail</b>\n\n<u>Please provide all necessary details: from and to which country the transfer is made, the purpose of the payment and any other significant details.</u>'

    order = data.get('order')
    order['amount'] = message.text

    await state.update_data(order=order,
                            amount=message.text,
                            state_process=state_process)
    # await state.update_data(amount=message.text)
    # await state.update_data(state_process=state_process)

    # state_process = data.get('state_process')
    # state_process += f'\nСумма: {message.text}'

    # await state.set_state(SwiftSepaStates.task_text)
    await state.set_state(SwiftSepaStates.task_text)

    # kb = create_swift_start_kb(select_language)
    kb = add_cancel_btn_to_kb(select_language)

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    #

    # await state_msg.edit_text(f'{state_process}\n<b>Опишите задачу, чтобы менеджеры могли быстрее все понять и оперативно начать выполнение...</b>',
    #                           reply_markup=kb.as_markup())
    # await message.answer('Напишите подробности операции...')

    await message.delete()


@main_router.message(SwiftSepaStates.task_text)
async def task_text_state(message: types.Message,
                          session: Session,
                          state: FSMContext,
                          bot: Bot,
                          api_client: Client):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    state_msg: tuple[str,str] = data.get('state_msg')
    chat_id, message_id = state_msg

    await state.update_data(task_text=message.text)

    order = data.get('order')
    order['comment'] = message.text
    await state.update_data(order=order)

    state_process = data.get('state_process')

    if select_language == 'ru':
        state_process += f'\nКомментарий: {message.text}'
        state_done_text = 'Заполнение окончено.'
    else:
        state_process += f'\nComment: {message.text}'
        state_done_text = 'Request is done.'

    await state.update_data(state_process=state_process)

    # preview_response_text = await swift_sepa_data(state)

    kb = create_kb_to_main(select_language)

    # async with api_client as app:
    #     channel = await app.create_channel(title='Test111')
    #     chat_link = await app.create_chat_invite_link(channel.id)

    # print(channel)
    # print(channel.__dict__)
    # print(chat_link.invite_link)


    # chat_link = await bot.create_chat_invite_link(chat_id=channel.id,
    #                                   name='test_link')
    
    # await message.answer(text=chat_link.invite_link)

    #
    await bot.edit_message_text(f'{state_process}\n\n<b>{state_done_text}</b>',
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    #

    # await state_msg.edit_text(f'{state_process}\n<b>Заполнение окончено.</b>',
    #                           reply_markup=kb.as_markup())
    # await message.answer(f'Ваша заявка:\n{preview_response_text}',
    #                      reply_markup=kb.as_markup())
    
    await message.delete()


@main_router.message(Command('send'))
async def send(message: types.Message,
               session: Session,
               bot: Bot):
    MassSendMessage = Base.classes.general_models_masssendmessage

    mass_message = session.query(MassSendMessage).options(joinedload(MassSendMessage.general_models_masssendimage_collection),
                                                      joinedload(MassSendMessage.general_models_masssendvideo_collection)).first()

    print(mass_message.general_models_masssendimage_collection)
    for q in mass_message.general_models_masssendimage_collection:
        print(q.__dict__)
    print(mass_message.general_models_masssendvideo_collection)
    for w in mass_message.general_models_masssendvideo_collection:
        print(w.__dict__)

    await try_add_file_ids_to_db(message,
                                 session,
                                 bot,
                                 mass_message)
    
    # session.refresh(mass_message)
    session.expire_all()

    print('22')
    for q in mass_message.general_models_masssendimage_collection:
        print(q.__dict__)
    print(mass_message.general_models_masssendvideo_collection)
    for w in mass_message.general_models_masssendvideo_collection:
        print(w.__dict__)

    # print(MassSendMessage)
    # print(MassSendMessage.__dict__)

    # os_path = os.path.dirname(os.path.abspath(__file__))

    # print(os_path)

    # valutes = session.query(Valutes).all()
    # messages = session.query(MassSendMessage).all()
    # MassSendImage = Base.classes.general_models_masssendimage
    # images = session.query(MassSendImage).all()

    # mass_message = session.query(MassSendMessage).options(joinedload(MassSendMessage.general_models_masssendimage_collection),
    #                                                   joinedload(MassSendMessage.general_models_masssendvideo_collection)).first()
   
    # for m in messages:
    #     # images = select(MassSendMessage).options(joinedload(MassSendMessage.images))
    #     # print(v.__dict__)
    #     # for i in m.general_models_masssendimage_collection:
    #     #     print(i.__dict__)
    #     images = [(image.id, image.file_id, types.InputMediaPhoto(media=types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{image.image}'))) for image in m.general_models_masssendimage_collection]
    #     update_image_list = []
    #     for image in images:
    #         if image[1] is None:
    #             # upload image to telegram server
    #             loaded_image = await message.answer_photo(image[-1].media)
    #             # delete image message from chat
    #             await bot.delete_message(message.chat.id, message.message_id)
    #             image_file_id = loaded_image.photo[0].file_id
    #             print(image[0], image_file_id)
    #             image_dict = {
    #                 'id': image[0],
    #                 'file_id': image_file_id,
    #             }
    #             update_image_list.append(image_dict)
    #         else:
    #             print('из БД', image[1])
    #     if update_image_list:
    #         session.bulk_update_mappings(
    #             MassSendImage,
    #             update_image_list,
    #         )
    #         session.commit()
    #         session.flush(MassSendMessage.general_models_masssendimage_collection)
    mass_message_text: str = mass_message.content
    print(mass_message_text)
    mass_message_text: str = mass_message_text.replace('<p>','')\
                                                .replace('</p>', '\n')\
                                                .replace('<br>', '')\
                                                .replace('<p class="">', '')\
                                                # .replace('<span', '<span class="tg-spoiler"')

    print(mass_message_text)

    images = [types.InputMediaPhoto(media=image.file_id) for image in mass_message.general_models_masssendimage_collection]
    videos = [types.InputMediaVideo(media=video.file_id) for video in mass_message.general_models_masssendvideo_collection]
    mb = MediaGroupBuilder(images+videos, caption=mass_message_text)
    
    files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
    mb_files = MediaGroupBuilder(files)
    # mb.build()
        # for image in m.general_models_masssendimage_collection:
        #     if image.file_id is None:

        #     image_id = await message.answer_photo(image.media)
        #     print(image_id)
        #     print('ID',image_id.photo[0].file_id)
        # images = [types.InputMediaPhoto(media=f'http://localhost:8000/django/media/{image.image}') for image in m.general_models_masssendimage_collection]
        # print(images)
        # videos = [types.InputMediaVideo(media=types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{video.video}')) for video in m.general_models_masssendvideo_collection]
        # for v in videos:
            # await message.answer_video(v.media)
            # video_id = await message.answer_video('BAACAgIAAxkDAAOTZl79M00aHNBaYsc4gNk6znwWiQ4AAhFPAALje_hKCvWrvLSuzxY1BA')
            # print(video_id)
            # print('ID',video_id.video.file_id)
        # videos = [types.InputMediaVideo(media=video.video) for video in m.general_models_masssendvideo_collection]
        # print(videos)

    # await message.answer_photo('https://img.freepik.com/free-photo/view-of-3d-adorable-cat-with-fluffy-clouds_23-2151113419.jpg')
    
    await message.answer_media_group(media=mb.build())
    await message.answer_media_group(media=mb_files.build())
    


# @main_router.message(F.video)
# async def add_photo(message: types.Message,
#                     session: Session,
#                     bot: Bot):
#     video = message.video
#     MassSendVideo = Base.classes.general_models_masssendvideo

#     session.execute(insert(MassSendVideo).values({'file_id': video.file_id,
#                                                   'video': video.file_name,
#                                                   'messsage_id': 1}))
#     session.commit()

#     await message.delete()

async def send_mass_message_test(bot: Bot,
                            session: Session,
                            user_id: int,
                            name_send: str):
        with session as session:
            Guest = Base.classes.general_models_guest
            # session: Session

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage
            # mass_message = session.query(MassSendMessage)\
            #                         .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
            #                                  joinedload(MassSendMessage.general_models_masssendvideo_collection))\
            #                         .first()
            mass_message = session.query(MassSendMessage)\
                                    .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
                                             joinedload(MassSendMessage.general_models_masssendvideo_collection))\
                                    .where(MassSendMessage.name == name_send).first()

            # try add file_id for each related file passed object
            await try_add_file_ids(bot, session, mass_message)
            # refresh all DB records
            session.expire_all()

            mass_message_text: str = mass_message.content
            print(mass_message_text)
            # validate content text
            mass_message_text: str = mass_message_text.replace('<p>','')\
                                                        .replace('</p>', '\n')\
                                                        .replace('<br>', '')\
                                                        .replace('<p class="">', '')\
                                                        .replace('&nbsp;', ' ')\
                                                        # .replace('<span>', '')\
                                                        # .replace('</span>', '')   

            # print(mass_message_text)

            images = [types.InputMediaPhoto(media=image.file_id) for image in mass_message.general_models_masssendimage_collection]
            videos = [types.InputMediaVideo(media=video.file_id) for video in mass_message.general_models_masssendvideo_collection]
            
            #test for moneyswap team
            # query = (
            #     select(Guest)\
            #     .where(Guest.tg_id.in_([60644557,
            #                             350016695,
            #                             471715294,
            #                             311364517,
            #                             283163508,
            #                             5047108619,
            #                             561803366,
            #                             686339126,
            #                             620839543,
            #                             375236081,

            #     ]))
            # )
            
            #test for me only
            query = (
                select(Guest)\
                .where(Guest.tg_id == user_id)
            )

            # mass_send for all guests
            # query = (select(Guest))


# [60644557,
#                                         471715294,
#                                         561803366,
#                                         686339126,
#                                         283163508,
#                                         283163508,
#                                         311364517]

            res = session.execute(query)

            guests = res.fetchall()

            # print(guests)

            image_video_group = None
            if list(images+videos):
                image_video_group = MediaGroupBuilder(images+videos, caption=mass_message_text)
            
            files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
            file_group = None
            if files:
                file_group = MediaGroupBuilder(files)

            # try:
            for guest in guests:
                try:
                    guest = guest[0]
                    _tg_id = guest.tg_id
                    if image_video_group is not None:
                        mb1 = await bot.send_media_group(_tg_id, media=image_video_group.build())
                        # print('MB1', mb1)
                    else:
                        await bot.send_message(_tg_id,
                                            text=mass_message_text)
                    if file_group is not None:
                        mb2 = await bot.send_media_group(_tg_id, media=file_group.build())    
                        # print('MB2', mb2)
                    # guest = session.query(Guest).where(Guest.tg_id == '350016695').first()
                    if not guest.is_active:
                        session.execute(update(Guest).where(Guest.tg_id == _tg_id).values(is_active=True))
                        # session.commit()
                except Exception as ex:
                    print(ex)
                    if guest.is_active:
                        session.execute(update(Guest).where(Guest.tg_id == _tg_id).values(is_active=False))
                    # session.commit()
                finally:
                    await sleep(0.3)
            
            try:
                session.commit()
            except Exception as ex:
                session.rollback()
                print('send error', ex)
            
            session.close()




async def send_mass_message(bot: Bot,
                            session: Session,
                            name_send: str):
        start_send_time = time.time()

        with session as session:
            Guest = Base.classes.general_models_guest
            # session: Session

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage
            # mass_message = session.query(MassSendMessage)\
            #                         .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
            #                                  joinedload(MassSendMessage.general_models_masssendvideo_collection))\
            #                         .first()
            mass_message = session.query(MassSendMessage)\
                                    .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
                                             joinedload(MassSendMessage.general_models_masssendvideo_collection))\
                                    .where(MassSendMessage.name == name_send).first()

            # try add file_id for each related file passed object
            await try_add_file_ids(bot, session, mass_message)
            # refresh all DB records
            session.expire_all()

            mass_message_text: str = mass_message.content
            # print(mass_message_text)
            # validate content text
            mass_message_text: str = mass_message_text.replace('<p>','')\
                                                        .replace('</p>', '\n')\
                                                        .replace('<br>', '')\
                                                        .replace('<p class="">', '')\
                                                        .replace('&nbsp;', ' ')
                                                        # .replace('<span', '<span class="tg-spoiler"')

            # print(mass_message_text)

            images = [types.InputMediaPhoto(media=image.file_id) for image in mass_message.general_models_masssendimage_collection]
            videos = [types.InputMediaVideo(media=video.file_id) for video in mass_message.general_models_masssendvideo_collection]
            
            #test for moneyswap team
            # query = (
            #     select(Guest)\
            #     .where(Guest.tg_id.in_([60644557,
            #                             350016695,
            #                             471715294,
            #                             311364517,
            #                             283163508,
            #                             5047108619,
            #                             561803366,
            #                             686339126,
            #                             620839543,
            #                             375236081,

            #     ]))
            # )
            
            #test for me only
            # query = (
            #     select(Guest)\
            #     .where(Guest.tg_id.in_([686339126]))
            # )

            # mass_send for all guests
            query = (select(Guest))


# [60644557,
#                                         471715294,
#                                         561803366,
#                                         686339126,
#                                         283163508,
#                                         283163508,
#                                         311364517]

            res = session.execute(query)

            guests = res.fetchall()

            start_users_count = len([guest for guest in guests if guest[0].is_active == True])

            # print(guests)

            image_video_group = None
            if list(images+videos):
                image_video_group = MediaGroupBuilder(images+videos, caption=mass_message_text)
            
            files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
            file_group = None
            if files:
                file_group = MediaGroupBuilder(files)

            # try:
            for guest in guests:
                try:
                    guest = guest[0]
                    _tg_id = guest.tg_id
                    if image_video_group is not None:
                        mb1 = await bot.send_media_group(_tg_id, media=image_video_group.build())
                        # print('MB1', mb1)
                    else:
                        await bot.send_message(_tg_id,
                                            text=mass_message_text)
                    if file_group is not None:
                        mb2 = await bot.send_media_group(_tg_id, media=file_group.build())    
                        # print('MB2', mb2)
                    # guest = session.query(Guest).where(Guest.tg_id == '350016695').first()
                    if not guest.is_active:
                        session.execute(update(Guest).where(Guest.tg_id == _tg_id).values(is_active=True))
                        # session.commit()
                except Exception as ex:
                    print(ex)
                    if guest.is_active:
                        session.execute(update(Guest).where(Guest.tg_id == _tg_id).values(is_active=False))
                    # session.commit()
                finally:
                    await sleep(0.3)
            
            end_send_time = time.time()
            
            try:
                session.commit()
                _text = ''
            except Exception as ex:
                session.rollback()
                _text = ''
                print('send error', ex)
            finally:
                execute_time = end_send_time - start_send_time

                # query = (
                #     select(
                #         Guest.id
                #     )\
                #     .where(Guest.is_active == False)
                # )

                end_active_users_count = session.query(Guest.tg_id).where(Guest.is_active == True).count()

                try:
                    _url = f'https://api.moneyswap.online/send_mass_message_info?execute_time={execute_time}&start_users_count={start_users_count}&end_users_count={end_active_users_count}'
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(_url,
                                            timeout=timeout) as response:
                            pass
                except Exception as ex:
                    print(ex)
                    pass
            session.close()


async def try_send_order(bot: Bot,
                         session: Session,
                         user_id: int,
                         order_id: int,
                         order_status: str | None):
    with session as session:
        CustomOrder = Base.classes.general_models_customorder
        Guest = Base.classes.general_models_guest

        query = (
            select(
                CustomOrder,
                Guest,
            )\
            .join(Guest,
                  CustomOrder.guest_id == Guest.tg_id)\
            .where(
                CustomOrder.guest_id == user_id,
                CustomOrder.id == order_id,
            )
        )

        res = session.execute(query)

        order = res.fetchall()
        print(order)

    if order:
        order, guest = order[0]
        chat_link = guest.chat_link
        language_code = guest.language_code

        print(order.__dict__)
        
        if order_status is not None and order_status == 'reject':
            if language_code == 'ru':
                _text = '❌ <b>Заявка отклонена</b>\n\nК сожалению, Ваша заявка отклонена. Мы не сможем осуществить данный перевод.'
            else:
                _text = '❌ <b>Request rejected</b>\n\nUnfortunately, your request has been rejected. We will not be able to complete this transfer.'

            try:
                await bot.send_message(chat_id=user_id,
                                       text=_text)
            # except TelegramForbiddenError as ex:
            #     print(ex)
            except Exception as ex:
                print(ex)
            
            return
        # else:

        if chat_link is None:
            print('делаю пост запрос')

            # body = f'''"tg_id": {order['guest_id']}, "type": "{order['request_type']}", "country": "{order['country']}", "sum": "{order['amount']}", "comment": "{order['comment']}", "time_create": {order['time_create'].timestamp()}'''

            # body = f'''"tg_id": {order.guest_id}, "type": "{order.request_type}", "country": "{order.country}", "sum": "{order.amount}", "comment": "{order.comment}", "time_create": {order.time_create.timestamp()}'''
            # json_order = {
            #     "order": '{' + body + '}'
            # }
            body = {'comment': f'Тип заявки: {order.request_type} | Сумма: {order.amount} | Коммент: {order.comment}'}

            json_order = json.dumps(body,
                                    ensure_ascii=False)

            print('json', json_order)
        
            async with aiohttp.ClientSession() as aiosession:
                response = await aiosession.post(url='https://api.moneyport.ru/api/partners/create-order',
                                            data=json_order,
                                            headers={'Authorization': f'Bearer {BEARER_TOKEN}',
                                                    'CONTENT-TYPE': 'application/json'})
                response_json = await response.json()
                
            chat_link = response_json.get('chat')

            if chat_link is not None:
                chat_link = chat_link.get('url')

                session.execute(update(Guest)\
                                .where(Guest.tg_id == user_id)\
                                .values(chat_link=chat_link))
                # guest.chat_link = chat_link
                session.commit()
            else:
                print('не получилось отправить, проблема на стороне MoneyPort')
                try:
                    result_text = f'❌Сообщение с ссылкой на MoneyPort не получилось отправить пользователю {user_id}, проблема на стороне MoneyPort'
                    
                    # if user_id == 686339126:
                    #     _url = f'https://api.moneyswap.online/test_send_result_chat_link?result_text={result_text}' 
                    # else:
                    _url = f'https://api.moneyswap.online/send_result_chat_link?result_text={result_text}'
                    
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(_url,
                                            timeout=timeout) as response:
                            pass
                except Exception as ex:
                    print(ex)
                    pass

                return {'status': 'error'}
        else:
            print('ссылка из базы', guest.chat_link)

        # chat_link_text = f'Ссылка на чат по Вашему обращению -> {chat_link}\n\n<i>*Можете удалить это сообщение, чтобы не портить вид чата, мы будем дублировать ссылку на чат в главном сообщении.</i>'
        if language_code == 'ru':
            chat_link_text = f'✅ <b>Заявка одобрена</b>\n\nВаша заявка успешно прошла проверку. Для обсуждения деталей вступите в чат с персональным менеджером нашей партнерской компании → {chat_link}'
        else:
            chat_link_text = f'✅ <b>Request approved</b>\n\nYour request has been successfully verified. To discuss details, join the chat with the personal manager of our partner company → {chat_link}'

        try:
            await bot.send_message(chat_id=user_id,
                                   text=chat_link_text)
        except TelegramForbiddenError as ex:
            print(ex)
            try:
                result_text = f'❌Сообщение с ссылкой на MoneyPort пользователю {user_id} не было доставлено (Пользователь заблокировал бота)'
                
                # if user_id == 686339126:
                #     _url = f'https://api.moneyswap.online/test_send_result_chat_link?result_text={result_text}'                    
                # else:
                _url = f'https://api.moneyswap.online/send_result_chat_link?result_text={result_text}'
                
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession() as session:
                    async with session.get(_url,
                                        timeout=timeout) as response:
                        pass
            except Exception as ex:
                print(ex)
                pass
            else:
                return {'status': 'error'}

        except Exception as ex:
            print(ex)
            print('Cообщение с ссылкой на чат не было отправлено.')
            # отправляю уведомление в бота уведолмений об ошибке
            try:
                result_text = f'❌Сообщение с ссылкой на MoneyPort пользователю {user_id} не было доставлено'
                
                # if user_id == 686339126:
                #     _url = f'https://api.moneyswap.online/test_send_result_chat_link?result_text={result_text}' 
                # else:
                _url = f'https://api.moneyswap.online/send_result_chat_link?result_text={result_text}'
                
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession() as session:
                    async with session.get(_url,
                                        timeout=timeout) as response:
                        pass
            except Exception as ex:
                print(ex)
                pass
            else:
                return {'status': 'error'}
        else:
            print('Cообщение с ссылкой на чат успешно отправлено.')
            # отправляю уведомление в бота уведолмений об успешной отправке ссылки на MoneyPort чат
            try:
                result_text = f'✅Сообщение с ссылкой на MoneyPort чат успешно отправлено пользователю {user_id}'
                
                # if user_id == 686339126:
                #     _url = f'https://api.moneyswap.online/test_send_result_chat_link?result_text={result_text}' 
                # else:
                _url = f'https://api.moneyswap.online/send_result_chat_link?result_text={result_text}'

                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession() as session:
                    async with session.get(_url,
                                        timeout=timeout) as response:
                        pass
            except Exception as ex:
                print(ex)
                pass
            else:
                return {'status': 'success'}



# @main_router.message(F.text == 'send_link22')
# async def send_link_test(message: types.Message,
#                                 session: Session,
#                                 state: FSMContext,
#                                 bot: Bot):
#     _text = 'Добрый день.\nПолучили от вас запрос на помощь в покупке квартиры в Таиланде.\nДля вас создан чат для продолжения консультации по вопросу https://t.me/+7JWLAnMKyUUwMWEy'
    
#     # guest
#     _chat_id = 7327884297


#     # sugar
#     # _chat_id = 293371619


#     # me
#     # _chat_id = 686339126
#     try:
#         await bot.send_message(chat_id=_chat_id,
#                                 text=_text)
#     except Exception as ex:
#         print('send error', ex)
#     else:
#         print('message sent successfully')
#     try:
#         await message.delete()
#     except Exception as ex:
#         print(ex)



@main_router.message()
async def ignore_any_message(message: types.Message):
    try:
        await message.delete()
    except Exception as ex:
        print(ex)