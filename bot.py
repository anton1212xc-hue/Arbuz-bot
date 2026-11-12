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
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

TOKEN = "1780243444:GNVsB25ytITDJMWilP1y64AZ0EdNSp4Rh-j"
SHUZAGRAM_SERVER_BASE = "https://api.shuzagram.com"

router = Router()

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
            balance INTEGER DEFAULT 0
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
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()

    await message.answer(
        "👋 Добро пожаловать на P2P Маркетплейс NFT за реальные Telegram Stars ✨.\n"
        "Покупка происходит через официальные счета Telegram!",
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

    if seller_id == callback.from_user.id:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="« К каталогу", callback_data="open_catalog")]
            ]
        )
        await callback.message.edit_text(
            f"🎨 **NFT: {title}**\n\n⚠️ Вы не можете купить свой собственный выставленный лот!",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 Купить за {price} Stars", callback_data=f"buy_invoice_{nft_id}")],
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

@router.callback_query(F.data == "sell_nft")
async def start_sell(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎁 Отправьте **картинку или скриншот** вашего NFT-подарка:"
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

# --- ВЫСТАВЛЕНИЕ ОФИЦИАЛЬНОГО СЧЕТА В ТЕЛЕГРАМЕ (ЗВЁЗДЫ) ---
@router.callback_query(F.data.startswith("buy_invoice_"))
async def create_invoice(callback: CallbackQuery):
    nft_id = int(callback.data.split("_")[2])

    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, seller_id FROM nfts WHERE id = ? AND status = 'active'", (nft_id,))
    nft = cursor.fetchone()
    conn.close()

    if not nft:
        await callback.answer("Этот NFT уже недоступен!", show_alert=True)
        return

    title, price, seller_id = nft

    if seller_id == callback.from_user.id:
        await callback.answer("Нельзя покупать свой собственный лот!", show_alert=True)
        return

    prices = [LabeledPrice(label=title, amount=price)]
    payload_data = f"nft_{nft_id}_seller_{seller_id}"

    # Отправка инвойса в Telegram Stars (валюта XTR)
    await callback.message.answer_invoice(
        title=f"Покупка {title}",
        description=f"Приобретение NFT-подарка у продавца ID {seller_id}",
        payload=payload_data,
        currency="XTR",
        prices=prices,
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

# --- ОБРАБОТКА УСПЕШНОЙ ОПЛАТЫ РЕАЛЬНЫМИ ЗВЁЗДАМИ ---
@router.message(F.successful_payment)
async def success_payment(message: Message, bot: Bot):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    
    try:
        parts = payload.split("_")
        nft_id = int(parts[1])
        seller_id = int(parts[3])
    except Exception:
        nft_id = None
        seller_id = None

    amount = payment_info.total_amount
    buyer_id = message.from_user.id

    if nft_id:
        conn = sqlite3.connect("marketplace.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT title, gift_media FROM nfts WHERE id = ?", (nft_id,))
        nft_data = cursor.fetchone()
        
        # Закрываем лот
        cursor.execute("UPDATE nfts SET status = 'sold' WHERE id = ?", (nft_id,))
        
        # Зачисляем звёзды на баланс продавца
        if seller_id:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, seller_id))
            
        conn.commit()
        conn.close()

        # Отправляем подарок покупателю
        if nft_data:
            title, gift_media = nft_data
            if gift_media:
                try:
                    await bot.send_photo(
                        chat_id=buyer_id,
                        photo=gift_media,
                        caption=f"🎉 **Покупка успешно завершена!**\nВы приобрели **{title}** за {amount} ⭐.\nАктив передан в ваш профиль."
                    )
                except Exception:
                    pass

        # Уведомляем продавца
        if seller_id:
            try:
                await bot.send_message(
                    chat_id=seller_id,
                    text=f"💰 **Ваш NFT ({title}) был успешно куплен!**\nС баланса покупателя списано и зачислено вам **{amount} ⭐**."
                )
            except Exception:
                pass

    await message.answer(
        "✅ **Оплата прошла успешно!**\n"
        f"С вашего баланса Telegram списано {amount} ⭐.\n"
        "Подарок отправлен в ваш чат, а продавец получил выплату.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "my_profile")
async def show_profile(callback: CallbackQuery):
    conn = sqlite3.connect("marketplace.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0

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
        f"💎 Заработано звёзд от продаж: **{balance} ⭐**\n"
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

    print("Маркетплейс бот запущен с поддержкой Telegram Stars!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
