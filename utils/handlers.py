from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from sqlalchemy import update, select, insert
from sqlalchemy.orm import Session

from db.base import Base

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
                           session: Session,
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
            session.execute(update(MassSendImage).where(MassSendImage.id==image.id).values(file_id=image_file_id))

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
            session.execute(update(MassSendVideo).where(MassSendVideo.id==video.id).values(file_id=video_file_id))

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
            session.execute(update(MassSendFile).where(MassSendFile.id==file.id).values(file_id=file_file_id))

    session.commit()



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
            

def get_exchange_name(review_msg_dict: dict,
                      session: Session):
    # marker = review_msg_dict.get('marker')
    exchange_name = review_msg_dict.get('exchange_name')

    # if marker and exchange_id:
    #     match marker:
    #         case 'no_cash':
    #             Exchange = Base.classes.no_cash_exchange
    #         case 'both':
    #             Exchange = Base.classes.no_cash_exchange
    #         case 'cash':
    #             Exchange = Base.classes.no_cash_exchange
    #         case 'partner':
    #             Exchange = Base.classes.no_cash_exchange
    if exchange_name:

        for exchange_model, marker in ((Base.classes.no_cash_exchange, 'no_cash'),
                                       (Base.classes.cash_exchange, 'cash'),
                                       (Base.classes.partners_exchange, 'partner')):
            query = (
                select(
                    exchange_model.id,
                )\
                .where(
                    exchange_model.name == exchange_name,
                    )
            )
            # with session as _session:
            res = session.execute(query)

            exchange_id = res.scalar_one_or_none()
            
            if exchange_id:
                return (
                    exchange_id,
                    marker,
                )
    

def try_activate_admin_exchange(user_id: int,
                                session: Session):
    AdminExchangeOrder = Base.classes.general_models_exchangeadminorder
    AdminExchange = Base.classes.general_models_exchangeadmin
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
               AdminExchangeOrder.moderation == True)
    )
    # with session as _session:
    res = session.execute(order_check_query)

    _order = res.scalar_one_or_none()

    if not _order:
            # return
        
            # with session as _session:
        res = session.execute(moderated_order_check_query)

        moderated_order = res.scalar_one_or_none()

        if not moderated_order:
            return 'empty'
        else:
            return 'exists'

    for _exchange_marker, _exchange in (('no_cash', Base.classes.no_cash_exchange),
                                      ('cash', Base.classes.cash_exchange),
                                      ('partner', Base.classes.partners_exchange)):
        query = (
            select(
                _exchange
            )\
            .where(
                _exchange.name == _order.exchange_name,
            )
        )
        # with session as _session:
        res = session.execute(query)

        res_exchange = res.scalar_one_or_none()

        if res_exchange:
            insert_data = {
                'user_id': user_id,
                'exchange_name': res_exchange.name,
                'exchange_id': res_exchange.id,
                'exchange_marker': _exchange_marker,
            }
            insert_query = (
                insert(
                    AdminExchange
                )\
                .values(**insert_data)
            )
            session.execute(insert_query)
            record_added = True

        if record_added:
            _order.moderation = True
            try:
                session.commit()
            except Exception as ex:
                print('ERROR WITH ADMIN ADD EXCHANGE', ex)
                session.rollback()
                return 'error'
            else:
                return _order.exchange_name
        else:
            return 'error'