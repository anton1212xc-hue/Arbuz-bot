import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка вашего кастомного сервера (ShuzaGram API)[span_0](start_span)[span_0](end_span)
custom_session = AiohttpSession(
    api=TelegramAPIServer.from_base(
        "https://api.shuzagram.com", 
        is_local=True
    )
)

BOT_TOKEN = "1780243438:gVyt2-oXtD942PCKZkYbkLKYMKzob9wQ10A"
bot = Bot(token=BOT_TOKEN, session=custom_session)
dp = Dispatcher()

# База данных пользователей в памяти
# user_id -> {"score": очки, "power": сила клика, "cost": цена улучшения, "name": имя}
users_data = {}

# Главное меню
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍉 Кликнуть АРБУЗ!", callback_data="click_arbuz")
    builder.button(text="🛒 Магазин", callback_data="shop")
    builder.button(text="🏆 Топ игроков", callback_data="show_top")
    builder.adjust(1, 2)
    return builder.as_markup()

# Кнопка возврата в меню
def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()

# Клавиатура магазина
def get_shop_keyboard(cost):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⚡ Улучшить клик (+1 сила) — {cost} 🍉", callback_data="buy_power")
    builder.button(text="⬅️ Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

# Получение или создание данных пользователя
def get_user(message_or_callback):
    user = message_or_callback.from_user
    user_id = user.id
    name = user.first_name or "Арбузер"
    if user_id not in users_data:
        users_data[user_id] = {
            "score": 0,
            "power": 1,
            "cost": 50, # Стартовая стоимость улучшения
            "name": name
        }
    else:
        users_data[user_id]["name"] = name
    return users_data[user_id]

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = get_user(message)
    await message.answer(
        f"🍉 **ArbuzClick Кликер**\n\n"
        f"Привет, {user['name']}!\n"
        f"Твой баланс: **{user['score']}** арбузов 🍉\n"
        f"Сила клика: **+{user['power']}** ⚡",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# Возврат в главное меню
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    user = get_user(callback)
    await callback.message.edit_text(
        f"🍉 **ArbuzClick Кликер**\n\n"
        f"Твой баланс: **{user['score']}** арбузов 🍉\n"
        f"Сила клика: **+{user['power']}** ⚡",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# Клик по арбузу
@dp.callback_query(F.data == "click_arbuz")
async def process_click(callback: types.CallbackQuery):
    user = get_user(callback)
    user["score"] += user["power"] # Добавляем очки с учетом силы клика
    
    try:
        await callback.message.edit_text(
            f"🍉 **ArbuzClick Кликер**\n\n"
            f"Твой баланс: **{user['score']}** арбузов 🍉\n"
            f"Сила клика: **+{user['power']}** ⚡",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    await callback.answer(f"+{user['power']} Арбуз! 🍉 (Всего: {user['score']})")

# Открытие магазина
@dp.callback_query(F.data == "shop")
async def open_shop(callback: types.CallbackQuery):
    user = get_user(callback)
    await callback.message.edit_text(
        f"🛒 **Магазин улучшений**\n\n"
        f"Твой баланс: **{user['score']}** 🍉\n"
        f"Текущая сила клика: **+{user['power']}** ⚡\n\n"
        f"Покупай улучшения, чтобы собирать арбузы быстрее!",
        reply_markup=get_shop_keyboard(user["cost"]),
        parse_mode="Markdown"
    )
    await callback.answer()

# Покупка улучшения силы клика
@dp.callback_query(F.data == "buy_power")
async def buy_power(callback: types.CallbackQuery):
    user = get_user(callback)
    if user["score"] >= user["cost"]:
        user["score"] -= user["cost"]
        user["power"] += 1
        user["cost"] = int(user["cost"] * 1.7) # Увеличиваем стоимость следующей покупки
        await callback.answer("🎉 Успешно! Сила клика повышена!", show_alert=True)
    else:
        await callback.answer("❌ Недостаточно арбузов для покупки!", show_alert=True)
        
    # Обновляем текст магазина
    await callback.message.edit_text(
        f"🛒 **Магазин улучшений**\n\n"
        f"Твой баланс: **{user['score']}** 🍉\n"
        f"Текущая сила клика: **+{user['power']}** ⚡\n\n"
        f"Покупай улучшения, чтобы собирать арбузы быстрее!",
        reply_markup=get_shop_keyboard(user["cost"]),
        parse_mode="Markdown"
    )

# Топ игроков
@dp.callback_query(F.data == "show_top")
async def show_top(callback: types.CallbackQuery):
    # Сортируем игроков по балансу (по убыванию)
    sorted_users = sorted(users_data.values(), key=lambda x: x["score"], reverse=True)
    
    top_text = "🏆 **Топ игроков по балансу:**\n\n"
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    for i, u in enumerate(sorted_users[:10], 1):
        medal = medals.get(i, f"{i}.")
        top_text += f"{medal} **{u['name']}** — {u['score']} 🍉 (Сила: +{u['power']})\n"
        
    if not sorted_users:
        top_text += "Пока нет активных игроков."

    await callback.message.edit_text(
        top_text,
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# Веб-сервер заглушка для Render
async def handle(request):
    return web.Response(text="Arbuz Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await web_server()
    print("Бот-кликер с магазином и топом запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
