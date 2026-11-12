import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

# Токен вашего бота
TOKEN = "1780243447:z-EViDoEUiE61aHerKad4WazMWTsKC3OraH"

# Настройка сессии для ShuzaGram
session = AiohttpSession(
    api=dict(
        base="https://api.shuzagram.com/bot{token}/{method}",
        file="https://api.shuzagram.com/file/bot{token}/{path}",
    )
)

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher(storage=MemoryStorage())


# Клавиатура главного меню
def get_main_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
          [KeyboardButton(text="🎰 Казино"), KeyboardButton(text="🛒 Шмотки")],
      ],
      resize_keyboard=True,
  )


# Обработчик команды /start
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
  user_name = message.from_user.first_name or "Бро"
  text = (
      f"Здорово, {user_name}! 🤙 Добро пожаловать в **бот бандит**.\n\n"
      "Это симулятор реальной жизни: поднимай бабосы, качай перса, бери"
      " бизнес в блок и стань федералом или авторитетом.\n\n"
      "Жми на кнопки ниже, чтобы начать движ:"
  )
  await message.answer(text, reply_markup=get_main_menu())


# Обработчик кнопки «Профиль»
@dp.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
  text = (
      "📊 **Твой профиль:**\n\n"
      "💰 Бахчи (бабосы): $1,000\n"
      "🧢 Ранг: Скуф / Обычный чел\n"
      "🛡 Защита: 10\n"
      "⚖️ Статус: На свободе"
  )
  await message.answer(text)


# Обработчик кнопки «Работа»
@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  text = (
      "мяумс, выбери работу, на которой хочешь сейчас работать:\n\n"
      "• 🤝 Рефка\n"
      "• 🍔 Бизнес\n"
      "• 🧱 Блок\n"
      "• 🚕 Таксист\n"
      "• 👮 Федерал"
  )
  await message.answer(text)


# Обработчик кнопки «Казино»
@dp.message(F.text == "🎰 Казино")
async def casino_handler(message: Message):
  text = (
      "🎲 Добро пожаловать в кинцо «как остаться без трусов»!\n"
      "За какой стол сядете?"
  )
  await message.answer(text)


# Обработчик кнопки «Шмотки»
@dp.message(F.text == "🛒 Шмотки")
async def market_handler(message: Message):
  text = (
      "🛍 **BB MARKET:**\n"
      "Тут можно прикупить шмотки для поднятия авторитета и защиты."
  )
  await message.answer(text)


# Общий обработчик текста
@dp.message()
async def echo_handler(message: Message):
  await message.answer("Чет непонятная малява. Пользуйся меню или пиши /start, бро.")


# --- ЗАГЛУШКА ВЕБ-СЕРВЕРА ДЛЯ RENDER ---
async def handle(request):
  return web.Response(
      text="Бот Бандит успешно пашет на ShuzaGram и ждет маслин!"
  )


async def start_web_server():
  app = web.Application()
  app.router.add_get("/", handle)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  print(f"Веб-сервер-заглушка запущен на порту {port}")


async def main():
  logging.basicConfig(level=logging.INFO)
  print("Бот бандит на aiogram запускается...")

  # Запускаем веб-сервер для порта Render
  asyncio.create_task(start_web_server())

  # Запускаем поллинг бота
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
