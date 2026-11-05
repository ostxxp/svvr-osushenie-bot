import asyncio
import logging
from pathlib import Path


from bot import start, handlers
from bot import inline_calendar
from bot.bot_init import dp, bot
from bot.reminder import send_reminders
from DB import database_funcs
from DB.database import Base, engine


async def main():
    # A new server has no SQLite schema or temporary report directories yet.
    Base.metadata.create_all(bind=engine)
    for directory in ("report_info", "feedbacks_temp"):
        Path(directory).mkdir(parents=True, exist_ok=True)
    dp.include_routers(
        start.router,
        handlers.router,
        inline_calendar.router
    )
    loop = asyncio.get_event_loop()
    prorabs = await database_funcs.get_prorabs()
    for prorab in prorabs:
        loop.create_task(send_reminders(prorab.id))
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
