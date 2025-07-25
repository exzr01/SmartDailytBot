import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Просте меню
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("👋 Привіт!"))
    await message.answer("Вітаю в SmartDailytBot!", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "👋 Привіт!")
async def reply_handler(message: types.Message):
    await message.reply("Привіт! Чим можу допомогти сьогодні?")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
