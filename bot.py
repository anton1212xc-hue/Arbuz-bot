import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка вашего кастомного сервера (ShuzaGram API)
custom_session = AiohttpSession(
    api=TelegramAPIServer.from_base(
        "https://api.shuzagram.com", 
        is_local=True
    )
)

# Ваш токен от BotFather в ShuzaGram
BOT_TOKEN = "1780243438:gVyt2-oXtD942PCKZkYbkLKYMKzob9wQ10A"
bot = Bot(token=BOT_TOKEN, session=custom_session)
dp = Dispatcher()

# Словарь для хранения очков игроков (user_id: очки)
users_score = {}

# Функция для создания кнопок кликера
def get_clicker_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍉 Кликнуть АРБУЗ!", callback_data="click_arbuz")
    builder.button(text="🏆 Счет", callback_data="show_score")
    builder.adjust(1) # Расположение кнопок в 1 колонку
    return builder.as_markup()

# Обработка команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_score:
        users_score[user_id] = 0
        
    await message.answer(
        "Добро пожаловать в **ArbuzClick**! 🍉\n\n"
        "Нажимайте на кнопку ниже, чтобы собирать арбузные очки!",
        reply_markup=get_clicker_keyboard(),
        parse_mode="Markdown"
    )

# Обработка клика по кнопке
@dp.callback_query(F.data == "click_arbuz")
async def process_click(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Увеличиваем счет на 1
    if user_id not in users_score:
        users_score[user_id] = 0
    users_score[user_id] += 1
    
    current_score = users_score[user_id]
    
    # Обновляем текст сообщения с новым счетом
    try:
        await callback.message.edit_text(
            f"🍉 **ArbuzClick Кликер**\n\n"
            f"Ваши очки: **{current_score}** арбузов 🚀",
            reply_markup=get_clicker_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        # Игнорируем ошибку, если пользователь кликает слишком быстро и текст не изменился
        pass
        
    # Всплывающее уведомление при клике (убирает анимацию загрузки с кнопки)
    await callback.answer(f"+1 Арбуз! 🍉 (Всего: {current_score})")

# Кнопка для проверки текущего счета
@dp.callback_query(F.data == "show_score")
async def process_score(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_score = users_score.get(user_id, 0)
    await callback.answer(f"Ваш общий результат: {current_score} арбузов 🍉", show_alert=True)

async def main():
    print("Бот-кликер запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
