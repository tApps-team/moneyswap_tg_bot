from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from pyrogram import Client
# from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self,
                 session_pool: sessionmaker):
        super().__init__()
        self.session_pool = session_pool
        # self.api_client = api_client
        # self.engine = engine

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:

        with self.session_pool() as session:
            data["session"] = session

        # data['api_client'] = self.api_client
        
        return await handler(event, data)