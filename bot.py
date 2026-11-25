import base64
import json
import os
import random
import sqlite3
import threading
import time
import requests

# Твой токен ШузаГрам
TOKEN = "1780243414:ijZnfeJtqAyNrk1o54ZTMOg24goyyOJl14y"
URL = f"https://api.shuzagram.com/bot{TOKEN}/"

DB_FILE = "database.db"
active_games = {}
admin_session = set()
ADMIN_PASSWORD = "gver1212"

# Токен берется из переменных окружения Render, а не прописан в коде!
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")


def sync_db_to_github():
  """Автоматически загружает database.db в репозиторий GitHub"""
  if not GITHUB_TOKEN or not GITHUB_REPO:
    return

  try:
    if not os.path.exists(DB_FILE):
      return

    with open(DB_FILE, "rb") as f:
      content_bytes = f.read()

    encoded_content = base64.b64encode(content_bytes).decode("utf-8")
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    r = requests.get(api_url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    data = {
        "message": "Auto-save database.db [Bot Backup]",
        "content": encoded_content,
    }
    if sha:
      data["sha"] = sha

    requests.put(api_url, headers=headers, json=data, timeout=10)
  except Exception as e:
    print(f"[GitHub Sync Error] {e}")


def init_db():
  if not os.path.exists(DB_FILE) and GITHUB_TOKEN and GITHUB_REPO:
    try:
      api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILE}"
      headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
      r = requests.get(api_url, headers=headers)
      if r.status_code == 200:
        download_url = r.json().get("download_url")
        if download_url:
          db_data = requests.get(download_url).content
          with open(DB_FILE, "wb") as f:
            f.write(db_data)
          print("[Init DB] База данных успешно скачана с GitHub!")
    except Exception as e:
      print(f"[Init DB Error] {e}")

  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            money INTEGER DEFAULT 1000,
            defense INTEGER DEFAULT 10,
            rank TEXT DEFAULT 'Скуф / Обычный чел'
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            biz_key TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_key TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
  conn.commit()
  conn.close()


def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
  data = {"chat_id": chat_id, "text": text}
  if reply_markup:
    data["reply_markup"] = json.dumps(reply_markup)
  if parse_mode:
    data["parse_mode"] = parse_mode
  try:
    requests.post(URL + "sendMessage", json=data, timeout=10)
  except Exception as e:
    print(f"[ERROR send_message] {e}")


def edit_message_text(chat_id, message_id, text, reply_markup=None):
  data = {
      "chat_id": chat_id,
      "message_id": message_id,
      "text": text,
      "parse_mode": "Markdown",
  }
  if reply_markup:
    data["reply_markup"] = json.dumps(reply_markup)
  try:
    requests.post(URL + "editMessageText", json=data, timeout=10)
  except Exception as e:
    print(f"[ERROR edit_message] {e}")


def answer_callback_query(callback_query_id, text=None, show_alert=False):
  data = {"callback_query_id": callback_query_id, "show_alert": show_alert}
  if text:
    data["text"] = text
  try:
    requests.post(URL + "answerCallbackQuery", json=data, timeout=10)
  except Exception as e:
    print(f"[ERROR answer_callback] {e}")


BUSINESSES = {
    "shaurma": {"name": "🌭 Ларек с шаурмой", "cost": 5000, "income": 500},
    "carwash": {"name": "🚗 Автомойка", "cost": 25000, "income": 2500},
    "club": {"name": "💎 Ночной клуб", "cost": 100000, "income": 10000},
    "casino_biz": {
        "name": "🎰 Подпольное казино",
        "cost": 500000,
        "income": 50000,
    },
    "vip_cartel": {"name": "👑 Картель", "cost": 0, "income": 500000},
}

CARS = {
    "vaz": {
        "name": "🚗 ВАЗ 2107 (Пуд соли)",
        "cost": 15000,
        "speed": "160 км/ч",
        "rarity": "🟢 Развалюха",
    },
    "bmw_e34": {
        "name": "🏎 BMW E34 (Бумер)",
        "cost": 80000,
        "speed": "240 км/ч",
        "rarity": "🔵 Элегантная",
    },
    "gelik": {
        "name": "🚙 Mercedes G-Class (Гелик)",
        "cost": 350000,
        "speed": "220 км/ч",
        "rarity": "🟣 Спорткар",
    },
    "lamborghini": {
        "name": "🏎 Lamborghini Huracan",
        "cost": 1200000,
        "speed": "325 км/ч",
        "rarity": "🟣 Спорткар",
    },
    "rolls_royce": {
        "name": "🚙 Rolls-Royce Cullinan",
        "cost": 7500000,
        "speed": "250 км/ч",
        "rarity": "🟡 Премиум",
    },
    "bugatti_divo": {
        "name": "🏎 Bugatti Divo",
        "cost": 15000000,
        "speed": "380 км/ч",
        "rarity": "👑 Ликвид (Донат)",
    },
}
car_keys = list(CARS.keys())


def get_main_menu():
  return {
      "keyboard": [
          [{"text": "👤 Профиль"}, {"text": "🏆 Топ бандюков"}],
          [{"text": "💼 Работа"}, {"text": "🏢 Бизнесы"}],
          [{"text": "🚗 Автосалон"}, {"text": "🎰 Казино"}],
          [{"text": "🛒 Шмотки"}],
      ],
      "resize_keyboard": True,
  }


def get_work_menu():
  return {
      "keyboard": [
          [{"text": "🤝 Раскидать рефки"}, {"text": "🚕 Угон тачки"}],
          [{"text": "🧱 Стрелка за блок"}, {"text": "👮 Сходняк"}],
          [{"text": "⬅️ Назад"}],
      ],
      "resize_keyboard": True,
  }


def get_business_menu():
  return {
      "keyboard": [
          [{"text": "🌭 Шаурма ($5k)"}, {"text": "🚗 Автомойка ($25k)"}],
          [{"text": "💎 Клуб ($100k)"}, {"text": "🎰 Казино ($500k)"}],
          [{"text": "💼 Мои бизнесы"}, {"text": "⬅️ Назад"}],
      ],
      "resize_keyboard": True,
  }


def get_casino_menu():
  return {
      "keyboard": [
          [{"text": "🎲 Сыграть в кости"}, {"text": "🃏 Сыграть в очко"}],
          [{"text": "⬅️ Назад"}],
      ],
      "resize_keyboard": True,
  }


def get_market_menu():
  return {
      "keyboard": [
          [
              {"text": "👕 Шмотка VETEMENTS ($500)"},
              {"text": "🛡 Прокачать защиту ($300)"},
          ],
          [{"text": "⬅️ Назад"}],
      ],
      "resize_keyboard": True,
  }


def get_admin_menu():
  return {
      "keyboard": [
          [{"text": "💸 Выдать бабло"}, {"text": "🏢 Выдать бизнес"}],
          [{"text": "📢 Сделать рассылку"}, {"text": "🚪 Выйти из админки"}],
      ],
      "resize_keyboard": True,
  }


def get_user(user_id, username=None):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT user_id, username, money, defense, rank FROM users WHERE"
      " user_id = ?",
      (user_id,),
  )
  row = cursor.fetchone()
  clean_username = username.lower() if username else str(user_id)

  if not row:
    cursor.execute(
        "INSERT INTO users (user_id, username, money, defense, rank) VALUES (?,"
        " ?, 1000, 10, 'Скуф / Обычный чел')",
        (user_id, clean_username),
    )
    conn.commit()
    money, defense, rank = 1000, 10, "Скуф / Обычный чел"
  else:
    _, db_username, money, defense, rank = row
    if username and db_username != clean_username:
      cursor.execute(
          "UPDATE users SET username = ? WHERE user_id = ?",
          (clean_username, user_id),
      )
      conn.commit()

  cursor.execute(
      "SELECT biz_key FROM businesses WHERE user_id = ?", (user_id,)
  )
  businesses = [b[0] for b in cursor.fetchall()]
  cursor.execute("SELECT car_key FROM cars WHERE user_id = ?", (user_id,))
  cars = [c[0] for c in cursor.fetchall()]
  conn.close()

  return {
      "user_id": user_id,
      "username": clean_username,
      "money": money,
      "defense": defense,
      "rank": rank,
      "businesses": businesses,
      "cars": cars,
  }


def update_user_money_and_stats(
    user_id, money=None, defense=None, rank=None
):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  if money is not None:
    cursor.execute(
        "UPDATE users SET money = ? WHERE user_id = ?", (money, user_id)
    )
  if defense is not None:
    cursor.execute(
        "UPDATE users SET defense = ? WHERE user_id = ?", (defense, user_id)
    )
  if rank is not None:
    cursor.execute(
        "UPDATE users SET rank = ? WHERE user_id = ?", (rank, user_id)
    )
  conn.commit()
  conn.close()
  sync_db_to_github()


def add_user_business(user_id, biz_key):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO businesses (user_id, biz_key) VALUES (?, ?)",
      (user_id, biz_key),
  )
  conn.commit()
  conn.close()
  sync_db_to_github()


def add_user_car(user_id, car_key):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO cars (user_id, car_key) VALUES (?, ?)", (user_id, car_key)
  )
  conn.commit()
  conn.close()
  sync_db_to_github()


def get_user_cars_detailed(user_id):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("SELECT id, car_key FROM cars WHERE user_id = ?", (user_id,))
  rows = cursor.fetchall()
  conn.close()
  return rows


def remove_car_by_db_id(db_id):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("DELETE FROM cars WHERE id = ?", (db_id,))
  conn.commit()
  conn.close()
  sync_db_to_github()


def get_all_user_ids():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("SELECT user_id FROM users")
  rows = cursor.fetchall()
  conn.close()
  return [row[0] for row in rows]


def get_user_by_username_or_id(target_raw):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  if target_raw.isdigit():
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?", (int(target_raw),)
    )
  else:
    cursor.execute(
        "SELECT user_id FROM users WHERE LOWER(username) = ?", (target_raw,)
    )
  row = cursor.fetchone()
  conn.close()
  return row[0] if row else None


def get_autosalon_inline(index: int):
  key = car_keys[index]
  car = CARS[key]
  return {
      "inline_keyboard": [
          [
              {"text": "⬅️ Назад", "callback_data": f"car_prev_{index}"},
              {"text": "➡️ Вперед", "callback_data": f"car_next_{index}"},
          ],
          [{"text": "🛒 Купить эту тачку", "callback_data": f"car_buy_{index}"}],
          [
              {"text": "🚙 Мой гараж", "callback_data": "garage_open"},
              {"text": "❌ Выйти в меню", "callback_data": "car_exit"},
          ],
      ]
  }


def get_garage_inline(index: int, db_id: int):
  return {
      "inline_keyboard": [
          [
              {"text": "⬅️ Назад", "callback_data": f"gar_prev_{index}"},
              {"text": "➡️ Вперед", "callback_data": f"gar_next_{index}"},
          ],
          [
              {
                  "text": "💸 Продать за полцены",
                  "callback_data": f"gar_sell_{db_id}_{index}",
              }
          ],
          [
              {"text": "🚗 В автосалон", "callback_data": "garage_to_shop"},
              {"text": "❌ Выйти в меню", "callback_data": "gar_exit"},
          ],
      ]
  }


def show_car_page(chat_id, message_id=None, index=0):
  global car_keys
  index = index % len(car_keys)
  key = car_keys[index]
  car = CARS[key]
  text = (
      f"🚗 **Автосалон «У Палыча»**\n\n🚙 Модель: **{car['name']}**\n🏷 Редкость:"
      f" **{car['rarity']}**\n⚡️ Макс. скорость: `{car['speed']}`\n💰 Цена:"
      f" **${car['cost']:,}**\n\n📄 Чёткая тачка, бери не пожалеешь!"
  )
  markup = get_autosalon_inline(index)
  if message_id:
    edit_message_text(chat_id, message_id, text, reply_markup=markup)
  else:
    send_message(chat_id, text, reply_markup=markup)


def show_garage_page(chat_id, message_id, user_id, index=0):
  cars_list = get_user_cars_detailed(user_id)
  if not cars_list:
    edit_message_text(
        chat_id,
        message_id,
        "Твой гараж пуст! Сначала купи тачку в автосалоне.",
        reply_markup={
            "inline_keyboard": [[{"text": "🚗 В автосалон", "callback_data": "garage_to_shop"}]]
        },
    )
    return
  index = index % len(cars_list)
  db_id, key = cars_list[index]
  car = CARS.get(
      key,
      {
          "name": key,
          "speed": "???",
          "cost": 0,
          "rarity": "🟢 Развалюха",
      },
  )
  sell_price = int(car["cost"] / 2) if car["cost"] > 0 else 0
  text = (
      f"🚙 **Твой гараж («У Палыча»)**\n\n🅿️ **Слот №{index + 1} из"
      f" {len(cars_list)}**\n🚗 Модель: **{car['name']}**\n🏷 Редкость:"
      f" **{car['rarity']}**\n⚡️ Макс. скорость: `{car['speed']}`\n💵 Цена продажи:"
      f" **${sell_price:,}**"
  )
  markup = get_garage_inline(index, db_id)
  edit_message_text(chat_id, message_id, text, reply_markup=markup)


def process_message(message):
  chat_id = message["chat"]["id"]
  user_id = message["from"]["id"]
  username = message["from"].get("username", str(user_id))
  text = message.get("text", "")

  user = get_user(user_id, username)

  if user_id in active_games:
    state = active_games[user_id]

    if state.get("action") == "give_money":
      active_games.pop(user_id, None)
      if text == "⬅️ Назад":
        send_message(chat_id, "Отменено.", reply_markup=get_admin_menu())
        return
      parts = text.split()
      if len(parts) >= 2:
        t_id = get_user_by_username_or_id(parts[0].lstrip("@"))
        if t_id and parts[1].isdigit():
          t_user = get_user(t_id)
          new_m = t_user["money"] + int(parts[1])
          update_user_money_and_stats(t_id, money=new_m)
          send_message(
              chat_id,
              f"✅ Выдано ${int(parts[1]):,} игроку @{t_user['username']}!",
              reply_markup=get_admin_menu(),
          )
          return
      send_message(
          chat_id, "❌ Неверный формат!", reply_markup=get_admin_menu()
      )
      return

    elif state.get("action") == "give_biz":
      active_games.pop(user_id, None)
      if text == "⬅️ Назад":
        send_message(chat_id, "Отменено.", reply_markup=get_admin_menu())
        return
      parts = text.split()
      if len(parts) >= 2:
        t_id = get_user_by_username_or_id(parts[0].lstrip("@"))
        biz_k = parts[1]
        if t_id and biz_k in BUSINESSES:
          t_user = get_user(t_id)
          add_user_business(t_id, biz_k)
          send_message(
              chat_id,
              f"✅ Выдан бизнес {BUSINESSES[biz_k]['name']} игроку"
              f" @{t_user['username']}!",
              reply_markup=get_admin_menu(),
          )
          return
      send_message(
          chat_id, "❌ Ошибка формата!", reply_markup=get_admin_menu()
      )
      return

    elif state.get("action") == "broadcast":
      active_games.pop(user_id, None)
      if text == "⬅️ Назад":
        send_message(chat_id, "Рассылка отменена.", reply_markup=get_admin_menu())
        return
      all_u = get_all_user_ids()
      count = 0
      for uid in all_u:
        send_message(uid, f"📢 **Рассылка от администрации:**\n\n{text}")
        count += 1
      send_message(
          chat_id,
          f"📢 Рассылка завершена! Получателей: {count}",
          reply_markup=get_admin_menu(),
      )
      return

    elif state.get("casino"):
      if text == "⬅️ Назад":
        active_games.pop(user_id, None)
        send_message(chat_id, "Вышел из казино.", reply_markup=get_casino_menu())
        return
      if not text.isdigit():
        send_message(chat_id, "⚠️ Ставка должна быть числом!")
        return
      bet = int(text)
      active_games.pop(user_id, None)
      if bet <= 0 or user["money"] < bet:
        send_message(
            chat_id,
            "❌ Недостаточно бабла или неверная ставка!",
            reply_markup=get_casino_menu(),
        )
        return
      win = random.choice([True, False])
      if win:
        new_m = user["money"] + bet
        update_user_money_and_stats(user_id, money=new_m)
        send_message(
            chat_id,
            f"🎲 Победа! Выиграл **+${bet:,}**! 💰\nБаланс: ${new_m:,}",
            reply_markup=get_casino_menu(),
        )
      else:
        new_m = user["money"] - bet
        update_user_money_and_stats(user_id, money=new_m)
        send_message(
            chat_id,
            f"🎲 Проиграл. Ставка ${bet:,} сгорела...\nБаланс: ${new_m:,}",
            reply_markup=get_casino_menu(),
        )
      return

    elif "job" in state:
      job_data = active_games.pop(user_id)
      correct = job_data["correct"]
      prizes = {"ref": 250, "car": 600, "block": 1000, "fed": 1800}
      prize = prizes.get(job_data["job"], 300)

      if text == correct:
        new_m = user["money"] + prize
        update_user_money_and_stats(user_id, money=new_m)
        send_message(
            chat_id,
            f"🎯 Успех! Выбор ({text}) верный.\nПолучено: **+${prize:,}**! 💸",
            reply_markup=get_work_menu(),
        )
      else:
        send_message(
            chat_id,
            f"💥 Мимо! Правильным ответом был `{correct}`.",
            reply_markup=get_work_menu(),
        )
      return

  if text == "/start":
    send_message(
        chat_id,
        f"Здорово, {message['from'].get('first_name', 'Бро')}! 🤙 Добро"
        " пожаловать в **бот бандит**.",
        reply_markup=get_main_menu(),
    )

  elif text == "⬅️ Назад":
    active_games.pop(user_id, None)
    send_message(chat_id, "Главное меню, бро:", reply_markup=get_main_menu())

  elif text == "👤 Профиль":
    user = get_user(user_id, username)
    send_message(
        chat_id,
        f"📊 **Твой профиль:**\n\n💰 Бахчи: ${user['money']:,}\n🧢 Ранг:"
        f" {user['rank']}\n🛡 Защита: {user['defense']}\n🏢 Бизнесов:"
        f" {len(user['businesses'])}\n🚗 Машин в гараже: {len(user['cars'])}",
        reply_markup=get_main_menu(),
    )

  elif text == "🏆 Топ бандюков":
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, money FROM users ORDER BY money DESC LIMIT 10"
    )
    rows = cursor.fetchall()
    conn.close()
    msg = "🏆 **Топ-10 авторитетов:**\n\n"
    for i, (u_n, mon) in enumerate(rows, 1):
      msg += f"{i}. @{u_n} — ${mon:,}\n"
    send_message(chat_id, msg, reply_markup=get_main_menu())

  elif text.startswith("/admin"):
    parts = text.split()
    if len(parts) > 1 and parts[1] == ADMIN_PASSWORD:
      admin_session.add(user_id)
      send_message(chat_id, "🔓 Админ-панель активна!", reply_markup=get_admin_menu())
    else:
      send_message(chat_id, "❌ Неверный пароль!")

  elif text == "🚪 Выйти из админки":
    admin_session.discard(user_id)
    send_message(chat_id, "Админ-режим отключен.", reply_markup=get_main_menu())

  elif text == "💸 Выдать бабло" and user_id in admin_session:
    active_games[user_id] = {"action": "give_money"}
    send_message(
        chat_id,
        "Введите: `@username сумма`",
        reply_markup={
            "keyboard": [[{"text": "⬅️ Назад"}]],
            "resize_keyboard": True,
        },
    )

  elif text == "🏢 Выдать бизнес" and user_id in admin_session:
    active_games[user_id] = {"action": "give_biz"}
    send_message(
        chat_id,
        "Введите: `@username ключ`",
        reply_markup={
            "keyboard": [[{"text": "⬅️ Назад"}]],
            "resize_keyboard": True,
        },
    )

  elif text == "📢 Сделать рассылку" and user_id in admin_session:
    active_games[user_id] = {"action": "broadcast"}
    send_message(
        chat_id,
        "Отправьте текст для рассылки:",
        reply_markup={
            "keyboard": [[{"text": "⬅️ Назад"}]],
            "resize_keyboard": True,
        },
    )

  elif text == "🚗 Автосалон":
    show_car_page(chat_id, index=0)

  elif text == "💼 Работа":
    send_message(chat_id, "Выбери тему работы:", reply_markup=get_work_menu())

  elif text == "🤝 Раскидать рефки":
    variants = ["💬 Спам в ЛС", "📢 Пост в чате", "🚪 Зайти в комменты"]
    active_games[user_id] = {"job": "ref", "correct": random.choice(variants)}
    send_message(
        chat_id,
        "📱 Куда закинешь ссылку?",
        reply_markup={
            "keyboard": [
                [
                    {"text": "💬 Спам в ЛС"},
                    {"text": "📢 Пост в чате"},
                    {"text": "🚪 Зайти в комменты"},
                ],
                [{"text": "⬅️ Назад"}],
            ],
            "resize_keyboard": True,
        },
    )

  elif text == "🚕 Угон тачки":
    variants = ["🔴 Красный провод", "🔵 Синий провод", "🟢 Зеленый провод"]
    active_games[user_id] = {"job": "car", "correct": random.choice(variants)}
    send_message(
        chat_id,
        "🚗 Какой провод дергать?",
        reply_markup={
            "keyboard": [
                [
                    {"text": "🔴 Красный провод"},
                    {"text": "🔵 Синий провод"},
                    {"text": "🟢 Зеленый провод"},
                ],
                [{"text": "⬅️ Назад"}],
            ],
            "resize_keyboard": True,
        },
    )

  elif text == "🧱 Стрелка за блок":
    variants = [
        "🛡 Сесть за укрытие",
        "💥 Идти в лобовую",
        "🏃 Обойти с фланга",
    ]
    active_games[user_id] = {"job": "block", "correct": random.choice(variants)}
    send_message(
        chat_id,
        "🧱 Какую тактику выберешь?",
        reply_markup={
            "keyboard": [
                [
                    {"text": "🛡 Сесть за укрытие"},
                    {"text": "💥 Идти в лобовую"},
                    {"text": "🏃 Обойти с фланга"},
                ],
                [{"text": "⬅️ Назад"}],
            ],
            "resize_keyboard": True,
        },
    )

  elif text == "👮 Сходняк":
    variants = [
        "💼 Дать на лапу",
        "🗣 Качать права",
        "🤝 Порешать по понятиям",
    ]
    active_games[user_id] = {"job": "fed", "correct": random.choice(variants)}
    send_message(
        chat_id,
        "👮 Как поведешь себя?",
        reply_markup={
            "keyboard": [
                [
                    {"text": "💼 Дать на лапу"},
                    {"text": "🗣 Качать права"},
                    {"text": "🤝 Порешать по понятиям"},
                ],
                [{"text": "⬅️ Назад"}],
            ],
            "resize_keyboard": True,
        },
    )

  elif text == "🎰 Казино":
    send_message(chat_id, "🎲 Выбирай игру:", reply_markup=get_casino_menu())

  elif text in ["🎲 Сыграть в кости", "🃏 Сыграть в очко"]:
    active_games[user_id] = {"casino": True}
    send_message(
        chat_id,
        "💰 Напиши сумму ставки числом:",
        reply_markup={
            "keyboard": [[{"text": "⬅️ Назад"}]],
            "resize_keyboard": True,
        },
    )

  elif text == "🏢 Бизнесы":
    send_message(
        chat_id, "🏢 **Биржа бизнесов:**", reply_markup=get_business_menu()
    )

  elif text in [
      "🌭 Шаурма ($5k)",
      "🚗 Автомойка ($25k)",
      "💎 Клуб ($100k)",
      "🎰 Казино ($500k)",
  ]:
    mapping = {
        "🌭 Шаурма ($5k)": "shaurma",
        "🚗 Автомойка ($25k)": "carwash",
        "💎 Клуб ($100k)": "club",
        "🎰 Казино ($500k)": "casino_biz",
    }
    b_key = mapping[text]
    cost = BUSINESSES[b_key]["cost"]
    if user["money"] < cost:
      send_message(chat_id, f"❌ Не хватает бабосов! Нужно ${cost:,}.")
    else:
      new_m = user["money"] - cost
      update_user_money_and_stats(user_id, money=new_m)
      add_user_business(user_id, b_key)
      send_message(
          chat_id,
          f"🎉 Куплен бизнес **{BUSINESSES[b_key]['name']}**!",
          reply_markup=get_business_menu(),
      )

  elif text == "💼 Мои бизнесы":
    bizs = user["businesses"]
    if not bizs:
      send_message(chat_id, "У тебя пока нет бизнесов.")
    else:
      from collections import Counter

      counts = Counter(bizs)
      msg = "🏢 **Твои бизнесы:**\n\n"
      total_inc = 0
      for k, cnt in counts.items():
        inc = BUSINESSES[k]["income"] * cnt
        total_inc += inc
        msg += f"• {BUSINESSES[k]['name']} (x{cnt}) — ${inc:,}/час\n"
      msg += f"\n💵 Доход в час: ${total_inc:,}"
      send_message(chat_id, msg)

  elif text == "🛒 Шмотки":
    send_message(chat_id, "🛍 **BB MARKET:**", reply_markup=get_market_menu())

  elif text in ["👕 Шмотка VETEMENTS ($500)", "🛡 Прокачать защиту ($300)"]:
    is_vet = "VETEMENTS" in text
    cost = 500 if is_vet else 300
    if user["money"] < cost:
      send_message(chat_id, f"❌ Не хватает бабосов! Нужно ${cost:,}.")
    else:
      new_m = user["money"] - cost
      if is_vet:
        update_user_money_and_stats(
            user_id, money=new_m, rank="Авторитет в VETEMENTS 🧥"
        )
        send_message(chat_id, f"🔥 Куплен VETEMENTS!", reply_markup=get_market_menu())
      else:
        new_def = user["defense"] + 15
        update_user_money_and_stats(user_id, money=new_m, defense=new_def)
        send_message(
            chat_id,
            f"🛡 Защита прокачана до {new_def}!",
            reply_markup=get_market_menu(),
        )
  else:
    send_message(
        chat_id,
        "Чет непонятная малява. Пользуйся меню или пиши /start, бро.",
        reply_markup=get_main_menu(),
    )


def process_callback(callback):
  query_id = callback["id"]
  data = callback["data"]
  chat_id = callback["message"]["chat"]["id"]
  message_id = callback["message"]["message_id"]
  user_id = callback["from"]["id"]

  if data == "car_exit":
    answer_callback_query(query_id)
    requests.post(
        URL + "deleteMessage", json={"chat_id": chat_id, "message_id": message_id}
    )
    send_message(chat_id, "Главное меню, бро:", reply_markup=get_main_menu())
    return

  if data == "garage_open":
    answer_callback_query(query_id)
    show_garage_page(chat_id, message_id, user_id, index=0)
    return

  if data == "garage_to_shop":
    answer_callback_query(query_id)
    show_car_page(chat_id, message_id, index=0)
    return

  if data.startswith("car_"):
    parts = data.split("_")
    action = parts[1]
    index = int(parts[2])
    if action == "prev":
      show_car_page(chat_id, message_id, index - 1)
    elif action == "next":
      show_car_page(chat_id, message_id, index + 1)
    elif action == "buy":
      key = car_keys[index]
      car = CARS[key]
      user = get_user(user_id)
      if user["money"] < car["cost"]:
        answer_callback_query(
            query_id,
            f"Не хватает бабосов! Нужно ${car['cost']:,}",
            show_alert=True,
        )
        return
      new_m = user["money"] - car["cost"]
      update_user_money_and_stats(user_id, money=new_m)
      add_user_car(user_id, key)
      answer_callback_query(
          query_id, f"🎉 Успешно куплено: {car['name']}!", show_alert=True
      )
      show_car_page(chat_id, message_id, index)
    return

  if data.startswith("gar_"):
    parts = data.split("_")
    action = parts[1]
    if action == "exit":
      answer_callback_query(query_id)
      requests.post(
          URL + "deleteMessage", json={"chat_id": chat_id, "message_id": message_id}
      )
      send_message(chat_id, "Главное меню, бро:", reply_markup=get_main_menu())
      return
    if action in ["prev", "next"]:
      answer_callback_query(query_id)
      show_garage_page(chat_id, message_id, user_id, int(parts[2]))
    elif action == "sell":
      db_id = int(parts[2])
      index = int(parts[3])
      cars_list = get_user_cars_detailed(user_id)
      target = next((c for c in cars_list if c[0] == db_id), None)
      if not target:
        answer_callback_query(query_id, "Слот уже пуст!", show_alert=True)
        return
      _, key = target
      sell_price = int(CARS[key]["cost"] / 2)
      remove_car_by_db_id(db_id)
      user = get_user(user_id)
      new_m = user["money"] + sell_price
      update_user_money_and_stats(user_id, money=new_m)
      answer_callback_query(
          query_id, f"💰 Выручено: ${sell_price:,}!", show_alert=True
      )
      show_garage_page(chat_id, message_id, user_id, index - 1)
    return


def hourly_income_loop():
  while True:
    time.sleep(3600)
    try:
      conn = sqlite3.connect(DB_FILE)
      cursor = conn.cursor()
      cursor.execute("SELECT DISTINCT user_id FROM businesses")
      users = cursor.fetchall()
      for (u_id,) in users:
        cursor.execute(
            "SELECT biz_key FROM businesses WHERE user_id = ?", (u_id,)
        )
        b_keys = [b[0] for b in cursor.fetchall()]
        from collections import Counter

        counts = Counter(b_keys)
        total = sum(
            BUSINESSES[k]["income"] * cnt
            for k, cnt in counts.items()
            if k in BUSINESSES
        )
        if total > 0:
          cursor.execute(
              "UPDATE users SET money = money + ? WHERE user_id = ?",
              (total, u_id),
          )
          conn.commit()
          send_message(
              u_id,
              f"💵 **Пассивный доход!**\nТвои бизнесы принесли **+${total:,}**"
              " за час.",
          )
      conn.close()
      sync_db_to_github()
    except Exception as e:
      print(f"[INCOME ERROR] {e}")


def main():
  init_db()
  print("Запуск бота с автосохранением на GitHub...")
  threading.Thread(target=hourly_income_loop, daemon=True).start()

  try:
    requests.get(URL + "deleteWebhook", params={"drop_pending_updates": True})
  except Exception:
    pass

  offset = 0
  while True:
    try:
      response = requests.get(
          URL + "getUpdates",
          params={"offset": offset, "timeout": 30},
          timeout=35,
      )
      data = response.json()
      if data.get("ok"):
        for update in data.get("result", []):
          offset = update["update_id"] + 1
          if "message" in update:
            process_message(update["message"])
          elif "callback_query" in update:
            process_callback(update["callback_query"])
    except Exception as e:
      print(f"[POLLING ERROR] {e}")
      time.sleep(3)


if __name__ == "__main__":
  main()
