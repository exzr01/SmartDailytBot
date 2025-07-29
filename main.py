import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# --- Структура тренувань ---
WORKOUTS = {
    "monday": {
        "title": "🔴 Понеділок – ГРУДИ + ТРІЦЕПС + ПЕРЕДНЯ ДЕЛЬТА",
        "exercises": [
            ("Жим штанги лежачи", "4×8"),
            ("Жим гантелей під кутом", "3×10"),
            ("Кросовер", "3×12"),
            ("Віджимання на брусах", "3×макс"),
            ("Жим вниз на тріцепс (канат)", "3×12"),
            ("Французький жим", "3×10"),
            ("Фронтальні підйоми гантелей", "3×15")
        ]
    },
    "wednesday": {
        "title": "🔵 Середа – СПИНА + БІЦЕПС + ЗАДНЯ ДЕЛЬТА",
        "exercises": [
            ("Тяга верхнього блоку", "4×10"),
            ("Тяга штанги в нахилі", "3×10"),
            ("Підтягування / нижня тяга", "3×макс"),
            ("Підйом штанги на біцепс", "3×12"),
            ("Молотки", "3×12"),
            ("Зворотні махи в нахилі", "3×15")
        ]
    },
    "friday": {
        "title": "🟢 П’ятниця – НОГИ + ПРЕС + БІЧНА ДЕЛЬТА",
        "exercises": [
            ("Жим ногами / Присідання", "4×10"),
            ("Румунська тяга", "3×12"),
            ("Випади", "3×10 на ногу"),
            ("Прес", "3×15"),
            ("Бічні махи гантелями стоячи", "3×15"),
            ("Бічні махи у тренажері", "3×15")
        ]
    }
}

user_progress = {}
user_cardio = {}

# --- Кнопки ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 Тренування", callback_data="workout")],
        [InlineKeyboardButton(text="➕ Додати активність", callback_data="add_activity")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])

def workout_day_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Переглянути деталі", callback_data="workout_details")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

def exercises_keyboard(weekday, user_id):
    buttons = []
    done = user_progress.get(user_id, {}).get(weekday, set())
    for i, (exercise, reps) in enumerate(WORKOUTS[weekday]["exercises"]):
        done_mark = "✅" if i in done else ""
        buttons.append([InlineKeyboardButton(
            text=f"{done_mark} {exercise} ({reps})",
            callback_data=f"toggle_{weekday}_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Обробники ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Обери дію:", reply_markup=main_menu())

@dp.callback_query(F.data == "workout")
async def workout_today(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    if weekday not in WORKOUTS:
        await callback.message.answer("Сьогодні день відпочинку 🌞")
    else:
        await callback.message.answer(f"<b>{WORKOUTS[weekday]['title']}</b>", reply_markup=workout_day_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "workout_details")
async def workout_details(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    keyboard = exercises_keyboard(weekday, callback.from_user.id)
    await callback.message.answer("Вправи на сьогодні:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_exercise(callback: types.CallbackQuery):
    _, weekday, index = callback.data.split("_")
    index = int(index)
    user_id = callback.from_user.id

    if user_id not in user_progress:
        user_progress[user_id] = {}
    if weekday not in user_progress[user_id]:
        user_progress[user_id][weekday] = set()

    if index in user_progress[user_id][weekday]:
        user_progress[user_id][weekday].remove(index)
    else:
        user_progress[user_id][weekday].add(index)

    keyboard = exercises_keyboard(weekday, user_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("Оновлено ✅")

@dp.callback_query(F.data == "add_activity")
async def add_custom_activity(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    today = datetime.datetime.now().strftime('%A').lower()
    user_cardio.setdefault(user_id, {}).setdefault(today, []).append("Кардіо / Додаткова активність")
    await callback.message.answer("✅ Активність додано до статистики!")
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def show_statistics(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    names = {
        "monday": "Пн",
        "tuesday": "Вт",
        "wednesday": "Ср",
        "thursday": "Чт",
        "friday": "Пт",
        "saturday": "Сб",
        "sunday": "Нд"
    }
    report = "📊 <b>Статистика тренувань:</b>\n"
    for day in days:
        if day in WORKOUTS:
            completed = "✅" if user_progress.get(user_id, {}).get(day) else "❌"
            report += f"{names[day]} – {WORKOUTS[day]['title']} {completed}\n"
        if user_cardio.get(user_id, {}).get(day):
            report += f"    🏃 Додаткова активність: {len(user_cardio[user_id][day])} раз(ів)\n"
    await callback.message.answer(report)
    await callback.answer()

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.answer("⬅️ Повертаємось у меню", reply_markup=main_menu())
    await callback.answer()

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
