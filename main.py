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

from db.base import engine, session, Base

from middlewares.db import DbSessionMiddleware

from config import (TOKEN,
                    db_url,
                    PUBLIC_URL,
                    API_ID,
                    API_HASH,
                    REDIS_HOST,
                    REDIS_PASSWORD)
from handlers import main_router, send_mass_message, try_send_order


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
api_client = Client('my_account',
                    api_id=API_ID,
                    api_hash=API_HASH)
#####

dp = Dispatcher(storage=storage)
# dp = Dispatcher()
dp.include_router(main_router)

#Add session and database connection in handlers 
dp.update.middleware(DbSessionMiddleware(session_pool=session,
                                         api_client=api_client))


# FastAPI lifespan ('startup' and 'shutdown') 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который будет выполнен при старте приложения
    print("Приложение запускается...")
    await bot.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}",
                          drop_pending_updates=True,
                          allowed_updates=['message', 'callback_query'])
    
    yield  # Это место, где приложение будет работать
    # Код, который будет выполнен при остановке приложения
    await bot.delete_webhook()
    print("Приложение останавливается...")


#Initialize web server
app = FastAPI(docs_url='/docs_bot',
              lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# event_loop = asyncio.get_event_loop()
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

config = Config(app=app,
                loop=event_loop,
                host='0.0.0.0',
                port=8001)
server = Server(config)


fast_api_router = APIRouter(prefix='/bot_api')
# app.include_router(fast_api_router)

#For set webhook
WEBHOOK_PATH = f'/webhook'

#Set webhook and create database on start
# @app.on_event('startup')
# async def on_startup():
#     print('startup')
#     await bot.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}",
#                           drop_pending_updates=True,
#                           allowed_updates=['message', 'callback_query'])


# @app.on_event('shutdown')
# async def on_shutdown():
#     print('shutdown')
#     await bot.delete_webhook()
    
    # Base.prepare(engine, reflect=True)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Код, который будет выполнен при старте приложения
#     print("Приложение запускается...")
#     await bot.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}",
#                           drop_pending_updates=True,
#                           allowed_updates=['message', 'callback_query'])
    
#     yield  # Это место, где приложение будет работать
#     # Код, который будет выполнен при остановке приложения
#     await bot.delete_webhook()
#     print("Приложение останавливается...")

# app.lifespan = lifespan

# app.add_event_handler("startup", lambda: print("Событие старта приложения"))
# app.add_event_handler("shutdown", lambda: print("Событие остановки приложения"))



#Endpoint for checking
@app.get(WEBHOOK_PATH)
async def any():
    return {'status': 'ok'}


#Endpoint for incoming updates
@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    tg_update = types.Update(**update)
    await dp.feed_update(bot=bot, update=tg_update)


#Endpoint for mass send message
@app.get('/send_mass_message')
async def send_mass_message_for_all_users(name_send: str):
    await send_mass_message(bot=bot,
                            session=session(),
                            name_send=name_send)
    

@app.get('/test_swift_sepa')
async def test_swift_sepa(user_id: int,
                          order_id: int):
    await try_send_order(bot=bot,
                         session=session(),
                         user_id=user_id,
                         order_id=order_id)
    

# app.include_router(fast_api_router)
# fast_api_router = APIRouter()

# @fast_api_router.get('/test')
# async def test_api():
#     Guest = Base.classes.general_models_guest

#     # with session() as conn:
#     #     conn: Session
#     #     conn.query(Guest)
#     await bot.send_message('686339126', 'what`s up')
    
# app = FastAPI()

# bot = Bot(TOKEN, parse_mode="HTML")

###

# fast_api_router = APIRouter()

# @fast_api_router.get('/test')
# async def test_api():
#     Guest = Base.classes.general_models_guest

#     # with session() as conn:
#     #     conn: Session
#     #     conn.query(Guest)
#     await send_mass_message(bot=bot,
#                             session=session())
    # await bot.send_message('686339126', 'what`s up')

# app.include_router(fast_api_router)
    ###


# async def main():
#     # bot = Bot(TOKEN, parse_mode="HTML")
#     # w = await bot.get_my_commands()
#     # print(w)
#     # await bot.set_my_commands([
#     #     types.BotCommand(command='send',description='send mass message'),
#     # ])
#     # w = await bot.get_my_commands()
#     # print(w)


#     api_client = Client('my_account',
#                         api_id=API_ID,
#                         api_hash=API_HASH)



#     dp = Dispatcher()
#     dp.include_router(main_router)
#     dp.update.middleware(DbSessionMiddleware(session_pool=session,
#                                              api_client=api_client))

#     # engine = create_engine(db_url,
#     #                        echo=True)

#     # Base.prepare(engine, reflect=True)
    

#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)


# if __name__ == '__main__':
    # uvicorn.run('main:app', host='0.0.0.0', port=8001)
    # asyncio.run(main())
    # event_loop.run_until_complete(server.serve())
if __name__ == '__main__':
    event_loop.run_until_complete(server.serve())