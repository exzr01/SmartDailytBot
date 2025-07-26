import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time
import openai

# Завантаження токенів
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to Railway → Variables.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please add it to Railway → Variables.")

# Налаштування OpenAI
openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Дефолтні плани
menu_today = {
    "breakfast": "🍳 Сніданок: Омлет з овочами",
    "lunch": "🍗 Обід: Куряче філе + гречка",
    "dinner": "🍜 Вечеря: Салат + тунець",
    "water": "💧 Вода: Підбивання: 2.5 літра"
}

trainings = {
    "Monday": "🄴 Понеділок: Груди + Тріцепс + Передня дельта...",
    "Wednesday": "🔵 Середа: Спина + Біцепс + Задня дельта...",
    "Friday": "🟢 П'ятниця: Ноги + Прес + Бічна дельта..."
}

# Нагадування
async def send_reminder(user_id: int, message: str):
    await bot.send_message(user_id, message)

# Складання розкладу на сьогодні
@dp.message(Command("Що сьогодні?"))
async def today_schedule(message: types.Message):
    today = datetime.now().strftime("%d.%m.%Y")
    weekday = datetime.now().strftime("%A")
    plan = f"\ud83d\udcc5 <b>Розклад на сьогодні ({today}):</b>\n"
    plan += "07:00 — 💪 Тренування\n" if weekday in trainings else ""
    plan += f"08:30 — {menu_today['breakfast']}\n"
    plan += f"13:00 — {menu_today['lunch']}\n"
    plan += f"19:00 — {menu_today['dinner']}\n"
    plan += f"21:00 — {menu_today['water']}"
    await message.answer(plan)

# Оновлення меню через GPT
@dp.message(Command("онови_меню"))
async def update_menu_handler(message: types.Message):
    prompt = "Згенеруй нове меню на день для жироспалення з використанням мультипечі. Виведи 3 прийоми їжі та норму води."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    new_plan = response.choices[0].message.content
    await message.answer(f"📊 Оновлене меню GPT:\n{new_plan}")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("👋 Бот активовано! Щоденні нагадування будуть приходити автоматично.")

    user_id = message.from_user.id
    scheduler.add_job(send_reminder, "cron", hour=7, minute=0, args=[user_id, "💪 Час тренування!"])
    scheduler.add_job(send_reminder, "cron", hour=8, minute=30, args=[user_id, menu_today['breakfast']])
    scheduler.add_job(send_reminder, "cron", hour=13, minute=0, args=[user_id, menu_today['lunch']])
    scheduler.add_job(send_reminder, "cron", hour=19, minute=0, args=[user_id, menu_today['dinner']])
    scheduler.add_job(send_reminder, "cron", hour=21, minute=0, args=[user_id, menu_today['water']])

    scheduler.start()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
