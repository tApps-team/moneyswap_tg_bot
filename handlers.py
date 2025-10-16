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

from sqlalchemy.orm import Session, joinedload, sessionmaker, selectinload
from sqlalchemy import insert, select, update, and_

from config import BEARER_TOKEN, FEEDBACK_REASON_PREFIX

from keyboards import (create_add_comment_kb, create_add_review_kb, create_dev_kb, create_kb_for_exchange_admin_comment, create_kb_for_exchange_admin_review, create_partner_site_kb, create_start_keyboard,
                       create_start_inline_keyboard, create_swift_condition_kb,
                       create_swift_start_kb,
                       add_cancel_btn_to_kb,
                       create_kb_to_main,
                       create_swift_sepa_kb,
                       create_support_kb,
                       create_feedback_form_reasons_kb, new_create_add_comment_kb, new_create_add_review_kb,
                       new_create_kb_for_exchange_admin_comment,
                       new_create_kb_for_exchange_admin_review,
                       reason_dict,
                       create_feedback_confirm_kb,
                       create_condition_kb,
                       add_switch_language_btn)

from states import SwiftSepaStates, FeedbackFormStates

from utils.handlers import get_exchange_name, new_get_exchange_data, new_try_activate_admin_exchange, new_try_activate_partner_admin_exchange, try_activate_admin_exchange, try_activate_partner_admin_exchange, try_add_file_ids_to_db, try_add_file_ids, swift_sepa_data, validate_amount
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
    comment_msg_dict = None
    activate_admin_exchange = None
    partner_activate_admin_exchange = None

    new_review_msg_dict = None
    new_comment_msg_dict = None
    new_activate_admin_exchange = None
    new_partner_activate_admin_exchange = None

    is_callback = isinstance(message, types.CallbackQuery)

    # _start_text = start_text
    _start_text = start_text_dict.get('ru') if select_language == 'ru'\
          else start_text_dict.get('en')
    
    utm_source = None

    if isinstance(message, types.Message):
        query_param = message.text.split()

        if len(query_param) > 1:
            utm_source = query_param[-1]

            if utm_source == 'get_id':
                _text = f'ID Вашего профиля: <b>{message.from_user.id}</b>'
                try:
                    await message.answer(text=_text)
                    await message.delete()
                except Exception as ex:
                    print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
                    return
                return

            if utm_source.startswith('review'):
                params = utm_source.split('__')

                if len(params) != 2:
                    if select_language == 'ru':
                        _text = 'Не удалось найти обменник на отзыв, некорректные данные в url'
                    else:
                        _text = 'Exchange to add review not found, uncorrect data in url'
                    try:
                        await bot.send_message(chat_id=message.from_user.id,
                                            text=_text)
                        await message.delete()
                    except Exception as ex:
                        print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
                        return
                    return
                
                review_msg_dict = {
                    # 'marker': params[1],
                    'exchange_name': params[-1],
                }

                utm_source = 'from_site'

            elif utm_source.startswith('new_review'):
                params = utm_source.split('__')

                if len(params) != 2:
                    if select_language == 'ru':
                        _text = 'Не удалось найти обменник на отзыв, некорректные данные в url'
                    else:
                        _text = 'Exchange to add review not found, uncorrect data in url'
                    try:
                        await bot.send_message(chat_id=message.from_user.id,
                                            text=_text)
                        await message.delete()
                    except Exception as ex:
                        print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
                        return
                    return
                
                new_review_msg_dict = {
                    # 'marker': params[1],
                    'exchange_id': params[-1],
                }

                utm_source = 'from_site'

            elif utm_source.startswith('comment'):
                params = utm_source.split('__')

                if len(params) != 3:
                    if select_language == 'ru':
                        _text = 'Не удалось найти обменник на комментарий, некорректные данные в url'
                    else:
                        _text = 'Exchange to add comment not found, uncorrect data in url'
                    try:
                        await bot.send_message(chat_id=message.from_user.id,
                                            text=_text)
                        await message.delete()
                    except Exception as ex:
                        print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
                        return
                    return
                
                comment_msg_dict = {
                    # 'marker': params[1],
                    'exchange_name': params[1],
                    'review_id': params[-1],
                }

                utm_source = 'from_site'

            elif utm_source.startswith('new_comment'):
                params = utm_source.split('__')

                if len(params) != 3:
                    if select_language == 'ru':
                        _text = 'Не удалось найти обменник на комментарий, некорректные данные в url'
                    else:
                        _text = 'Exchange to add comment not found, uncorrect data in url'
                    try:
                        await bot.send_message(chat_id=message.from_user.id,
                                            text=_text)
                        await message.delete()
                    except Exception as ex:
                        print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
                        return
                    return
                
                new_comment_msg_dict = {
                    # 'marker': params[1],
                    'exchange_id': params[1],
                    'review_id': params[-1],
                }

                utm_source = 'from_site'
            
            elif utm_source.startswith('admin'):
                activate_admin_exchange = True
                utm_source = 'from_admin_activate'

            elif utm_source.startswith('new_admin'):
                new_activate_admin_exchange = True
                utm_source = 'from_admin_activate'

            elif utm_source.startswith('new_partner_admin'):
                new_partner_activate_admin_exchange = True
                utm_source = 'from_partner_admin_activate'

            elif utm_source.startswith('partner_admin'):
                partner_activate_admin_exchange = True
                utm_source = 'from_partner_admin_activate'
            
    with session as _session:
        Guest = Base.classes.general_models_guest

        tg_id = message.from_user.id
        guest = _session.query(Guest)\
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
            _session.execute(insert(Guest).values(**value_dict))
            _session.commit()
            first_visit = True
        else:
            chat_link  = guest.chat_link
            first_visit = False

    # has_pinned_message = message.chat.pinned_message

    if review_msg_dict and not first_visit:
        with session as _session:
            exchange_data = get_exchange_name(review_msg_dict,
                                            _session)
        if exchange_data is not None:
            exchange_id, marker = exchange_data
            _kb = create_add_review_kb(exchange_id,
                                       marker,
                                       select_language).as_markup()
            # _text = f'Оставить отзыв на обменник {exchange_name}'
            if select_language == 'ru':
                _text = f'Оставить отзыв на обменник {review_msg_dict.get("exchange_name")}'
            else:
                _text = f'Add review to exchanger {review_msg_dict.get("exchange_name")}'
            # for blocked review
            blocked_add_review = (_text, exchange_id, marker)
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для отзыва'
            else:
                _text = 'Exchanger to add review not found'
            # for blocked review
            blocked_add_review = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
            await message.delete()
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked review
            await state.update_data(blocked_add_review=blocked_add_review)
            return
        return
    
    if new_review_msg_dict and not first_visit:
        with session as _session:
            exchange_data = new_get_exchange_data(new_review_msg_dict,
                                                  _session)
        if exchange_data is not None:
            exchange_id, exchange_name = exchange_data
            _kb = new_create_add_review_kb(exchange_id,
                                           select_language).as_markup()
            # _text = f'Оставить отзыв на обменник {exchange_name}'
            if select_language == 'ru':
                _text = f'Оставить отзыв на обменник {exchange_name}'
            else:
                _text = f'Add review to exchanger {exchange_name}'
            # for blocked review
            blocked_add_review = (_text, exchange_id)
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для отзыва'
            else:
                _text = 'Exchanger to add review not found'
            # for blocked review
            blocked_add_review = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
            await message.delete()
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked review
            await state.update_data(blocked_add_review=blocked_add_review)
            return
        return
    
    if comment_msg_dict and not first_visit:
        with session as _session:
            exchange_data = get_exchange_name(comment_msg_dict,
                                            _session)
        if exchange_data is not None:
            exchange_id, marker = exchange_data

            comment_msg_dict.update({'exchange_id': exchange_id,
                                     'marker': marker})
            
            _kb = create_add_comment_kb(comment_msg_dict,
                                       select_language).as_markup()

            if select_language == 'ru':
                _text = f'Оставить комментарий на обменник {comment_msg_dict.get("exchange_name")}'
            else:
                _text = f'Add comment to exchanger {comment_msg_dict.get("exchange_name")}'
            # for blocked comment
            blocked_add_comment = (_text, exchange_id, marker, comment_msg_dict.get('review_id'))
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для комментария'
            else:
                _text = 'Exchanger to add comment not found'
            # for blocked comment
            blocked_add_comment = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
            await message.delete()
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked comment
            await state.update_data(blocked_add_comment=blocked_add_comment)
            return
        return
    
    if new_comment_msg_dict and not first_visit:
        with session as _session:
            exchange_data = new_get_exchange_data(new_comment_msg_dict,
                                                  _session)
        if exchange_data is not None:
            exchange_id, exchange_name = exchange_data

            # new_comment_msg_dict.update({'exchange_id': exchange_id,
            #                          'marker': marker})
            
            _kb = new_create_add_comment_kb(new_comment_msg_dict,
                                            select_language).as_markup()

            if select_language == 'ru':
                _text = f'Оставить комментарий на обменник {exchange_name}'
            else:
                _text = f'Add comment to exchanger {exchange_name}'
            # for blocked comment
            blocked_add_comment = (_text, exchange_id, new_comment_msg_dict.get('review_id'))
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для комментария'
            else:
                _text = 'Exchanger to add comment not found'
            # for blocked comment
            blocked_add_comment = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
            await message.delete()
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked comment
            await state.update_data(blocked_add_comment=blocked_add_comment)
            return
        return

    
    elif activate_admin_exchange and not first_visit:
        with session as _session:
            has_added = try_activate_admin_exchange(message.from_user.id,
                                                    session=_session)
        
        try:
            match has_added:
                    case 'empty':
                        await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                            disable_web_page_preview=True)
                    case 'error':
                        await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                            disable_web_page_preview=True)
                    case 'exists':
                        await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                            disable_web_page_preview=True)
                    case _:
                        await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return

        try:
            await message.delete()
        except Exception:    
            pass
        
        return
    
    elif new_activate_admin_exchange and not first_visit:
        with session as _session:
            has_added = new_try_activate_admin_exchange(message.from_user.id,
                                                        session=_session)
        
        try:
            match has_added:
                    case 'empty':
                        await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                            disable_web_page_preview=True)
                    case 'error':
                        await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                            disable_web_page_preview=True)
                    case 'exists':
                        await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                            disable_web_page_preview=True)
                    case _:
                        await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return

        try:
            await message.delete()
        except Exception:    
            pass
        
        return

    elif partner_activate_admin_exchange and not first_visit:
        with session as _session:
            has_added = try_activate_partner_admin_exchange(message.from_user.id,
                                                            session=_session)
        try:
            match has_added:
                case 'empty':
                    await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                        disable_web_page_preview=True)
                case 'error':
                    await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case 'exists':
                    await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case _:
                    await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return
        try:
            await message.delete()
        except Exception:    
            pass
        
        return
    
    elif new_partner_activate_admin_exchange and not first_visit:
        with session as _session:
            has_added = new_try_activate_partner_admin_exchange(message.from_user.id,
                                                                session=_session)
        try:
            match has_added:
                case 'empty':
                    await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                        disable_web_page_preview=True)
                case 'error':
                    await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case 'exists':
                    await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case _:
                    await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return
        try:
            await message.delete()
        except Exception:    
            pass
        
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
            
            blocked_add_review: tuple = data.get('blocked_add_review')
            blocked_add_comment: tuple = data.get('blocked_add_comment')

            if blocked_add_review:
                if len(blocked_add_review) == 1:
                    _text = blocked_add_review[0]
                    _kb = None
                else:
                    _text = blocked_add_review[0]
                    _exchange_id, _marker = blocked_add_review[1:]
                    _kb = create_add_review_kb(_exchange_id,
                                               _marker,
                                               select_language).as_markup()
                await bot.send_message(chat_id=message.from_user.id,
                                       text=_text,
                                       reply_markup=_kb)
                blocked_add_review = True

            elif blocked_add_comment:
                if len(blocked_add_comment) == 1:
                    _text = blocked_add_comment[0]
                    _kb = None
                else:
                    _text = blocked_add_comment[0]
                    _exchange_id, _marker, _review_id = blocked_add_comment[1:]
                    _comment_msg_dict = {
                        'exchange_id': _exchange_id,
                        'marker': _marker,
                        'review_id': _review_id,
                    }
                    _kb = create_add_comment_kb(_comment_msg_dict,
                                               select_language).as_markup()
                await bot.send_message(chat_id=message.from_user.id,
                                       text=_text,
                                       reply_markup=_kb)
                blocked_add_comment = True

        except TelegramForbiddenError:
            return
        else:
            if isinstance(blocked_add_review, bool):
                # if data.get('blocked_add_review'):
                #     data.pop('blocked_add_review')
                await state.update_data(blocked_add_review=None)
            elif isinstance(blocked_add_comment, bool):
                # if data.get('blocked_add_comment'):
                #     data.pop('blocked_add_comment')
                await state.update_data(blocked_add_comment=None)

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
        with session as _session:
            exchange_data = get_exchange_name(review_msg_dict,
                                            _session)
        if exchange_data is not None:
            exchange_id, marker = exchange_data
            _kb = create_add_review_kb(exchange_id,
                                       marker,
                                       select_language).as_markup()
            if select_language == 'ru':
                _text = f'Оставить отзыв на обменник {review_msg_dict.get("exchange_name")}'
            else:
                _text = f'Add review to exchanger {review_msg_dict.get("exchange_name")}'
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для отзыва'
            else:
                _text = 'Exchanger to add review not found'
            # for blocked review
            blocked_add_review = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            await state.update_data(blocked_add_review=blocked_add_review)
            return
        
    if new_review_msg_dict:
        with session as _session:
            exchange_data = new_get_exchange_data(new_review_msg_dict,
                                                  _session)
        if exchange_data is not None:
            exchange_id, exchange_name = exchange_data
            _kb = new_create_add_review_kb(exchange_id,
                                           select_language).as_markup()
            # _text = f'Оставить отзыв на обменник {exchange_name}'
            if select_language == 'ru':
                _text = f'Оставить отзыв на обменник {exchange_name}'
            else:
                _text = f'Add review to exchanger {exchange_name}'
            # for blocked review
            blocked_add_review = (_text, exchange_id)
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для отзыва'
            else:
                _text = 'Exchanger to add review not found'
            # for blocked review
            blocked_add_review = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
            await message.delete()
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked review
            await state.update_data(blocked_add_review=blocked_add_review)
            return
        # return
            
    if comment_msg_dict:
        with session as _session:
            exchange_data = get_exchange_name(comment_msg_dict,
                                            _session)
        if exchange_data is not None:
            exchange_id, marker = exchange_data
            comment_msg_dict.update({'exchange_id': exchange_id,
                                     'marker': marker})
            _kb = create_add_comment_kb(comment_msg_dict,
                                       select_language).as_markup()
            # _text = f'Оставить отзыв на обменник {exchange_name}'
            if select_language == 'ru':
                _text = f'Оставить комментарий на обменник {comment_msg_dict.get("exchange_name")}'
            else:
                _text = f'Add comment to exchanger {comment_msg_dict.get("exchange_name")}'
            # for blocked comment
            blocked_add_comment = (_text, exchange_id, marker, comment_msg_dict.get('review_id'))
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для комментария'
            else:
                _text = 'Exchanger to add comment not found'
            # for blocked comment
            blocked_add_comment = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked comment
            await state.update_data(blocked_add_comment=blocked_add_comment)
            return
        try:
            await message.delete()
        except Exception:
            pass

    if new_comment_msg_dict:
        with session as _session:
            exchange_data = new_get_exchange_data(new_comment_msg_dict,
                                                  _session)
        if exchange_data is not None:
            exchange_id, exchange_name = exchange_data

            # new_comment_msg_dict.update({'exchange_id': exchange_id,
            #                          'marker': marker})
            
            _kb = new_create_add_comment_kb(new_comment_msg_dict,
                                            select_language).as_markup()

            if select_language == 'ru':
                _text = f'Оставить комментарий на обменник {exchange_name}'
            else:
                _text = f'Add comment to exchanger {exchange_name}'
            # for blocked comment
            blocked_add_comment = (_text, exchange_id, new_comment_msg_dict.get('review_id'))
        else:
            _kb = None

            if select_language == 'ru':
                _text = 'Не удалось найти обменник для комментария'
            else:
                _text = 'Exchanger to add comment not found'
            # for blocked comment
            blocked_add_comment = (_text, )
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
            await message.delete()
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked comment
            await state.update_data(blocked_add_comment=blocked_add_comment)
            return
        return

    if activate_admin_exchange:
        with session as _session:
            has_added = try_activate_admin_exchange(message.from_user.id,
                                                    session=_session)
        try:
            match has_added:
                case 'empty':
                    await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы')
                case 'error':
                    await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>')
                case 'exists':
                    await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>')
                case _:
                    await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return
        # if has_added:
        #     await message.answer(text=f'Обменник {has_added} успешно привязан к вашему профилю✅')
        # else:
        #     await message.answer(text=f'К сожалению, не смогли найти подходящую заявку на подключения, связитесь с тех.поддержкой для решения проблемы')
        try:
            await message.delete()
        except Exception:
            pass
        
        return
    
    if new_activate_admin_exchange:
        with session as _session:
            has_added = new_try_activate_admin_exchange(message.from_user.id,
                                                        session=_session)
        
        try:
            match has_added:
                    case 'empty':
                        await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                            disable_web_page_preview=True)
                    case 'error':
                        await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                            disable_web_page_preview=True)
                    case 'exists':
                        await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                            disable_web_page_preview=True)
                    case _:
                        await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return

        try:
            await message.delete()
        except Exception:    
            pass

        return
    
    if partner_activate_admin_exchange:
        with session as _session:
            has_added = try_activate_partner_admin_exchange(message.from_user.id,
                                                            session=_session)
        try:
            match has_added:
                case 'empty':
                    await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                        disable_web_page_preview=True)
                case 'error':
                    await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case 'exists':
                    await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case _:
                    await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return

        try:
            await message.delete()
        except Exception:    
            pass
        
        return
    
    if new_partner_activate_admin_exchange:
        with session as _session:
            has_added = new_try_activate_partner_admin_exchange(message.from_user.id,
                                                                session=_session)
        try:
            match has_added:
                case 'empty':
                    await message.answer(text=f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы',
                                        disable_web_page_preview=True)
                case 'error':
                    await message.answer(text=f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case 'exists':
                    await message.answer(text=f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>',
                                        disable_web_page_preview=True)
                case _:
                    await message.answer(text=f'✅Обменник {has_added} успешно привязан к вашему профилю')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return
        try:
            await message.delete()
        except Exception:    
            pass
        
        return



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


@main_router.message(Command('dev'))
async def start_swift_sepa(message: types.Message,
                           state: FSMContext,
                           bot: Bot):
    # data = await state.get_data()
    channel_id = '-1002659926226'

    photo_id = 'AgACAgIAAxkBAAEBQxpoeNJx4-N9uFiC4k0HvoatifLMugACo_IxG1l-yEuws1i2nNZ3WAEAAwIAA3MAAzYE'

    _text = '<b>Добро пожаловать в MoneySwap</b> 💱\n\nМы помогаем бизнесу проводить обмены и делать переводы по всему миру!\n\n💸 Оплатите недвижимость, машину, учебу, поставки и другие запросы с помощью MoneySwap!\n\nЧтобы подобрать надежный обменник или оформить SWIFT/SEPA-перевод, воспользуйтесь нашим <b>сайтом</b> или <b>Telegram-ботом</b>:\n\n🔺 <a href="https://t.me/MoneySwap_robot?start=business-tg">Telegram-бот MoneySwap</a>\n🔺 <a href="https://www.moneyswap.online/">Сайт MoneySwap</a>📚\n\nТакже читайте <a href="https://www.moneyswap.online/blog">блог MoneySwap</a>, где вы можете узнать больше про криптовалюты, финансы и переводы.\n\n❓ А если есть какие-то вопросы, обращайтесь в <a href="https://t.me/MoneySwap_support">Support</a> или <a href="https://t.me/moneyswap_admin">Admin</a>.\n\nНаши ресурсы:\n\n💬 <a href="https://t.me/MoneySwap_robot?start=business-tg">Telegram-бот</a> |🌐<a href="https://www.moneyswap.online/">Cайт</a> |📚<a href="https://www.moneyswap.online/blog">Блог</a> | 📝 <a href="https://dzen.ru/moneyswap">Дзен-канал</a> |💬 <a href="https://t.me/MoneySwap_support">Поддержка</a>\n\n\n<i>Напоминаем, что наша поддержка и администрация не занимаются обменом, он происходит на стороне партнеров!</i>'

    _kb = create_dev_kb()

    try:

        msg = await bot.send_photo(chat_id=channel_id,
                            photo=photo_id,
                            caption=_text,
                            reply_markup=_kb.as_markup())
        
        await bot.pin_chat_message(chat_id=channel_id,
                                message_id=msg.message_id)
    except Exception as ex:
        print(ex)
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

    
@main_router.message(F.content_type == types.ContentType.PHOTO)
async def photo_test(message: types.Message,
                    state: FSMContext,
                    bot: Bot):
    print(message.photo)
    print('*' * 10)
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
    if message.text.find('start') != -1:
        await state.clear()
        await start(message,
                    session,
                    state,
                    bot,
                    text_msg='Главное меню')
        return
        
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
    try:
        await bot.edit_message_text(text=_text,
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=feedback_confirm_kb.as_markup())
    except Exception as ex:
        print(ex)
        _msg = await bot.send_message(text=_text,
                                chat_id=chat_id,
                                    reply_markup=feedback_confirm_kb.as_markup())
        
        state_msg = (_msg.chat.id, _msg.message_id)

        await state.update_data(state_msg=state_msg)

    # await bot.edit_message_reply_markup(chat_id=chat_id,
    #                                     message_id=message_id,
    #                                     reply_markup=feedback_confirm_kb.as_markup())
    try:
        await message.delete()
    except Exception:
        pass
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

    with session as _session:

        check_query = (
            select(
                Order.id,
            )\
            .where(
                and_(
                    Order.guest_id == order['guest_id'],
                    Order.comment == order['comment'],
                    Order.time_create >= datetime.now() - timedelta(minutes=1),
                )
            )
        )

        check_res = _session.execute(check_query)

        if check_res.scalar_one_or_none():
            
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
            return
        
        new_order = Order(**order)  # предполагая, что order — это словарь
        _session.add(new_order)
        _session.commit()

        _session.refresh(new_order)

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
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.get(_url,
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


# @main_router.message(SwiftSepaStates.country)
# async def country_state(message: types.Message,
#                         session: Session,
#                         state: FSMContext,
#                         bot: Bot):
#     language_code = message.from_user.language_code
#     data = await state.get_data()

#     # if not data.get('order') or not data.get('proccess_msg'):
#     #     await message.answer(text='Что то пошло не так, попробуйте еще раз.')
#     #     await state.clear()

#     #     await start(message,
#     #                 session,
#     #                 state,
#     #                 bot,
#     #                 text_msg='Главное меню')
#     #     return
#     # state_msg: tuple[str, str] = data.get('state_msg')
#     # chat_id, message_id = state_msg
#     state_msg: tuple[str,str] = data.get('state_msg')
#     chat_id, message_id = state_msg

#     # state_msg: types.Message = data.get('state_msg')
#     await state.update_data(country=message.text)

#     #
#     order = data.get('order')
#     order['country'] = message.text
#     await state.update_data(order=order)
#     #

#     state_process = data.get('state_process')
#     state_process += f'\nСтрана: {message.text}'
#     await state.update_data(state_process=state_process)

#     await state.set_state(SwiftSepaStates.amount)

#     kb = add_cancel_btn_to_kb(language_code)

#     #
#     await bot.edit_message_text(f'{state_process}\n<b>Введите сумму...</b>',
#                                 chat_id=chat_id,
#                                 message_id=message_id,
#                                 reply_markup=kb.as_markup())
#     #

#     # await state_msg.edit_text(f'{state_process}\n<b>Введите сумму...</b>',
#     #                           reply_markup=kb.as_markup())
#     # await message.answer('Введите сумму...')

#     await message.delete()


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
async def send_notification_to_exchange_admin(user_id: int,
                                              exchange_id: int,
                                              exchange_marker: str,
                                              review_id: int,
                                              session: Session,
                                              bot: Bot):
    Review = Base.classes.general_models_newbasereview

    # match marker:
    #     case 'no_cash':
    #         Review = Base.classes.no_cash_review
    #         Exchange = Base.classes.no_cash_exchange
    #     case 'cash':
    #         Review = Base.classes.cash_review
    #         Exchange = Base.classes.cash_exchange
    #     case 'partner':
    #         Review = Base.classes.partners_review
    #         Exchange = Base.classes.partners_exchange

    query = (
        select(
            Review,
        )\
        .where(Review.id == review_id)
    )
    with session as _session:
        res = _session.execute(query)

        review = res.scalar_one_or_none()

    # try:
    #     review, exchange = res[0]
    # except Exception as ex:
    #     print('error, empty res',ex)
    #     return

    if not review:
        print('error, review not found')
        return
    
    if review.grade == '1':
        _grade = 'Положительный'
    elif review.grade == '0':
        _grade = 'Нейтральный'
    elif review.grade == '-1':
        _grade = 'Отрицательный'

    _text = f'💬 Новый отзыв на прикрепленный обменник {review.exchange_name}\n\n<b>Оценка:</b> {_grade}'

    if review.transaction_id:
        _text += f'\n<b>Номер транзакции:</b> {review.transaction_id}\n\n📌 Просим вас оперативно отреагировать — ситуация находится на контроле администрации <b>MoneySwap</b>.'

    _text += '\n\nПерейти к отзыву можно по кнопке ниже👇'

    _kb = create_kb_for_exchange_admin_review(exchange_id=exchange_id,
                                              exchange_marker=exchange_marker,
                                              review_id=review_id)
    try:
        print('send')
        await bot.send_message(chat_id=user_id,
                            text=_text,
                            reply_markup=_kb.as_markup())
    except Exception as ex:
        print(ex)


async def new_send_notification_to_exchange_admin(user_id: int,
                                              exchange_id: int,
                                              review_id: int,
                                              session: Session,
                                              bot: Bot):
    Review = Base.classes.general_models_review
    Exchange = Base.classes.general_models_exchanger

    query = (
        select(
            Review,
            Exchange,
        )\
        .select_from(Review)\
        .join(Exchange,
              Review.exchange_id == Exchange.id)\
        .where(Review.id == review_id)
    )
    with session as _session:
        res = _session.execute(query)

        review_data = res.fetchall()

    if not review_data:
        print(f'ERROR, REVIEW NOT FOUND BY GIVEN "review_id" {review_id}')
        return
    else:
        review, exchange = review_data[0]
    
    if review.grade == '1':
        _grade = 'Положительный'
    elif review.grade == '0':
        _grade = 'Нейтральный'
    elif review.grade == '-1':
        _grade = 'Отрицательный'

    _text = f'💬 Новый отзыв на прикрепленный обменник {exchange.name}\n\n<b>Оценка:</b> {_grade}'

    if review.transaction_id:
        _text += f'\n<b>Номер транзакции:</b> {review.transaction_id}\n\n📌 Просим вас оперативно отреагировать — ситуация находится на контроле администрации <b>MoneySwap</b>.'

    _text += '\n\nПерейти к отзыву можно по кнопке ниже👇'

    _kb = new_create_kb_for_exchange_admin_review(exchange_id=exchange_id,
                                                  review_id=review_id)
    try:
        await bot.send_message(chat_id=user_id,
                               text=_text,
                               reply_markup=_kb.as_markup())
        print(f'SEND TO EXCHANGE ADMIN REVIEW NOTIFICATION {_text}')
        update_query = (
            update(
                Review
            )\
            .where(
                Review.id == review_id,
            )\
            .values(has_send_to_admin=True)
        )
        with session as _session:
            _session.execute(update_query)
            try:
                _session.commit()
            except Exception as ex:
                print(ex)
                _session.rollback()
    except Exception as ex:
        print(f'ERROR WITH TRY SEND MESSAGE TO EXCHANGE ADMIN REVIEW NOTIFICATION {_text}', ex)


async def send_comment_notification_to_exchange_admin(user_id: int,
                                                      exchange_id: int,
                                                      exchange_marker: str,
                                                      review_id: int,
                                                      session: Session,
                                                      bot: Bot):
    Review = Base.classes.general_models_newbasereview
    # Comment = Base.classes.general_models_newbasecomment

    query = (
        select(
            # Comment,
            Review
        )\
        # .join(Review,
        #       Comment.review_id == Review.id)\
        .where(Review.id == review_id)
    )
    with session as _session:
        res = _session.execute(query)

        review = res.scalar_one_or_none()

    if review:
        # comment, review = res[0]

        # if comment.grade == '1':
        #     _grade = 'Положительный'
        # elif comment.grade == '0':
        #     _grade = 'Нейтральный'
        # elif comment.grade == '-1':
        #     _grade = 'Отрицательный'


        _text = f'💬 Новый комментарий на отзыв прикрепленного обменника {review.exchange_name}'

        _text += '\n\nПерейти к комментарию можно по кнопке ниже👇'

        # if comment.tran
        _kb = create_kb_for_exchange_admin_comment(exchange_id=exchange_id,
                                                   exchange_marker=exchange_marker,
                                                   review_id=review.id)
        try:
            print('send')
            await bot.send_message(chat_id=user_id,
                                text=_text,
                                reply_markup=_kb.as_markup())
        except Exception as ex:
            print(ex)

    pass


async def new_send_comment_notification_to_exchange_admin(user_id: int,
                                                      exchange_id: int,
                                                      review_id: int,
                                                      session: Session,
                                                      bot: Bot):
    Review = Base.classes.general_models_review
    Exchange = Base.classes.general_models_exchanger

    query = (
        select(
            Review,
            Exchange,
        )\
        .select_from(Review)\
        .join(Exchange,
              Review.exchange_id == Exchange.id)\
        .where(Review.id == review_id)
    )
    with session as _session:
        res = _session.execute(query)

        review_data = res.fetchall()

    if review_data:
        review, exchange = review_data[0]

        _text = f'💬 Новый комментарий на отзыв прикрепленного обменника {exchange.name}'

        _text += '\n\nПерейти к комментарию можно по кнопке ниже👇'

        _kb = new_create_kb_for_exchange_admin_comment(exchange_id=exchange_id,
                                                       review_id=review.id)
        try:
            print(f'SEND TO EXCHANGE ADMIN COMMENT NOTIFICATION {_text}')
            await bot.send_message(chat_id=user_id,
                                text=_text,
                                reply_markup=_kb.as_markup())
        except Exception as ex:
            print(ex)


async def send_comment_notification_to_review_owner(user_id: int,
                                                    exchange_id: int,
                                                    exchange_marker: str,
                                                    review_id: int,
                                                    session: Session,
                                                    bot: Bot):
    Review = Base.classes.general_models_newbasereview
    Comment = Base.classes.general_models_newbasecomment

    query = (
        select(
            # Comment,
            Review
        )\
        # .join(Review,
        #       Comment.review_id == Review.id)\
        .where(Review.id == review_id)
    )
    with session as _session:
        res = _session.execute(query)

        review = res.scalar_one_or_none()

    if review:
        # comment, review = res[0]

        _text = f'💬 Новый комментарий на Ваш отзыв обменника {review.exchange_name}'

        _text += '\n\nПерейти к отзыву можно по кнопке ниже👇'
        
        _kb = create_kb_for_exchange_admin_comment(exchange_id=exchange_id,
                                                   exchange_marker=exchange_marker,
                                                   review_id=review.id)
        try:
            print('send')
            await bot.send_message(chat_id=user_id,
                                text=_text,
                                reply_markup=_kb.as_markup())
        except Exception as ex:
            print(ex)

    pass


async def new_send_comment_notification_to_review_owner(user_id: int,
                                                    exchange_id: int,
                                                    review_id: int,
                                                    session: Session,
                                                    bot: Bot):
    Review = Base.classes.general_models_review
    Exchange = Base.classes.general_models_exchanger

    query = (
        select(
            Review,
            Exchange,
        )\
        .select_from(Review)\
        .join(Exchange,
              Review.exchange_id == Exchange.id)\
        .where(Review.id == review_id)
    )
    with session as _session:
        res = _session.execute(query)

        review_data = res.fetchall()

    if review_data:
        review, exchange = review_data[0]

        _text = f'💬 Новый комментарий на Ваш отзыв обменника {exchange.name}'

        _text += '\n\nПерейти к отзыву можно по кнопке ниже👇'
        
        _kb = new_create_kb_for_exchange_admin_comment(exchange_id=exchange_id,
                                                       review_id=review.id)
        try:
            await bot.send_message(chat_id=user_id,
                                text=_text,
                                reply_markup=_kb.as_markup())
            print(f'SEND MESSAGE TO REVIEW OWNER WITH TEXT {_text}')
        except Exception as ex:
            print(f'ERROR WITH TRY MESSAGE TO REVIEW OWNER WITH TEXT {_text}', ex)

    pass


async def send_mass_message_test(bot: Bot,
                            session: Session,
                            user_id: int,
                            name_send: str):
        with session as _session:
            Guest = Base.classes.general_models_guest
            # session: Session

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage
            # mass_message = session.query(MassSendMessage)\
            #                         .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
            #                                  joinedload(MassSendMessage.general_models_masssendvideo_collection))\
            #                         .first()
            mass_message = _session.query(MassSendMessage)\
                                    .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
                                             joinedload(MassSendMessage.general_models_masssendvideo_collection),
                                             joinedload(MassSendMessage.general_models_masssendfile_collection))\
                                    .where(MassSendMessage.name == name_send).first()

            # try add file_id for each related file passed object
            await try_add_file_ids(bot, _session, mass_message)
            # refresh all DB records
            _session.expire_all()

            mass_message_text: str = mass_message.content
            print(mass_message_text)
            # validate content text
            mass_message_text: str = mass_message_text.replace('<p>','')\
                                                        .replace('</p>', '\n')\
                                                        .replace('<br>', '')\
                                                        .replace('<p class="">', '')\
                                                        .replace('&nbsp;', ' ')\
                                                        .replace('<span>', '')\
                                                        .replace('</span>', '')   

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

            active_tg_id_update_list = []
            unactive_tg_id_update_list = []

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
                        active_tg_id_update_list.append(_tg_id)
                except Exception as ex:
                    print(ex)
                    if guest.is_active:
                        unactive_tg_id_update_list.append(_tg_id)
                finally:
                    await sleep(0.3)
            
            active_update_query = (
                update(
                    Guest
                )\
                .values(is_active=True)\
                .where(
                    Guest.tg_id.in_(active_tg_id_update_list)
                )
            )
            unactive_update_query = (
                update(
                    Guest
                )\
                .values(is_active=False)\
                .where(
                    Guest.tg_id.in_(unactive_tg_id_update_list)
                )
            )

            try:
                if active_tg_id_update_list:
                    _session.execute(active_update_query)
                if unactive_tg_id_update_list:
                    _session.execute(unactive_update_query)
                _session.commit()
            except Exception as ex:
                _session.rollback()
                print('send error', ex)
            
            # session.close()




async def send_mass_message(bot: Bot,
                            db_session: Session,
                            name_send: str):
        start_send_time = time.time()

        with db_session as _session:
            Guest = Base.classes.general_models_guest

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage

            mass_message = _session.query(MassSendMessage)\
                                    .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
                                             joinedload(MassSendMessage.general_models_masssendvideo_collection),
                                             joinedload(MassSendMessage.general_models_masssendfile_collection))\
                                    .where(MassSendMessage.name == name_send).first()

            # try add file_id for each related file passed object
            await try_add_file_ids(bot, _session, mass_message)
            # refresh all DB records
            _session.expire_all()

            mass_message_text: str = mass_message.content

            # validate content text
            mass_message_text: str = mass_message_text.replace('<p>','')\
                                                        .replace('</p>', '\n')\
                                                        .replace('<br>', '')\
                                                        .replace('<p class="">', '')\
                                                        .replace('&nbsp;', ' ')\
                                                        .replace('<span>', '')\
                                                        .replace('</span>', '')   


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

            res = _session.execute(query)

            guests = res.fetchall()

        start_users_count = len([guest for guest in guests if guest[0].is_active == True])

        image_video_group = None

        if list(images+videos):
            image_video_group = MediaGroupBuilder(images+videos, caption=mass_message_text)
        
        files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
        file_group = None
        if files:
            file_group = MediaGroupBuilder(files)

        # try:
        active_tg_id_update_list = []
        unactive_tg_id_update_list = []

        for guest in guests:
            try:
                guest = guest[0]
                _tg_id = guest.tg_id
                if image_video_group is not None:
                    mb1 = await bot.send_media_group(_tg_id, media=image_video_group.build())
                    # print('MB1', mb1)
                    print(f'отправлено юзеру ( с медиа файлами ) {_tg_id}✅')
                else:
                    await bot.send_message(_tg_id,
                                        text=mass_message_text)
                    print(f'отправлено юзеру {_tg_id}✅')
                if file_group is not None:
                    mb2 = await bot.send_media_group(_tg_id, media=file_group.build())
                    print(f'отправлено юзеру ( с док файлами ) {_tg_id}✅')

                if not guest.is_active:
                    active_tg_id_update_list.append(_tg_id)
                    # session.execute(update(Guest).where(Guest.tg_id == _tg_id).values(is_active=True))
            except Exception as ex:
                print(f'{ex} ❌')
                if guest.is_active:
                    unactive_tg_id_update_list.append(_tg_id)
                    # session.execute(update(Guest).where(Guest.tg_id == _tg_id).values(is_active=False))
            finally:
                await sleep(0.3)
        
        end_send_time = time.time()

        active_update_query = (
            update(
                Guest
            )\
            .values(is_active=True)\
            .where(
                Guest.tg_id.in_(active_tg_id_update_list)
            )
        )
        unactive_update_query = (
            update(
                Guest
            )\
            .values(is_active=False)\
            .where(
                Guest.tg_id.in_(unactive_tg_id_update_list)
            )
        )
        
        with db_session as _session:
            try:
                if active_tg_id_update_list:
                    _session.execute(active_update_query)
                if unactive_tg_id_update_list:
                    _session.execute(unactive_update_query)
                _session.commit()
                _text = ''
            except Exception as ex:
                _session.rollback()
                _text = ''
                print('send error', ex)
            finally:
                execute_time = end_send_time - start_send_time

                _valid_time = round(execute_time / 60 / 60, 2)

                if _valid_time == 0:
                    valid_time = f'{round(execute_time)} (время в секундах)'
                else:
                    valid_time = f'{_valid_time} (время в часах)'



                # query = (
                #     select(
                #         Guest.id
                #     )\
                #     .where(Guest.is_active == False)
                # )
                with db_session as _session:
                    end_active_users_count = _session.query(Guest.tg_id).where(Guest.is_active == True).count()

                try:
                    _url = f'https://api.moneyswap.online/send_mass_message_info?execute_time={valid_time}&start_users_count={start_users_count}&end_users_count={end_active_users_count}'
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession() as aiosession:
                        async with aiosession.get(_url,
                                            timeout=timeout) as response:
                            pass
                except Exception as ex:
                    print(ex)
                    pass
                # session.close()


async def try_send_order(bot: Bot,
                         session: Session,
                         user_id: int,
                         order_id: int,
                         order_status: str | None):
    with session as _session:
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

        res = _session.execute(query)

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

                with session as _session:
                    try:
                        _session.execute(update(Guest)\
                                        .where(Guest.tg_id == user_id)\
                                        .values(chat_link=chat_link))
                        # guest.chat_link = chat_link
                        _session.commit()
                    except Exception as ex:
                        print(ex, 'не получилось отправить, проблема на нашей стороне')
                        try:
                            result_text = f'❌Сообщение с ссылкой на MoneyPort не получилось отправить пользователю {user_id}, проблема на нашей стороне'
                            
                            # if user_id == 686339126:
                            #     _url = f'https://api.moneyswap.online/test_send_result_chat_link?result_text={result_text}' 
                            # else:
                            _url = f'https://api.moneyswap.online/send_result_chat_link?result_text={result_text}'
                            
                            timeout = aiohttp.ClientTimeout(total=5)
                            async with aiohttp.ClientSession() as aiosession:
                                async with aiosession.get(_url,
                                                    timeout=timeout) as response:
                                    pass
                        except Exception as ex:
                            print(ex)
                            pass

                        return {'status': 'error'}

            else:
                print('не получилось отправить, проблема на стороне MoneyPort')
                try:
                    result_text = f'❌Сообщение с ссылкой на MoneyPort не получилось отправить пользователю {user_id}, проблема на стороне MoneyPort'
                    
                    # if user_id == 686339126:
                    #     _url = f'https://api.moneyswap.online/test_send_result_chat_link?result_text={result_text}' 
                    # else:
                    _url = f'https://api.moneyswap.online/send_result_chat_link?result_text={result_text}'
                    
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession() as aiosession:
                        async with aiosession.get(_url,
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
                async with aiohttp.ClientSession() as aiosession:
                    async with aiosession.get(_url,
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
                async with aiohttp.ClientSession() as aiosession:
                    async with aiosession.get(_url,
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
                async with aiohttp.ClientSession() as aiosession:
                    async with aiosession.get(_url,
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
async def exchange_admin_direction_notification(user_id: int,
                                                text: str,
                                                bot: Bot):
    try:
        _kb = create_partner_site_kb()
        await bot.send_message(chat_id=user_id,
                               text=text,
                               reply_markup=_kb.as_markup())
    except Exception as ex:
        print(ex)





@main_router.message()
async def ignore_any_message(message: types.Message):
    try:
        await message.delete()
    except Exception as ex:
        print(ex)