import json
import asyncio
import redis.asyncio as redis

from db.base import async_session_maker
from .bot import bot
from .redis_handlers import new_send_review_notification_to_exchange_admin

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

        print('запустил из redis`a')

        await new_send_review_notification_to_exchange_admin(
            user_id=data["user_id"],
            exchange_id=data["exchange_id"],
            review_id=data["review_id"],
            session=async_session_maker(),
            bot=bot
        )