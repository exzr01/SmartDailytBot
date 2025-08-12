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

# Пам'ять у процесі (перезапускається при рестарті)
user_progress = {}  # {user_id: {day_key: set(ex_idx)}}
user_cardio = {}    # {user_id: {day_key: [activities]}}

# --- Утиліти дат ---
def get_today_key() -> str | None:
    # 0=Mon ... 6=Sun
    wd = datetime.datetime.now().weekday()
    mapping = {0: "monday", 2: "wednesday", 4: "friday"}
    return mapping.get(wd)

def weekday_name_ua(day_key: str) -> str:
    mapping = {
        "monday": "Пн",
        "wednesday": "Ср",
        "friday": "Пт",
    }
    return mapping.get(day_key, day_key)

# --- Кнопки ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 Тренування", callback_data="workout")],
        [InlineKeyboardButton(text="➕ Додати активність", callback_data="add_activity")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])

def workout_day_keyboard(day_key: str | None):
    rows = []
    if day_key:
        rows.append([InlineKeyboardButton(text="Переглянути деталі", callback_data=f"workout_details:{day_key}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def exercises_keyboard(day_key: str, user_id: int):
    buttons = []
    done = user_progress.get(user_id, {}).get(day_key, set())
    for i, (exercise, reps) in enumerate(WORKOUTS[day_key]["exercises"]):
        done_mark = "✅" if i in done else "⬜️"
        buttons.append([InlineKeyboardButton(
            text=f"{done_mark} {exercise} ({reps})",
            callback_data=f"toggle:{day_key}:{i}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Обробники ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Обери дію:", reply_markup=main_menu())

@dp.callback_query(F.data == "workout")
async def workout_today(callback: types.CallbackQuery):
    day_key = get_today_key()
    if not day_key:
        await callback.message.answer("Сьогодні день відпочинку 🌞", reply_markup=workout_day_keyboard(None))
    else:
        await callback.message.answer(
            f"<b>{WORKOUTS[day_key]['title']}</b>",
            reply_markup=workout_day_keyboard(day_key)
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("workout_details"))
async def workout_details(callback: types.CallbackQuery):
    # формат: workout_details:monday
    parts = callback.data.split(":")
    day_key = parts[1] if len(parts) > 1 else get_today_key()
    if not day_key or day_key not in WORKOUTS:
        await callback.message.answer("Сьогодні немає силового дня. Зроби кардіо 30–40 хв 🚶‍♂️", reply_markup=main_menu())
        await callback.answer()
        return
    keyboard = exercises_keyboard(day_key, callback.from_user.id)
    await callback.message.answer("Вправи на сьогодні:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("toggle:"))
async def toggle_exercise(callback: types.CallbackQuery):
    # формат: toggle:monday:2
    _, day_key, idx = callback.data.split(":")
    index = int(idx)
    user_id = callback.from_user.id

    user_progress.setdefault(user_id, {}).setdefault(day_key, set())
    if index in user_progress[user_id][day_key]:
        user_progress[user_id][day_key].remove(index)
    else:
        user_progress[user_id][day_key].add(index)

    keyboard = exercises_keyboard(day_key, user_id)
    # редагуємо існуюче повідомлення — завжди передаємо markup
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("Оновлено ✅")

@dp.callback_query(F.data == "add_activity")
async def add_custom_activity(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    day_key = get_today_key() or "rest"
    user_cardio.setdefault(user_id, {}).setdefault(day_key, []).append("Кардіо / Додаткова активність")
    await callback.message.answer("✅ Активність додано до статистики!", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def show_statistics(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    report = "📊 <b>Статистика тренувань:</b>\n"
    for day_key in ["monday", "wednesday", "friday"]:
        title = WORKOUTS[day_key]["title"]
        completed_flag = "✅" if user_progress.get(user_id, {}).get(day_key) else "❌"
        report += f"{weekday_name_ua(day_key)} – {title} {completed_flag}\n"
        if user_cardio.get(user_id, {}).get(day_key):
            report += f"    🏃 Додаткова активність: {len(user_cardio[user_id][day_key])} раз(ів)\n"
    # День відпочинку — також покажемо, якщо були активності
    rest_acts = user_cardio.get(user_id, {}).get("rest", [])
    if rest_acts:
        report += f"Нд/дні відпочинку – 🏃 активність: {len(rest_acts)} раз(ів)\n"
    await callback.message.answer(report, reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.answer("⬅️ Повертаємось у меню", reply_markup=main_menu())
    await callback.answer()

async def main():
    # Якщо захочеш — додамо нагадування через scheduler.add_job(...)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
