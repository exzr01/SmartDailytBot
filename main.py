import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to Railway → Variables.")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Сталий розклад
DAILY_PLAN = {
    "07:00": "🏋️Тренування: Груди + трицепс",
    "08:30": "🍳 Сніданок: Омлет з овочами",
    "13:00": "🍗 Обід: Куряче філе + гречка",
    "19:00": "🥗 Вечеря: Салат + тунець",
    "21:00": "💧 Вода: Підбивання: 2.5 літра"
}

# Головна кнопка
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❓ Що сьогодні?")],
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Бот запущено успішно ✅\nЩоденні нагадування активні!",
        reply_markup=main_keyboard
    )

@dp.message()
async def today_schedule(message: types.Message):
    if message.text == "❓ Що сьогодні?":
        today = datetime.now().strftime("%d.%m.%Y")
        schedule_text = f"🗓️ <b>Розклад на сьогодні ({today}):</b>\n\n"
        for time, task in DAILY_PLAN.items():
            schedule_text += f"<b>{time}</b> — {task}\n"
        await message.answer(schedule_text)

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
