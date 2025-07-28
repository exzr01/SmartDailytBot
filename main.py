# Додамо логіку відмітки підходів у вправі для SmartDailyBot

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Збережемо приклад плану тренування з підходами
WORKOUT_SETS = {
    "monday": [
        {"exercise": "Жим лежачи", "sets": 3, "done": [False, False, False]},
        {"exercise": "Кросовер", "sets": 3, "done": [False, False, False]},
        {"exercise": "Бруси", "sets": 3, "done": [False, False, False]}
    ]
}

# Генерація клавіатури для відмітки підходів

def generate_sets_keyboard(day):
    keyboard = []
    for i, exercise in enumerate(WORKOUT_SETS[day]):
        row = []
        for j in range(exercise['sets']):
            label = "✅" if exercise['done'][j] else f"{j+1}"
            row.append(InlineKeyboardButton(
                text=label,
                callback_data=f"set_done:{day}:{i}:{j}"
            ))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Хендлер для показу тренування з відміткою підходів
@dp.callback_query(F.data == "track_workout")
async def track_workout(callback: types.CallbackQuery):
    weekday = datetime.datetime.now().strftime('%A').lower()
    if weekday not in WORKOUT_SETS:
        await callback.message.answer("Сьогодні тренування немає")
        return
    text = "<b>Виконуй вправи й відмічай підходи:</b>\n\n"
    for i, ex in enumerate(WORKOUT_SETS[weekday]):
        status = " ".join(["✅" if done else "🔲" for done in ex["done"]])
        text += f"{ex['exercise']}: {status}\n"
    await callback.message.answer(text, reply_markup=generate_sets_keyboard(weekday))
    await callback.answer()

# Хендлер для обробки відмітки підходу
@dp.callback_query(F.data.startswith("set_done"))
async def mark_set_done(callback: types.CallbackQuery):
    _, day, ex_idx, set_idx = callback.data.split(":")
    ex_idx, set_idx = int(ex_idx), int(set_idx)
    WORKOUT_SETS[day][ex_idx]['done'][set_idx] = not WORKOUT_SETS[day][ex_idx]['done'][set_idx]
    await track_workout(callback)
