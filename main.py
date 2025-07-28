import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
openai = OpenAI(api_key=OPENAI_API_KEY)

# 📌 Збереження виконаних підходів
user_progress = {}

TRAINING_PLAN = {
    "monday": [
        {"exercise": "Жим гантелей на груди", "sets": 4, "reps": 12},
        {"exercise": "Підйом гантелей в сторони", "sets": 3, "reps": 15},
        {"exercise": "Французький жим", "sets": 4, "reps": 10}
    ],
    "wednesday": [
        {"exercise": "Підтягування з утриманням", "sets": 4, "reps": 8},
        {"exercise": "Зведення гантелей за спину", "sets": 3, "reps": 12},
        {"exercise": "Молоткова з грифом", "sets": 4, "reps": 10}
    ],
    "friday": [
        {"exercise": "Присідання з гантелями", "sets": 4, "reps": 15},
        {"exercise": "Румунська тяга", "sets": 3, "reps": 12},
        {"exercise": "Скручування на прес", "sets": 4, "reps": 20}
    ]
}

def get_weekday():
    return datetime.datetime.now().strftime("%A").lower()

def generate_workout_keyboard(user_id, day_key):
    keyboard = []
    progress = user_progress.get(user_id, {}).get(day_key, {})
    for i, ex in enumerate(TRAINING_PLAN[day_key]):
        done_sets = progress.get(i, 0)
        label = f"{ex['exercise']} — {done_sets}/{ex['sets']} підходів"
        callback_data = f"set_{day_key}_{i}"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(CommandStart())
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Що сьогодні?", callback_data="today")]
    ])
    await message.answer("Привіт! Обери дію:", reply_markup=keyboard)

@dp.callback_query(F.data == "today")
async def today_plan(callback: CallbackQuery):
    user_id = callback.from_user.id
    day = get_weekday()
    if day in TRAINING_PLAN:
        text = "<b>Тренування:</b>\n"
        for ex in TRAINING_PLAN[day]:
            text += f"• {ex['exercise']} — {ex['sets']}x{ex['reps']}\n"
        await callback.message.answer(text, reply_markup=generate_workout_keyboard(user_id, day))
    else:
        await callback.message.answer("Сьогодні немає тренування. Рекомендуємо кардіо 🚶‍♂️")
    await callback.answer()

@dp.callback_query(F.data.startswith("set_"))
async def handle_set(callback: CallbackQuery):
    user_id = callback.from_user.id
    _, day_key, index = callback.data.split("_")
    index = int(index)

    progress = user_progress.setdefault(user_id, {}).setdefault(day_key, {})
    progress[index] = min(progress.get(index, 0) + 1, TRAINING_PLAN[day_key][index]['sets'])

    await callback.message.edit_reply_markup(reply_markup=generate_workout_keyboard(user_id, day_key))
    await callback.answer("✅ Підхід відмічено")

@dp.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Що сьогодні?", callback_data="today")]
    ])
    await callback.message.edit_text("⬅️ Повертаємось", reply_markup=keyboard)
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
