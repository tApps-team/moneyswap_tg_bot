import json
import asyncio
import redis.asyncio as redis

from db.base import async_session_maker
from .bot import bot
from .redis_handlers import BACKGROUND_TASK_DICT

from config import REDIS_HOST, REDIS_PASSWORD


async def redis_listener():
    r = redis.Redis(host=REDIS_HOST,
                    password=REDIS_PASSWORD,
                    port=6379)

    pubsub = r.pubsub()
    await pubsub.subscribe("review_notifications")

    async for message in pubsub.listen():

        if message["type"] != "message":
            continue

        data = json.loads(message["data"])

        event = message["event"]

        background_task = BACKGROUND_TASK_DICT.get(event)

        if not background_task:
            return

        print(f'запустил из redis`a {event} задачу...')

        await background_task(
            user_id=int(data["user_id"]),
            exchange_id=int(data["exchange_id"]),
            review_id=int(data["review_id"]),
            session=async_session_maker(),
            bot=bot
        )