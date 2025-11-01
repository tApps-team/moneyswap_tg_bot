import json
import time

from asyncio import sleep

from datetime import datetime, timedelta

import aiohttp

from aiogram import Router, types, Bot, F
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError

from sqlalchemy.orm import Session, joinedload, sessionmaker, selectinload
from sqlalchemy import insert, select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import BEARER_TOKEN, FEEDBACK_REASON_PREFIX

from keyboards import (create_add_comment_kb,
                       create_add_review_kb,
                       create_dev_kb,
                       create_kb_for_exchange_admin_comment,
                       create_kb_for_exchange_admin_review,
                       create_partner_site_kb,
                       create_start_keyboard,
                       create_start_inline_keyboard,
                       create_swift_condition_kb,
                       create_swift_start_kb,
                       add_cancel_btn_to_kb,
                       create_kb_to_main,
                       create_swift_sepa_kb,
                       create_support_kb,
                       create_feedback_form_reasons_kb,
                       new_create_kb_for_exchange_admin_comment,
                       new_create_kb_for_exchange_admin_review,
                       reason_dict,
                       create_feedback_confirm_kb,
                       create_condition_kb,
                       add_switch_language_btn)

from states import SwiftSepaStates, FeedbackFormStates

from utils.handlers import (construct_activate_exchange_admin_message,
                            construct_activate_partner_exchange_admin_message,
                            construct_add_comment_message,
                            construct_add_review_message,
                            get_exchange_data,
                            try_activate_admin_exchange,
                            try_activate_partner_admin_exchange,
                            try_add_file_ids_to_db,
                            try_add_file_ids,
                            swift_sepa_data,
                            validate_amount,
                            consctruct_start_massage)
from utils.multilanguage import start_text_dict

from db.base import Base


main_router = Router()


################################### START HANDLER ###################################
@main_router.message(Command('start'))
async def start(message: types.Message,
                session: AsyncSession,
                state: FSMContext,
                bot: Bot):

    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
        await state.update_data(select_language=select_language)

    review_msg_dict = None
    comment_msg_dict = None
    activate_admin_exchange = None
    partner_activate_admin_exchange = None

    _start_text = start_text_dict.get('ru') if select_language == 'ru'\
          else start_text_dict.get('en')
    
    utm_source = None

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

        if utm_source.startswith('new_review'):
            params = utm_source.split('__')
            print('ADD REVIEW PARAMS', params)

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
                'exchange_id': int(params[-1]),
            }

            utm_source = 'from_site'

        elif utm_source.startswith('new_comment'):
            params = utm_source.split('__')
            print('ADD REVIEW PARAMS', params)

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
                'exchange_id': int(params[1]),
                'review_id': int(params[-1]),
            }

            utm_source = 'from_site'
        
        elif utm_source.startswith('new_admin'):
            activate_admin_exchange = True
            utm_source = 'from_admin_activate'

        elif utm_source.startswith('new_partner_admin'):
            partner_activate_admin_exchange = True
            utm_source = 'from_partner_admin_activate'
            
    async with session as _session:
        Guest = Base.classes.general_models_guest

        tg_id = message.from_user.id

        guest_query = (
            select(Guest)\
            .where(Guest.tg_id == tg_id)
        )

        guest_res = await session.execute(guest_query)

        guest = guest_res.scalar_one_or_none()
    
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

        insert_guest_query = (
            insert(
                Guest
            )\
            .values(**value_dict)
        )
        async with session as _session:
            await _session.execute(insert_guest_query)
            await _session.commit()
        first_visit = True
    else:
        chat_link  = guest.chat_link
        first_visit = False

    if review_msg_dict and not first_visit:
        _text, _kb, blocked_add_review = await construct_add_review_message(review_msg_dict=review_msg_dict,
                                                                            session=session,
                                                                            select_language=select_language)
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
    
    if comment_msg_dict and not first_visit:
        _text, _kb, blocked_add_comment = await construct_add_comment_message(comment_msg_dict=comment_msg_dict,
                                                                            session=session,
                                                                            select_language=select_language)
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
    
    elif activate_admin_exchange and not first_visit:
        _text = await construct_activate_exchange_admin_message(message.from_user.id,
                                                                session=session)
        try:
            await message.answer(text=_text,
                                 disable_web_page_preview=True)

        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')

        try:
            await message.delete()
        except Exception:    
            pass
        
        return

    elif partner_activate_admin_exchange and not first_visit:
        _text = await construct_activate_partner_exchange_admin_message(message.from_user.id,
                                                                        session=session)
        
        try:
            await message.answer(text=_text,
                                 disable_web_page_preview=True)

        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')

        try:
            await message.delete()
        except Exception:    
            pass
        
        return

    if chat_link:
        if select_language == 'ru':
            chat_link_text = f'Cсылка на чата по Вашим обращениям -> {chat_link}'
        else:
            chat_link_text = f'Link to chat for your requests -> {chat_link}'
        
        _start_text += f'\n\n{chat_link_text}'

    try:
        _start_text, start_kb = await consctruct_start_massage(user_id=message.from_user.id,
                                                                select_language=select_language,
                                                                session=session,
                                                                chat_link=chat_link)
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
                _exchange_id = blocked_add_review[-1]
                _kb = create_add_review_kb(_exchange_id,
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
                _exchange_id, _review_id = blocked_add_comment[1:]
                _comment_msg_dict = {
                    'exchange_id': _exchange_id,
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
            await state.update_data(blocked_add_review=None)

        elif isinstance(blocked_add_comment, bool):
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

    # if first visit block
    if review_msg_dict:
        _text, _kb, blocked_add_review = await construct_add_review_message(review_msg_dict=review_msg_dict,
                                                                            session=session,
                                                                            select_language=select_language)
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            await state.update_data(blocked_add_review=blocked_add_review)
        
        return
            
    if comment_msg_dict:
        _text, _kb, blocked_add_comment = await construct_add_comment_message(comment_msg_dict=comment_msg_dict,
                                                                            session=session,
                                                                            select_language=select_language)
        try:
            await bot.send_message(chat_id=message.from_user.id,
                                text=_text,
                                reply_markup=_kb)
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            # for blocked comment
            await state.update_data(blocked_add_comment=blocked_add_comment)
        try:
            await message.delete()
        except Exception:
            pass

        return
    
    if activate_admin_exchange:
        _text = await construct_activate_exchange_admin_message(message.from_user.id,
                                                                session=session)
        try:
            await message.answer(text=_text,
                                    disable_web_page_preview=True)

        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')
            return
        try:
            await message.delete()
        except Exception:
            pass
        
        return

    if partner_activate_admin_exchange:
        _text = await construct_activate_partner_exchange_admin_message(message.from_user.id,
                                                                        session=session)
        
        try:
            await message.answer(text=_text,
                                    disable_web_page_preview=True)
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE ON /START tg_id {message.from_user.id} {ex}')

        try:
            await message.delete()
        except Exception:    
            pass
        
        return
################################### END START HANDLER ###################################


@main_router.callback_query(F.data.startswith('lang'))
async def switch_language_main_message(callback: types.CallbackQuery,
                                       session: AsyncSession,
                                       state: FSMContext,
                                       bot: Bot):
    callback_data = callback.data.split('_')[-1]

    if callback_data == 'ru':
        select_language = 'ru'
    else:
        select_language = 'en'
    
    await state.update_data(select_language=select_language)

    _start_text, start_kb = await consctruct_start_massage(user_id=callback.from_user.id,
                                                           select_language=select_language,
                                                           session=session)
    try:
        await bot.edit_message_text(text=_start_text,
                                    chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    disable_web_page_preview=True,
                                    reply_markup=start_kb.as_markup())

        await callback.answer()
    except Exception as ex:
        print(ex)

        try:
            await bot.send_message(text=_start_text,
                                   chat_id=callback.from_user.id,
                                   disable_web_page_preview=True,
                                   reply_markup=start_kb.as_markup())
            
            await bot.delete_message(chat_id=callback.from_user.id,
                                     message_id=callback.message.message_id)
        except Exception:
            pass
    finally:
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


@main_router.callback_query(F.data.in_(('cancel', 'to_main')))
async def back_to_main(callback: types.CallbackQuery,
                       state: FSMContext,
                       session: AsyncSession,
                       bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')
    chat_id = callback.from_user.id
    message_id = callback.message.message_id

    await state.set_state()

    try:
        await bot.delete_message(chat_id=chat_id,
                                 message_id=message_id)
    except Exception:
        _text = 'Сообщение больше недоступно' if select_language == 'ru'\
                else 'The message is no longer available'
        try:
            await bot.edit_message_text(text=_text,
                                        chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=None)
        except Exception as ex:
            print(ex)
            pass
    finally:
        await callback.answer()


################################### SWIFT/SEPA STATE ###################################
@main_router.callback_query(F.data == 'invoice_swift/sepa')
async def invoice_swift_sepa(callback: types.CallbackQuery,
                            session: AsyncSession,
                            state: FSMContext,
                            bot: Bot):
    data = await state.get_data()

    state_msg: tuple = data.get('state_msg')
    select_language = data.get('select_language')

    if state_msg:
        chat_id, message_id = state_msg

        try:
            await bot.delete_message(chat_id=chat_id,
                                     message_id=message_id)
        except Exception:
            _text = 'Сообщение больше недоступно' if select_language == 'ru'\
                    else 'The message is no longer available'
            try:
                await bot.edit_message_text(text=_text,
                                            chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=None)
            except Exception as ex:
                print(ex)
                pass
        finally:
            await state.update_data(state_msg=None)

    if not select_language:
        select_language = 'ru'

    _text = 'Выберите действие' if select_language == 'ru' else 'Choose an action'

    await state.set_state(SwiftSepaStates.request_type)

    chat_id = callback.message.chat.id

    swift_sepa_kb = create_swift_start_kb(select_language)
    swift_sepa_kb = add_cancel_btn_to_kb(select_language,
                                         swift_sepa_kb)

    try:
        state_msg = await bot.send_message(text=_text,
                                           chat_id=chat_id,
                                           reply_markup=swift_sepa_kb.as_markup())
        await state.update_data(order=dict(),
                                state_msg=(chat_id, state_msg.message_id))
        
    except TelegramForbiddenError:
        return
    
    await callback.answer()


@main_router.callback_query(F.data.in_(('pay_payment', 'access_payment')))
async def request_type_state(callback: types.CallbackQuery,
                             session: AsyncSession,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()

    state_msg = data.get('state_msg')
    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    chat_id, message_id = state_msg

    request_type = 'Оплатить платеж' if callback.data == 'pay_payment' else 'Принять платеж'

    if select_language == 'ru':
        state_process = f'\nТип заявки: {request_type}'
        _text = f'{state_process}\n\n<b>Введите сумму и валюту платежа</b>\n\n⚠️ <u>Внимание: минимальная сумма платежа составляет 3000$.</u>'
    else:
        request_dict = {
            'Оплатить платеж': 'Make a Payment',
            'Принять платеж': 'Receive a Payment',
        }
        state_process = f'\nRequest Type: {request_dict.get(request_type)}'
        _text = f'{state_process}\n\n<b>Input payment and valute amount</b>\n\n⚠️ <u>Please note: the minimum payment amount is 3000$</u>'

    order = data.get('order')
    order['request_type'] = request_type

    await state.update_data(order=order,
                            state_process=state_process,
                            request_type=callback.data)

    await state.set_state(SwiftSepaStates.amount)

    kb = add_cancel_btn_to_kb(select_language)

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    try:
        await callback.answer()
    except Exception:
        pass


@main_router.message(SwiftSepaStates.amount)
async def amount_state(message: types.Message,
                       session: AsyncSession,
                       state: FSMContext,
                       bot: Bot):
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
        _text = f'{state_process}\n\n<b>Подробно опишите перевод</b>\n\n<u>Укажите все необходимые детали: из какой страны и в какую осуществляется перевод, назначение платежа и любые другие значимые детали.</u>'
    else:

        state_process += f'\nAmount: {message.text}'
        _text = f'{state_process}\n\n<b>Describe your request in detail</b>\n\n<u>Please provide all necessary details: from and to which country the transfer is made, the purpose of the payment and any other significant details.</u>'

    order = data.get('order')
    order['amount'] = message.text

    await state.update_data(order=order,
                            amount=message.text,
                            state_process=state_process)

    await state.set_state(SwiftSepaStates.task_text)

    kb = add_cancel_btn_to_kb(select_language)

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())

    await message.delete()


@main_router.message(SwiftSepaStates.task_text)
async def task_text_state(message: types.Message,
                          session: AsyncSession,
                          state: FSMContext,
                          bot: Bot):
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

    kb = create_kb_to_main(select_language)

    await bot.edit_message_text(f'{state_process}\n\n<b>{state_done_text}</b>',
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    
    await message.delete()


@main_router.callback_query(F.data == 'send_app')
async def send_order(callback: types.CallbackQuery,
                   session: AsyncSession,
                   state: FSMContext,
                   bot: Bot):
    
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

    print('order', order)

    await state.update_data(state_msg=None)

    Order = Base.classes.general_models_customorder


    async with session as _session:

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

        check_res = await _session.execute(check_query)

        if check_res.scalar_one_or_none():
            
            if select_language == 'ru':
                _text = '⏳ Ваша заявка успешно принята. При положительном решении Вам будет отправлена ссылка на вступление в чат с персональным менеджером от нашей партнерской компании, который будет сопровождать ваш перевод'
            else:
                _text = '⏳ Your request has been successfully accepted. If the decision is positive, you will be sent a link to join the chat with a personal manager from our partner company, who will accompany your transfer'

            await callback.answer(text=_text,
                                  show_alert=True)
            
            try:
                await callback.message.delete()
            except Exception:
                pass

            return
        
        new_order = Order(**order)  # предполагая, что order — это словарь
        _session.add(new_order)
        try:
            await _session.commit()
            await _session.refresh(new_order)
        except Exception as ex:
            print('ERROR WITH TRY ADD SWIFT/SEPA ORDER', ex)
            if select_language == 'ru':
                _text = '❗️ К сожалению, произошла ошибка. Приносим свои извинения и просим Вас попробовать создать заявку позже.'
            else:
                _text = '❗️ Unfortunately, an error occurred. We apologize and ask that you try submitting your order later.'
            try:
                await callback.answer(text=_text,
                                    show_alert=True)
                await callback.message.delete()
            except Exception:
                pass
            return

    print(new_order.__dict__)

    user_id = new_order.guest_id
    order_id = new_order.id
    marker = 'swift/sepa'

    if select_language == 'ru':
        _text = '⏳ Ваша заявка успешно принята. При положительном решении Вам будет отправлена ссылка на вступление в чат с персональным менеджером от нашей партнерской компании, который будет сопровождать ваш перевод'
    else:
        _text = '⏳ Your request has been successfully accepted. If the decision is positive, you will be sent a link to join the chat with a personal manager from our partner company, who will accompany your transfer'

    await callback.answer(text=_text,
                          show_alert=True)
    
    try:
        await callback.message.delete()
    except Exception:
        pass

    _url = f'https://api.moneyswap.online/send_to_tg_group?user_id={user_id}&order_id={order_id}&marker={marker}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.get(_url,
                               timeout=timeout) as response:
            pass
################################### END SWIFT/SEPA STATE ###################################


@main_router.message(F.content_type == types.ContentType.PHOTO)
async def photo_test(message: types.Message,
                    state: FSMContext,
                    bot: Bot):
    print(message.photo)
    print('*' * 10) 


################################### FEEDBACK FORM STATE ###################################
@main_router.callback_query(F.data == 'support')
async def start_support(callback: types.CallbackQuery,
                        session: AsyncSession,
                        state: FSMContext,
                        bot: Bot,):
    data = await state.get_data()

    state_msg: tuple = data.get('state_msg')
    select_language = data.get('select_language')

    if state_msg:
        chat_id, message_id = state_msg

        try:
            await bot.delete_message(chat_id=chat_id,
                                     message_id=message_id)
        except Exception:
            _text = 'Сообщение больше недоступно' if select_language == 'ru'\
                    else 'The message is no longer available'
            try:
                await bot.edit_message_text(text=_text,
                                            chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=None)
            except Exception as ex:
                print(ex)
                pass
        finally:
            await state.update_data(state_msg=None)

    if not select_language:
        select_language = 'ru'

    chat_id = callback.message.chat.id

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
        state_msg = await bot.send_message(text=_text,
                                           chat_id=chat_id,
                                           disable_web_page_preview=True,
                                           reply_markup=reason_kb.as_markup())
        await state.update_data(state_msg=(chat_id, state_msg.message_id))
    except TelegramForbiddenError:
        return
    
    await callback.answer()

    
@main_router.callback_query(F.data.startswith(FEEDBACK_REASON_PREFIX))
async def request_type_state(callback: types.CallbackQuery,
                             session: AsyncSession,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()

    state_msg: tuple = data.get('state_msg')
    chat_id, message_id = state_msg

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'
    
    reason = callback.data.split('__')[-1]

    feedback_form = data.get('feedback_form')

    feedback_form['reason'] = reason

    await state.update_data(feedback_form=feedback_form,
                            state_msg=(chat_id, message_id))

    await state.set_state(FeedbackFormStates.description)

    kb = add_cancel_btn_to_kb(select_language)

    _text = '<b>Опишите проблему, если это нужно</b>\nЕсли нет напишите "Нет"' if select_language == 'ru'\
                else '<b>Describe the issue if necessary</b>\nIf not, type “No”'

    await bot.edit_message_text(text=_text,
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=kb.as_markup())
    
    await callback.answer()


@main_router.message(FeedbackFormStates.description)
async def request_type_state(message: types.Message,
                             session: AsyncSession,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()

    state_msg: tuple = data.get('state_msg')
    chat_id, message_id = state_msg

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    description = message.text

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
    
    await message.delete()
    

@main_router.message(FeedbackFormStates.contact)
async def country_state(message: types.Message,
                        session: AsyncSession,
                        state: FSMContext,
                        bot: Bot):
    data = await state.get_data()

    state_msg: tuple = data.get('state_msg')
    chat_id, message_id = state_msg

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    contact = message.text

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

    await message.delete()


@main_router.message(FeedbackFormStates.username)
async def country_state(message: types.Message,
                        session: AsyncSession,
                        state: FSMContext,
                        bot: Bot):
    data = await state.get_data()

    state_msg: tuple = data.get('state_msg')
    chat_id, message_id = state_msg

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    username = message.text

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

    try:
        await message.delete()
    except Exception:
        pass


@main_router.callback_query(F.data == 'feedback_form_send')
async def feedback_form_send(callback: types.CallbackQuery,
                            session: AsyncSession,
                            state: FSMContext,
                            bot: Bot):
    data = await state.get_data()

    select_language = data.get('select_language')

    if not select_language:
        select_language = 'ru'

    feedback_form = data.get('feedback_form')

    feedback_values = {
        'reasons': reason_dict.get(feedback_form['reason']),
        'username': feedback_form['username'],
        'email': feedback_form['contact'],
        'description': feedback_form['description'],
        'time_create': datetime.now(),
    }

    FeedbackForm = Base.classes.general_models_feedbackform


    async with session as _session:
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
        check_feedback = await _session.execute(check_feedback_query)
        check_feedback = check_feedback.scalar_one_or_none()

        if check_feedback:
            _text = 'Обращение уже было отправлено или Вы пытаетесь отправить одно и то же обращение, ожидайте с Вами свяжутся'
            await callback.answer(text=_text,
                                  show_alert=True)
            try:
                await callback.message.delete()
            except Exception:
                pass

            return

        _feedback_form = FeedbackForm(**feedback_values)
        _session.add(_feedback_form)

        try:
            await _session.commit()
            await _session.refresh(_feedback_form)

            user_id = callback.from_user.id
            marker = 'feedback_form'
            order_id = _feedback_form.id

            _text = 'Обращение успешно отправлено!' if select_language == 'ru'\
                    else 'Request has been send successfully!'
        except Exception as ex:
            print(ex)
            await _session.rollback()
            _text = 'Что то пошло не так, попробуйте повторить позже' if select_language == 'ru'\
                    else 'Something wrong, try repeat later'

        await callback.answer(text=_text,
                              show_alert=True)

        try:
            await callback.message.delete()
        except Exception:
            pass

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
################################### END FEEDBACK FORM STATE ###################################


# @main_router.message(Command('send'))
# async def send(message: types.Message,
#                session: AsyncSession,
#                bot: Bot):
#     MassSendMessage = Base.classes.general_models_masssendmessage

#     mass_message = session.query(MassSendMessage).options(joinedload(MassSendMessage.general_models_masssendimage_collection),
#                                                       joinedload(MassSendMessage.general_models_masssendvideo_collection)).first()

#     print(mass_message.general_models_masssendimage_collection)
#     for q in mass_message.general_models_masssendimage_collection:
#         print(q.__dict__)
#     print(mass_message.general_models_masssendvideo_collection)
#     for w in mass_message.general_models_masssendvideo_collection:
#         print(w.__dict__)

#     await try_add_file_ids_to_db(message,
#                                  session,
#                                  bot,
#                                  mass_message)
    
#     # session.refresh(mass_message)
#     session.expire_all()

#     print('22')
#     for q in mass_message.general_models_masssendimage_collection:
#         print(q.__dict__)
#     print(mass_message.general_models_masssendvideo_collection)
#     for w in mass_message.general_models_masssendvideo_collection:
#         print(w.__dict__)

#     # print(MassSendMessage)
#     # print(MassSendMessage.__dict__)

#     # os_path = os.path.dirname(os.path.abspath(__file__))

#     # print(os_path)

#     # valutes = session.query(Valutes).all()
#     # messages = session.query(MassSendMessage).all()
#     # MassSendImage = Base.classes.general_models_masssendimage
#     # images = session.query(MassSendImage).all()

#     # mass_message = session.query(MassSendMessage).options(joinedload(MassSendMessage.general_models_masssendimage_collection),
#     #                                                   joinedload(MassSendMessage.general_models_masssendvideo_collection)).first()
   
#     # for m in messages:
#     #     # images = select(MassSendMessage).options(joinedload(MassSendMessage.images))
#     #     # print(v.__dict__)
#     #     # for i in m.general_models_masssendimage_collection:
#     #     #     print(i.__dict__)
#     #     images = [(image.id, image.file_id, types.InputMediaPhoto(media=types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{image.image}'))) for image in m.general_models_masssendimage_collection]
#     #     update_image_list = []
#     #     for image in images:
#     #         if image[1] is None:
#     #             # upload image to telegram server
#     #             loaded_image = await message.answer_photo(image[-1].media)
#     #             # delete image message from chat
#     #             await bot.delete_message(message.chat.id, message.message_id)
#     #             image_file_id = loaded_image.photo[0].file_id
#     #             print(image[0], image_file_id)
#     #             image_dict = {
#     #                 'id': image[0],
#     #                 'file_id': image_file_id,
#     #             }
#     #             update_image_list.append(image_dict)
#     #         else:
#     #             print('из БД', image[1])
#     #     if update_image_list:
#     #         session.bulk_update_mappings(
#     #             MassSendImage,
#     #             update_image_list,
#     #         )
#     #         session.commit()
#     #         session.flush(MassSendMessage.general_models_masssendimage_collection)
#     mass_message_text: str = mass_message.content
#     print(mass_message_text)
#     mass_message_text: str = mass_message_text.replace('<p>','')\
#                                                 .replace('</p>', '\n')\
#                                                 .replace('<br>', '')\
#                                                 .replace('<p class="">', '')\
#                                                 # .replace('<span', '<span class="tg-spoiler"')

#     print(mass_message_text)

#     images = [types.InputMediaPhoto(media=image.file_id) for image in mass_message.general_models_masssendimage_collection]
#     videos = [types.InputMediaVideo(media=video.file_id) for video in mass_message.general_models_masssendvideo_collection]
#     mb = MediaGroupBuilder(images+videos, caption=mass_message_text)
    
#     files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
#     mb_files = MediaGroupBuilder(files)
#     # mb.build()
#         # for image in m.general_models_masssendimage_collection:
#         #     if image.file_id is None:

#         #     image_id = await message.answer_photo(image.media)
#         #     print(image_id)
#         #     print('ID',image_id.photo[0].file_id)
#         # images = [types.InputMediaPhoto(media=f'http://localhost:8000/django/media/{image.image}') for image in m.general_models_masssendimage_collection]
#         # print(images)
#         # videos = [types.InputMediaVideo(media=types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{video.video}')) for video in m.general_models_masssendvideo_collection]
#         # for v in videos:
#             # await message.answer_video(v.media)
#             # video_id = await message.answer_video('BAACAgIAAxkDAAOTZl79M00aHNBaYsc4gNk6znwWiQ4AAhFPAALje_hKCvWrvLSuzxY1BA')
#             # print(video_id)
#             # print('ID',video_id.video.file_id)
#         # videos = [types.InputMediaVideo(media=video.video) for video in m.general_models_masssendvideo_collection]
#         # print(videos)

#     # await message.answer_photo('https://img.freepik.com/free-photo/view-of-3d-adorable-cat-with-fluffy-clouds_23-2151113419.jpg')
    
#     await message.answer_media_group(media=mb.build())
#     await message.answer_media_group(media=mb_files.build())
    


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
async def send_review_notification_to_exchange_admin(user_id: int,
                                              exchange_id: int,
                                              exchange_marker: str,
                                              review_id: int,
                                              session: AsyncSession,
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
    async with session as _session:
        res = await _session.execute(query)

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


async def new_send_review_notification_to_exchange_admin(user_id: int,
                                                  exchange_id: int,
                                                  review_id: int,
                                                  session: AsyncSession,
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
    async with session as _session:
        res = await _session.execute(query)

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
    except Exception as ex:
        print(f'ERROR WITH TRY SEND MESSAGE TO EXCHANGE ADMIN REVIEW NOTIFICATION {_text}', ex)



async def send_comment_notification_to_exchange_admin(user_id: int,
                                                      exchange_id: int,
                                                      exchange_marker: str,
                                                      review_id: int,
                                                      session: AsyncSession,
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
    async with session as _session:
        res = await _session.execute(query)

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
                                                          session: AsyncSession,
                                                          bot: Bot):
    Review = Base.classes.general_models_newbasereview
    Exchange = Base.classes.general_models_exchanger

    query = (
        select(
            Exchange,
            Review,
        )\
        .select_from(Review)\
        .join(Exchange,
              Review.exchange_id == Exchange.id)\
        .where(Review.id == review_id)
    )
    async with session as _session:
        res = await _session.execute(query)

        review_data = res.fetchall()

    if review_data:
        exchange, review = review_data[0]

        _text = f'💬 Новый комментарий на отзыв прикрепленного обменника {exchange.name}'

        _text += '\n\nПерейти к комментарию можно по кнопке ниже👇'

        _kb = new_create_kb_for_exchange_admin_comment(exchange_id=exchange_id,
                                                       review_id=review.id)
        try:
            await bot.send_message(chat_id=user_id,
                                text=_text,
                                reply_markup=_kb.as_markup())
            print(f'SEND TO EXCHANGE ADMIN COMMENT NOTIFICATION {_text}')
        except Exception as ex:
            print(f'ERROR WITH TRY SEND MESSAGE TO EXCHANGE ADMIN COMMENT NOTIFICATION {_text}', ex)


async def send_comment_notification_to_review_owner(user_id: int,
                                                    exchange_id: int,
                                                    exchange_marker: str,
                                                    review_id: int,
                                                    session: AsyncSession,
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
    async with session as _session:
        res = await _session.execute(query)

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
                                                        session: AsyncSession,
                                                        bot: Bot):
    Review = Base.classes.general_models_review
    Exchange = Base.classes.general_models_exchanger

    query = (
        select(
            Exchange,
            Review
        )\
        .join(Exchange,
              Review.exchange_id == Exchange.id)\
        .where(Review.id == review_id)
    )
    async with session as _session:
        res = await _session.execute(query)

        review_data = res.fetchall()

    if review_data:
        exchange, review = review_data[0]

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
                                 session: AsyncSession,
                                 user_id: int,
                                 name_send: str):
        async with session as _session:
            Guest = Base.classes.general_models_guest

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage

            query = (
                select(
                    MassSendMessage
                )\
                .options(
                    selectinload(MassSendMessage.general_models_masssendimage_collection),
                    selectinload(MassSendMessage.general_models_masssendvideo_collection),
                    selectinload(MassSendMessage.general_models_masssendfile_collection),
                )\
                .where(MassSendMessage.name == name_send)
            )

            res = await _session.execute(query)

            mass_message = res.scalar_one_or_none()

            # try add file_id for each related file passed object
            await try_add_file_ids(bot, _session, mass_message)
            # refresh all DB records
            # await _session.refresh()
            await _session.refresh(mass_message, 
                attribute_names=[
                    "general_models_masssendimage_collection",
                    "general_models_masssendvideo_collection",
                    "general_models_masssendfile_collection"
                ]
            )

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
            
            #test for specific user
            query = (
                select(Guest)\
                .where(Guest.tg_id == user_id)
            )

            res = await _session.execute(query)

            guests = res.fetchall()

            image_video_group = None
            if list(images+videos):
                image_video_group = MediaGroupBuilder(images+videos, caption=mass_message_text)
            
            files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
            file_group = None
            if files:
                file_group = MediaGroupBuilder(files)

            active_tg_id_update_list = []
            unactive_tg_id_update_list = []

            for guest in guests:
                try:
                    guest = guest[0]
                    _tg_id = guest.tg_id
                    if image_video_group is not None:
                        mb1 = await bot.send_media_group(_tg_id, media=image_video_group.build())
                    else:
                        await bot.send_message(_tg_id,
                                            text=mass_message_text)
                    if file_group is not None:
                        mb2 = await bot.send_media_group(_tg_id, media=file_group.build())    
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
                    await _session.execute(active_update_query)
                if unactive_tg_id_update_list:
                    await _session.execute(unactive_update_query)
                await _session.commit()
            except Exception as ex:
                await _session.rollback()
                print('send error', ex)


async def send_mass_message(bot: Bot,
                            db_session: AsyncSession,
                            name_send: str):
        start_send_time = time.time()

        async with db_session as _session:
            Guest = Base.classes.general_models_guest

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage

            # mass_message = _session.query(MassSendMessage)\
            #                         .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
            #                                  joinedload(MassSendMessage.general_models_masssendvideo_collection),
            #                                  joinedload(MassSendMessage.general_models_masssendfile_collection))\
            #                         .where(MassSendMessage.name == name_send).first()

            query = (
                select(
                    MassSendMessage
                )\
                .options(
                    selectinload(MassSendMessage.general_models_masssendimage_collection),
                    selectinload(MassSendMessage.general_models_masssendvideo_collection),
                    selectinload(MassSendMessage.general_models_masssendfile_collection),
                )\
                .where(MassSendMessage.name == name_send)
            )

            res = await _session.execute(query)

            mass_message = res.scalar_one_or_none()

            if not mass_message:
                return
            # try add file_id for each related file passed object
            await try_add_file_ids(bot, _session, mass_message)
            # refresh all DB records
            # await _session.refresh(mass_message)
            await _session.refresh(mass_message, 
                attribute_names=[
                    "general_models_masssendimage_collection",
                    "general_models_masssendvideo_collection",
                    "general_models_masssendfile_collection"
                ]
            )
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

            res = await _session.execute(query)

            guests = res.fetchall()

        start_users_count = len([guest for guest in guests if guest[0].is_active == True])

        image_video_group = None

        if list(images+videos):
            image_video_group = MediaGroupBuilder(images+videos, caption=mass_message_text)
        
        files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
        file_group = None
        if files:
            file_group = MediaGroupBuilder(files)

        active_tg_id_update_list = []
        unactive_tg_id_update_list = []

        for guest in guests:
            try:
                guest = guest[0]
                _tg_id = guest.tg_id
                if image_video_group is not None:
                    mb1 = await bot.send_media_group(_tg_id, media=image_video_group.build())
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
            except Exception as ex:
                print(f'{ex} ❌')
                if guest.is_active:
                    unactive_tg_id_update_list.append(_tg_id)
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
        
        async with db_session as _session:
            try:
                if active_tg_id_update_list:
                    await _session.execute(active_update_query)
                if unactive_tg_id_update_list:
                    await _session.execute(unactive_update_query)
                await _session.commit()
                _text = ''
            except Exception as ex:
                await _session.rollback()
                _text = ''
                print('send error', ex)
            finally:
                execute_time = end_send_time - start_send_time

                _valid_time = round(execute_time / 60 / 60, 2)

                if _valid_time == 0:
                    valid_time = f'{round(execute_time)} (время в секундах)'
                else:
                    valid_time = f'{_valid_time} (время в часах)'

                async with db_session as _session:
                    # end_active_users_count = _session.query(Guest.tg_id).where(Guest.is_active == True).count()
                    stmt = select(
                        func.count(Guest.tg_id)
                        )\
                        .where(
                            Guest.is_active.is_(True)
                            )
                    result = await _session.execute(stmt)
                    end_active_users_count = result.scalar_one()

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


async def try_send_order(bot: Bot,
                         session: AsyncSession,
                         user_id: int,
                         order_id: int,
                         order_status: str | None):
    async with session as _session:
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

        res = await _session.execute(query)

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

            except Exception as ex:
                print(ex)
            
            return

        if chat_link is None:
            print('делаю пост запрос')

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

                async with session as _session:
                    try:
                        await _session.execute(update(Guest)\
                                        .where(Guest.tg_id == user_id)\
                                        .values(chat_link=chat_link))
                        await _session.commit()
                    except Exception as ex:
                        print(ex, 'не получилось отправить, проблема на нашей стороне')
                        try:
                            await _session.rollback()
                            result_text = f'❌Сообщение с ссылкой на MoneyPort не получилось отправить пользователю {user_id}, проблема на нашей стороне'
                            
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