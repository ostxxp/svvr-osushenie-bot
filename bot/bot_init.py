import asyncio
import logging

from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError, TelegramServerError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RetryRequestMiddleware:
    async def __call__(self, make_request, bot, method):
        delays = (1, 2, 4)

        for attempt in range(len(delays) + 1):
            try:
                return await make_request(bot, method)
            except (TelegramNetworkError, TelegramServerError) as error:
                if attempt == len(delays):
                    raise

                delay = delays[attempt]
                logger.warning(
                    "Telegram request %s failed, retrying in %s seconds: %s",
                    type(method).__name__,
                    delay,
                    error,
                )
                await asyncio.sleep(delay)


session = AiohttpSession(timeout=20)
session.middleware(RetryRequestMiddleware())

bot = Bot(token=getenv("BOT_TOKEN"), session=session)
dp = Dispatcher()
