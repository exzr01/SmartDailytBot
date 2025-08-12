import os
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Kyiv"))

# --- Тренування ---
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

# --- Rest Day чекліст ---
REST_TODO = [
    "Zone 2 — 30–40 хв",
    "10 000 кроків",
    "Мобільність — 12 хв",
    "Core — 8 хв",
    "Дихання — 5 хв",
    "Ролер/масаж — 5–7 хв",
    "Гідрація/харчування виконано",
    "Сон — план на ніч"
]

# ===== ЗБЕРІГАННЯ СТАНУ (в пам’яті процесу) =====
# прогрес тренування по даті
user_progress: dict[int, dict[str, set[int]]] = {}          # {uid: {YYYY-MM-DD: set(ex_idx)}}
# чекліст Rest Day по даті
user_rest: dict[int, dict[str, set[int]]] = {}              # {uid: {YYYY-MM-DD: set(item_idx)}}
# кардіо/активності по даті
user_cardio: dict[int, dict[str, list[str]]] = {}           # {uid: {YYYY-MM-DD: [labels...]}}
# харчування по даті
user_nutrition: dict[int, dict[str, dict]] = {}             # {uid: {YYYY-MM-DD: {"meals":[{"name","kcal"}], "protein_g": int}}}
# активні користувачі (для щоденного пінгу)
subscribers: set[int] = set()

# ===== ДАТИ / ДНІ =====
def today_str() -> str:
    return dt.date.today().isoformat()

def weekday_key_by_date(d: dt.date) -> str | None:
    return {0: "monday", 2: "wednesday", 4: "friday"}.get(d.weekday())

def weekday_short_ua(d: dt.date) -> str:
    return ["Пн","Вт","Ср","Чт","Пт","Сб","Нд"][d.weekday()]

# ===== КНОПКИ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 Тренування", callback_data="workout_today")],
        [InlineKeyboardButton(text="🍽 Харчування", callback_data="nutrition_menu")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])

def exercises_keyboard(date_str: str, day_key: str, uid: int):
    done = user_progress.get(uid, {}).get(date_str, set())
    rows = []
    for i, (exercise, reps) in enumerate(WORKOUTS[day_key]["exercises"]):
        mark = "✅" if i in done else "⬜️"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {exercise} ({reps})",
            callback_data=f"toggle:{date_str}:{day_key}:{i}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def rest_keyboard(date_str: str, uid: int):
    done = user_rest.get(uid, {}).get(date_str, set())
    rows = []
    for i, item in enumerate(REST_TODO):
        mark = "✅" if i in done else "⬜️"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {item}",
            callback_data=f"rtoggle:{date_str}:{i}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def nutrition_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати прийом їжі", callback_data="nut:add_meal")],
        [InlineKeyboardButton(text="🍗 Додати білок (г/день)", callback_data="nut:add_protein")],
        [InlineKeyboardButton(text="🧮 Ввести підсумок калорій", callback_data="nut:add_total")],
        [InlineKeyboardButton(text="📄 Показати записи сьогодні", callback_data="nut:show_today")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# ===== FSM ДЛЯ ХАРЧУВАННЯ =====
class AddMeal(StatesGroup):
    waiting_name = State()
    waiting_kcal = State()

class AddProtein(StatesGroup):
    waiting_value = State()

class AddTotal(StatesGroup):
    waiting_value = State()

# ===== РЕНДЕР СТОРІНОК =====
def render_workout_today(uid: int) -> tuple[str, InlineKeyboardMarkup]:
    d = dt.date.today()
    dstr = d.isoformat()
    day_key = weekday_key_by_date(d)
    if not day_key:
        text = "<b>Rest Day</b>\nЛегкий день відновлення. Відмічай виконане 👇"
        return text, rest_keyboard(dstr, uid)
    title = WORKOUTS[day_key]["title"]
    text = f"<b>{title}</b>\nОбирай вправи та відмічай виконане:"
    return text, exercises_keyboard(dstr, day_key, uid)

def render_nutrition_today(uid: int) -> str:
    dstr = today_str()
    data = user_nutrition.get(uid, {}).get(dstr, {})
    meals = data.get("meals", [])
    protein = data.get("protein_g", 0)
    kcal_total = sum(int(m["kcal"]) for m in meals) if meals else 0
    if meals:
        meals_lines = "\n".join([f"• {m['name']} — {m['kcal']} ккал" for m in meals])
    else:
        meals_lines = "—"
    return (
        f"🍽 <b>Харчування {dstr}</b>\n"
        f"{meals_lines}\n"
        f"———\n"
        f"Сумарно: <b>{kcal_total}</b> ккал\n"
        f"Білок: <b>{protein}</b> г"
    )

# ===== ХЕНДЛЕРИ /start =====
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    subscribers.add(message.from_user.id)
    await message.answer("Привіт! Обери дію:", reply_markup=main_menu())

# ===== ТРЕНУВАННЯ =====
@dp.callback_query(F.data == "workout_today")
async def workout_today(cb: types.CallbackQuery):
    text, kb = render_workout_today(cb.from_user.id)
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("toggle:"))
async def toggle_exercise(cb: types.CallbackQuery):
    # toggle:YYYY-MM-DD:day_key:index
    _, dstr, day_key, idx = cb.data.split(":")
    i = int(idx)
    uid = cb.from_user.id
    user_progress.setdefault(uid, {}).setdefault(dstr, set())
    if i in user_progress[uid][dstr]:
        user_progress[uid][dstr].remove(i)
    else:
        user_progress[uid][dstr].add(i)
    kb = exercises_keyboard(dstr, day_key, uid)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer("Оновлено ✅")

@dp.callback_query(F.data.startswith("rtoggle:"))
async def toggle_rest(cb: types.CallbackQuery):
    # rtoggle:YYYY-MM-DD:index
    _, dstr, idx = cb.data.split(":")
    i = int(idx)
    uid = cb.from_user.id
    user_rest.setdefault(uid, {}).setdefault(dstr, set())
    if i in user_rest[uid][dstr]:
        user_rest[uid][dstr].remove(i)
    else:
        user_rest[uid][dstr].add(i)
    kb = rest_keyboard(dstr, uid)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer("Оновлено ✅")

# ===== ХАРЧУВАННЯ =====
@dp.callback_query(F.data == "nutrition_menu")
async def nutrition_menu(cb: types.CallbackQuery):
    await cb.message.answer(render_nutrition_today(cb.from_user.id), reply_markup=nutrition_keyboard())
    await cb.answer()

@dp.callback_query(F.data == "nut:show_today")
async def nutrition_show_today(cb: types.CallbackQuery):
    await cb.message.answer(render_nutrition_today(cb.from_user.id), reply_markup=nutrition_keyboard())
    await cb.answer()

@dp.callback_query(F.data == "nut:add_meal")
async def nut_add_meal(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddMeal.waiting_name)
    await state.update_data(tmp_meal={})
    await cb.message.answer("Введи <b>назву страви</b> (наприклад: «Омлет з сиром»):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Скасувати", callback_data="back")]]))
    await cb.answer()

@dp.message(AddMeal.waiting_name)
async def nut_meal_got_name(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    tmp = data.get("tmp_meal", {})
    tmp["name"] = msg.text.strip()
    await state.update_data(tmp_meal=tmp)
    await state.set_state(AddMeal.waiting_kcal)
    await msg.answer("Тепер введи <b>калорії</b> цієї страви числом (наприклад: 320):")

@dp.message(AddMeal.waiting_kcal)
async def nut_meal_got_kcal(msg: types.Message, state: FSMContext):
    text = msg.text.strip().replace(",", ".")
    if not text.replace(".", "", 1).isdigit():
        await msg.answer("Введи число, будь ласка (наприклад: 320)")
        return
    kcal = int(float(text))
    uid = msg.from_user.id
    dstr = today_str()

    data = await state.get_data()
    tmp = data.get("tmp_meal", {})
    name = tmp.get("name", "Без назви")

    user_nutrition.setdefault(uid, {}).setdefault(dstr, {}).setdefault("meals", [])
    user_nutrition[uid][dstr]["meals"].append({"name": name, "kcal": kcal})

    await state.clear()
    await msg.answer(f"✅ Додано: <b>{name}</b> — {kcal} ккал", reply_markup=nutrition_keyboard())

@dp.callback_query(F.data == "nut:add_protein")
async def nut_add_protein(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddProtein.waiting_value)
    await cb.message.answer("Введи <b>загальний білок за день</b> у грамах (наприклад: 150):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Скасувати", callback_data="back")]]))
    await cb.answer()

@dp.message(AddProtein.waiting_value)
async def nut_protein_value(msg: types.Message, state: FSMContext):
    v = msg.text.strip()
    if not v.isdigit():
        await msg.answer("Введи число, будь ласка (наприклад: 150)")
        return
    grams = int(v)
    uid = msg.from_user.id
    dstr = today_str()
    user_nutrition.setdefault(uid, {}).setdefault(dstr, {})["protein_g"] = grams
    await state.clear()
    await msg.answer(f"✅ Записано білок: {grams} г", reply_markup=nutrition_keyboard())

@dp.callback_query(F.data == "nut:add_total")
async def nut_add_total(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddTotal.waiting_value)
    await cb.message.answer("Введи <b>підсумок калорій за день</b> (числом, наприклад: 1650):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Скасувати", callback_data="back")]]))
    await cb.answer()

@dp.message(AddTotal.waiting_value)
async def nut_total_value(msg: types.Message, state: FSMContext):
    v = msg.text.strip().replace(",", ".")
    if not v.replace(".", "", 1).isdigit():
        await msg.answer("Введи число, будь ласка (наприклад: 1650)")
        return
    total = int(float(v))
    uid = msg.from_user.id
    dstr = today_str()
    # Зберігаємо як окреме поле, щоб можна було або сумувати з прийомів, або брати це значення
    user_nutrition.setdefault(uid, {}).setdefault(dstr, {})["total_kcal_manual"] = total
    await state.clear()
    await msg.answer(f"✅ Підсумок дня: {total} ккал", reply_markup=nutrition_keyboard())

# ===== СТАТИСТИКА (14 днів) =====
@dp.callback_query(F.data == "stats")
async def show_statistics(cb: types.CallbackQuery):
    uid = cb.from_user.id
    today = dt.date.today()
    start = today - dt.timedelta(days=13)

    lines = ["📊 <b>Статистика (ост. 14 днів)</b>"]
    sessions_done = 0
    sessions_total = 0
    rest_done_days = 0
    rest_total_days = 0
    cardio_total = 0
    kcal_total_sum = 0
    protein_total_sum = 0
    days_count_for_kcal = 0
    days_count_for_protein = 0

    for i in range(14):
        day = start + dt.timedelta(days=i)
        dstr = day.isoformat()
        dshort = weekday_short_ua(day)
        day_key = weekday_key_by_date(day)

        # nutrition
        nd = user_nutrition.get(uid, {}).get(dstr, {})
        meals = nd.get("meals", [])
        protein = nd.get("protein_g", None)
        kcal_from_meals = sum(int(m["kcal"]) for m in meals) if meals else 0
        kcal_manual = nd.get("total_kcal_manual", None)
        kcal_total = kcal_manual if isinstance(kcal_manual, int) else kcal_from_meals

        if kcal_total:
            kcal_total_sum += kcal_total
            days_count_for_kcal += 1
        if isinstance(protein, int):
            protein_total_sum += protein
            days_count_for_protein += 1

        # cardio
        cardio_cnt = len(user_cardio.get(uid, {}).get(dstr, []))
        cardio_total += cardio_cnt

        if day_key:
            total_ex = len(WORKOUTS[day_key]["exercises"])
            done_ex = len(user_progress.get(uid, {}).get(dstr, set()))
            status = f"{done_ex}/{total_ex} {'✅' if done_ex > 0 else '❌'}"
            sessions_total += 1
            if done_ex == total_ex and total_ex > 0:
                sessions_done += 1
            lines.append(
                f"{dshort} {dstr} — {WORKOUTS[day_key]['title']} | {status}"
                + (f" | 🏃 {cardio_cnt}" if cardio_cnt else "")
                + (f" | 🍽 {kcal_total} ккал" if kcal_total else "")
                + (f" | 🍗 {protein} г" if isinstance(protein, int) else "")
            )
        else:
            rest_total_days += 1
            done_cnt = len(user_rest.get(uid, {}).get(dstr, set()))
            if done_cnt == len(REST_TODO) and len(REST_TODO) > 0:
                rest_done_days += 1
            lines.append(
                f"{dshort} {dstr} — Rest Day | {done_cnt}/{len(REST_TODO)}"
                + (f" | 🏃 {cardio_cnt}" if cardio_cnt else "")
                + (f" | 🍽 {kcal_total} ккал" if kcal_total else "")
                + (f" | 🍗 {protein} г" if isinstance(protein, int) else "")
            )

    # Підсумки
    rate = f"{(sessions_done / sessions_total * 100):.0f}%" if sessions_total else "0%"
    avg_kcal = f"{(kcal_total_sum / days_count_for_kcal):.0f}" if days_count_for_kcal else "—"
    avg_protein = f"{(protein_total_sum / days_count_for_protein):.0f}" if days_count_for_protein else "—"

    lines.append("\n<b>Підсумок за 14 днів</b>")
    lines.append(f"• Повністю виконаних тренувань: {sessions_done}/{sessions_total} ({rate})")
    lines.append(f"• Rest Days повністю закриті: {rest_done_days}/{rest_total_days}")
    lines.append(f"• Додаткові активності (кардіо тощо): {cardio_total}")
    lines.append(f"• Середні калорії/день: {avg_kcal} ккал")
    lines.append(f"• Середній білок/день: {avg_protein} г")

    await cb.message.answer("\n".join(lines), reply_markup=main_menu())
    await cb.answer()

# ===== НАГАДУВАННЯ О 21:30 (Europe/Kyiv) =====
async def daily_nutrition_ping():
    text = (
        "⏰ <b>Кінець дня</b>\n"
        "Скинь, будь ласка, що їв сьогодні та калорії.\n"
        "Можеш додати прийоми їжі/білок/підсумок тут:"
    )
    for uid in list(subscribers):
        try:
            await bot.send_message(uid, text, reply_markup=nutrition_keyboard())
        except Exception:
            # користувач, імовірно, зупинив бота — просто ігноруємо
            pass

async def on_startup():
    # щодня о 21:30 за Києвом
    scheduler.add_job(daily_nutrition_ping, "cron", hour=21, minute=30)
    scheduler.start()

@dp.callback_query(F.data == "back")
async def go_back(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("⬅️ Повертаємось у меню", reply_markup=main_menu())
    await cb.answer()

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
