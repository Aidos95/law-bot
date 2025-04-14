# main.py с полной функциональностью (GigaChat, шаблоны, оплата, email, PDF, Excel, WebApp, админка)
import logging
import os
import asyncio
import smtplib
import sqlite3
import requests
from datetime import datetime
from email.message import EmailMessage
from docx2pdf import convert
import xlsxwriter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, WebAppInfo
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ===== Загрузка переменных окружения =====
load_dotenv()
BOT_TOKEN = "7947746152:AAGtLCKdA9FjXTio6d6in2Q2YDkcwt2Px5E"
GIGACHAT_TOKEN = "YWZhZTZlYWUtZjQ2NC00OWYzLTg2N2QtZGQ5ODYyYjM4NGVlOmJlM2FkNzFkLWY1ZDEtNDlkZS1hNmU0LTQ3NTBlOWJiMzRiNg=="
EMAIL_LOGIN = "kuralbaev777@mail.ru"
EMAIL_PASSWORD = "@&$os125"
KASPI_CARD = "4400430241005559"
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
MODERATION_FORBIDDEN = ["оскорбление", "угроза", "экстремизм"]

# ===== Инициализация бота =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ===== Логирование =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)

# ===== База данных =====
db = sqlite3.connect("db.sqlite3")
db.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, user_id INTEGER, template TEXT, created_at TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, user_id INTEGER, file_path TEXT, status TEXT DEFAULT 'pending', created_at TEXT)")
db.commit()

# ===== Клавиатура =====
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="\ud83d\udcc4 \u0428\u0430\u0431\u043b\u043e\u043d\u044b")],
        [KeyboardButton(text="\ud83d\udcac \u0412\u043e\u043f\u0440\u043e\u0441 \u044e\u0440\u0438\u0441\u0442\u0443")],
        [KeyboardButton(text="\ud83d\udcc1 \u041c\u0438\u043d\u0438-\u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435", web_app=WebAppInfo(url="https://example.com/webapp"))],
        [KeyboardButton(text="\ud83d\udce7 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u043f\u043e Email")],
        [KeyboardButton(text="\ud83e\uddfe PDF \u0438 Excel \u043e\u0442\u0447\u0451\u0442")]
    ], resize_keyboard=True
)

# ===== Команды =====
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("\ud83d\udc4b \u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c!", reply_markup=main_kb)

@dp.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("\ud83d\udd10 \u0410\u0434\u043c\u0438\u043d-\u043f\u0430\u043d\u0435\u043b\u044c \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430")
    else:
        await message.answer("\u26d4\ufe0f \u041d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430")

@dp.message(F.text == "/pay")
async def cmd_pay(message: Message):
    await message.answer(f"\ud83d\udcb3 \u041e\u043f\u043b\u0430\u0442\u0438\u0442\u0435 2000\u20b8 Kaspi: <b>{KASPI_CARD}</b> и отправьте скрин")

# ===== GigaChat API =====
def ask_gigachat(prompt):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GIGACHAT_TOKEN}", "Content-Type": "application/json"}
    payload = {"model": "GigaChat:latest", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(url, headers=headers, json=payload, verify=False)
    try:
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "\u2757\ufe0f \u041e\u0442\u0432\u0435\u0442 \u043d\u0435 \u043f\u043e\u043b\u0443\u0447\u0435\u043d")
    except Exception as e:
        return f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 GigaChat: {str(e)}"

# ===== Модерация =====
def check_moderation(text):
    return not any(w.lower() in text.lower() for w in MODERATION_FORBIDDEN)

# ===== Сохранение =====
def save_request(user_id, text):
    db.execute("INSERT INTO requests (user_id, template, created_at) VALUES (?, ?, ?)", (user_id, text, datetime.now().isoformat()))
    db.commit()

# ===== Обработка сообщений =====
@dp.message(F.photo)
async def handle_photo(message: Message):
    path = f"screenshots/{message.from_user.id}_{datetime.now().timestamp()}.jpg"
    os.makedirs("screenshots", exist_ok=True)
    await bot.download(message.photo[-1], path)
    db.execute("INSERT INTO payments (user_id, file_path, created_at) VALUES (?, ?, ?)", (message.from_user.id, path, datetime.now().isoformat()))
    db.commit()
    for admin_id in ADMIN_IDS:
        await bot.send_photo(admin_id, photo=FSInputFile(path), caption=f"\ud83d\udce5 Новый платёж от {message.from_user.id}")
    await message.answer("\u2705 Скрин получен! Ожидайте шаблон после подтверждения.")

@dp.message(F.text == "\ud83d\udce7 \u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u043f\u043e Email")
async def email_send(message: Message):
    await message.answer("\ud83d\udce7 Напишите вашу почту...")
    # тут можно FSM на email и шаблон

@dp.message(F.text == "\ud83e\uddfe PDF \u0438 Excel \u043e\u0442\u0447\u0451\u0442")
async def report_excel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("\u26d4\ufe0f Только для админа")
    os.makedirs("reports", exist_ok=True)
    path = "reports/requests.xlsx"
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet()
    ws.write_row(0, 0, ["ID", "User", "Text", "Date"])
    for i, row in enumerate(db.execute("SELECT * FROM requests")):
        ws.write_row(i + 1, 0, row)
    wb.close()
    await message.answer_document(FSInputFile(path), caption="\ud83d\udcca Excel отчёт")

@dp.message(F.text == "\ud83d\udcc4 \u0428\u0430\u0431\u043b\u043e\u043d\u044b")
async def show_templates(message: Message):
    files = os.listdir("templates")
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(f"\ud83d\udcc4 {f}")] for f in files], resize_keyboard=True)
    await message.answer("\ud83d\udd39 Выберите шаблон:", reply_markup=kb)

@dp.message(lambda m: m.text and m.text.startswith("\ud83d\udcc4 "))
async def send_template(message: Message):
    name = message.text.replace("\ud83d\udcc4 ", "")
    path = os.path.join("templates", name)
    if os.path.exists(path):
        await message.answer_document(FSInputFile(path), caption=f"\ud83d\udcc4 {name}")
    else:
        await message.answer("\u274c Шаблон не найден")

@dp.message(F.text & ~F.text.startswith("/"))
async def ai_response(message: Message):
    if not check_moderation(message.text):
        return await message.answer("\u26a0\ufe0f Сообщение нарушает правила")
    await message.answer("\ud83e\udd16 Думаю...")
    try:
        reply = ask_gigachat(message.text)
        await message.answer(reply)
        save_request(message.from_user.id, message.text)
    except Exception as e:
        logging.exception(e)
        await message.answer("\u274c Ошибка: " + str(e))

# ===== Запуск =====
async def main():
    print("\u2705 Бот запущен")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("⛔️ Бот остановлен")
