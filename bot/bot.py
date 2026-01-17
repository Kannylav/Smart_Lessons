
import os
import asyncio

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# FSM — механизм состояний (шаги диалога)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage


from states import Flow


# переменные окружения
load_dotenv()

# токены из енв
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаём объект бота
bot = Bot(token=BOT_TOKEN)

# Dispatcher — управляет обработкой сообщений
# MemoryStorage — хранит состояния пользователей в памяти
dp = Dispatcher(storage=MemoryStorage())


# кнопки((

# Главное меню
MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Оценить урок")],
        [KeyboardButton(text="❓ Задать вопрос")],
    ],
    resize_keyboard=True
)

# Кнопки для оценки восприятия урока
MOOD_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👍"), KeyboardButton(text="😐"), KeyboardButton(text="👎")]
    ],
    resize_keyboard=True
)

# Кнопки для оценки по 5-балльной шкале
RATING_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=str(i)) for i in range(1, 6)]
    ],
    resize_keyboard=True
)

# Кнопка "Пропустить" для комментария
SKIP_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Пропустить")]],
    resize_keyboard=True
)


# чтобы он смайлики понимал

def normalize_mood(text: str):
   
    return {
        "👍": "like",
        "😐": "ok",
        "👎": "dislike"
    }.get(text)


# хендлеры

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    
    await state.clear()  # очищаем предыдущие состояния

    await message.answer(
        "Привет! 👋\n\n"
        "Я бот для *анонимной обратной связи*.\n"
        "Ты можешь оценить урок или задать вопрос учителю.\n\n"
        "Выбери действие 👇",
        reply_markup=MAIN_KB,
        parse_mode="Markdown"
    )


# оценка урока

@dp.message(F.text == "⭐ Оценить урок")
async def rate_lesson_start(message: Message, state: FSMContext):
    
    await state.clear()
    await state.set_state(Flow.waiting_lesson_code)

    # Сохраняем режим — оценка
    await state.update_data(mode="rate")

    await message.answer("Введите код урока:")


# вопроосс

@dp.message(F.text == "❓ Задать вопрос")
async def ask_question_start(message: Message, state: FSMContext):
    
    await state.clear()
    await state.set_state(Flow.waiting_lesson_code)

    
    await state.update_data(mode="question")

    await message.answer("Введите код урока:")


# ввод кода

@dp.message(Flow.waiting_lesson_code)
async def got_lesson_code(message: Message, state: FSMContext):
   
    data = await state.get_data()
    mode = data.get("mode")

    code = message.text.strip().upper()

    # для бд
    lesson = {
        "id": 1,
        "title": f"Демо-урок ({code})"
    }

    # для id 
    await state.update_data(lesson_id=lesson["id"])

    # если вопрос
    if mode == "question":
        await state.set_state(Flow.waiting_question)
        await message.answer(
            f"✍️ Напиши анонимный вопрос по уроку:\n\n*{lesson['title']}*",
            parse_mode="Markdown"
        )
        return

    # если оценка
    await state.set_state(Flow.waiting_mood)
    await message.answer(
        f"📘 Урок: *{lesson['title']}*\n\n"
        "Как ты оцениваешь понимание / впечатление?",
        reply_markup=MOOD_KB,
        parse_mode="Markdown"
    )


# выбор смайликов

@dp.message(Flow.waiting_mood)
async def got_mood(message: Message, state: FSMContext):
    mood = normalize_mood(message.text)

    if mood is None:
        await message.answer("Пожалуйста, выбери 👍 😐 или 👎")
        return

    await state.update_data(mood=mood)
    await state.set_state(Flow.waiting_rating)

    await message.answer(
        "Поставь оценку от 1 до 5:",
        reply_markup=RATING_KB
    )


# оценка 1 - 5

@dp.message(Flow.waiting_rating)
async def got_rating(message: Message, state: FSMContext):
    try:
        rating = int(message.text)
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        await message.answer("Введите число от 1 до 5.")
        return

    await state.update_data(rating=rating)
    await state.set_state(Flow.waiting_comment)

    await message.answer(
        "Хочешь оставить комментарий? (можно пропустить)",
        reply_markup=SKIP_KB
    )


# комменты

@dp.message(Flow.waiting_comment)
async def got_comment(message: Message, state: FSMContext):
    data = await state.get_data()

    # это если "пропустить"
    comment = None
    if message.text.lower() != "пропустить":
        comment = message.text.strip()

    await state.clear()
    await message.answer(
        "✅ Спасибо! Твоя оценка сохранена анонимно.",
        reply_markup=MAIN_KB
    )


# для вопросов

@dp.message(Flow.waiting_question)
async def got_question(message: Message, state: FSMContext):
    text = message.text.strip()

    if len(text) < 3:
        await message.answer("Вопрос слишком короткий. Попробуй написать подробнее 🙂")
        return

    await state.clear()
    await message.answer(
        "📨 Вопрос отправлен анонимно.",
        reply_markup=MAIN_KB
    )


# для запуска

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
