import asyncio

import uvicorn
from uvicorn import Config, Server

from fastapi import FastAPI, APIRouter

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.base import engine, session, Base

from middlewares.db import DbSessionMiddleware

from config import TOKEN, db_url, PUBLIC_URL
from handlers import main_router, send_mass_message


###DEV###

#DATABASE
# engine = create_engine(db_url,
#                        echo=True)

# Base.prepare(engine, reflect=True)

# session = sessionmaker(engine, expire_on_commit=False)


#TG BOT
bot = Bot(TOKEN, parse_mode="HTML")

dp = Dispatcher(storage=MemoryStorage())
dp.include_router(main_router)

#Add session and database connection in handlers 
dp.update.middleware(DbSessionMiddleware(session_pool=session))

#Initialize web server
app = FastAPI()
event_loop = asyncio.get_event_loop()
config = Config(app=app,
                loop=event_loop,
                host='0.0.0.0',
                port=8001)
server = Server(config)


fast_api_router = APIRouter(prefix='/bot_api')
app.include_router(fast_api_router)

#For set webhook
WEBHOOK_PATH = f'/webhook'

#Set webhook and create database on start
@app.on_event('startup')
async def on_startup():
    await bot.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}",
                          drop_pending_updates=True)
    
    # Base.prepare(engine, reflect=True)


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
@fast_api_router.get('/send_mass_message')
async def send_mass_message_for_all_users():
    await send_mass_message(bot=bot,
                            session=session())
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



#     dp = Dispatcher()
#     dp.include_router(main_router)
#     dp.update.middleware(DbSessionMiddleware(session_pool=session))

#     engine = create_engine(db_url,
#                            echo=True)

#     # Base.prepare(engine, reflect=True)

#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)


# if __name__ == '__main__':
#     uvicorn.run('main:app', host='0.0.0.0', port=8001)
#     asyncio.run(main())
    # event_loop.run_until_complete(server.serve())
if __name__ == '__main__':
    event_loop.run_until_complete(server.serve())