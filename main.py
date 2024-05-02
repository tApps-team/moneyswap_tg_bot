import asyncio

from uvicorn import Config, Server

from fastapi import FastAPI

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import engine, session

from middlewares.db import DbSessionMiddleware

from config import TOKEN, db_url, PUBLIC_URL
from handlers import main_router


#DATABASE
# engine = create_engine(db_url,
#                        echo=True)

# Base.prepare(engine, reflect=True)

# session = sessionmaker(engine, expire_on_commit=False)


#TG BOT
bot = Bot(TOKEN)

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


#For set webhook
WEBHOOK_PATH = f'/{TOKEN}'

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


# async def main():
#     # bot = Bot(TOKEN)
#     # dp = Dispatcher()
#     dp.include_router(main_router)

#     engine = create_engine(db_url,
#                            echo=True)

#     Base.prepare(engine, reflect=True)

#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)


# if __name__ == '__main__':
#     asyncio.run(main())
if __name__ == '__main__':
    event_loop.run_until_complete(server.serve())