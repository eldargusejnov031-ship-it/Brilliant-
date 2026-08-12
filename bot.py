import os
import time
import random
import sqlite3
import threading

import requests
import telebot
from telebot import types
from flask import Flask, request


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Environment Variables")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден в Environment Variables")


bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


# =========================================================
# HUGGING FACE
# =========================================================

HF_URL = "https://router.huggingface.co/v1/chat/completions"

HF_MODEL = os.getenv(
    "HF_MODEL",
    "openai/gpt-oss-120b:groq"
)

ai_memory = {}


def ask_ai(user_id, question):
    history = ai_memory.setdefault(user_id, [])

    messages = [
        {
            "role": "system",
            "content": (
                "Ты дружелюбный русскоязычный Telegram-бот. "
                "Отвечай понятно, коротко и интересно."
            )
        }
    ]

    messages.extend(history[-10:])

    messages.append({
        "role": "user",
        "content": question
    })

    response = requests.post(
        HF_URL,
        headers={
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "model": HF_MODEL,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        },
        timeout=90
    )

    if response.status_code != 200:
        print("HF ERROR:", response.status_code)
        print(response.text)
        raise RuntimeError("Ошибка Hugging Face")

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    history.append({
        "role": "user",
        "content": question
    })

    history.append({
        "role": "assistant",
        "content": answer
    })

    ai_memory[user_id] = history[-10:]

    return answer


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

db = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    coins INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    messages INTEGER DEFAULT 0,
    last_bonus INTEGER DEFAULT 0
)
""")

db.commit()


def register_user(message):
    user_id = message.from_user.id

    user = db.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not user:
        db.execute(
            """
            INSERT INTO users
            (user_id, name)
            VALUES (?, ?)
            """,
            (
                user_id,
                message.from_user.first_name or "Игрок"
            )
        )
        db.commit()


def get_user(user_id):
    return db.execute(
        """
        SELECT user_id, name, coins, xp,
               messages, last_bonus
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchone()


def add_xp(user_id, amount):
    db.execute(
        "UPDATE users SET xp=xp+? WHERE user_id=?",
        (amount, user_id)
    )
    db.commit()


def add_coins(user_id, amount):
    db.execute(
        "UPDATE users SET coins=coins+? WHERE user_id=?",
        (amount, user_id)
    )
    db.commit()


def add_message(user_id):
    db.execute(
        """
        UPDATE users
        SET messages=messages+1,
            xp=xp+2
        WHERE user_id=?
        """,
        (user_id,)
    )
    db.commit()


# =========================================================
# RUST — ПРЕДМЕТЫ
# =========================================================

# Здесь можешь постепенно добавлять свои предметы.
# Формат:
#
# "id": {
#     "name": "Название",
#     "category": "Категория",
#     "craft": {
#         "Ресурс": количество
#     }
# }

RUST_ITEMS = {
    "campfire": {
        "name": "🔥 Костёр",
        "category": "Постройки",
        "craft": {
            "Дерево": 100
        }
    },

    "furnace": {
        "name": "🔥 Печь",
        "category": "Постройки",
        "craft": {
            "Камень": 200,
            "Дерево": 100
        }
    },

    "box": {
        "name": "📦 Ящик",
        "category": "Хранение",
        "craft": {
            "Дерево": 100
        }
    },

    "stash": {
        "name": "👜 Маленький тайник",
        "category": "Хранение",
        "craft": {
            "Ткань": 10
        }
    },

    "sleeping_bag": {
        "name": "🛏 Спальный мешок",
        "category": "Постройки",
        "craft": {
            "Ткань": 30
        }
    },

    "wood_door": {
        "name": "🚪 Деревянная дверь",
        "category": "Строительство",
        "craft": {
            "Дерево": 100
        }
    },

    "lantern": {
        "name": "🏮 Фонарь",
        "category": "Освещение",
        "craft": {
            "Металлические фрагменты": 20,
            "Ткань": 10
        }
    },

    "planter": {
        "name": "🌱 Горшок",
        "category": "Фермерство",
        "craft": {
            "Дерево": 100
        }
    },

    "sign": {
        "name": "🪧 Табличка",
        "category": "Строительство",
        "craft": {
            "Дерево": 100
        }
    }
}


# =========================================================
# СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ
# =========================================================

search_users = set()
craft_users = {}
game_users = {}


# =========================================================
# КЛАВИАТУРА
# =========================================================

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🔥 Rust",
        "🤖 ИИ"
    )

    keyboard.row(
        "👤 Профиль",
        "🎁 Бонус"
    )

    keyboard.row(
        "🎮 Игры",
        "🛠 Инструменты"
    )

    return keyboard


def rust_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton(
            "📦 Все предметы",
            callback_data="rust_items"
        ),
        types.InlineKeyboardButton(
            "🔎 Поиск",
            callback_data="rust_search"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🔨 Крафт",
            callback_data="rust_craft"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🧱 Строительство",
            callback_data="cat_Строительство"
        ),
        types.InlineKeyboardButton(
            "🏠 Постройки",
            callback_data="cat_Постройки"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📦 Хранение",
            callback_data="cat_Хранение"
        ),
        types.InlineKeyboardButton(
            "🌱 Фермерство",
            callback_data="cat_Фермерство"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="main"
        )
    )

    return keyboard


def items_keyboard(items=None):
    if items is None:
        items = list(RUST_ITEMS.keys())

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    for item_id in items:
        item = RUST_ITEMS[item_id]

        keyboard.add(
            types.InlineKeyboardButton(
                item["name"],
                callback_data=f"item:{item_id}"
            )
        )

    keyboard.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="rust"
        )
    )

    return keyboard


# =========================================================
# /START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    register_user(message)

    bot.send_message(
        message.chat.id,
        "👋 Привет!\n\n"
        "🔥 Добро пожаловать в Rust AI Bot!\n\n"
        "Выбирай раздел:",
        reply_markup=main_keyboard()
    )


# =========================================================
# RUST
# =========================================================

@bot.message_handler(
    func=lambda message: message.text == "🔥 Rust"
)
def rust(message):
    bot.send_message(
        message.chat.id,
        "🔥 RUST\n\nВыбери раздел:",
        reply_markup=rust_keyboard()
    )


# =========================================================
# ИИ
# =========================================================

@bot.message_handler(
    func=lambda message: message.text == "🤖 ИИ"
)
def ai_mode(message):
    bot.send_message(
        message.chat.id,
        "🤖 ИИ готов.\n\n"
        "Просто напиши свой вопрос."
    )


# =========================================================
# ПРОФИЛЬ
# =========================================================

@bot.message_handler(
    func=lambda message: message.text == "👤 Профиль"
)
def profile(message):
    register_user(message)

    user = get_user(message.from_user.id)

    level = (user[3] // 100) + 1

    bot.send_message(
        message.chat.id,
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"🧑 Имя: {user[1]}\n"
        f"⭐ Уровень: {level}\n"
        f"✨ XP: {user[3]}\n"
        f"🪙 Монеты: {user[2]}\n"
        f"💬 Сообщений: {user[4]}"
    )


# =========================================================
# БОНУС
# =========================================================

@bot.message_handler(
    func=lambda message: message.text == "🎁 Бонус"
)
def bonus(message):
    register_user(message)

    user_id = message.from_user.id
    user = get_user(user_id)

    now = int(time.time())

    if now - user[5] < 86400:
        remaining = 86400 - (now - user[5])

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        bot.send_message(
            message.chat.id,
            f"⏳ Бонус уже получен.\n"
            f"Следующий через {hours}ч {minutes}мин."
        )

        return

    coins = random.randint(50, 150)
    xp = random.randint(10, 30)

    db.execute(
        """
        UPDATE users
        SET coins=coins+?,
            xp=xp+?,
            last_bonus=?
        WHERE user_id=?
        """,
        (
            coins,
            xp,
            now,
            user_id
        )
    )

    db.commit()

    bot.send_message(
        message.chat.id,
        "🎁 БОНУС ПОЛУЧЕН!\n\n"
        f"🪙 +{coins} монет\n"
        f"⭐ +{xp} XP"
    )


# =========================================================
# ИГРЫ
# =========================================================

@bot.message_handler(
    func=lambda message: message.text == "🎮 Игры"
)
def games(message):
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "🎲 Угадай число",
            callback_data="game_number"
        )
    )

    bot.send_message(
        message.chat.id,
        "🎮 ИГРЫ",
        reply_markup=keyboard
    )


# =========================================================
# CALLBACKS
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    bot.answer_callback_query(call.id)

    # Главное меню
    if data == "main":
        bot.send_message(
            chat_id,
            "🏠 Главное меню:",
            reply_markup=main_keyboard()
        )
        return

    # Rust
    if data == "rust":
        bot.edit_message_text(
            "🔥 RUST\n\nВыбери раздел:",
            chat_id,
            call.message.message_id,
            reply_markup=rust_keyboard()
        )
        return

    # Все предметы
    if data == "rust_items" or data == "rust_craft":
        bot.edit_message_text(
            "📦 ПРЕДМЕТЫ RUST\n\nВыбери предмет:",
            chat_id,
            call.message.message_id,
            reply_markup=items_keyboard()
        )
        return

    # Поиск
    if data == "rust_search":
        search_users.add(user_id)

        bot.send_message(
            chat_id,
            "🔎 Напиши название предмета:"
        )
        return

    # Категория
    if data.startswith("cat_"):
        category = data[4:]

        found = [
            item_id
            for item_id, item in RUST_ITEMS.items()
            if item["category"] == category
        ]

        if not found:
            bot.answer_callback_query(
                call.id,
                "В этой категории пока нет предметов.",
                show_alert=True
            )
            return

        bot.edit_message_text(
            f"📂 {category}\n\nВыбери предмет:",
            chat_id,
            call.message.message_id,
            reply_markup=items_keyboard(found)
        )
        return

    # Предмет
    if data.startswith("item:"):
        item_id = data[5:]

        if item_id not in RUST_ITEMS:
            return

        item = RUST_ITEMS[item_id]

        text = (
            f"{item['name']}\n\n"
            f"📂 Категория: {item['category']}\n\n"
            "🔨 КРАФТ НА 1 ШТУКУ:\n"
        )

        for resource, amount in item["craft"].items():
            text += f"• {resource}: {amount}\n"

        keyboard = types.InlineKeyboardMarkup()

        keyboard.add(
            types.InlineKeyboardButton(
                "🧮 Рассчитать количество",
                callback_data=f"calculate:{item_id}"
            )
        )

        keyboard.add(
            types.InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="rust_items"
            )
        )

        bot.edit_message_text(
            text,
            chat_id,
            call.message.message_id,
            reply_markup=keyboard
        )
        return

    # Калькулятор
    if data.startswith("calculate:"):
        item_id = data[10:]

        if item_id not in RUST_ITEMS:
            return

        craft_users[user_id] = item_id

        bot.send_message(
            chat_id,
            f"🧮 {RUST_ITEMS[item_id]['name']}\n\n"
            "Напиши, сколько штук нужно изготовить:"
        )
        return

    # Игра
    if data == "game_number":
        game_users[user_id] = random.randint(1, 10)

        bot.send_message(
            chat_id,
            "🎲 Я загадал число от 1 до 10.\n"
            "Попробуй угадать!"
        )
        return


# =========================================================
# ТЕКСТ
# =========================================================

@bot.message_handler(content_types=["text"])
def text_handler(message):

    register_user(message)

    user_id = message.from_user.id
    text = message.text.strip()

    # Меню уже обработано выше
    if text in [
        "🔥 Rust",
        "🤖 ИИ",
        "👤 Профиль",
        "🎁 Бонус",
        "🎮 Игры",
        "🛠 Инструменты"
    ]:
        return

    # Игра
    if user_id in game_users:

        try:
            number = int(text)
        except ValueError:
            bot.reply_to(
                message,
                "❌ Введи число от 1 до 10."
            )
            return

        answer = game_users[user_id]

        if number == answer:

            del game_users[user_id]

            add_coins(user_id, 50)
            add_xp(user_id, 20)

            bot.reply_to(
                message,
                "🎉 Правильно!\n\n"
                "🪙 +50 монет\n"
                "⭐ +20 XP"
            )

        elif number < answer:

            bot.reply_to(
                message,
                "⬆️ Моё число больше."
            )

        else:

            bot.reply_to(
                message,
                "⬇️ Моё число меньше."
            )

        return

    # Поиск
    if user_id in search_users:

        search_users.remove(user_id)

        query = text.lower()

        found = []

        for item_id, item in RUST_ITEMS.items():

            if (
                query in item["name"].lower()
                or query in item["category"].lower()
                or query in item_id.lower()
            ):
                found.append(item_id)

        if not found:

            bot.reply_to(
                message,
                "❌ Ничего не найдено."
            )

        else:

            bot.send_message(
                message.chat.id,
                "🔎 НАЙДЕНО:",
                reply_markup=items_keyboard(found)
            )

        return

    # Калькулятор крафта
    if user_id in craft_users:

        item_id = craft_users[user_id]

        try:
            amount = int(text)

            if amount <= 0:
                raise ValueError

        except ValueError:

            bot.reply_to(
                message,
                "❌ Напиши положительное целое число."
            )
            return

        del craft_users[user_id]

        item = RUST_ITEMS[item_id]

        result = (
            "🧮 РАСЧЁТ КРАФТА\n\n"
            f"{item['name']}\n"
            f"📦 Количество: {amount} шт.\n\n"
            "📋 ВСЕГО НУЖНО:\n"
        )

        for resource, one_amount in item["craft"].items():

            total = one_amount * amount

            result += (
                f"• {resource}: {total}\n"
            )

        add_xp(user_id, 5)

        bot.send_message(
            message.chat.id,
            result
        )

        return

    # Обычный текст → ИИ
    add_message(user_id)

    try:

        bot.send_chat_action(
            message.chat.id,
            "typing"
        )

        answer = ask_ai(
            user_id,
            text
        )

        bot.reply_to(
            message,
            answer
        )

    except Exception as error:

        print("AI ERROR:", error)

        bot.reply_to(
            message,
            "❌ ИИ временно не отвечает.\n\n"
            "Проверь HF_TOKEN и модель Hugging Face."
        )


# =========================================================
# RENDER
# =========================================================

@app.route("/", methods=["GET"])
def index():
    return "Rust AI Bot is running!", 200


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def telegram_webhook():

    if request.headers.get("content-type") == "application/json":

        update = telebot.types.Update.de_json(
            request.get_data().decode("utf-8")
        )

        bot.process_new_updates([update])

        return "OK", 200

    return "Bad Request", 400


# =========================================================
# WEBHOOK SETUP
# =========================================================

def setup_webhook():

    time.sleep(3)

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if not render_url:
        print(
            "⚠️ RENDER_EXTERNAL_URL не найден."
        )
        return

    webhook_url = (
        render_url.rstrip("/")
        + "/webhook"
    )

    try:

        bot.remove_webhook()

        time.sleep(1)

        bot.set_webhook(
            url=webhook_url
        )

        print("==============================")
        print("🤖 RUST AI BOT ЗАПУЩЕН")
        print("🔥 Rust: OK")
        print("🧠 Hugging Face: OK")
        print("🌐 Webhook:", webhook_url)
        print("==============================")

    except Exception as error:

        print(
            "❌ WEBHOOK ERROR:",
            error
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    threading.Thread(
        target=setup_webhook,
        daemon=True
    ).start()

    print(
        f"?
