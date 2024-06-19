import os

from aiogram import Router, types, Bot, F
from aiogram.types import BufferedInputFile, URLInputFile
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from pyrogram import Client

from sqlalchemy.orm import Session, joinedload, sessionmaker
from sqlalchemy import insert, select, update

from keyboards import create_start_keyboard, create_swift_start_kb, add_cancel_btn_to_kb, create_kb_to_main

from states import SwiftSepaStates

from utils.handlers import try_add_file_ids_to_db, try_add_file_ids, swift_sepa_data

from db.base import Base


main_router = Router()

start_text = '💱<b>Добро пожаловать в MoneySwap!</b>\n\nНаш бот поможет найти лучшую сделку под вашу задачу 💸\n\n👉🏻 <b>Чтобы начать поиск</b>, выберите категорию “безналичные”, “наличные” или “Swift/Sepa” и нажмите на нужную кнопку ниже.\n\nЕсли есть какие-то вопросы, обращайтесь [поддержка]. Мы всегда готовы вам помочь!'



# api_id = 25776470
# api_hash = 'd60713b9c6b73973ad06827530d4ed8f'
# api_client = Client('my_account',
#                     api_id=api_id,
#                     api_hash=api_hash)



@main_router.message(Command('start'))
async def start(message: types.Message,
                session: Session,
                state: FSMContext,
                bot: Bot):
    state_data = await state.get_data()
    prev_start_msg = state_data.get('start_msg')

    if not prev_start_msg:
        # await bot.delete_message(message.chat.id,
        #                          start_msg)
        
        Guest = Base.classes.general_models_guest

        tg_id = message.from_user.id
        guest = session.query(Guest).where(Guest.tg_id == tg_id).first()
        # print(guest)
        if not guest:
            value_dict = {
                'username': message.from_user.username,
                'tg_id': tg_id,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name,
                'language_code': message.from_user.language_code,
                'is_premium': bool(message.from_user.is_premium),
                'is_active': True,
            }
            session.execute(insert(Guest).values(**value_dict))
            session.commit()
    start_kb = create_start_keyboard(message.from_user.id)
    start_msg = await message.answer(start_text,
                                    parse_mode='html',
                                    reply_markup=start_kb.as_markup(resize_keyboard=True,
                                                                    is_persistent=True))
    await state.update_data(start_msg=start_msg.message_id)
    try:
        await bot.delete_message(message.chat.id,
                                prev_start_msg)
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass


@main_router.message(F.text == 'Swift/Sepa')
async def start_swift_sepa(message: types.Message,
                           state: FSMContext):
    await state.set_state(SwiftSepaStates.request_type)

    swift_start_kb = create_swift_start_kb()
    kb = add_cancel_btn_to_kb(swift_start_kb)

    state_msg = await message.answer('<b>Выберите тип заявки</b>',
                         reply_markup=kb.as_markup())
    
    await state.update_data(state_msg=state_msg)
    await message.delete()


@main_router.callback_query(F.data.in_(('cancel', 'to_main')))
async def back_to_main(callback: types.CallbackQuery,
                       state: FSMContext,
                       session: Session,
                       bot: Bot):
    state_data = await state.get_data()
    start_msg = state_data.get('start_msg')
    await state.clear()
    
    if start_msg:
        await state.update_data(start_msg=start_msg)
    
    await start(callback.message,
                session,
                state,
                bot)


@main_router.callback_query(F.data == 'send_app')
async def send_app(callback: types.CallbackQuery,
                   session: Session,
                   state: FSMContext,
                   bot: Bot,
                   api_client: Client):
    data = await state.get_data()
    state_process = data.get('state_process')
    username = callback.message.from_user.username
    print(username)
    print(callback.message.chat.id)
    print(callback.message.from_user.id)
    print(callback.from_user.id)

    async with api_client as app:
        super_group = await app.create_supergroup(title=f'HelpChat|{username}')
        chat_link = await app.create_chat_invite_link(super_group.id,
                                                      name=f'HelpChat|{username}')
    if state_process is not None:
        await bot.send_message(super_group.id,
                               state_process)

    print(super_group)
    print(super_group.__dict__)
    print(chat_link.invite_link)
    # _chat = await callback.message.chat.create_invite_link(name='22qwerty')
    # _chat.invite_link
    # chat_link = await bot.create_chat_invite_link(chat_id=callback.message.chat.id,
    #                                               name=f'Чат по заявке 22| {username}')
    await callback.answer(text='Ваша заявка успешно отправлена!',
                          show_alert=True)
    # await callback.message.answer(text= _chat.invite_link)
    await callback.message.answer(f'Ссылка на чат по Вашему обращению -> {chat_link.invite_link}')
    await start(callback.message,
                session,
                state,
                bot)


@main_router.callback_query(F.data.in_(('pay_payment', 'access_payment')))
async def request_type_state(callback: types.CallbackQuery,
                             session: Session,
                             state: FSMContext,
                             bot: Bot):
    data = await state.get_data()
    state_msg: types.Message = data.get('state_msg')
    request_type = 'Оплатить платеж' if callback.data == 'pay_payment' else 'Принять платеж'
    state_process = f'Тип заявки: {request_type}'
    await state.update_data(state_process=state_process)
    # print(state_msg)
    await state.update_data(request_type=callback.data)

    await state.set_state(SwiftSepaStates.country)

    kb = add_cancel_btn_to_kb()

    await state_msg.edit_text(f'{state_process}\n<b>Введите страну...</b>',
                              reply_markup=kb.as_markup())
    # await callback.message.answer('Введите страну...')

    # await callback.message.delete()


@main_router.message(SwiftSepaStates.country)
async def country_state(message: types.Message,
                        session: Session,
                        state: FSMContext,
                        bot: Bot):
    data = await state.get_data()
    state_msg: types.Message = data.get('state_msg')
    await state.update_data(country=message.text)

    state_process = data.get('state_process')
    state_process += f'\nСтрана: {message.text}'
    await state.update_data(state_process=state_process)

    await state.set_state(SwiftSepaStates.amount)

    kb = add_cancel_btn_to_kb()

    await state_msg.edit_text(f'{state_process}\n<b>Введите сумму...</b>',
                              reply_markup=kb.as_markup())
    # await message.answer('Введите сумму...')

    await message.delete()


@main_router.message(SwiftSepaStates.amount)
async def amount_state(message: types.Message,
                       session: Session,
                       state: FSMContext,
                       bot: Bot):
    data = await state.get_data()
    state_msg: types.Message = data.get('state_msg')

    await state.update_data(amount=message.text)

    state_process = data.get('state_process')
    state_process += f'\nСумма: {message.text}'
    await state.update_data(state_process=state_process)

    await state.set_state(SwiftSepaStates.task_text)

    kb = add_cancel_btn_to_kb()

    await state_msg.edit_text(f'{state_process}\n<b>Опишите задачу, чтобы менеджеры могли быстрее все понять и оперативно начать выполнение...</b>',
                              reply_markup=kb.as_markup())
    # await message.answer('Напишите подробности операции...')

    await message.delete()


@main_router.message(SwiftSepaStates.task_text)
async def task_text_state(message: types.Message,
                          session: Session,
                          state: FSMContext,
                          bot: Bot,
                          api_client: Client):
    data = await state.get_data()
    state_msg: types.Message = data.get('state_msg')

    await state.update_data(task_text=message.text)

    state_process = data.get('state_process')
    state_process += f'\nКомментарий: {message.text}'
    await state.update_data(state_process=state_process)

    # preview_response_text = await swift_sepa_data(state)

    kb = create_kb_to_main()

    # async with api_client as app:
    #     channel = await app.create_channel(title='Test111')
    #     chat_link = await app.create_chat_invite_link(channel.id)

    # print(channel)
    # print(channel.__dict__)
    # print(chat_link.invite_link)


    # chat_link = await bot.create_chat_invite_link(chat_id=channel.id,
    #                                   name='test_link')
    
    # await message.answer(text=chat_link.invite_link)

    await state_msg.edit_text(f'{state_process}\n<b>Заполнение окончено.</b>',
                              reply_markup=kb.as_markup())
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


async def send_mass_message(bot: Bot,
                            session: Session):
        with session as session:
            Guest = Base.classes.general_models_guest
            # session: Session

            # get MassSendMessage model from DB
            MassSendMessage = Base.classes.general_models_masssendmessage
            mass_message = session.query(MassSendMessage)\
                                    .options(joinedload(MassSendMessage.general_models_masssendimage_collection),
                                             joinedload(MassSendMessage.general_models_masssendvideo_collection))\
                                    .first()
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
                                                        # .replace('<span', '<span class="tg-spoiler"')

            print(mass_message_text)

            images = [types.InputMediaPhoto(media=image.file_id) for image in mass_message.general_models_masssendimage_collection]
            videos = [types.InputMediaVideo(media=video.file_id) for video in mass_message.general_models_masssendvideo_collection]

            image_video_group = None
            if list(images+videos):
                image_video_group = MediaGroupBuilder(images+videos, caption=mass_message_text)
            
            files = [types.InputMediaDocument(media=file.file_id) for file in mass_message.general_models_masssendfile_collection]
            file_group = None
            if files:
                file_group = MediaGroupBuilder(files)

            try:
                if image_video_group is not None:
                    mb1 = await bot.send_media_group('686339126', media=image_video_group.build())
                    print('MB1', mb1)
                if file_group is not None:
                    mb2 = await bot.send_media_group('686339126', media=file_group.build())    
                    print('MB2', mb2)
                guest = session.query(Guest).where(Guest.tg_id == '686339126').first()
                if not guest.is_active:
                   session.execute(update(Guest).where(Guest.tg_id == '686339126').values(is_active=True))
                   session.commit()
            except Exception:
                session.execute(update(Guest).where(Guest.tg_id == '686339126').values(is_active=False))
                session.commit()
            
            session.close()
