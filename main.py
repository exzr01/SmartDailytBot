import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
openai = OpenAI(api_key=OPENAI_API_KEY)

# Дані
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
    [InlineKeyboardButton(text="🍽️ Меню", callback_data="menu")]
])

def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍼 Сніданок", callback_data="gpt_breakfast")],
        [InlineKeyboardButton(text="🥚 Обід", callback_data="gpt_lunch")],
        [InlineKeyboardButton(text="🧃 Вечеря", callback_data="gpt_dinner")],
        [InlineKeyboardButton(text="💪 Оновити тренування", callback_data="gpt_workout")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# Обробники
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привіт! Я SmartDailyBot. Обери дію:", reply_markup=main_menu)

@dp.callback_query(F.data == "today")
async def today_plan(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні відпочинок 🌞")
    meals = f"\n\n🍼 Сніданок: {MEAL_PLAN['breakfast']}\n🥚 Обід: {MEAL_PLAN['lunch']}\n🧃 Вечеря: {MEAL_PLAN['dinner']}"
    await callback.message.answer(f"<b>Твій день:</b>\n\n{workout}{meals}")
    await callback.answer()

@dp.callback_query(F.data == "workout")
async def workout_details(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    workout = WORKOUT_PLAN.get(weekday, "Сьогодні тренувань немає")
    await callback.message.answer(f"<b>Тренування:</b>\n{workout}", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💪 Оновити тренування GPT", callback_data="gpt_workout")]]
    ))
    await callback.answer()

@dp.callback_query(F.data == "menu")
async def menu_details(callback: types.CallbackQuery):
    meals = f"🍼 Сніданок: {MEAL_PLAN['breakfast']}\n🥚 Обід: {MEAL_PLAN['lunch']}\n🧃 Вечеря: {MEAL_PLAN['dinner']}"
    await callback.message.answer(f"<b>Меню на сьогодні:</b>\n{meals}", reply_markup=menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.answer("Повертаємось в головне меню:", reply_markup=main_menu)
    await callback.answer()

@dp.callback_query(F.data.in_(["gpt_breakfast", "gpt_lunch", "gpt_dinner", "gpt_workout"]))
async def gpt_update_part(callback: types.CallbackQuery):
    type_map = {
        "gpt_breakfast": ("breakfast", "Створи один варіант здорового сніданку для жироспалення."),
        "gpt_lunch": ("lunch", "Створи один варіант здорового обіду для жироспалення."),
        "gpt_dinner": ("dinner", "Створи один варіант здорової вечері для жироспалення."),
        "gpt_workout": ("workout", "Сформуй одне тренування для жироспалення на цілий день."),
    }
    field, prompt = type_map[callback.data]

    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = completion.choices[0].message.content

        if field == "workout":
            weekday = datetime.datetime.now().strftime('%A').lower()
            WORKOUT_PLAN[weekday] = content
        else:
            MEAL_PLAN[field] = content

        await callback.message.answer(f"Оновлено GPT:
<b>{field}</b>:
{content}")
    except OpenAIError as e:
        await callback.message.answer(f"Помилка GPT: {e}")
    await callback.answer()

# Нагадування
async def send_reminders():
    now = datetime.datetime.now().strftime('%H:%M')
    weekday = datetime.datetime.now().strftime('%A').lower()
    for user_id in [123456789]:
        if now == "07:00":
            await bot.send_message(user_id, "📊 Час тренування! Перевір, що на сьогодні:", reply_markup=main_menu)
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
