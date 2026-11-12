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

# Простая база данных в памяти для каждого игрока (баланс, защита, ранг)
users_db = {}


def get_user(user_id):
  if user_id not in users_db:
    users_db[user_id] = {
        "money": 1000,
        "defense": 10,
        "rank": "Скуф / Обычный чел",
    }
  return users_db[user_id]


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


def get_casino_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="🎲 Бросить кости ($100)"), KeyboardButton(text="🃏 Очко ($200)")],
          [KeyboardButton(text="⬅️ Назад")],
      ],
      resize_keyboard=True,
  )


def get_market_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [
              KeyboardButton(text="👕 Шмотка VETEMENTS ($500)"),
              KeyboardButton(text="🛡 Прокачать защиту ($300)"),
          ],
          [KeyboardButton(text="⬅️ Назад")],
      ],
      resize_keyboard=True,
  )


# --- ОБРАБОТЧИКИ ---


@dp.message(F.text == "/start")
async def cmd_start(message: Message):
  user = get_user(message.from_user.id)
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
  user = get_user(message.from_user.id)
  text = (
      f"📊 **Твой профиль:**\n\n"
      f"💰 Бахчи (бабосы): ${user['money']:,}\n"
      f"🧢 Ранг: {user['rank']}\n"
      f"🛡 Защита: {user['defense']}\n"
      f"⚖️ Статус: На свободе"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  await message.answer(
      "мяумс, выбери работу, на которой хочешь сейчас работать:",
      reply_markup=get_work_menu(),
  )


# Интерактив по работе (начисление денег)
@dp.message(
    F.text.in_(["🤝 Рефка", "🍔 Бизнес", "🧱 Блок", "🚕 Таксист", "👮 Федерал"])
)
async def choose_work_handler(message: Message):
  user = get_user(message.from_user.id)
  earned = 150 if message.text in ["🤝 Рефка", "🚕 Таксист"] else 300
  user["money"] += earned
  await message.answer(
      f"Ты отработал на позиции **{message.text}** и поднял **${earned}**! 💸\n"
      f"Текущий баланс: ${user['money']:,}",
      reply_markup=get_work_menu(),
  )


@dp.message(F.text == "🎰 Казино")
async def casino_handler(message: Message):
  await message.answer(
      "🎲 Добро пожаловать в кинцо «как остаться без трусов»!\nЗа какой стол сядете?",
      reply_markup=get_casino_menu(),
  )


@dp.message(F.text.in_(["🎲 Бросить кости ($100)", "🃏 Очко ($200)"]))
async def casino_game_handler(message: Message):
  user = get_user(message.from_user.id)
  cost = 100 if "100" in message.text else 200

  if user["money"] < cost:
    await message.answer(
        f"Эу, бро! У тебя недостаточно бабосов ($ {user['money']}). Иди работай!",
        reply_markup=get_casino_menu(),
    )
    return

  user["money"] -= cost
  # Простой рандом выигрыша
  import random

  win = random.choice([True, False])

  if win:
    prize = cost * 2
    user["money"] += prize
    await message.answer(
        f"🎲 Удача на твоей стороне! Ты сорвал куш и выиграл **${prize}**! 💰\n"
        f"Баланс: ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
  else:
    await message.answer(
        f"🎲 Не фартануло, бро. Ты проиграл ${cost}. Кинцо оказалось суровым...\n"
        f"Баланс: ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )


@dp.message(F.text == "🛒 Шмотки")
async def market_handler(message: Message):
  await message.answer(
      "🛍 **BB MARKET:**\nТут можно прикупить шмотки для поднятия авторитета и защиты.",
      reply_markup=get_market_menu(),
  )


@dp.message(F.text.in_(["👕 Шмотка VETEMENTS ($500)", "🛡 Прокачать защиту ($300)"]))
async def market_buy_handler(message: Message):
  user = get_user(message.from_user.id)
  is_vetements = "VETEMENTS" in message.text
  cost = 500 if is_vetements else 300

  if user["money"] < cost:
    await message.answer(
        f"Не хватает бабосов на этот прикид! У тебя ${user['money']}.",
        reply_markup=get_market_menu(),
    )
    return

  user["money"] -= cost
  if is_vetements:
    user["rank"] = "Авторитет в VETEMENTS 🧥"
    await message.answer(
        f"Ты купил **VETEMENTS** за ${cost}! Твой ранг повышен до: **{user['rank']}** 🔥\n"
        f"Баланс: ${user['money']:,}",
        reply_markup=get_market_menu(),
    )
  else:
    user["defense"] += 15
    await message.answer(
        f"Ты прокачал защиту на +15! Теперь твоя защита: **{user['defense']}** 🛡\n"
        f"Баланс: ${user['money']:,}",
        reply_markup=get_market_menu(),
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

  asyncio.create_task(start_web_server())

  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
