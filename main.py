import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling
import json
from datetime import datetime
import logging
import os

API_TOKEN = '8490201143:AAFtNGM5uxulM1DuB-Vq_pvSm0NYPft70Fs'
USER_ID = 7793370563

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

def load_schedule():
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

async def send_schedule():
    while True:
        now = datetime.now().strftime("%A").lower()
        current_time = datetime.now().strftime("%H:%M")
        data = load_schedule()

        if now in data and current_time in data[now]["meals"]:
            text = data[now]["meals"][current_time]
            await bot.send_message(USER_ID, f"🍽️ {text}")

        if now in data and current_time in data[now]["workout"]:
            workout = data[now]["workout"][current_time]
            await bot.send_message(USER_ID, f"🏋️‍♂️ Тренування на сьогодні: {workout}")

        await asyncio.sleep(60)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("👋 Привіт! Я SmartDailytBot. Щодня надсилатиму тобі тренування і меню за розкладом.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(send_schedule())
    start_polling(dp, skip_updates=True)
