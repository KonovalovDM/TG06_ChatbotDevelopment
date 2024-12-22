import asyncio
import random
import logging
import requests
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TOKEN
import json

# Загрузка текстов сообщений
with open("messages.json", "r", encoding="utf-8") as file:
    MESSAGES = json.load(file)

# Логгирование
logging.basicConfig(level=logging.INFO)

# Бот и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавиатура
keyboards = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Регистрация в телеграм боте"),
            KeyboardButton(text="Курс валют")
        ],
        [
            KeyboardButton(text="Советы по экономии"),
            KeyboardButton(text="Личные финансы")
        ]
    ],
    resize_keyboard=True
)


# Подключение к SQLite
conn = sqlite3.connect("user.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    name TEXT,
    category1 TEXT,
    category2 TEXT,
    category3 TEXT,
    expenses1 REAL,
    expenses2 REAL,
    expenses3 REAL
)
''')
conn.commit()

# FSM-состояния
class FinancesForm(StatesGroup):
    category1 = State()
    expenses1 = State()
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State()

@dp.message(Command("start"))
async def send_start(message: Message):
    await message.answer(MESSAGES["start_message"], reply_markup=keyboards)

@dp.message(F.text == "Регистрация в телеграм боте")
async def registration(message: Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    with sqlite3.connect("user.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if user:
            await message.answer(MESSAGES["already_registered"])
        else:
            cursor.execute("INSERT INTO users (telegram_id, name) VALUES (?, ?)", (telegram_id, name))
            conn.commit()
            await message.answer(MESSAGES["registration_success"])

@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/7ef3a10b089a9cd920aec19f/latest/USD"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        usd_to_rub = data["conversion_rates"]["RUB"]
        usd_to_eur = data["conversion_rates"]["EUR"]
        euro_to_rub = 1 / usd_to_eur * usd_to_rub
        usd_to_cny = data["conversion_rates"]["CNY"]
        cny_to_rub = 1 / usd_to_cny * usd_to_rub
        usd_to_inr = data["conversion_rates"]["INR"]
        inr_to_rub = 1 / usd_to_inr * usd_to_rub
        await message.answer(MESSAGES["currency_rates"].format(usd_to_rub=usd_to_rub, eur_to_rub=euro_to_rub, cny_to_rub=cny_to_rub, inr_to_rub=inr_to_rub))
    except requests.RequestException as e:
        logging.error(f"Ошибка API: {e}")
        await message.answer(MESSAGES["currency_error"])

@dp.message(F.text == "Советы по экономии")
async def send_tips(message: Message):
    tip = random.choice(MESSAGES["financial_tips"])
    await message.answer(tip)

@dp.message(F.text == "Личные финансы")
async def finances_start(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.category1)
    await message.reply(MESSAGES["enter_category"].format(category_number=1))

@dp.message(FinancesForm.category1)
async def finances_category1(message: Message, state: FSMContext):
    await state.update_data(category1=message.text)
    await state.set_state(FinancesForm.expenses1)
    await message.reply(MESSAGES["enter_expense"].format(category_number=1))

@dp.message(FinancesForm.expenses1)
async def finances_expenses1(message: Message, state: FSMContext):
    await state.update_data(expenses1=float(message.text))
    await state.set_state(FinancesForm.category2)
    await message.reply(MESSAGES["enter_category"].format(category_number=2))

@dp.message(FinancesForm.category2)
async def finances_category2(message: Message, state: FSMContext):
    await state.update_data(category2=message.text)
    await state.set_state(FinancesForm.expenses2)
    await message.reply(MESSAGES["enter_expense"].format(category_number=2))

@dp.message(FinancesForm.expenses2)
async def finances_expenses2(message: Message, state: FSMContext):
    await state.update_data(expenses2=float(message.text))
    await state.set_state(FinancesForm.category3)
    await message.reply(MESSAGES["enter_category"].format(category_number=3))

@dp.message(FinancesForm.category3)
async def finances_category3(message: Message, state: FSMContext):
    await state.update_data(category3=message.text)
    await state.set_state(FinancesForm.expenses3)
    await message.reply(MESSAGES["enter_expense"].format(category_number=3))

@dp.message(FinancesForm.expenses3)
async def finances_expenses3(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = message.from_user.id
    cursor.execute('''UPDATE users SET category1 = ?, expenses1 = ?, category2 = ?, expenses2 = ?, category3 = ?, expenses3 = ? WHERE telegram_id = ?''',
                   (data['category1'], data['expenses1'], data['category2'], data['expenses2'], data['category3'], float(message.text), telegram_id))
    conn.commit()
    await state.clear()
    await message.answer(MESSAGES["expenses_saved"])

@dp.message(Command("help"))
async def show_help(message: Message):
    await message.answer(MESSAGES["help_message"])


@dp.message(Command("see_db"))
async def see_database(message: Message):
    with sqlite3.connect("user.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, category1, expenses1, category2, expenses2, category3, expenses3 FROM users")
        users_data = cursor.fetchall()

    if users_data:
        response = MESSAGES["db_data"].format(
            data="\n\n".join(
                f"Имя: {name}\n"
                f"Категория 1: {category1}, Расходы: {expenses1:.2f}\n"
                f"Категория 2: {category2}, Расходы: {expenses2:.2f}\n"
                f"Категория 3: {category3}, Расходы: {expenses3:.2f}"
                for name, category1, expenses1, category2, expenses2, category3, expenses3 in users_data
            )
        )
    else:
        response = MESSAGES["db_empty"]

    await message.answer(response)


# Запуск бота
async def main():
    try:
        logging.debug("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка во время работы бота: {e}")
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())