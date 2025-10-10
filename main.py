import asyncio

import redis

import redis.asyncio
import redis.asyncio.client
from uvicorn import Config, Server

from pyrogram import Client

from starlette.middleware.cors import CORSMiddleware

from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.base import engine, Base, async_session_maker, init_models

from middlewares.db import DbSessionMiddleware

from config import (TOKEN,
                    db_url,
                    PUBLIC_URL,
                    API_ID,
                    API_HASH,
                    REDIS_HOST,
                    REDIS_PASSWORD)
from handlers import (exchange_admin_direction_notification,
                      main_router,
                      new_send_comment_notification_to_review_owner,
                      new_send_notification_to_exchange_admin,
                      send_comment_notification_to_exchange_admin,
                      send_comment_notification_to_review_owner,
                      send_mass_message,
                      send_mass_message_test,
                      send_notification_to_exchange_admin,
                      try_send_order)
from schemas import ExchangeAdminNotification


###DEV###

#DATABASE
# engine = create_engine(db_url,
#                        echo=True)

# Base.prepare(engine, reflect=True)

# session = sessionmaker(engine, expire_on_commit=False)

#Initialize Redis storage
redis_client = redis.asyncio.client.Redis(host=REDIS_HOST,
                                          password=REDIS_PASSWORD)
storage = RedisStorage(redis=redis_client)


#TG BOT
# bot = Bot(TOKEN, parse_mode="HTML")
bot = Bot(TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

#####
# api_client = Client('my_account',
#                     api_id=API_ID,
#                     api_hash=API_HASH)
#####

dp = Dispatcher(storage=storage)
# dp = Dispatcher()
dp.include_router(main_router)

#Add session and database connection in handlers 
# dp.update.middleware(DbSessionMiddleware(session_pool=session,
#                                          api_client=api_client))
dp.update.middleware(DbSessionMiddleware(session_pool=async_session_maker))


# FastAPI lifespan ('startup' and 'shutdown') 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который будет выполнен при старте приложения
    print("Приложение запускается...")
    await bot.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}",
                          allowed_updates=['message', 'callback_query'])
                        #   drop_pending_updates=True,
    # Инициализация БД (reflection)
    await init_models()
    yield  # Это место, где приложение будет работать
    # Код, который будет выполнен при остановке приложения
    await bot.delete_webhook()
    print("Приложение останавливается...")


#Initialize web server
# app = FastAPI(docs_url='/docs_bot',
#               lifespan=lifespan)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # event_loop = asyncio.get_event_loop()
# event_loop = asyncio.new_event_loop()
# asyncio.set_event_loop(event_loop)

# config = Config(app=app,
#                 loop=event_loop,
#                 host='0.0.0.0',
#                 port=8001,
#                 lifespan='on')
# server = Server(config)


# fast_api_router = APIRouter(prefix='/bot_api')
# app.include_router(fast_api_router)

#For set webhook
WEBHOOK_PATH = f'/webhook'

#Endpoint for checking
# @app.get(WEBHOOK_PATH)
# async def any():
#     return {'status': 'ok'}


#Endpoint for incoming updates
# @app.post(WEBHOOK_PATH)
# async def bot_webhook(update: dict):
#     tg_update = types.Update(**update)
#     await dp.feed_update(bot=bot, update=tg_update)



async def main():
    await init_models()
    # bot = Bot(TOKEN,
    #         default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # dp = Dispatcher(storage=storage)
    # # dp = Dispatcher()
    # dp.include_router(main_router)

    # #Add session and database connection in handlers 
    # # dp.update.middleware(DbSessionMiddleware(session_pool=session,
    # #                                          api_client=api_client))
    # dp.update.middleware(DbSessionMiddleware(session_pool=async_session_maker))
    await dp.start_polling(bot)
#Endpoint for mass send message
# @app.get('/send_mass_message')
# async def send_mass_message_for_all_users(name_send: str):
#     await send_mass_message(bot=bot,
#                             db_session=session(),
#                             name_send=name_send)
    

# @app.get('/test_swift_sepa')
# async def test_swift_sepa(user_id: int,
#                           order_id: int,
#                           order_status: str = None):
#     return await try_send_order(bot=bot,
#                                 session=session(),
#                                 user_id=user_id,
#                                 order_id=order_id,
#                                 order_status=order_status)
    

# @app.get('/test_moder_send')
# async def test_moder_send(user_id: int,
#                           name_send: str):
#     await send_mass_message_test(bot=bot,
#                             session=session(),
#                             user_id=user_id,
#                             name_send=name_send)


# @app.get('/send_notification_to_exchange_admin')
# async def send_notification_to_admin(user_id: int,
#                                      exchange_id: int,
#                                      exchange_marker: str,
#                                      review_id: int):
#     await send_notification_to_exchange_admin(user_id,
#                                               exchange_id,
#                                               exchange_marker,
#                                               review_id,
#                                               session=session(),
#                                               bot=bot)
    

# @app.get('/new_send_notification_to_exchange_admin')
# async def new_send_notification_to_admin(user_id: int,
#                                      exchange_id: int,
#                                      review_id: int):
#     await new_send_notification_to_exchange_admin(user_id,
#                                               exchange_id,
#                                               review_id,
#                                               session=session(),
#                                               bot=bot)
    

# @app.get('/send_comment_notification_to_exchange_admin')
# async def send_notification_to_admin(user_id: int,
#                                      exchange_id: int,
#                                      exchange_marker: str,
#                                      review_id: int):
#     await send_comment_notification_to_exchange_admin(user_id,
#                                                       exchange_id,
#                                                       exchange_marker,
#                                                       review_id,
#                                                       session=session(),
#                                                       bot=bot)
    

# @app.get('/send_comment_notification_to_review_owner')
# async def send_notification_to_r_owner(user_id: int,
#                                        exchange_id: int,
#                                        exchange_marker: str,
#                                        review_id: int):
#     await send_comment_notification_to_review_owner(user_id,
#                                                     exchange_id,
#                                                     exchange_marker,
#                                                     review_id,
#                                                     session=session(),
#                                                     bot=bot)
    

# @app.get('/new_send_comment_notification_to_review_owner')
# async def new_send_notification_to_r_owner(user_id: int,
#                                        exchange_id: int,
#                                        review_id: int):
#     await new_send_comment_notification_to_review_owner(user_id,
#                                                     exchange_id,
#                                                     review_id,
#                                                     session=session(),
#                                                     bot=bot)
    

# @app.post('/exchange_admin_direction_notification')
# async def exchange_admin_notification(data: ExchangeAdminNotification):
#     await exchange_admin_direction_notification(data.user_id,
#                                                 data.text,
#                                                 bot=bot)


if __name__ == '__main__':
    # event_loop.run_until_complete(server.serve())
    asyncio.run(main())