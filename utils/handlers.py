from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from sqlalchemy import update, select, insert, delete, and_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import Base

from keyboards import (create_add_comment_kb,
                       create_start_inline_keyboard,
                       add_switch_language_btn,
                       create_add_review_kb)

from .multilanguage import start_text_dict


start_text = '💱<b>Добро пожаловать в MoneySwap!</b>\n\nНаш бот поможет найти лучшую сделку под вашу задачу 💸\n\n👉🏻 <b>Чтобы начать поиск</b>, выберите категорию “безналичные”, “наличные” или “Swift/Sepa” и нажмите на нужную кнопку ниже.\n\nЕсли есть какие-то вопросы, обращайтесь <a href="https://t.me/MoneySwap_support">Support</a> или <a href="https://t.me/moneyswap_admin">Admin</a>. Мы всегда готовы вам помочь!'


async def consctruct_start_massage(user_id: int,
                                   select_language: str,
                                   session: AsyncSession,
                                   chat_link: str = None):
    """
    Возвращает стартовое сообщение и клавиатуру

    Returns:
        tuple: Кортеж вида:
        (
            _start_text,
            start_kb,
        )
    """

    _start_text = start_text_dict.get('ru') if select_language == 'ru'\
          else start_text_dict.get('en')
    
    start_kb = create_start_inline_keyboard(user_id,
                                            select_language)
    start_kb = add_switch_language_btn(start_kb,
                                       select_language)

    if chat_link:
        if select_language == 'ru':
            chat_link_text = f'Cсылка на чата по Вашим обращениям -> {chat_link}'
        else:
            chat_link_text = f'Link to chat for your requests -> {chat_link}'
        
        _start_text += f'\n\n{chat_link_text}'
    else:
        Guest = Base.classes.general_models_guest

        chat_link_query = (
            select(
                Guest.chat_link,
            )\
            .where(
                Guest.tg_id == user_id
            )
        )
        async with session as _session:
            res = await _session.execute(chat_link_query)

            chat_link = res.scalar_one_or_none()
        
        if chat_link:
            if select_language == 'ru':
                chat_link_text = f'Cсылка на чата по Вашим обращениям -> {chat_link}'
            else:
                chat_link_text = f'Link to chat for your requests -> {chat_link}'
            
            _start_text += f'\n\n{chat_link_text}'

    return (
        _start_text,
        start_kb,
    )


async def construct_add_review_message(review_msg_dict: dict,
                                       session: AsyncSession,
                                       select_language: str) -> tuple:
    """
    Возвращает сообщение для добавления отзыва, клавиатуру и возможную блокировку сообщения

    Returns:
        tuple: Кортеж вида:
        (
            _text,
            _kb,
            blocked_add_review,
        )
    """
    async with session as _session:
        exchange_data = await get_exchange_data(review_msg_dict,
                                                _session)
    if exchange_data is not None:
        exchange_id, exchange_name = exchange_data
        _kb = create_add_review_kb(exchange_id,
                                   select_language).as_markup()

        if select_language == 'ru':
            _text = f'Оставить отзыв на обменник <b>{exchange_name}</b>'
        else:
            _text = f'Add review to exchanger <b>{exchange_name}</b>'
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

    return (
        _text,
        _kb,
        blocked_add_review,
    )


async def construct_add_comment_message(comment_msg_dict: dict,
                                       session: AsyncSession,
                                       select_language: str) -> tuple:
    """
    Возвращает сообщение для добавления комментария, клавиатуру и возможную блокировку сообщения

    Returns:
        tuple: Кортеж вида:
        (
            _text,
            _kb,
            blocked_add_comment,
        )
    """
    async with session as _session:
        exchange_data = await get_exchange_data(comment_msg_dict,
                                                _session)
    if exchange_data is not None:
        exchange_id, exchange_name = exchange_data
        
        _kb = create_add_comment_kb(comment_msg_dict,
                                    select_language).as_markup()

        if select_language == 'ru':
            _text = f'Оставить комментарий на обменник <b>{exchange_name}</b>'
        else:
            _text = f'Add comment to exchanger <b>{exchange_name}</b>'
        # for blocked comment
        blocked_add_comment = (_text, exchange_id, comment_msg_dict.get('review_id'))
    else:
        _kb = None

        if select_language == 'ru':
            _text = 'Не удалось найти обменник для комментария'
        else:
            _text = 'Exchanger to add comment not found'
        # for blocked comment
        blocked_add_comment = (_text, )

    return (
        _text,
        _kb,
        blocked_add_comment,
    )


async def construct_activate_exchange_admin_message(user_id: int,
                                                    session: AsyncSession) -> str:
    """
    Возвращает информативное сообщение об активации админа обменника

    Returns:
        text: str
    """
    async with session as _session:
        has_added = await try_activate_admin_exchange(user_id,
                                                      session=_session)
    
    match has_added:
            case 'empty':
                text = f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы'
            case 'error':
                text = f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>'
            case 'exists':
                text = f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>'
            case _:
                text = f'✅Обменник {has_added} успешно привязан к вашему профилю'

    return text


async def construct_activate_partner_exchange_admin_message(user_id: int,
                                                            session: AsyncSession) -> str:
    """
    Возвращает информативное сообщение об активации админа обменника из партнерского кабинета

    Returns:
        text: str
    """
    async with session as _session:
        has_added = await try_activate_partner_admin_exchange(user_id,
                                                                session=_session)
        
    match has_added:
            case 'empty':
                text = f'❗️К сожалению, не смогли найти подходящую заявку на подключения, связитесь с <a href="https://t.me/MoneySwap_support">тех.поддержкой</a> для решения проблемы'
            case 'error':
                text = f'❗️Возникли сложности, обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>'
            case 'exists':
                text = f'✔️Заявка уже была обработана\nЕсли Вы всё равно столкнулись с проблемами обратитесь в <a href="https://t.me/MoneySwap_support">тех.поддержку</a>'
            case _:
                text = f'✅Обменник {has_added} успешно привязан к вашему профилю'

    return text


async def try_add_file_ids_to_db(message: types.Message,
                                 session: Session,
                                 bot: Bot,
                                 obj):
    MassSendImage = Base.classes.general_models_masssendimage

    # # images = select(MassSendMessage).options(joinedload(MassSendMessage.images))

    for image in obj.general_models_masssendimage_collection:
        # update_image_list = []
        if image.file_id is None:
            image_file = types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{image.image}')
            # upload image to telegram server
            loaded_image = await message.answer_photo(image_file)
            # delete image message from chat
            # await message.delete()
            await bot.delete_message(message.chat.id, loaded_image.message_id)

            image_file_id = loaded_image.photo[0].file_id
            print(image.id, image_file_id)
            session.execute(update(MassSendImage).where(MassSendImage.id==image.id).values(file_id=image_file_id))
    #         # image_dict = {
    #         #     'id': image.id,
    #         #     'file_id': image_file_id,
    #         # }
    #         # update_image_list.append(image_dict)
    # # if update_image_list:
    #     # session.execute(update(MassSendImage),
    #     #                 update_image_list)
    #     # session.bulk_update_mappings(
    #     #     MassSendImage,
    #     #     update_image_list,
    #     # )
    session.commit()

    MassSendVideo = Base.classes.general_models_masssendvideo

    for video in obj.general_models_masssendvideo_collection:
        update_video_list = []
        if video.file_id is None:
            video_file = types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{video.video}')
            # upload image to telegram server
            loaded_video = await message.answer_video(video_file,
                                                      width=1920,
                                                      height=1080)
            print('*' * 10)
            print(loaded_video)
            print('*' * 10)
            # delete image message from chat
            await message.delete()
            await bot.delete_message(message.chat.id, loaded_video.message_id)

            video_file_id = loaded_video.video.file_id
            session.execute(update(MassSendVideo).where(MassSendVideo.id==video.id).values(file_id=video_file_id))
    #         print(video.id, video_file_id)
    session.commit()
    #         video_dict = {
    #             'id': video.id,
    #             'file_id': video_file_id,
    #         }
    #         update_video_list.append(video_dict)
    # if update_video_list:
    #     session.bulk_update_mappings(
    #         MassSendVideo,
    #         update_video_list,
    #     )
    #     # session.flush(obj.general_models_masssendimage_collection)
    # session.commit()

    MassSendFile = Base.classes.general_models_masssendfile
    for file in obj.general_models_masssendfile_collection:
        # update_image_list = []
        if file.file_id is None:
            file_file = types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{file.file}')
            # upload image to telegram server
            loaded_file = await message.answer_document(file_file)
            print('FILE')
            print(loaded_file)
            # delete image message from chat
            # await message.delete()
            await bot.delete_message(message.chat.id, loaded_file.message_id)

            file_file_id = loaded_file.document.file_id
            print(file.id, file_file_id)
            session.execute(update(MassSendFile).where(MassSendFile.id==file.id).values(file_id=file_file_id))
            session.commit()
    # session.refresh(obj)
    # images = [(image.id, image.file_id, types.InputMediaPhoto(media=types.FSInputFile(path=f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{image.image}'))) for image in m.general_models_masssendimage_collection]
    # for image in images:
    #     if image[1] is None:
    #         # upload image to telegram server
    #         loaded_image = await message.answer_photo(image[-1].media)
    #         # delete image message from chat
    #         await bot.delete_message(message.chat.id, message.message_id)
    #         image_file_id = loaded_image.photo[0].file_id
    #         print(image[0], image_file_id)
    #         image_dict = {
    #             'id': image[0],
    #             'file_id': image_file_id,
    #         }
    #         update_image_list.append(image_dict)
    #     else:
    #         print('из БД', image[1])
    # if update_image_list:
    #     session.bulk_update_mappings(
    #         MassSendImage,
    #         update_image_list,
    #     )
    #     session.commit()
    #     session.flush(obj.general_models_masssendimage_collection)


async def try_add_file_ids(bot: Bot,
                           session: AsyncSession,
                           obj):
    MassSendImage = Base.classes.general_models_masssendimage
    for image in obj.general_models_masssendimage_collection:
        if image.file_id is None:
            # _path = f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{image.image}'
            _path = f'https://api.moneyswap.online/media/{image.image}'

            print(_path)
            # image_file = types.FSInputFile(path=_path)
            image_file = types.URLInputFile(url=_path)

            # upload image to telegram server
            loaded_image = await bot.send_photo(686339126, image_file)
            print(loaded_image)
            # delete image message from chat
            await bot.delete_message(loaded_image.chat.id, loaded_image.message_id)

            image_file_id = loaded_image.photo[0].file_id
            print(image.id, image_file_id)
            await session.execute(update(MassSendImage).where(MassSendImage.id==image.id).values(file_id=image_file_id))

    MassSendVideo = Base.classes.general_models_masssendvideo
    for video in obj.general_models_masssendvideo_collection:
        if video.file_id is None:
            # _path = f'/home/skxnny/web/backup_bestexchange/django_fastapi/media/{video.video}'
            _path = f'https://api.moneyswap.online/media/{video.video}'
            print(_path)
            video_file = types.URLInputFile(url=_path)
            # upload video to telegram server
            loaded_video = await bot.send_video(686339126,
                                                video_file,
                                                width=1920,
                                                height=1080)
            # delete image message from chat
            await bot.delete_message(loaded_video.chat.id, loaded_video.message_id)

            video_file_id = loaded_video.video.file_id
            await session.execute(update(MassSendVideo).where(MassSendVideo.id==video.id).values(file_id=video_file_id))

    MassSendFile = Base.classes.general_models_masssendfile
    for file in obj.general_models_masssendfile_collection:
        if file.file_id is None:
            _path = f'https://api.moneyswap.online/media/{file.file}'

            file_file = types.URLInputFile(url=_path)
            # upload file to telegram server
            loaded_file = await bot.send_document(686339126,
                                                file_file)
            # delete image message from chat
            await bot.delete_message(loaded_file.chat.id, loaded_file.message_id)

            file_file_id = loaded_file.document.file_id
            print(file.id, file_file_id)
            await session.execute(update(MassSendFile).where(MassSendFile.id==file.id).values(file_id=file_file_id))

    await session.commit()



async def swift_sepa_data(state: FSMContext):
    # res = []
    data = await state.get_data()
    request_text = 'Оплатить платеж' if data['request_type'] == 'pay' else 'Принять платеж'
    # res.append(request_type)
    request_type = f"Тип заявки: {request_text}"
    country = f"Страна: {data['country']}"
    amount = f"Сумма: {data['amount']}"
    task_text = f"Комментарий: {data['task_text']}"
    res = '\n'.join(
        (request_type,
         country,
         amount,
         task_text),
        )
    return res


def validate_amount(amount_text: str):
    len_amount_text = len(amount_text.split())

    if len_amount_text == 1:
        if amount_text.isdigit():
            return True
        elif amount_text[1:].isdigit():
            return True
        elif amount_text[:-1].isdigit():
            return True
        else:
            return False
    else:
        amount_list = amount_text.split()
        
        for amount_el in amount_list:
            if amount_el.isdigit():
                return True
            

async def get_exchange_data(review_msg_dict: dict,
                            session: AsyncSession):

    exchange_id = review_msg_dict.get('exchange_id')

    if exchange_id:

        Exchanger = Base.classes.general_models_exchanger
        
        query = (
            select(
                Exchanger.name,
            )\
            .where(
                Exchanger.id == exchange_id,
                )
        )

        res = await session.execute(query)

        exchange_name = res.scalar_one_or_none()
        
        if exchange_name:            
            return (
                exchange_id,
                exchange_name,
            )
    

async def try_activate_admin_exchange(user_id: int,
                                      session: AsyncSession):
    AdminExchangeOrder = Base.classes.general_models_newexchangeadminorder
    AdminExchange = Base.classes.general_models_newexchangeadmin
    record_added = False

    order_check_query = (
        select(
            AdminExchangeOrder
        )\
        .where(AdminExchangeOrder.user_id == user_id,
               AdminExchangeOrder.moderation == False)
    )
    moderated_order_check_query = (
        select(
            AdminExchangeOrder
        )\
        .where(AdminExchangeOrder.user_id == user_id,
               AdminExchangeOrder.moderation == True)\
               .order_by(
                   AdminExchangeOrder.time_create.desc(),
               )
    )

    res = await session.execute(order_check_query)

    _order = res.scalar_one_or_none()

    if not _order:

        res = await session.execute(moderated_order_check_query)

        moderated_order = res.scalar_one_or_none()

        if not moderated_order:
            return 'empty'
        else:
            return 'exists'

    Exchanger = Base.classes.general_models_exchanger
    
    query = (
        select(
            Exchanger
        )\
        .where(
            Exchanger.id == _order.exchange_id,
        )
    )

    res = await session.execute(query)

    exchanger = res.scalar_one_or_none()

    if exchanger:
        insert_data = {
            'user_id': user_id,
            'exchange_id': exchanger.id,
            'notification': True,
        }
        insert_query = (
            insert(
                AdminExchange
            )\
            .values(**insert_data)
        )
        await session.execute(insert_query)
        record_added = True

    if record_added:
        _order.moderation = True
        try:
            await session.commit()
        except Exception as ex:
            print('ERROR WITH ADMIN ADD EXCHANGE', ex)
            await session.rollback()
            return 'error'
        else:
            return exchanger.name
    else:
        return 'error'
    

# try_activate_partner_admin_exchange

async def try_activate_partner_admin_exchange(user_id: int,
                                              session: AsyncSession):
    AdminExchangeOrder = Base.classes.general_models_newexchangeadminorder
    AdminExchange = Base.classes.general_models_newexchangeadmin
    record_added = False

    order_check_query = (
        select(
            AdminExchangeOrder
        )\
        .where(AdminExchangeOrder.user_id == user_id,
               AdminExchangeOrder.moderation == False)
    )
    moderated_order_check_query = (
        select(
            AdminExchangeOrder
        )\
        .where(AdminExchangeOrder.user_id == user_id,
               AdminExchangeOrder.moderation == True)\
               .order_by(
                   AdminExchangeOrder.time_create.desc(),
               )
    )

    res = await session.execute(order_check_query)

    _order = res.scalar_one_or_none()

    if not _order:

        res = await session.execute(moderated_order_check_query)

        moderated_order = res.scalar_one_or_none()

        if not moderated_order:
            return 'empty'
        else:
            return 'exists'

    Exchanger = Base.classes.general_models_exchanger
    
    query = (
        select(
            Exchanger
        )\
        .where(
            Exchanger.id == _order.exchange_id,
        )
    )

    res = await session.execute(query)

    exchanger = res.scalar_one_or_none()

    if exchanger:
        check_delete = (
            delete(
                AdminExchange
            )\
            .where(
                and_(
                    AdminExchange.exchange_id == exchanger.id,
                )
            )
        )

        await session.execute(check_delete)
        
        insert_data = {
            'user_id': user_id,
            'exchange_id': exchanger.id,
            'notification': True,
        }
        insert_query = (
            insert(
                AdminExchange
            )\
            .values(**insert_data)
        )
        await session.execute(insert_query)
        record_added = True

    if record_added:
        _order.moderation = True
        try:
            await session.commit()
        except Exception as ex:
            print('ERROR WITH ADMIN ADD EXCHANGE', ex)
            await session.rollback()
            return 'error'
        else:
            return exchanger.name
    else:
        return 'error'
