from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from sqlalchemy import update
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