# main.py с полной функциональностью (GigaChat, шаблоны, оплата, email, PDF, Excel, WebApp, админка)
import logging
import os
from dotenv import load_dotenv
load_dotenv()
import smtplib
import sqlite3
import requests
from datetime import datetime
from email.message import EmailMessage
from docx2pdf import convert
import xlsxwriter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InputFile, WebAppInfo, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotSettings
from aiogram.fsm.storage.memory import MemoryStorage
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotSettings(parse_mode=ParseMode.HTML)
)
import asyncio
from dotenv import load_dotenv

# ===== Логирование =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ===== Настройки =====
load_dotenv()
BOT_TOKEN = "7947746152:AAGtLCKdA9FjXTio6d6in2Q2YDkcwt2Px5E"
GIGACHAT_TOKEN = "YWZhZTZlYWUtZjQ2NC00OWYzLTg2N2QtZGQ5ODYyYjM4NGVlOmJlM2FkNzFkLWY1ZDEtNDlkZS1hNmU0LTQ3NTBlOWJiMzRiNg=="
EMAIL_LOGIN = "kuralbaev777@mail.ru"
EMAIL_PASSWORD = "@&$os125"
KASPI_CARD = "4400430241005559"
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
MODERATION_FORBIDDEN = ["оскорбление", "угроза", "экстремизм"]

# ===== БД =====
db = sqlite3.connect("db.sqlite3")
db.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, user_id INTEGER, template TEXT, created_at TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER, phone TEXT, created_at TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, user_id INTEGER, file_path TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
db.commit()

# ===== Бот =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ===== Клавиатура =====
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Шаблоны")],
        [KeyboardButton(text="💬 Вопрос юристу")],
        [KeyboardButton(text="📑 Мини-приложение", web_app=WebAppInfo(url="https://example.com/webapp"))],
        [KeyboardButton(text="📧 Получить по Email")],
        [KeyboardButton(text="🧾 PDF и Excel отчёт")]
    ],
    resize_keyboard=True
)

# ===== Команды =====
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("👋 Добро пожаловать в Юрист-бот!\nПолучите шаблоны, задайте вопрос юристу или оплатите Kaspi:", reply_markup=main_kb)

@dp.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🔐 Админ-панель: доступ подтвержден.")
    else:
        await message.answer("⛔ Нет доступа.")

@dp.message(F.text == "/pay")
async def cmd_pay(message: Message):
    await message.answer(f"💳 Для получения шаблона переведите 2000₸ на Kaspi: <b>{KASPI_CARD}</b> и отправьте скрин.")

# ===== Ответ ИИ =====
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_question(message: Message):
    if not check_moderation(message.text):
        await message.answer("⚠️ Сообщение нарушает правила. Переформулируйте.")
        return
    await message.answer("🤖 Думаю...")
    try:
        response = ask_gigachat(message.text)
        await message.answer(response)
        save_request(message.from_user.id, message.text)
    except Exception as e:
        logging.exception(e)
        await message.answer(f"❌ Ошибка GigaChat: {str(e)}")

# ===== Модерация =====
def check_moderation(text):
    for word in MODERATION_FORBIDDEN:
        if word.lower() in text.lower():
            return False
    return True

# ===== GigaChat API =====
def ask_gigachat(prompt):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GIGACHAT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "GigaChat:latest",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=payload, verify=False)
    try:
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        elif "detail" in result:
            return f"⚠️ GigaChat ответил: {result['detail']}"
        elif "error" in result:
            return f"❌ Ошибка GigaChat: {result['error']}"
        else:
            return f"⚠️ Неожиданный ответ GigaChat: {result}"
    except Exception as e:
        return f"❌ Ошибка при разборе ответа GigaChat: {str(e)}"

# ===== Сохранение =====
def save_request(user_id, text):
    db.execute("INSERT INTO requests (user_id, template, created_at) VALUES (?, ?, ?)", (user_id, text, datetime.now().isoformat()))
    db.commit()

# ===== Запуск бота =====
async def main():
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
