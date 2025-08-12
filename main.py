import os
import asyncio
import datetime as dt
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

# --- Структура тренувань (як було) ---
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

# ======== НОВЕ: зберігаємо прогрес по ДАТІ =========
# user_progress = { user_id: { "YYYY-MM-DD": set(exercise_indexes) } }
# user_cardio   = { user_id: { "YYYY-MM-DD": [activities...] } }
user_progress: dict[int, dict[str, set[int]]] = {}
user_cardio: dict[int, dict[str, list[str]]] = {}

# --- Дати/дні ---
def today_date_str() -> str:
    return dt.date.today().isoformat()  # 'YYYY-MM-DD'

def weekday_key_by_date(d: dt.date) -> str | None:
    mapping = {0: "monday", 2: "wednesday", 4: "friday"}
    return mapping.get(d.weekday())

def weekday_short_ua(d: dt.date) -> str:
    return ["Пн","Вт","Ср","Чт","Пт","Сб","Нд"][d.weekday()]

# --- Кнопки ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 Тренування", callback_data="workout_today")],
        [InlineKeyboardButton(text="➕ Додати активність", callback_data="add_activity")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])

def exercises_keyboard(date_str: str, day_key: str, user_id: int):
    buttons = []
    done = user_progress.get(user_id, {}).get(date_str, set())
    for i, (exercise, reps) in enumerate(WORKOUTS[day_key]["exercises"]):
        mark = "✅" if i in done else "⬜️"
        buttons.append([InlineKeyboardButton(
            text=f"{mark} {exercise} ({reps})",
            callback_data=f"toggle:{date_str}:{day_key}:{i}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Рендер тренування на день (одразу з чекбоксами) ---
def render_workout_for_today(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    date_str = today_date_str()
    day_key = weekday_key_by_date(dt.date.today())
    if not day_key:
        # День відпочинку, показуємо меседж + назад
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ])
        return ("Сьогодні день відпочинку 🌞 Зроби кардіо 30–40 хв 🚶‍♂️", kb)
    title = WORKOUTS[day_key]["title"]
    text = f"<b>{title}</b>\nОбирай вправи та відмічай виконане:"
    kb = exercises_keyboard(date_str, day_key, user_id)
    return (text, kb)

# --- Handlers ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Обери дію:", reply_markup=main_menu())

# НОВЕ: натискаєш «Тренування» — одразу план з чекбоксами (без «деталей»)
@dp.callback_query(F.data == "workout_today")
async def workout_today(callback: types.CallbackQuery):
    text, kb = render_workout_for_today(callback.from_user.id)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# Тогл по конкретній ДАТІ (щодня чистий аркуш)
@dp.callback_query(F.data.startswith("toggle:"))
async def toggle_exercise(callback: types.CallbackQuery):
    # toggle:YYYY-MM-DD:day_key:index
    _, date_str, day_key, idx = callback.data.split(":")
    index = int(idx)
    uid = callback.from_user.id

    user_progress.setdefault(uid, {}).setdefault(date_str, set())
    if index in user_progress[uid][date_str]:
        user_progress[uid][date_str].remove(index)
    else:
        user_progress[uid][date_str].add(index)

    kb = exercises_keyboard(date_str, day_key, uid)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Оновлено ✅")

@dp.callback_query(F.data == "add_activity")
async def add_custom_activity(callback: types.CallbackQuery):
    uid = callback.from_user.id
    date_str = today_date_str()
    user_cardio.setdefault(uid, {}).setdefault(date_str, []).append("Кардіо / Додаткова активність")
    await callback.message.answer("✅ Активність додано до статистики!", reply_markup=main_menu())
    await callback.answer()

# РОЗШИРЕНА статистика: останні 14 днів + підсумок за тиждень
@dp.callback_query(F.data == "stats")
async def show_statistics(callback: types.CallbackQuery):
    uid = callback.from_user.id
    today = dt.date.today()
    start = today - dt.timedelta(days=13)
    lines = ["📊 <b>Статистика (ост. 14 днів)</b>"]

    sessions_done = 0
    sessions_total = 0
    cardio_total = 0

    for i in range(14):
        day = start + dt.timedelta(days=i)
        dstr = day.isoformat()
        dshort = weekday_short_ua(day)

        day_key = weekday_key_by_date(day)
        cardio_cnt = len(user_cardio.get(uid, {}).get(dstr, []))
        cardio_total += cardio_cnt

        if day_key:
            total_ex = len(WORKOUTS[day_key]["exercises"])
            done_ex = len(user_progress.get(uid, {}).get(dstr, set()))
            status = "✅" if done_ex > 0 else "❌"
            sessions_total += 1
            if done_ex == total_ex:
                sessions_done += 1
            lines.append(f"{dshort} {dstr} — {WORKOUTS[day_key]['title']} | {done_ex}/{total_ex} вправ {status}"
                         + (f" | 🏃 {cardio_cnt}" if cardio_cnt else ""))
        else:
            # Відпочинок
            status = "—"
            lines.append(f"{dshort} {dstr} — День відпочинку {status}"
                         + (f" | 🏃 {cardio_cnt}" if cardio_cnt else ""))

    # Підсумок
    rate = f"{(sessions_done / sessions_total * 100):.0f}%" if sessions_total else "0%"
    lines.append("\n<b>Підсумок за 14 днів</b>")
    lines.append(f"• Повністю виконаних тренувань: {sessions_done}/{sessions_total} ({rate})")
    lines.append(f"• Додаткові активності (кардіо тощо): {cardio_total}")

    await callback.message.answer("\n".join(lines), reply_markup=main_menu())
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
