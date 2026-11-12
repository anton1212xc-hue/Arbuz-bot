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
OWNER_ID = 1780243435  # Укажите ваш Telegram ID
ADMIN_PASSWORD = "gver1212"  # Пароль для админ-панели (можешь изменить)

# Настройка кастомного сервера для ShuzaGram в aiogram 3.x
custom_server = TelegramAPIServer.from_base("https://api.shuzagram.com")
session = AiohttpSession(api=custom_server)

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher(storage=MemoryStorage())

# Базы данных
users_db = {}
active_games = {}  # {user_id: {"type": ..., "data": ...}}
admin_session = set()  # Список авторизованных админов


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


# Тематические клавиатуры для мини-игр на работах
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
          [KeyboardButton(text="➕ Накинуть $100,000"), KeyboardButton(text="🛡 Сделать макс. защиту")],
          [KeyboardButton(text="🚪 Выйти из админки")],
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
      "Здесь тебя ждет жесткая жизнь: уникальные мини-игры на работах,"
      " продвинутое казино с выбором ставок, бизнесы и авторитет!"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
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
  sorted_users = sorted(
      users_db.values(), key=lambda x: x["money"], reverse=True
  )
  text = "🏆 **Топ-10 авторитетов по бабосам:**\n\n"
  for i, u in enumerate(sorted_users[:10], 1):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
    text += f"{medals} ID {u['user_id']} — 💰 **${u['money']:,}**\n"
  await message.answer(text, reply_markup=get_main_menu())


# --- АДМИН-ПАНЕЛЬ ---


@dp.message(F.text.startswith("/admin"))
async def admin_login_command(message: Message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    await message.answer(
        "Введи пароль вместе с командой, например: `/admin твой_пароль`",
        parse_mode="Markdown",
    )
    return

  password = parts[1]
  if password == ADMIN_PASSWORD:
    admin_session.add(message.from_user.id)
    await message.answer(
        "🔓 Пароль принят! Добро пожаловать в админ-панель.",
        reply_markup=get_admin_menu(),
    )
  else:
    await message.answer("❌ Неверный пароль!")


@dp.message(F.text == "🚪 Выйти из админки")
async def admin_logout(message: Message):
  admin_session.discard(message.from_user.id)
  await message.answer(
      "Админ-режим отключен.", reply_markup=get_main_menu()
  )


@dp.message(F.text == "➕ Накинуть $100,000")
async def admin_add_money(message: Message):
  if message.from_user.id not in admin_session:
    return
  user = get_user(message.from_user.id)
  user["money"] += 100000
  await message.answer(
      f"💵 Админ-бонус зачислен! Баланс: ${user['money']:,}",
      reply_markup=get_admin_menu(),
  )


@dp.message(F.text == "🛡 Сделать макс. защиту")
async def admin_max_defense(message: Message):
  if message.from_user.id not in admin_session:
    return
  user = get_user(message.from_user.id)
  user["defense"] = 999
  user["rank"] = "Бессмертный Босс 👑"
  await message.answer(
      "🛡 Защита выкручена на максимум (999)! Ранг изменен.",
      reply_markup=get_admin_menu(),
  )


# --- ТЕМАТИЧЕСКИЕ МИНИ-ИГРЫ НА РАБОТАХ ---


@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  await message.answer(
      "мяумс, выбери тему. В каждой работе своя уникальная мини-игра, где можно"
      " подняться или остаться ни с чем:",
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


# Обработка выборов в мини-играх
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
  if user_id not in active_games:
    await message.answer(
        "Сначала выбери работу в меню!", reply_markup=get_work_menu()
    )
    return

  game_data = active_games.pop(user_id)
  job_type = game_data["job"]
  user = get_user(user_id)
  choice = message.text

  # Логика для каждой работы: только 1 вариант из 3 приносит победу
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
    await message.answer(
        f"🎯 Четкий расчет! Твой выбор ({choice}) оказался верным.\n"
        f"Ты успешно справился с темой и поднял **+${prize:,}**! 💸\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_work_menu(),
    )
  else:
    await message.answer(
        f"💥 Мимо! Выбор ({choice}) прогорел. Менты / конкуренты тебя приняли,"
        f" ушел ни с чем.",
        reply_markup=get_work_menu(),
    )


# --- ПРОДВИНУТОЕ КАЗИНО (ВЫБОР СТАВКИ И ИГРЫ) ---


@dp.message(F.text == "🎰 Казино")
async def casino_handler(message: Message):
  await message.answer(
      "🎲 Добро пожаловать в кинцо «как остаться без трусов»!\nВыбирай игру:",
      reply_markup=get_casino_menu(),
  )


@dp.message(F.text.in_(["🎲 Сыграть в кости", "🃏 Сыграть в очко"]))
async def casino_select_game(message: Message):
  g_type = "dice" if "кости" in message.text else "cards"
  active_games[message.from_user.id] = {"casino": g_type}
  await message.answer(
      "💰 Напиши сумму, которую хочешь поставить (например: `500` или `5000`),"
      " или нажми «Назад»:",
      parse_mode="Markdown",
      reply_markup=ReplyKeyboardMarkup(
          keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True
      ),
  )


# Обработка ставки в казино в текстовом виде
@dp.message(
    F.text.regexp(r"^\d+$").filter(lambda msg: msg.from_user.id in active_games)
)
async def casino_process_bet(message: Message):
  user_id = message.from_user.id
  bet_amount = int(message.text)
  user = get_user(user_id)

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

  game_info = active_games.pop(user_id)
  user["money"] -= bet_amount

  # Рандом исхода казино (шанс 50 на 50)
  win = random.choice([True, False])

  if win:
    payout = bet_amount * 2
    user["money"] += payout
    await message.answer(
        f"🎲 Удача на твоей стороне! Ты поднял куш **+${payout:,}**! 💰\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
  else:
    await message.answer(
        f"🎲 Не фартануло. Ставка ${bet_amount:,} сгорела в казино...\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )


# --- БИЗНЕСЫ ---


@dp.message(F.text == "🏢 Бизнесы")
async def business_menu_handler(message: Message):
  await message.answer(
      "🏢 **Биржа бизнесов:**\nДоход каждого бизнеса равен его цене с урезанным"
      " нулем!\n👑 Картель за 250 Звезд приносит **500,000 в час**!",
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
      f"🎉 Куплен **{biz_info['name']}** за ${biz_info['cost']:,}!\nПрибыль:"
      f" ${biz_info['income']:,}/час.\nБаланс: ${user['money']:,}",
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
      "👑 Оплата прошла успешно! **Картель** твой, доход 500k/час активирован! 🔥",
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

  total_income = 0
  text = "🏢 **Твои владения:**\n\n"
  for key in user["businesses"]:
    b = BUSINESSES[key]
    total_income += b["income"]
    text += f"• {b['name']} — 💵 **${b['income']:,}/час**\n"

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
