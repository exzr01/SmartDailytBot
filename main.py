import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to Railway → Variables.")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Повне меню на день (приклад для жироспалення)
DAILY_MENU = """
🍽️ <b>Меню на день</b> (жироспалення):
- Сніданок: Омлет з 3 яєць + овочі
- Перекус: Грецький йогурт + ягоди
- Обід: Куряче філе з булгуром + салат
- Перекус: Горіхи/протеїновий батончик
- Вечеря: Риба в мультипечі + овочі
- Вода: 2.5–3 л 💧
"""

# Розклад тренувань
WORKOUTS = {
    "monday": """
🔴 <b>Понеділок – ГРУДИ + ТРІЦЕПС + ПЕРЕДНЯ ДЕЛЬТА</b>
1. Жим штанги лежачи — 4×8
2. Жим гантелей під кутом — 3×10
3. Кросовер — 3×12
4. Віджимання на брусах — 3×макс
5. Жим вниз на тріцепс (канат) — 3×12
6. Французький жим — 3×10
7. Фронтальні підйоми гантелей — 3×15
""",
    "wednesday": """
🔵 <b>Середа – СПИНА + БІЦЕПС + ЗАДНЯ ДЕЛЬТА</b>
1. Тяга верхнього блоку — 4×10
2. Тяга штанги в нахилі — 3×10
3. Підтягування / нижня тяга — 3×макс
4. Підйом штанги на біцепс — 3×12
5. Молотки — 3×12
6. Зворотні махи (задня дельта) — 3×15
""",
    "friday": """
🟢 <b>П’ятниця – НОГИ + ПРЕС + БІЧНА ДЕЛЬТА</b>
1. Жим ногами / Присідання — 4×10
2. Румунська тяга — 3×12
3. Випади — 3×10 на ногу
4. Прес — 3×15
5. Бічні махи гантелями — 3×15
6. Бічні махи у тренажері — 3×15
"""
}


# Старт
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Що сьогодні?", callback_data="today")]
    ])
    await message.answer("👋 Вітаю у SmartDailyBot! Обери дію:", reply_markup=kb)


# Обробка кнопки "Що сьогодні?"
@dp.callback_query(lambda c: c.data == "today")
async def handle_today(callback: types.CallbackQuery):
    weekday = datetime.now().strftime("%A").lower()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏋 Подивитись тренування", callback_data="workout")],
        [InlineKeyboardButton(text="🍽 Переглянути меню", callback_data="menu")]
    ])

    if weekday in WORKOUTS:
        await callback.message.answer(f"🔔 Сьогодні день тренування!", reply_markup=kb)
    else:
        await callback.message.answer("🔕 Сьогодні відпочинок, але меню завжди актуальне 🍽", reply_markup=kb)

    await callback.answer()


# Обробка кнопки "Подивитись тренування"
@dp.callback_query(lambda c: c.data == "workout")
async def handle_workout(callback: types.CallbackQuery):
    weekday = datetime.now().strftime("%A").lower()
    workout = WORKOUTS.get(weekday, "Сьогодні немає тренування 💤")
    await callback.message.answer(workout)
    await callback.answer()


# Обробка кнопки "Переглянути меню"
@dp.callback_query(lambda c: c.data == "menu")
async def handle_menu(callback: types.CallbackQuery):
    await callback.message.answer(DAILY_MENU)
    await callback.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
