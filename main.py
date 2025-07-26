import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to Railway → Variables.")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please add it to Railway → Variables.")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Статичне меню і тренування (залишаємо як було)
MENU = "🥣 Сніданок: Омлет із овочами\n🥗 Обід: Курка з рисом\n🍽 Вечеря: Лосось і салат"
WORKOUTS = {
    "Понеділок": "1. Жим штанги лежачи — 4×8\n2. Жим гантелей під кутом — 3×10\n3. Кросовер — 3×12...",
    "Середа": "1. Тяга верхнього блоку — 4×10\n2. Тяга штанги в нахилі — 3×10...",
    "Пʼятниця": "1. Жим ногами — 4×10\n2. Румунська тяга — 3×12..."
}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Що сьогодні?", callback_data="today")],
        [InlineKeyboardButton(text="Оновити меню GPT", callback_data="update_menu")],
        [InlineKeyboardButton(text="Оновити тренування GPT", callback_data="update_workout")]
    ])
    await message.answer("👋 Бот запущено! Обери опцію:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "today")
async def today_callback(callback: types.CallbackQuery):
    today = datetime.now().strftime("%A")
    day_map = {"Monday": "Понеділок", "Wednesday": "Середа", "Friday": "Пʼятниця"}
    day = day_map.get(today, "")
    workout = WORKOUTS.get(day, "Сьогодні відпочинок 🧘‍♂️")
    await callback.message.answer(f"🏋️ Тренування на сьогодні ({day}):\n{workout}\n\n🍽 Меню:\n{MENU}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "update_menu")
async def update_menu(callback: types.CallbackQuery):
    await callback.message.answer("🔄 Оновлюю меню через GPT...")
    prompt = "Створи фітнес-меню на день: сніданок, обід і вечеря, для спалювання жиру. Коротко."
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    global MENU
    MENU = response.choices[0].message.content.strip()
    await callback.message.answer(f"✅ Нове меню збережено:\n{MENU}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "update_workout")
async def update_workout(callback: types.CallbackQuery):
    await callback.message.answer("🔄 Оновлюю тренування через GPT...")
    prompt = "Створи фітнес тренування (фулбаді або спліт) на день для жироспалення. Коротко, але детально."
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    today = datetime.now().strftime("%A")
    day_map = {"Monday": "Понеділок", "Wednesday": "Середа", "Friday": "Пʼятниця"}
    day = day_map.get(today, "Інший день")
    global WORKOUTS
    WORKOUTS[day] = response.choices[0].message.content.strip()
    await callback.message.answer(f"✅ Нове тренування збережено на {day}:")
    await callback.message.answer(WORKOUTS[day])
    await callback.answer()

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
