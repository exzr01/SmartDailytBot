import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from openai import AsyncOpenAI

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
openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Розклад
WORKOUT_PLAN = {
    "monday": "🔴 Понедiлок – ГРУДИ + ТРIЦЕПС + ПЕРЕДНЯ ДЕЛЬТА...",
    "wednesday": "🔵 Середа – СПИНА + БIЦЕПС + ЗАДНЯ ДЕЛЬТА...",
    "friday": "🔷 П’ятниця – НОГИ + ПРЕС + БIЧНА ДЕЛЬТА..."
}

MEAL_PLAN = {
    "breakfast": "🍼 Омлет з овочами в мультипечі",
    "lunch": "🥚 Куряче філе з броколі",
    "dinner": "🧃 Риба з овочами на парі"
}

# Кнопки
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❓ Що сьогодні?", callback_data="today")],
    [InlineKeyboardButton(text="💪 Тренування", callback_data="workout")],
    [InlineKeyboardButton(text="🍽️ Меню", callback_data="menu")],
    [InlineKeyboardButton(text="✨ Оновити через GPT", callback_data="update_menu")]
])

update_menu_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Сніданок", callback_data="gpt_breakfast")],
    [InlineKeyboardButton(text="Обід", callback_data="gpt_lunch")],
    [InlineKeyboardButton(text="Вечеря", callback_data="gpt_dinner")],
    [InlineKeyboardButton(text="Тренування", callback_data="gpt_workout")],
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Я SmartDailyBot. Обери дію:", reply_markup=main_menu)

@dp.callback_query(F.data == "today")
async def today_plan(callback: CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні відпочинок 🌞")
    meals = f"\n\n🍼 Сніданок: {MEAL_PLAN['breakfast']}\n🥚 Обід: {MEAL_PLAN['lunch']}\n🧃 Вечеря: {MEAL_PLAN['dinner']}"
    await callback.message.answer(f"<b>Твій день:</b>\n\n{workout}{meals}")
    await callback.answer()

@dp.callback_query(F.data == "workout")
async def workout_details(callback: CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні тренувань немає")
    await callback.message.answer(f"<b>Тренування:</b>\n{workout}")
    await callback.answer()

@dp.callback_query(F.data == "menu")
async def menu_details(callback: CallbackQuery):
    meals = f"🍼 Сніданок: {MEAL_PLAN['breakfast']}\n🥚 Обід: {MEAL_PLAN['lunch']}\n🧃 Вечеря: {MEAL_PLAN['dinner']}"
    await callback.message.answer(f"<b>Меню на сьогодні:</b>\n{meals}")
    await callback.answer()

@dp.callback_query(F.data == "update_menu")
async def update_menu(callback: CallbackQuery):
    await callback.message.answer("Онови окремий пункт через GPT:", reply_markup=update_menu_markup)
    await callback.answer()

async def gpt_generate(prompt: str) -> str:
    response = await openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ти фітнес-асистент. Відповідай коротко."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

@dp.callback_query(F.data.in_("gpt_breakfast", "gpt_lunch", "gpt_dinner", "gpt_workout"))
async def gpt_update_specific(callback: CallbackQuery):
    field_map = {
        "gpt_breakfast": ("breakfast", "Оновлюю сніданок...", "Сніданок для жироспалення"),
        "gpt_lunch": ("lunch", "Оновлюю обід...", "Обід для жироспалення"),
        "gpt_dinner": ("dinner", "Оновлюю вечерю...", "Вечеря для жироспалення"),
        "gpt_workout": ("workout", "Оновлюю тренування...", "Тренування фулбаді на один день")
    }
    field, wait_msg, prompt = field_map[callback.data]
    await callback.message.answer(wait_msg)
    try:
        result = await gpt_generate(prompt)
        if field == "workout":
            weekday = datetime.datetime.now().strftime('%A').lower()
            WORKOUT_PLAN[weekday] = result
        else:
            MEAL_PLAN[field] = result
        await callback.message.answer(f"✅ Оновлено: {result}")
    except Exception as e:
        await callback.message.answer(f"Помилка при генерації: {e}")
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Повертаємось в меню:", reply_markup=main_menu)
    await callback.answer()

# Нагадування
async def send_reminders():
    now = datetime.datetime.now().strftime('%H:%M')
    weekday = datetime.datetime.now().strftime('%A').lower()
    for user_id in [123456789]:  # Заміни на свій ID
        if now == "07:00":
            await bot.send_message(user_id, "📊 Час тренування!", reply_markup=main_menu)
        elif now == "08:30":
            await bot.send_message(user_id, f"🍼 Сніданок: {MEAL_PLAN['breakfast']}")
        elif now == "13:00":
            await bot.send_message(user_id, f"🥚 Обід: {MEAL_PLAN['lunch']}")
        elif now == "19:00":
            await bot.send_message(user_id, f"🧃 Вечеря: {MEAL_PLAN['dinner']}")

scheduler.add_job(send_reminders, 'cron', minute='0', hour='7,8,13,19')

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
