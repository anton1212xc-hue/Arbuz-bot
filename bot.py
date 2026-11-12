import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

# Токен из вашего скриншота
TOKEN = "1780243444:GNVsB25ytITDJMWilP1y64AZ0EdNSp4Rh-j"

# Кастомный базовый URL для ShuzaGram API (согласно их документации)
# Обратите внимание: TelegramAPIServer сам подставит нужные методы (/bot<token>/<method>)
SHUZAGRAM_SERVER_BASE = "https://api.shuzagram.com"

router = Router()


# 1. Команда /start с инлайн-кнопкой каталога
@router.message(F.text == "/start")
async def cmd_start(message: Message):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🛍 Открыть каталог NFT", callback_data="open_catalog"
              )
          ]
      ]
  )
  await message.answer(
      "Привет! Добро пожаловать на маркетплейс NFT за Telegram Stars ✨.\n"
      "Нажми кнопку ниже, чтобы посмотреть доступные товары:",
      reply_markup=keyboard,
  )


# 2. Обработка нажатия на инлайн-кнопку «Каталог»
@router.callback_query(F.data == "open_catalog")
async def show_catalog(callback: CallbackQuery):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="💎 Купить за 50 Stars", callback_data="buy_nft_1"
              )
          ],
          [
              InlineKeyboardButton(
                  text="« Назад", callback_data="back_to_main"
              )
          ],
      ]
  )

  await callback.message.edit_text(
      "🎨 **NFT #001: Cyber Punk Cat**\n"
      "Редкий цифровой арт в сети.\n"
      "Цена: 50 Звёзд ⭐",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# Возврат в главное меню
@router.callback_query(F.data == "back_to_main")
async def back_main(callback: CallbackQuery):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🛍 Открыть каталог NFT", callback_data="open_catalog"
              )
          ]
      ]
  )
  await callback.message.edit_text(
      "Главное меню маркетплейса. Выберите действие:", reply_markup=keyboard
  )
  await callback.answer()


# 3. Инициирование покупки NFT за Звёзды
@router.callback_query(F.data == "buy_nft_1")
async def buy_nft(callback: CallbackQuery):
  prices = [LabeledPrice(label="NFT #001", amount=50)]

  await callback.message.answer_invoice(
      title="Покупка NFT #001",
      description="Приобретение цифрового актива Cyber Punk Cat",
      payload="nft_pay_payload_001",
      currency="XTR",  # Валюта Звёзд Telegram
      prices=prices,
  )
  await callback.answer()


# 4. Предпроверка платежа
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
  await pre_checkout_query.answer(ok=True)


# 5. Успешная оплата
@router.message(F.successful_payment)
async def success_payment(message: Message):
  payment_info = message.successful_payment
  await message.answer(
      "✅ **Оплата прошла успешно!**\n"
      f"Вы купили NFT за {payment_info.total_amount} ⭐.\n"
      "Товар отправлен в ваш профиль.",
      parse_mode="Markdown",
  )


async def main():
  # Создаем конфигурацию для кастомного сервера ShuzaGram API через TelegramAPIServer
  custom_server = TelegramAPIServer.from_base(SHUZAGRAM_SERVER_BASE)
  session = AiohttpSession(api=custom_server)

  # Передаем сессию в инициализацию бота
  bot = Bot(token=TOKEN, session=session)
  storage = MemoryStorage()
  dp = Dispatcher(storage=storage)
  dp.include_router(router)

  print("Бот успешно запущен и подключен к ShuzaGram!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())
