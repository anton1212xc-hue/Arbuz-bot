import asyncio
import logging
import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
)

# Токен вашего бота
TOKEN = "1780243447:z-EViDoEUiE61aHerKad4WazMWTsKC3OraH"
OWNER_ID = 123456789  # Укажите ваш ID для получения уведомлений о донатах

# Настройка кастомного сервера для ShuzaGram в aiogram 3.x
custom_server = TelegramAPIServer.from_base("https://api.shuzagram.com")
session = AiohttpSession(api=custom_server)

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher(storage=MemoryStorage())

# База данных пользователей в памяти
users_db = {}
# Словарь для временного хранения активных мини-игр игроков
active_games = {}


def get_user(user_id):
  if user_id not in users_db:
    users_db[user_id] = {
        "user_id": user_id,
        "money": 1000,
        "defense": 10,
        "rank": "Скуф / Обычный чел",
        "businesses": [],
    }
  return users_db[user_id]


# Бизнесы (доход ровно на ноль меньше цены)
BUSINESSES = {
    "shaurma": {"name": "🌭 Ларек с шаурмой", "cost": 5000, "income": 500},
    "carwash": {"name": "🚗 Автомойка", "cost": 25000, "income": 2500},
    "club": {"name": "💎 Ночной клуб", "cost": 100000, "income": 10000},
    "casino_biz": {
        "name": "🎰 Подпольное казино",
        "cost": 500000,
        "income": 50000,
    },
    "vip_cartel": {
        "name": "👑 Картель (За звезды)",
        "cost_stars": 250,
        "income": 500000,  # 500k в час!
    },
}

# --- КЛАВИАТУРЫ ---


def get_main_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🏆 Топ бандюков")],
          [KeyboardButton(text="💼 Работа"), KeyboardButton(text="🏢 Бизнесы")],
          [KeyboardButton(text="🎰 Казино"), KeyboardButton(text="🛒 Шмотки")],
      ],
      resize_keyboard=True,
  )


def get_work_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="🤝 Раскидать рефки"), KeyboardButton(text="🚕 Угон тачки")],
          [KeyboardButton(text="🧱 Стрелка за блок"), KeyboardButton(text="👮 Сходняк")],
          [KeyboardButton(text="⬅️ Назад")],
      ],
      resize_keyboard=True,
  )


# Клавиатура для мини-игр (выбор варианта)
def get_minigame_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="🔴 Красное"), KeyboardButton(text="⚫ Черное")],
          [KeyboardButton(text="❌ Слинять с темы")],
      ],
      resize_keyboard=True,
  )


def get_business_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="🌭 Шаурма ($5k)"), KeyboardButton(text="🚗 Автомойка ($25k)")],
          [KeyboardButton(text="💎 Клуб ($100k)"), KeyboardButton(text="🎰 Казино ($500k)")],
          [KeyboardButton(text="👑 Картель (250 ⭐)")],
          [KeyboardButton(text="💼 Мои бизнесы"), KeyboardButton(text="⬅️ Назад")],
      ],
      resize_keyboard=True,
  )


def get_casino_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [
              KeyboardButton(text="🎲 Бросить кости ($100)"),
              KeyboardButton(text="🃏 Очко ($200)"),
          ],
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
  get_user(message.from_user.id)
  user_name = message.from_user.first_name or "Бро"
  text = (
      f"Здорово, {user_name}! 🤙 Добро пожаловать в **бот бандит**.\n\n"
      "Здесь тебя ждет жесткая жизнь: проходи мини-игры на работах, поднимай"
      " бабосы, скупай бизнесы с пассивным доходом и залетай в топ!"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
  # Очищаем мини-игру если была активна
  active_games.pop(message.from_user.id, None)
  await message.answer("Главное меню, бро:", reply_markup=get_main_menu())


@dp.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
  user = get_user(message.from_user.id)
  biz_count = len(user["businesses"])
  text = (
      f"📊 **Твой профиль:**\n\n"
      f"💰 Бахчи (бабосы): ${user['money']:,}\n"
      f"🧢 Ранг: {user['rank']}\n"
      f"🛡 Защита: {user['defense']}\n"
      f"🏢 Куплено бизнесов: {biz_count}\n"
      f"⚖️ Статус: На свободе"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "🏆 Топ бандюков")
async def top_players_handler(message: Message):
  # Сортируем пользователей по балансу
  sorted_users = sorted(
      users_db.values(), key=lambda x: x["money"], reverse=True
  )
  text = "🏆 **Топ-10 авторитетов по бабосам:**\n\n"
  for i, u in enumerate(sorted_users[:10], 1):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
    text += f"{medals} ID {u['user_id']} — 💰 **${u['money']:,}**\n"
  await message.answer(text, reply_markup=get_main_menu())


# --- РАБОТА С МИНИ-ИГРАМИ ---


@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  await message.answer(
      "мяумс, выбери движ. На каждой работе надо сыграть в мини-игру, иначе"
      " без бабков останешься!",
      reply_markup=get_work_menu(),
  )


@dp.message(
    F.text.in_([
        "🤝 Раскидать рефки",
        "🚕 Угон тачки",
        "🧱 Стрелка за блок",
        "👮 Сходняк",
    ])
)
async def start_minigame(message: Message):
  # Запускаем мини-игру: игроку нужно угадать правильный исход (Красное или Черное)
  active_games[message.from_user.id] = message.text
  await message.answer(
      f"🎯 Ты двинулся на тему: **{message.text}**.\n"
      "Чтобы залутать бабки, устрой мазу: выбирай цвет наудачу (Красное или"
      " Черное). Ошибешься — пролетишь по полной!",
      reply_markup=get_minigame_menu(),
  )


@dp.message(F.text.in_(["🔴 Красное", "⚫ Черное"]))
async def process_minigame(message: Message):
  user_id = message.from_user.id
  if user_id not in active_games:
    await message.answer(
        "Сначала выбери работу в меню!", reply_markup=get_work_menu()
    )
    return

  job_name = active_games.pop(user_id)
  user = get_user(user_id)

  # Мини-игра: рандом угадывания
  winning_choice = random.choice(["🔴 Красное", "⚫ Черное"])
  user_choice = message.text

  rewards = {
      "🤝 Раскидать рефки": 200,
      "🚕 Угон тачки": 500,
      "🧱 Стрелка за блок": 900,
      "👮 Сходняк": 1500,
  }
  prize = rewards.get(job_name, 300)

  if user_choice == winning_choice:
    user["money"] += prize
    await message.answer(
        f"🎯 Четкий выбор! Выпало {winning_choice}.\n"
        f"Ты успешно справился с работой **{job_name}** и поднял **+${prize:,}**! 💸\n"
        f"Баланс: ${user['money']:,}",
        reply_markup=get_work_menu(),
    )
  else:
    await message.answer(
        f"💥 Не фартануло! Выпало {winning_choice}.\n"
        f"Тебя спалили/отшили на теме **{job_name}**. Ушел ни с чем!",
        reply_markup=get_work_menu(),
    )


@dp.message(F.text == "❌ Слинять с темы")
async def cancel_minigame(message: Message):
  active_games.pop(message.from_user.id, None)
  await message.answer(
      "Ты соскочил с движухи. Возвращаемся в меню:",
      reply_markup=get_work_menu(),
  )


# --- БИЗНЕСЫ ---


@dp.message(F.text == "🏢 Бизнесы")
async def business_menu_handler(message: Message):
  await message.answer(
      "🏢 **Биржа бизнесов:**\nПокупай предприятия. Доход каждого бизнеса равен"
      " его цене с урезанным нулем!\n👑 Картель за 250 Звезд приносит аж"
      " **500,000 в час**!",
      reply_markup=get_business_menu(),
  )


@dp.message(
    F.text.in_([
        "🌭 Шаурма ($5k)",
        "🚗 Автомойка ($25k)",
        "💎 Клуб ($100k)",
        "🎰 Казино ($500k)",
    ])
)
async def buy_business_in_cash(message: Message):
  user = get_user(message.from_user.id)
  mapping = {
      "🌭 Шаурма ($5k)": "shaurma",
      "🚗 Автомойка ($25k)": "carwash",
      "💎 Клуб ($100k)": "club",
      "🎰 Казино ($500k)": "casino_biz",
  }
  key = mapping.get(message.text)
  biz_info = BUSINESSES[key]

  if key in user["businesses"]:
    await message.answer(
        f"У тебя уже есть этот бизнес: **{biz_info['name']}**!",
        reply_markup=get_business_menu(),
    )
    return

  if user["money"] < biz_info["cost"]:
    await message.answer(
        f"Не хватает бабосов! Нужно ${biz_info['cost']:,}, а у тебя"
        f" ${user['money']:,}.",
        reply_markup=get_business_menu(),
    )
    return

  user["money"] -= biz_info["cost"]
  user["businesses"].append(key)
  await message.answer(
      f"🎉 Поздравляю! Ты купил **{biz_info['name']}** за"
      f" ${biz_info['cost']:,}!\nПрибыль: ${biz_info['income']:,}/час.\nБаланс:"
      f" ${user['money']:,}",
      reply_markup=get_business_menu(),
  )


@dp.message(F.text == "👑 Картель (250 ⭐)")
async def buy_cartel_stars(message: Message):
  user = get_user(message.from_user.id)
  if "vip_cartel" in user["businesses"]:
    await message.answer(
        "У тебя уже оформлен Картель!", reply_markup=get_business_menu()
    )
    return

  prices = [LabeledPrice(label="👑 Картель (500k/час)", amount=250)]
  await message.answer_invoice(
      title="Покупка Картеля",
      description=(
          "Элитный бизнес за звезды! Приносит 500,000 бабосов в час."
      ),
      payload="buy_vip_cartel",
      currency="XTR",
      prices=prices,
  )


@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
  await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
  user = get_user(message.from_user.id)
  if "vip_cartel" not in user["businesses"]:
    user["businesses"].append("vip_cartel")

  if OWNER_ID and message.from_user.id != OWNER_ID:
    try:
      await bot.send_message(
          OWNER_ID,
          f"👑 Внимание! Пользователь @{message.from_user.username or message.from_user.id}"
          " купил Картель за 250 Звезд!",
      )
    except Exception:
      pass

  await message.answer(
      "👑 Оплата прошла успешно! **Картель** твой, авторитет на максимуме, доход"
      " 500k/час пошел! 🔥",
      reply_markup=get_main_menu(),
  )


@dp.message(F.text == "💼 Мои бизнесы")
async def show_my_businesses(message: Message):
  user = get_user(message.from_user.id)
  if not user["businesses"]:
    await message.answer(
        "У тебя пока пусто. Пора замутить бизнес!",
        reply_markup=get_business_menu(),
    )
    return

  total_hourly_income = 0
  text = "🏢 **Твои владения:**\n\n"
  for key in user["businesses"]:
    b = BUSINESSES[key]
    total_hourly_income += b["income"]
    text += f"• {b['name']} — 💵 **${b['income']:,}/час**\n"

  text += f"\n📊 **Общий пассивный доход в час:** ${total_hourly_income:,}"
  await message.answer(text, reply_markup=get_business_menu())


# --- КАЗИНО И МАГАЗИН ---


@dp.message(F.text == "🎰 Казино")
async def casino_handler(message: Message):
  await message.answer(
      "🎲 Добро пожаловать в кинцо «как остаться без трусов»!\nЗа какой стол"
      " сядете?",
      reply_markup=get_casino_menu(),
  )


@dp.message(F.text.in_(["🎲 Бросить кости ($100)", "🃏 Очко ($200)"]))
async def casino_game_handler(message: Message):
  user = get_user(message.from_user.id)
  cost = 100 if "100" in message.text else 200

  if user["money"] < cost:
    await message.answer(
        f"Эу, бро! Не хватает бабосов (${user['money']:,}). Иди работай!",
        reply_markup=get_casino_menu(),
    )
    return

  user["money"] -= cost
  win = random.choice([True, False])

  if win:
    prize = cost * 2
    user["money"] += prize
    await message.answer(
        f"🎲 Удача на твоей стороне! Выиграл **${prize:,}**! 💰\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
  else:
    await message.answer(
        f"🎲 Не фартануло. Проиграл ${cost}.\nБаланс: ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )


@dp.message(F.text == "🛒 Шмотки")
async def market_handler(message: Message):
  await message.answer(
      "🛍 **BB MARKET:**\nТут можно прикупить шмотки для авторитета.",
      reply_markup=get_market_menu(),
  )


@dp.message(F.text.in_(["👕 Шмотка VETEMENTS ($500)", "🛡 Прокачать защиту ($300)"]))
async def market_buy_handler(message: Message):
  user = get_user(message.from_user.id)
  is_vetements = "VETEMENTS" in message.text
  cost = 500 if is_vetements else 300

  if user["money"] < cost:
    await message.answer(
        f"Не хватает бабосов! У тебя ${user['money']:,}.",
        reply_markup=get_market_menu(),
    )
    return

  user["money"] -= cost
  if is_vetements:
    user["rank"] = "Авторитет в VETEMENTS 🧥"
    await message.answer(
        f"Куплен **VETEMENTS**! Ранг: **{user['rank']}** 🔥\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_market_menu(),
    )
  else:
    user["defense"] += 15
    await message.answer(
        f"Защита прокачана! Теперь защита: **{user['defense']}** 🛡\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_market_menu(),
    )


@dp.message()
async def echo_handler(message: Message):
  await message.answer(
      "Чет непонятная малява. Пользуйся меню или пиши /start, бро.",
      reply_markup=get_main_menu(),
  )


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
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
