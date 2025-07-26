import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import openai

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
openai.api_key = OPENAI_API_KEY

# Розклад
WORKOUT_PLAN = {
    "monday": "\ud83d\udd34 Понедiлок \u2013 ГРУДИ + ТРIЦЕПС + ПЕРЕДНЯ ДЕЛЬТА...",
    "wednesday": "\ud83d\udd35 Середа \u2013 СПИНА + БIЦЕПС + ЗАДНЯ ДЕЛЬТА...",
    "friday": "\ud83d\udd37 П\u2019ятниця \u2013 НОГИ + ПРЕС + БIЧНА ДЕЛЬТА..."
}

MEAL_PLAN = {
    "breakfast": "\ud83c\udf7c Омлет з овочами в мультипечі",
    "lunch": "\ud83e\udd5a Куряче філе з броколі",
    "dinner": "\ud83e\uddc3 Риба з овочами на парі"
}

# Кнопки
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="\u2753 Що сьогодні?", callback_data="today")],
    [InlineKeyboardButton(text="\ud83d\udcaa Тренування", callback_data="workout")],
    [InlineKeyboardButton(text="\ud83c\udf7d\ufe0f Меню", callback_data="menu")],
    [InlineKeyboardButton(text="\u2728 Оновити через GPT", callback_data="gpt_update")]
])

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Я SmartDailyBot. Обери дію:", reply_markup=main_menu)

@dp.callback_query(F.data == "today")
async def today_plan(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні відпочинок \ud83c\udf1e")
    meals = f"\n\n\ud83c\udf7c Сніданок: {MEAL_PLAN['breakfast']}\n\ud83e\udd5a Обід: {MEAL_PLAN['lunch']}\n\ud83e\uddc3 Вечеря: {MEAL_PLAN['dinner']}"
    await callback.message.answer(f"<b>Твій день:</b>\n\n{workout}{meals}")
    await callback.answer()

@dp.callback_query(F.data == "workout")
async def workout_details(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні тренувань немає")
    await callback.message.answer(f"<b>Тренування:</b>\n{workout}")
    await callback.answer()

@dp.callback_query(F.data == "menu")
async def menu_details(callback: types.CallbackQuery):
    meals = f"\ud83c\udf7c Сніданок: {MEAL_PLAN['breakfast']}\n\ud83e\udd5a Обід: {MEAL_PLAN['lunch']}\n\ud83e\uddc3 Вечеря: {MEAL_PLAN['dinner']}"
    await callback.message.answer(f"<b>Меню на сьогодні:</b>\n{meals}")
    await callback.answer()

@dp.callback_query(F.data == "gpt_update")
async def gpt_update(callback: types.CallbackQuery):
    await callback.message.answer("Генерую новий план з OpenAI...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ти фітнес-дієтолог. Створи коротке меню на день з трьома прийомами їжі для жироспалення."},
                {"role": "user", "content": "Онови меню для жироспалення. Вкажи сніданок, обід, вечерю."}
            ]
        )
        content = response.choices[0].message.content
        await callback.message.answer(f"Оновлене меню GPT:\n{content}")
    except Exception as e:
        await callback.message.answer(f"Помилка при генерації: {e}")
    await callback.answer()

# Нагадування
async def send_reminders():
    now = datetime.datetime.now().strftime('%H:%M')
    weekday = datetime.datetime.now().strftime('%A').lower()
    for user_id in [7793370563]:  # Тут додай свій ID або список
        if now == "07:00":
            await bot.send_message(user_id, "\ud83d\udcca Час тренування! Перевір, що на сьогодні:", reply_markup=main_menu)
        elif now == "08:30":
            await bot.send_message(user_id, f"\ud83c\udf7c Сніданок: {MEAL_PLAN['breakfast']}")
        elif now == "13:00":
            await bot.send_message(user_id, f"\ud83e\udd5a Обід: {MEAL_PLAN['lunch']}")
        elif now == "19:00":
            await bot.send_message(user_id, f"\ud83e\uddc3 Вечеря: {MEAL_PLAN['dinner']}")

scheduler.add_job(send_reminders, 'cron', minute='0', hour='7,8,13,19')

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
