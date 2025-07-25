import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to Railway → Variables.")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
user_chat_id = None  # тимчасово тут зберігаємо ID

reminders = [
    {"time": "07:00", "text": "🏋️‍♂️ Пора тренування: груди + трицепс 💪"},
    {"time": "08:30", "text": "🍳 Сніданок: омлет з овочами та авокадо 🥑"},
    {"time": "13:00", "text": "🍗 Обід: куряче філе, рис та овочі"},
    {"time": "16:30", "text": "🥜 Перекус: грецький йогурт з горіхами"},
    {"time": "19:30", "text": "🥦 Вечеря: риба з броколі на пару"},
    {"time": "22:00", "text": "🛌 Час відпочивати. Завтра новий день!"},
]

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    global user_chat_id
    user_chat_id = message.chat.id
    await message.answer("✅ Бот активовано! Щоденні нагадування будуть приходити автоматично.")

async def send_reminder(text):
    if user_chat_id:
        try:
            await bot.send_message(chat_id=user_chat_id, text=text)
        except Exception as e:
            print(f"❌ Помилка надсилання: {e}")

async def main():
    for reminder in reminders:
        hour, minute = reminder["time"].split(":")
        scheduler.add_job(send_reminder, CronTrigger(hour=hour, minute=minute), args=[reminder["text"]])
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
