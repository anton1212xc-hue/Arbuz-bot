import asyncio
import json
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
OWNER_ID = 1780243435  # Твой личный ID
ADMIN_PASSWORD = "gver1212"  # Пароль для админ-панели

# Настройка кастомного сервера для ShuzaGram в aiogram 3.x
custom_server = TelegramAPIServer.from_base("https://api.shuzagram.com")
session = AiohttpSession(api=custom_server)

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher(storage=MemoryStorage())

# Файл для постоянного сохранения данных
DB_FILE = "database.json"

users_db = {}  # {user_id (int): user_data}
username_to_id = {}  # Для поиска по @username
active_games = {}  # {user_id: {...}}
admin_session = set()  # Список авторизованных админов


# --- ФУНКЦИИ СОХРАНЕНИЯ И ЗАГРУЗКИ ---
def load_database():
  global users_db, username_to_id
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # JSON сохраняет ключи словарей как строки, конвертируем user_id обратно в int
        users_db = {int(k): v for k, v in data.items()}
        # Восстанавливаем словарь юзернеймов
        for u_id, u_data in users_db.items():
          if "username" in u_data and u_data["username"]:
            username_to_id[u_data["username"].lower()] = u_id
      print(f"База данных успешно загружена. Игроков: {len(users_db)}")
    except Exception as e:
      print(f"Ошибка загрузки базы данных: {e}")
      users_db = {}


def save_database():
  try:
    with open(DB_FILE, "w", encoding="utf-8") as f:
      # json требует строковые ключи, у нас user_id и так преобразуется
      json.dump(users_db, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Ошибка сохранения базы данных: {e}")


def get_user(user_id, username=None):
  if user_id not in users_db:
    users_db[user_id] = {
        "user_id": user_id,
        "username": username.lower() if username else str(user_id),
        "money": 1000,
        "defense": 10,
        "rank": "Скуф / Обычный чел",
        "businesses": [],
    }
  if username:
    users_db[user_id]["username"] = username.lower()
    username_to_id[username.lower()] = user_id

  save_database()  # Автосохранение при получении/создании пользователя
  return users_db[user_id]


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
        "income": 500000,
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


def get_ref_keyboard():
  return ReplyKeyboardMarkup(
      keyboard=[
          [
              KeyboardButton(text="💬 Спам в ЛС"),
              KeyboardButton(text="📢 Пост в чате"),
              KeyboardButton(text="🚪 Зайти в комменты"),
          ],
          [KeyboardButton(text="❌ Слинять")],
      ],
      resize_keyboard=True,
  )


def get_car_keyboard():
  return ReplyKeyboardMarkup(
      keyboard=[
          [
              KeyboardButton(text="🔴 Красный провод"),
              KeyboardButton(text="🔵 Синий провод"),
              KeyboardButton(text="🟢 Зеленый провод"),
          ],
          [KeyboardButton(text="❌ Слинять")],
      ],
      resize_keyboard=True,
  )


def get_block_keyboard():
  return ReplyKeyboardMarkup(
      keyboard=[
          [
              KeyboardButton(text="🛡 Сесть за укрытие"),
              KeyboardButton(text="💥 Идти в лобовую"),
              KeyboardButton(text="🏃 Обойти с фланга"),
          ],
          [KeyboardButton(text="❌ Слинять")],
      ],
      resize_keyboard=True,
  )


def get_fed_keyboard():
  return ReplyKeyboardMarkup(
      keyboard=[
          [
              KeyboardButton(text="💼 Дать на лапу"),
              KeyboardButton(text="🗣 Качать права"),
              KeyboardButton(text="🤝 Порешать по понятиям"),
          ],
          [KeyboardButton(text="❌ Слинять")],
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
              KeyboardButton(text="🎲 Сыграть в кости"),
              KeyboardButton(text="🃏 Сыграть в очко"),
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


def get_admin_menu():
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="💸 Выдать бабло"), KeyboardButton(text="🏢 Выдать бизнес")],
          [KeyboardButton(text="🚪 Выйти из админки")],
      ],
      resize_keyboard=True,
  )


# --- ОБРАБОТЧИКИ ---


@dp.message(F.text == "/start")
async def cmd_start(message: Message):
  get_user(message.from_user.id, message.from_user.username)
  user_name = message.from_user.first_name or "Бро"
  text = (
      f"Здорово, {user_name}! 🤙 Добро пожаловать в **бот бандит**.\n\n"
      "Скупай сколько угодно одинаковых бизнесов, крути мини-игры и залетай в топ!"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
  active_games.pop(message.from_user.id, None)
  await message.answer("Главное меню, бро:", reply_markup=get_main_menu())


@dp.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
  user = get_user(message.from_user.id, message.from_user.username)
  biz_count = len(user["businesses"])
  text = (
      f"📊 **Твой профиль:**\n\n"
      f"💰 Бахчи (бабосы): ${user['money']:,}\n"
      f"🧢 Ранг: {user['rank']}\n"
      f"🛡 Защита: {user['defense']}\n"
      f"🏢 Всего бизнесов: {biz_count}\n"
      f"⚖️ Статус: На свободе"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "🏆 Топ бандюков")
async def top_players_handler(message: Message):
  sorted_users = sorted(
      users_db.values(), key=lambda x: x["money"], reverse=True
  )
  text = "🏆 **Топ-10 авторитетов по бабосам:**\n\n"
  for i, u in enumerate(sorted_users[:10], 1):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
    identifier = f"@{u['username']}" if u["username"] else f"ID {u['user_id']}"
    text += f"{medals} {identifier} — 💰 **${u['money']:,}**\n"
  await message.answer(text, reply_markup=get_main_menu())


# --- АДМИН-ПАНЕЛЬ ---


@dp.message(F.text.startswith("/admin"))
async def admin_login_command(message: Message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    await message.answer(
        "Введи пароль вместе с командой, например: `/admin gver1212`",
        parse_mode="Markdown",
    )
    return

  password = parts[1]
  if password == ADMIN_PASSWORD:
    admin_session.add(message.from_user.id)
    await message.answer(
        "🔓 Админ-панель активна!", reply_markup=get_admin_menu()
    )
  else:
    await message.answer("❌ Неверный пароль!")


@dp.message(F.text == "🚪 Выйти из админки")
async def admin_logout(message: Message):
  admin_session.discard(message.from_user.id)
  await message.answer(
      "Админ-режим отключен.", reply_markup=get_main_menu()
  )


@dp.message(F.text == "💸 Выдать бабло")
async def admin_prompt_money(message: Message):
  if message.from_user.id not in admin_session:
    return
  active_games[message.from_user.id] = {"admin_action": "give_money"}
  await message.answer(
      "Введите данные в формате:\n`@username сумма` (или `ID сумма`)\nПример:"
      " `@nikiteeess 500000`",
      parse_mode="Markdown",
  )


@dp.message(F.text == "🏢 Выдать бизнес")
async def admin_prompt_business(message: Message):
  if message.from_user.id not in admin_session:
    return
  active_games[message.from_user.id] = {"admin_action": "give_biz"}
  await message.answer(
      "Введите данные в формате:\n`@username ключ_бизнеса`\n\nДоступные ключи"
      " бизнесов:\n• `shaurma`\n• `carwash`\n• `club`\n• `casino_biz`\n•"
      " `vip_cartel`\nПример: `@nikiteeess vip_cartel`",
      parse_mode="Markdown",
  )


@dp.message(
    lambda msg: msg.from_user.id in admin_session
    and msg.from_user.id in active_games
    and "admin_action" in active_games[msg.from_user.id]
)
async def admin_process_action(message: Message):
  user_id = message.from_user.id
  action_data = active_games.pop(user_id)
  action = action_data["admin_action"]

  parts = message.text.strip().split()
  if len(parts) < 2:
    await message.answer(
        "Ошибка формата! Попробуйте снова через кнопки админки."
    )
    return

  target_raw = parts[0].lstrip("@").lower()
  arg = parts[1]

  target_user = None
  if target_raw.isdigit():
    t_id = int(target_raw)
    if t_id in users_db:
      target_user = users_db[t_id]
  else:
    if target_raw in username_to_id:
      target_user = users_db[username_to_id[target_raw]]

  if not target_user:
    await message.answer(
        f"❌ Пользователь `{target_raw}` не найден в базе данных (он должен"
        " хотя бы раз нажать /start в боте).",
        parse_mode="Markdown",
    )
    return

  if action == "give_money":
    if not arg.isdigit():
      await message.answer("❌ Сумма должна быть числом!")
      return
    amount = int(arg)
    target_user["money"] += amount
    save_database()
    await message.answer(
        f"✅ Успешно! Игроку @{target_user['username']} выдано ${amount:,}."
        f" Новый баланс: ${target_user['money']:,}",
        reply_markup=get_admin_menu(),
    )

  elif action == "give_biz":
    if arg not in BUSINESSES:
      await message.answer(
          "❌ Неверный ключ бизнеса! Используйте: shaurma, carwash, club,"
          " casino_biz, vip_cartel"
      )
      return
    target_user["businesses"].append(arg)
    save_database()
    biz_name = BUSINESSES[arg]["name"]
    await message.answer(
        f"✅ Успешно! Игроку @{target_user['username']} выдан бизнес: {biz_name}.",
        reply_markup=get_admin_menu(),
    )


# --- ТЕМАТИЧЕСКИЕ МИНИ-ИГРЫ НА РАБОТАХ ---


@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  await message.answer(
      "мяумс, выбери тему. В каждой работе своя уникальная мини-игра:",
      reply_markup=get_work_menu(),
  )


@dp.message(F.text == "🤝 Раскидать рефки")
async def work_ref_start(message: Message):
  active_games[message.from_user.id] = {"job": "ref"}
  await message.answer(
      "📱 Ты засел за спам. Куда закинешь пацанам ссылку?",
      reply_markup=get_ref_keyboard(),
  )


@dp.message(F.text == "🚕 Угон тачки")
async def work_car_start(message: Message):
  active_games[message.from_user.id] = {"job": "car"}
  await message.answer(
      "🚗 Взломал тачку под окнами. Какой провод дергать?",
      reply_markup=get_car_keyboard(),
  )


@dp.message(F.text == "🧱 Стрелка за блок")
async def work_block_start(message: Message):
  active_games[message.from_user.id] = {"job": "block"}
  await message.answer(
      "🧱 На районе замес. Какую тактику выберешь?",
      reply_markup=get_block_keyboard(),
  )


@dp.message(F.text == "👮 Сходняк")
async def work_fed_start(message: Message):
  active_games[message.from_user.id] = {"job": "fed"}
  await message.answer(
      "👮 Серьезный базар с авторитетами. Как поведешь себя?",
      reply_markup=get_fed_keyboard(),
  )


@dp.message(F.text == "❌ Слинять")
async def cancel_job(message: Message):
  active_games.pop(message.from_user.id, None)
  await message.answer("Соскочил с темы.", reply_markup=get_work_menu())


@dp.message(
    F.text.in_([
        "💬 Спам в ЛС",
        "📢 Пост в чате",
        "🚪 Зайти в комменты",
        "🔴 Красный провод",
        "🔵 Синий провод",
        "🟢 Зеленый провод",
        "🛡 Сесть за укрытие",
        "💥 Идти в лобовую",
        "🏃 Обойти с фланга",
        "💼 Дать на лапу",
        "🗣 Качать права",
        "🤝 Порешать по понятиям",
    ])
)
async def process_job_choice(message: Message):
  user_id = message.from_user.id
  if user_id not in active_games or "job" not in active_games[user_id]:
    await message.answer(
        "Сначала выбери работу в меню!", reply_markup=get_work_menu()
    )
    return

  game_data = active_games.pop(user_id)
  job_type = game_data["job"]
  user = get_user(user_id, message.from_user.username)
  choice = message.text

  win = False
  prize = 0

  if job_type == "ref":
    winning_choice = "📢 Пост в чате"
    prize = 250
    win = choice == winning_choice
  elif job_type == "car":
    winning_choice = "🔵 Синий провод"
    prize = 600
    win = choice == winning_choice
  elif job_type == "block":
    winning_choice = "🏃 Обойти с фланга"
    prize = 1000
    win = choice == winning_choice
  elif job_type == "fed":
    winning_choice = "🤝 Порешать по понятиям"
    prize = 1800
    win = choice == winning_choice

  if win:
    user["money"] += prize
    save_database()
    await message.answer(
        f"🎯 Четкий расчет! Выбор ({choice}) верный.\nУспех! Получено:"
        f" **+${prize:,}**! 💸\nБаланс: ${user['money']:,}",
        reply_markup=get_work_menu(),
    )
  else:
    await message.answer(
        f"💥 Мимо! Выбор ({choice}) прогорел. Ушел ни с чем.",
        reply_markup=get_work_menu(),
    )


# --- КАЗИНО ---


@dp.message(F.text == "🎰 Казино")
async def casino_handler(message: Message):
  await message.answer(
      "🎲 Добро пожаловать в казино! Выбирай игру:",
      reply_markup=get_casino_menu(),
  )


@dp.message(F.text.in_(["🎲 Сыграть в кости", "🃏 Сыграть в очко"]))
async def casino_select_game(message: Message):
  g_type = "dice" if "кости" in message.text else "cards"
  active_games[message.from_user.id] = {"casino": g_type}
  await message.answer(
      "💰 Напиши сумму ставки числом (например: `500`):",
      parse_mode="Markdown",
      reply_markup=ReplyKeyboardMarkup(
          keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True
      ),
  )


@dp.message(
    F.text.regexp(r"^\d+$").filter(
        lambda msg: msg.from_user.id in active_games
        and "casino" in active_games[msg.from_user.id]
    )
)
async def casino_process_bet(message: Message):
  user_id = message.from_user.id
  bet_amount = int(message.text)
  user = get_user(user_id, message.from_user.username)

  if bet_amount <= 0:
    await message.answer("Ставка должна быть больше нуля, бро.")
    return

  if user["money"] < bet_amount:
    await message.answer(
        f"Эу! У тебя нет столько бабла. Твой баланс: ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
    active_games.pop(user_id, None)
    return

  active_games.pop(user_id, None)
  user["money"] -= bet_amount

  win = random.choice([True, False])
  if win:
    payout = bet_amount * 2
    user["money"] += payout
    await message.answer(
        f"🎲 Удача на твоей стороне! Выиграл **+${payout:,}**! 💰\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
  else:
    await message.answer(
        f"🎲 Не фартануло. Ставка ${bet_amount:,} сгорела...\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
  save_database()


# --- ПОКУПКА БИЗНЕСОВ ---


@dp.message(F.text == "🏢 Бизнесы")
async def business_menu_handler(message: Message):
  await message.answer(
      "🏢 **Биржа бизнесов:**\nТы можешь покупать **несколько одинаковых"
      " бизнесов**! Каждый новый приносит пассивный доход.",
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
  user = get_user(message.from_user.id, message.from_user.username)
  mapping = {
      "🌭 Шаурма ($5k)": "shaurma",
      "🚗 Автомойка ($25k)": "carwash",
      "💎 Клуб ($100k)": "club",
      "🎰 Казино ($500k)": "casino_biz",
  }
  key = mapping.get(message.text)
  biz_info = BUSINESSES[key]

  if user["money"] < biz_info["cost"]:
    await message.answer(
        f"Не хватает бабосов! Нужно ${biz_info['cost']:,}, а у тебя"
        f" ${user['money']:,}.",
        reply_markup=get_business_menu(),
    )
    return

  user["money"] -= biz_info["cost"]
  user["businesses"].append(key)
  save_database()
  await message.answer(
      f"🎉 Ты успешно докупил **{biz_info['name']}**!\nПрибыль:"
      f" ${biz_info['income']:,}/час.\nБаланс: ${user['money']:,}",
      reply_markup=get_business_menu(),
  )


@dp.message(F.text == "👑 Картель (250 ⭐)")
async def buy_cartel_stars(message: Message):
  prices = [LabeledPrice(label="👑 Картель (500k/час)", amount=250)]
  await message.answer_invoice(
      title="Покупка Картеля",
      description="Элитный бизнес за звезды! Приносит 500,000 в час.",
      payload="buy_vip_cartel",
      currency="XTR",
      prices=prices,
  )


@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
  await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
  user = get_user(message.from_user.id, message.from_user.username)
  user["businesses"].append("vip_cartel")
  save_database()

  if OWNER_ID and message.from_user.id != OWNER_ID:
    try:
      await bot.send_message(
          OWNER_ID,
          f"👑 Внимание! @{message.from_user.username or message.from_user.id}"
          " купил Картель за 250 Звезд!",
      )
    except Exception:
      pass

  await message.answer(
      "👑 Оплата прошла успешно! Еще один **Картель** добавлен в твою"
      " империю! 🔥",
      reply_markup=get_main_menu(),
  )


@dp.message(F.text == "💼 Мои бизнесы")
async def show_my_businesses(message: Message):
  user = get_user(message.from_user.id, message.from_user.username)
  if not user["businesses"]:
    await message.answer(
        "У тебя пока пусто. Пора замутить бизнес!",
        reply_markup=get_business_menu(),
    )
    return

  from collections import Counter

  counts = Counter(user["businesses"])

  total_income = 0
  text = "🏢 **Твои владения:**\n\n"
  for key, count in counts.items():
    b = BUSINESSES[key]
    inc = b["income"] * count
    total_income += inc
    text += f"• {b['name']} (x{count}) — 💵 **${inc:,}/час**\n"

  text += f"\n📊 **Общий пассивный доход в час:** ${total_income:,}"
  await message.answer(text, reply_markup=get_business_menu())


# --- МАГАЗИН ШМОТОК ---


@dp.message(F.text == "🛒 Шмотки")
async def market_handler(message: Message):
  await message.answer(
      "🛍 **BB MARKET:**\nТут можно прикупить шмотки для авторитета.",
      reply_markup=get_market_menu(),
  )


@dp.message(F.text.in_(["👕 Шмотка VETEMENTS ($500)", "🛡 Прокачать защиту ($300)"]))
async def market_buy_handler(message: Message):
  user = get_user(message.from_user.id, message.from_user.username)
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
  save_database()


@dp.message()
async def echo_handler(message: Message):
  await message.answer(
      "Чет непонятная малява. Пользуйся меню или пиши /start, бро.",
      reply_markup=get_main_menu(),
  )


# --- ВЕБ-СЕРВЕР И САМОПИНГ ДЛЯ RENDER ---
async def handle(request):
  return web.Response(text="Бот Бандит на связи и работает!")


async def keep_alive():
  render_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:10000")
  while True:
    await asyncio.sleep(300)
    try:
      import aiohttp

      async with aiohttp.ClientSession() as session:
        async with session.get(render_url) as resp:
          print(f"Пинг сервера для поддержания активности: статус {resp.status}")
    except Exception as e:
      print(f"Ошибка пинга: {e}")


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

  # Загружаем сохраненную базу данных при старте
  load_database()

  # Запускаем веб-сервер и фоновый самопинг
  asyncio.create_task(start_web_server())
  asyncio.create_task(keep_alive())

  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
