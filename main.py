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
from openai import OpenAI, OpenAIError

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to Railway → Variables.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please add it to Railway → Variables.")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()
openai = OpenAI(api_key=OPENAI_API_KEY)

WORKOUT_PLAN = {
    "monday": "🔴 Понедiлок – ГРУДИ + ТРIЦЕПС + ПЕРЕДНЯ ДЕЛЬТА",
    "wednesday": "🔵 Середа – СПИНА + БIЦЕПС + ЗАДНЯ ДЕЛЬТА",
    "friday": "🔷 П’ятниця – НОГИ + ПРЕС + БIЧНА ДЕЛЬТА"
}

MEAL_PLAN = {
    "breakfast": {"text": "🍼 Омлет з овочами в мультипечі", "calories": 300},
    "lunch": {"text": "🥚 Куряче філе з броколі", "calories": 500},
    "dinner": {"text": "🧃 Риба з овочами на парі", "calories": 400}
}

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❓ Що сьогодні?", callback_data="today")],
    [InlineKeyboardButton(text="💪 Тренування", callback_data="workout")],
    [InlineKeyboardButton(text="🍽️ Меню", callback_data="menu")]
])

def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Оновити сніданок", callback_data="gpt_breakfast")],
        [InlineKeyboardButton(text="✨ Оновити обід", callback_data="gpt_lunch")],
        [InlineKeyboardButton(text="✨ Оновити вечерю", callback_data="gpt_dinner")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

def workout_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Оновити тренування", callback_data="gpt_workout")],
        [InlineKeyboardButton(text="➕ Додати своє тренування", callback_data="custom_workout")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Я SmartDailyBot. Обери дію:", reply_markup=main_menu)

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.edit_text("⬅️ Повертаємось в головне меню", reply_markup=main_menu)
    await callback.answer()

@dp.callback_query(F.data == "today")
async def today_plan(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні немає тренування. Рекомендуємо легке кардіо 🚶‍♂️")
    meals = "\n".join([
        f"{MEAL_PLAN[meal]['text']} — {MEAL_PLAN[meal]['calories']} ккал" for meal in ["breakfast", "lunch", "dinner"]
    ])
    await callback.message.answer(f"<b>Твій день:</b>\n\n<b>Тренування:</b>\n{workout}\n\n<b>Меню:</b>\n{meals}")
    await callback.answer()

@dp.callback_query(F.data == "workout")
async def workout_details(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні немає тренування. Спробуй кардіо 🚴")
    await callback.message.answer(f"<b>Тренування:</b>\n{workout}", reply_markup=workout_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "menu")
async def menu_details(callback: types.CallbackQuery):
    meals = "\n".join([
        f"{MEAL_PLAN[meal]['text']} — {MEAL_PLAN[meal]['calories']} ккал" for meal in ["breakfast", "lunch", "dinner"]
    ])
    await callback.message.answer(f"<b>Меню на сьогодні:</b>\n{meals}", reply_markup=menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "custom_workout")
async def custom_workout(callback: types.CallbackQuery):
    await callback.message.answer("Надішли своє тренування текстом, і я його збережу (не збережеться після перезапуску)")
    await callback.answer()

@dp.callback_query(F.data.in_(["gpt_breakfast", "gpt_lunch", "gpt_dinner", "gpt_workout"]))
async def gpt_update(callback: types.CallbackQuery):
    target = callback.data.split("_")[1]
    prompts = {
        "breakfast": "Створи здоровий сніданок до 300 ккал у форматі 1 речення",
        "lunch": "Створи здоровий обід до 500 ккал у форматі 1 речення",
        "dinner": "Створи легку вечерю до 400 ккал у форматі 1 речення",
        "workout": "Створи коротке тренування для жироспалення на один день"
    }
    try:
        chat = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ти фітнес-асистент і дієтолог."},
                {"role": "user", "content": prompts[target]}
            ]
        )
        result = chat.choices[0].message.content
        if target in MEAL_PLAN:
            MEAL_PLAN[target]['text'] = result
        elif target == "workout":
            weekday = datetime.datetime.now().strftime('%A').lower()
            WORKOUT_PLAN[weekday] = result
        await callback.message.answer(f"Оновлено GPT:\n{result}")
    except OpenAIError as e:
        await callback.message.answer(f"Помилка GPT: {str(e)}")
    await callback.answer()

# Нагадування
async def send_reminders():
    now = datetime.datetime.now().strftime('%H:%M')
    weekday = datetime.datetime.now().strftime('%A').lower()
    user_ids = [7793370563]  # заміни на свій Telegram user_id
    for user_id in user_ids:
        if now == "07:00":
            await bot.send_message(user_id, "📊 Час тренування! Перевір, що на сьогодні:", reply_markup=main_menu)
        elif now == "08:30":
            await bot.send_message(user_id, f"🍼 Сніданок: {MEAL_PLAN['breakfast']['text']}")
        elif now == "13:00":
            await bot.send_message(user_id, f"🥚 Обід: {MEAL_PLAN['lunch']['text']}")
        elif now == "19:00":
            await bot.send_message(user_id, f"🧃 Вечеря: {MEAL_PLAN['dinner']['text']}")

scheduler.add_job(send_reminders, 'cron', minute='0', hour='7,8,13,19')

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
