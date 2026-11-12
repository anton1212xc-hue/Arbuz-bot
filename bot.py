import time
import requests

TOKEN = "1780243447:z-EViDoEUiE61aHerKad4WazMWTsKC3OraH"
BASE_URL = f"https://api.shuzagram.com/bot{TOKEN}"


def send_message(chat_id, text, reply_markup=None):
  """Функция для отправки сообщений в ShuzaGram"""
  url = f"{BASE_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": text}
  if reply_markup:
    payload["reply_markup"] = reply_markup
  response = requests.post(url, json=payload)
  return response.json()


def get_updates(offset=None):
  """Получение новых сообщений от пользователей"""
  url = f"{BASE_URL}/getUpdates"
  params = {"offset": offset, "timeout": 30}
  try:
    response = requests.get(url, params=params)
    return response.json()
  except Exception as e:
    print(f"Ошибка соединения: {e}")
    return {"ok": False, "result": []}


def main():
  print("Бот бандит успешно запущен на ShuzaGram! Ожидание маслин... то есть сообщений.")
  offset = None

  while True:
    data = get_updates(offset)
    if data.get("ok"):
      for update in data.get("result", []):
        offset = update["update_id"] + 1

        if "message" in update:
          chat_id = update["message"]["chat"]["id"]
          text = update["message"].get("text", "")
          user_name = update["message"]["from"].get("first_name", "Бро")

          print.info = f"Получено сообщение от {user_name}: {text}"

          # Логика команд
          if text == "/start":
            reply_text = (
                f"Здорово, {userءнаме if 'userءнаме' in locals() else 'бро'}! 🤙"
                " Добро пожаловать в **бот бандит**.\n\nЭто симулятор"
                " реальной жизни: поднимай бабосы, качай перса, бери бизнес в"
                " блок и стань федералом или авторитетом.\n\nЖми на кнопки ниже,"
                " чтобы начать движ:"
            )

            # Создаем клавиатуру в стиле меню игры
            keyboard = {
                "keyboard": [[{"text": "👤 Профиль"}, {"text": "💼 Работа"}],
                             [{"text": "🎰 Казино"}, {"text": "🛒 Шмотки"}]],
                "resize_keyboard": True,
            }
            send_message(chat_id, reply_text, reply_markup=keyboard)

          elif text == "👤 Профиль":
            send_message(
                chat_id,
                "📊 **Твой профиль:**\n\n💰 Бахчи (бабосы): $1,000\n🧢 Ранг: Скуф"
                " / Обычный чел\n🛡 Защита: 10\n⚖️ Статус: На свободе",
            )

          elif text == "💼 Работа":
            send_message(
                chat_id,
                "мяумс, выбери работу, на которой хочешь сейчас"
                " работать:\n\n• 🤝 Рефка\n• 🍔 Бизнес\n• 🧱 Блок\n• 🚕"
                " Таксист\n• 👮 Федерал",
            )

          elif text == "🎰 Казино":
            send_message(
                chat_id,
                "🎲 Добро пожаловать в кинцо «как остаться без трусов»!\nЗа"
                " какой стол сядете?",
            )

          elif text == "🛒 Шмотки":
            send_message(
                chat_id,
                "🛍 **BB MARKET:**\nТут можно прикупить шмотки для поднятия"
                " авторитета и защиты (например, HCCI HENTAI SHIRT или"
                " суету)[span_4](start_span)[span_4](end_span).",
            )

          else:
            send_message(
                chat_id,
                "Чет непонятная малява. Пользуйся меню или пиши /start, бро.",
            )

    time.sleep(1)


if __name__ == "__main__":
  main()
