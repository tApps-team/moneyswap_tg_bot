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
    await pubsub.subscribe("notitication_events")

    async for message in pubsub.listen():

        if message["type"] != "message":
            continue

        data = json.loads(message["data"])

        event_from_data = data.get("event")

        print('EVENT',event_from_data)

        event = BACKGROUND_TASK_DICT(event_from_data)

        print('new EVENT',event)
        

        background_task = BACKGROUND_TASK_DICT.get(event)

        if not background_task:
            print(f'не нашел фоновую задачу {event_from_data}!!!')
            print(BACKGROUND_TASK_DICT.keys())
            return

        print(f'запустил из redis`a {event_from_data} задачу...')

        await background_task(
            user_id=int(data["user_id"]),
            exchange_id=int(data["exchange_id"]),
            review_id=int(data["review_id"]),
            session=async_session_maker(),
            bot=bot
        )