import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

# Токен вашего бота
TOKEN = "1780243447:z-EViDoEUiE61aHerKad4WazMWTsKC3OraH"

# Настройка кастомного сервера для ShuzaGram в aiogram 3.x
custom_server = TelegramAPIServer.from_base("https://api.shuzagram.com")
session = AiohttpSession(api=custom_server)

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher(storage=MemoryStorage())


# --- КЛАВИАТУРЫ ---


def get_main_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
          [KeyboardButton(text="🎰 Казино"), KeyboardButton(text="🛒 Шмотки")],
      ],
      resize_keyboard=True,
  )


def get_work_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="🤝 Рефка"), KeyboardButton(text="🍔 Бизнес")],
          [KeyboardButton(text="🧱 Блок"), KeyboardButton(text="🚕 Таксист")],
          [KeyboardButton(text="👮 Федерал"), KeyboardButton(text="⬅️ Назад")],
      ],
      resize_keyboard=True,
  )


# --- ОБРАБОТЧИКИ ---


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


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
  await message.answer("Главное меню, бро:", reply_markup=get_main_menu())


@dp.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
  await message.answer(
      "📊 **Твой профиль:**\n\n💰 Бахчи (бабосы): $1,000\n🧢 Ранг: Скуф /"
      " Обычный чел\n🛡 Защита: 10\n⚖️ Статус: На свободе",
      reply_markup=get_main_menu(),
  )


@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  await message.answer(
      "мяумс, выбери работу, на которой хочешь сейчас работать:",
      reply_markup=get_work_menu(),
  )


# Обработчики конкретных работ
@dp.message(
    F.text.in_(["🤝 Рефка", "🍔 Бизнес", "🧱 Блок", "🚕 Таксист", "👮 Федерал"])
)
async def choose_work_handler(message: Message):
  await message.answer(
      f"Ты устроился на работу: **{message.text}**. Начинай суету! 💼",
      reply_markup=get_work_menu(),
  )


@dp.message(F.text == "🎰 Казино")
async def casino_handler(message: Message):
  await message.answer(
      "🎲 Добро пожаловать в кинцо «как остаться без трусов»!\nЗа какой стол"
      " сядете?",
      reply_markup=get_main_menu(),
  )


@dp.message(F.text == "🛒 Шмотки")
async def market_handler(message: Message):
  await message.answer(
      "🛍 **BB MARKET:**\nТут можно прикупить шмотки для поднятия авторитета и"
      " защиты.",
      reply_markup=get_main_menu(),
  )


@dp.message()
async def echo_handler(message: Message):
  await message.answer(
      "Чет непонятная малява. Пользуйся меню или пиши /start, бро.",
      reply_markup=get_main_menu(),
  )


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (Free Web Service) ---
async def handle(request):
  return web.Response(text="Бот Бандит на связи и работает!")


async def start_web_server():
  app = web.Application()
  app.router.add_get("/", handle)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  print(f"Веб-сервер запущен на порту {port}")


async def main():
  logging.basicConfig(level=logging.INFO)
  print("Запуск бота бандита...")

  # Запускаем фоновый веб-сервер для порта Render
  asyncio.create_task(start_web_server())

  # Запускаем поллинг бота
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
