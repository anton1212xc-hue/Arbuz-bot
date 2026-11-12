import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

TOKEN = "1780243444:GNVsB25ytITDJMWilP1y64AZ0EdNSp4Rh-j"
SHUZAGRAM_SERVER_BASE = "https://api.shuzagram.com"

router = Router()

# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nfts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            title TEXT,
            description TEXT,
            price INTEGER,
            gift_media TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            stars_wallet INTEGER DEFAULT 500
        )
    """)
    conn.commit()
    conn.close()

init_db()

class SellNFT(StatesGroup):
    waiting_for_media = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()

def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Открыть каталог NFT", callback_data="open_catalog")],
            [InlineKeyboardButton(text="🎁 Выставить свой NFT / Подарок", callback_data="sell_nft")],
            [InlineKeyboardButton(text="👤 Мой профиль / Баланс", callback_data="my_profile")]
        ]
    )

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    # Выдаем тестовые 500 звезд для проверки покупки, если пользователя нет
    cursor.execute("INSERT OR IGNORE INTO users (user_id, stars_wallet) VALUES (?, 500)", (message.from_user.id,))
    conn.commit()
    conn.close()

    await message.answer(
        "👋 Добро пожаловать на P2P Маркетплейс NFT и подарков за Telegram Stars ✨.\n"
        "Здесь вы можете безопасно продавать и покупать цифровые активы!",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню маркетплейса. Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "open_catalog")
async def show_catalog(callback: CallbackQuery):
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, price FROM nfts WHERE status = 'active'")
    items = cursor.fetchall()
    conn.close()

    if not items:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
        ])
        await callback.message.edit_text(
            "📭 В каталоге пока нет активных NFT.\nБудьте первыми, кто выставит подарок!",
            reply_markup=keyboard
        )
        await callback.answer()
        return

    keyboard_buttons = []
    for item_id, title, price in items:
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"🎁 {title} — {price} ⭐", callback_data=f"view_nft_{item_id}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_to_main")])
    
    await callback.message.edit_text(
        "🛍 **Актуальный каталог NFT и подарков:**\nВыберите лот для просмотра:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_nft_"))
async def view_nft(callback: CallbackQuery):
    nft_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, price, seller_id, gift_media FROM nfts WHERE id = ? AND status = 'active'", (nft_id,))
    nft = cursor.fetchone()
    conn.close()

    if not nft:
        await callback.answer("Этот NFT уже куплен или снят с продажи!", show_alert=True)
        return

    title, description, price, seller_id, gift_media = nft

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 Подтвердить покупку за {price} ⭐", callback_data=f"buy_confirm_{nft_id}")],
            [InlineKeyboardButton(text="« К каталогу", callback_data="open_catalog")]
        ]
    )

    caption = (
        f"🎁 **NFT / Подарок: {title}**\n\n"
        f"📝 Описание: {description}\n"
        f"🏷 Цена: {price} ⭐\n"
        f"👤 Продавец ID: `{seller_id}`"
    )

    if gift_media:
        await callback.message.answer_photo(photo=gift_media, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        
    await callback.answer()

@router.callback_query(F.data.startswith("sell_nft"))
async def start_sell(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎁 Отправьте **картинку или анимацию** вашего NFT-подарка:"
    )
    await state.set_state(SellNFT.waiting_for_media)
    await callback.answer()

@router.message(SellNFT.waiting_for_media, F.photo)
async def process_media(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(gift_media=photo_id)
    await message.answer("📝 Введите **название** вашего NFT или подарка:")
    await state.set_state(SellNFT.waiting_for_title)

@router.message(SellNFT.waiting_for_media)
async def process_media_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте картинку или фото подарка:")

@router.message(SellNFT.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("📄 Теперь введите **описание** лота:")
    await state.set_state(SellNFT.waiting_for_description)

@router.message(SellNFT.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("💰 Укажите **стоимость** в Звёздах (только число, например: `100`):")
    await state.set_state(SellNFT.waiting_for_price)

@router.message(SellNFT.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите корректное число для цены:")
        return

    price = int(message.text)
    data = await state.get_data()
    
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO nfts (seller_id, title, description, price, gift_media, status) VALUES (?, ?, ?, ?, ?, 'active')",
        (message.from_user.id, data["title"], data["description"], price, data["gift_media"])
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        "✅ **Ваш NFT успешно выставлен на продажу!**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# --- ПРЯМАЯ И БЫСТРАЯ ПОКУПКА БЕЗ ЗАВИСАНИЙ ИНВОЙСА ---
@router.callback_query(F.data.startswith("buy_confirm_"))
async def buy_nft_direct(callback: CallbackQuery, bot: Bot):
    nft_id = int(callback.data.split("_")[2])
    buyer_id = callback.from_user.id

    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, seller_id, gift_media FROM nfts WHERE id = ? AND status = 'active'", (nft_id,))
    nft = cursor.fetchone()

    if not nft:
        conn.close()
        await callback.answer("Этот NFT уже куплен или недоступен!", show_alert=True)
        return

    title, price, seller_id, gift_media = nft

    # Проверяем баланс покупателя
    cursor.execute("SELECT stars_wallet FROM users WHERE user_id = ?", (buyer_id,))
    buyer_row = cursor.fetchone()
    buyer_balance = buyer_row[0] if buyer_row else 0

    if buyer_balance < price:
        conn.close()
        await callback.answer(f"❌ Недостаточно звёзд! У вас {buyer_balance} ⭐, а нужно {price} ⭐.", show_alert=True)
        return

    # Проводим транзакцию
    # Списываем у покупателя
    cursor.execute("UPDATE users SET stars_wallet = stars_wallet - ? WHERE user_id = ?", (price, buyer_id))
    # Зачисляем продавцу
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, seller_id))
    # Помечаем товар проданным
    cursor.execute("UPDATE nfts SET status = 'sold' WHERE id = ?", (nft_id,))
    
    conn.commit()
    conn.close()

    # Отправляем подарок покупателю
    if gift_media:
        try:
            await bot.send_photo(
                chat_id=buyer_id,
                photo=gift_media,
                caption=f"🎉 **Поздравляем с успешной покупкой!**\nВы приобрели **{title}** за {price} ⭐.\nАктив передан в ваш профиль."
            )
        except Exception:
            pass

    # Уведомляем продавца
    if seller_id:
        try:
            await bot.send_message(
                chat_id=seller_id,
                text=f"💰 **Ваш NFT ({title}) был успешно куплен!**\nВам начислено **{price} ⭐** на баланс."
            )
        except Exception:
            pass

    await callback.message.answer(
        "✅ **Покупка успешно завершена!**\n"
        f"Вы купили NFT за {price} ⭐.\n"
        "Товар отправлен в ваш чат, а продавец получил оплату.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "my_profile")
async def show_profile(callback: CallbackQuery):
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, stars_wallet FROM users WHERE user_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0
    wallet = row[1] if row else 0

    cursor.execute("SELECT COUNT(*) FROM nfts WHERE seller_id = ? AND status = 'active'", (callback.from_user.id,))
    active_listings = cursor.fetchone()[0]
    conn.close()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
        ]
    )

    await callback.message.edit_text(
        f"👤 **Ваш профиль:**\n\n"
        f"⭐ Доступно звезд для трат: **{wallet} ⭐**\n"
        f"💎 Заработано от продаж: **{balance} ⭐**\n"
        f"📦 Ваших активных лотов: **{active_listings}**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

async def main():
    custom_server = TelegramAPIServer.from_base(SHUZAGRAM_SERVER_BASE)
    session = AiohttpSession(api=custom_server)

    bot = Bot(token=TOKEN, session=session)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    print("Маркетплейс бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
