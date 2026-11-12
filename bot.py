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
# Укажите ваш Telegram user_id (числом), чтобы получать уведомления или админские права, если нужно
OWNER_ID = 1780243435  # Замените при желании на свой ID

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


def get_user(user_id):
  if user_id not in users_db:
    users_db[user_id] = {
        "money": 1000,
        "defense": 10,
        "rank": "Скуф / Обычный чел",
        "job": None,
        "businesses": [],  # список купленных бизнесов
    }
  return users_db[user_id]


# Доступные бизнесы
BUSINESSES = {
    "shaurma": {"name": "🌭 Ларек с шаурмой", "cost": 5000, "income": 50},
    "carwash": {"name": "🚗 Автомойка", "cost": 25000, "income": 250},
    "club": {"name": "💎 Ночной клуб", "cost": 100000, "income": 1200},
    "casino_biz": {
        "name": "🎰 Подпольное казино",
        "cost": 500000,
        "income": 7000,
    },
    "vip_cartel": {
        "name": "👑 Картель (За звезды)",
        "cost_stars": 250,
        "income": 35000,
    },
}

# --- КЛАВИАТУРЫ ---


def get_main_menu():
  return ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
        [KeyboardButton(text="🏢 Бизнесы"), KeyboardButton(text="🎰 Казино")],
        [KeyboardButton(text="🛒 Шмотки")],
    ],
    resize_keyboard=True,
  )


def get_work_menu():
  return ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤝 Рефка (Клик)"), KeyboardButton(text="🚕 Угон тачки")],
        [KeyboardButton(text="🧱 Стрелка за блок"), KeyboardButton(text="👮 Сходняк")],
        [KeyboardButton(text="⬅️ Назад")],
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


# --- ОБРАБОТЧИКИ КОМАНД И МЕНЮ ---


@dp.message(F.text == "/start")
async def cmd_start(message: Message):
  get_user(message.from_user.id)
  user_name = message.from_user.first_name or "Бро"
  text = (
      f"Здорово, {user_name}! 🤙 Добро пожаловать в **бот бандит**.\n\n"
      "Это симулятор реальной жизни: поднимай бабосы, устраивай мини-игры на"
      " работах, покупай бизнесы с пассивным доходом и стань авторитетом!\n\n"
      "Жми на кнопки ниже, чтобы начать движ:"
  )
  await message.answer(text, reply_markup=get_main_menu())


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
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


# --- РАБОТА И МИНИ-ИГРЫ ---


@dp.message(F.text == "💼 Работа")
async def work_handler(message: Message):
  await message.answer(
      "мяумс, выбери движ для заработка. Прояви себя в мини-игре:",
      reply_markup=get_work_menu(),
  )


@dp.message(F.text == "🤝 Рефка (Клик)")
async def work_ref(message: Message):
  user = get_user(message.from_user.id)
  earned = 150
  user["money"] += earned
  await message.answer(
      f"🤝 Ты раскидал рефки по пацанам и поднял **${earned}**! 💸\nБаланс:"
      f" ${user['money']:,}",
      reply_markup=get_work_menu(),
  )


@dp.message(F.text == "🚕 Угон тачки")
async def work_car(message: Message):
  user = get_user(message.from_user.id)
  # Мини-игра: шанс удачного угона 60%
  success = random.random() < 0.6
  if success:
    earned = 400
    user["money"] += earned
    await message.answer(
        f"🚗 Четкий угон! Тачка ушла на запчасти, ты поднял **${earned}**! 🔥\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_work_menu(),
    )
  else:
    await message.answer(
        "🚨 Ментяры спалили на месте! Убежал без бабла, повезло, что хоть"
        " ноги целы.",
        reply_markup=get_work_menu(),
    )


@dp.message(F.text == "🧱 Стрелка за блок")
async def work_block(message: Message):
  user = get_user(message.from_user.id)
  # Мини-игра: драка стенка на стенку
  win = random.choice([True, False])
  if win:
    earned = 750
    user["money"] += earned
    await message.answer(
        f"🧱 Наша взяла в перестрелке за район! Забрали кассу: **${earned}**! 💰\nБаланс:"
        f" ${user['money']:,}",
        reply_markup=get_work_menu(),
    )
  else:
    user["defense"] = max(0, user["defense"] - 2)
    await message.answer(
        "💥 Ох и отмудохали тебя на блоке... Потерял немного защиты (-2 щита)."
        f" Текущая защита: {user['defense']}",
        reply_markup=get_work_menu(),
    )


@dp.message(F.text == "👮 Сходняк")
async def work_fed(message: Message):
  user = get_user(message.from_user.id)
  # Мини-игра
  earned = random.randint(500, 1200)
  user["money"] += earned
  await message.answer(
      f"👮 Удалось порешать вопросы на сходняке с авторитетами. Получено:"
      f" **${earned}**! 💼\nБаланс: ${user['money']:,}",
      reply_markup=get_work_menu(),
  )


# --- ПОКУПКА БИЗНЕСОВ ---


@dp.message(F.text == "🏢 Бизнесы")
async def business_menu_handler(message: Message):
  await message.answer(
      "🏢 **Биржа бизнесов:**\nПокупай предприятия, получай статус и пассивный"
      " доход. Самый крутой Картель оформляется за Звезды (Stars)!",
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

  # Сопоставляем текст с ключом в словаре
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
        f"У тебя уже куплен этот бизнес: **{biz_info['name']}**!",
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
      f"🎉 Поздравляю! Ты успешно приобрел **{biz_info['name']}** за"
      f" ${biz_info['cost']:,}!\nОн будет приносить стабильный доход в час."
      f" Баланс: ${user['money']:,}",
      reply_markup=get_business_menu(),
  )


# Покупка элитного бизнеса за Звезды (Telegram Stars)
@dp.message(F.text == "👑 Картель (250 ⭐)")
async def buy_cartel_stars(message: Message):
  user = get_user(message.from_user.id)
  if "vip_cartel" in user["businesses"]:
    await message.answer(
        "У тебя уже куплен самый дорогой бизнес — Картель!",
        reply_markup=get_business_menu(),
    )
    return

  # Создаем инвойс на оплату Telegram Stars (внутренняя валюта XTR)
  prices = [LabeledPrice(label="👑 Картель (Элитный бизнес)", amount=250)]
  await message.answer_invoice(
      title="Покупка Картеля",
      description=(
          "Самый мощный бизнес в игре! Приносит максимальный доход и"
          " авторитет."
      ),
      payload="buy_vip_cartel",
      currency="XTR",  # Код для Telegram Stars
      prices=prices,
  )


# Подтверждение предварительного чека для Звезд
@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
  await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


# Успешная оплата звездами (Деньги/Звезды уходят боту/владельцу)
@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
  user = get_user(message.from_user.id)
  if "vip_cartel" not in user["businesses"]:
    user["businesses"].append("vip_cartel")

  # Если настроен OWNER_ID, можно переслать уведомление властелину бота
  if OWNER_ID and message.from_user.id != OWNER_ID:
    try:
      await bot.send_message(
          OWNER_ID,
          f"💰 Внимание! Пользователь @{message.from_user.username or message.from_user.id}"
          " купил Картель за 250 Звезд!",
      )
    except Exception:
      pass

  await message.answer(
      "👑 Оплата прошла успешно! **Картель** теперь твой! Никто на районе не"
      " посмеет тебе перечить, а доход максимальный! 🔥",
      reply_markup=get_main_menu(),
  )


@dp.message(F.text == "💼 Мои бизнесы")
async def show_my_businesses(message: Message):
  user = get_user(message.from_user.id)
  if not user["businesses"]:
    await message.answer(
        "У тебя пока нет ни одного бизнеса. Пора замутить что-то серьезное!",
        reply_markup=get_business_menu(),
    )
    return

  total_hourly_income = 0
  text = "🏢 **Твои владения и пассивный доход:**\n\n"
  for key in user["businesses"]:
    b = BUSINESSES[key]
    total_hourly_income += b["income"]
    text += f"• {b['name']} — приносит 💵 **${b['income']:,}/час**\n"

  text += f"\n📊 **Общий доход в час:** ${total_hourly_income:,}"
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
        f"Эу, бро! У тебя недостаточно бабосов (${user['money']:,}). Иди работай!",
        reply_markup=get_casino_menu(),
    )
    return

  user["money"] -= cost
  win = random.choice([True, False])

  if win:
    prize = cost * 2
    user["money"] += prize
    await message.answer(
        f"🎲 Удача на твоей стороне! Ты сорвал куш и выиграл **${prize:,}**!"
        f" 💰\nБаланс: ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )
  else:
    await message.answer(
        f"🎲 Не фартануло, бро. Ты проиграл ${cost}. Кинцо оказалось"
        f" суровым...\nБаланс: ${user['money']:,}",
        reply_markup=get_casino_menu(),
    )


@dp.message(F.text == "🛒 Шмотки")
async def market_handler(message: Message):
  await message.answer(
      "🛍 **BB MARKET:**\nТут можно прикупить шмотки для поднятия авторитета и"
      " защиты.",
      reply_markup=get_market_menu(),
  )


@dp.message(F.text.in_(["👕 Шмотка VETEMENTS ($500)", "🛡 Прокачать защиту ($300)"]))
async def market_buy_handler(message: Message):
  user = get_user(message.from_user.id)
  is_vetements = "VETEMENTS" in message.text
  cost = 500 if is_vetements else 300

  if user["money"] < cost:
    await message.answer(
        f"Не хватает бабосов на этот прикид! У тебя ${user['money']:,}.",
        reply_markup=get_market_menu(),
    )
    return

  user["money"] -= cost
  if is_vetements:
    user["rank"] = "Авторитет в VETEMENTS 🧥"
    await message.answer(
        f"Ты купил **VETEMENTS** за ${cost}! Твой ранг повышен до:"
        f" **{user['rank']}** 🔥\nБаланс: ${user['money']:,}",
        reply_markup=get_market_menu(),
    )
  else:
    user["defense"] += 15
    await message.answer(
        f"Ты прокачал защиту на +15! Теперь твоя защита: **{user['defense']}**"
        f" 🛡\nБаланс: ${user['money']:,}",
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
