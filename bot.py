import os
import random
import sqlite3
import time
import requests
import telebot

from telebot import types


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "openai/gpt-oss-120b:groq"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Environment Variables")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден в Environment Variables")

bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "bot.db"


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    coins INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    messages INTEGER DEFAULT 0,
    last_bonus INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS achievements (
    user_id INTEGER,
    achievement TEXT,
    UNIQUE(user_id, achievement)
)
""")

db.commit()


# ============================================================
# AI MEMORY
# ============================================================

ai_memory = {}

MAX_MEMORY = 10


def ask_ai(user_id, text):

    if user_id not in ai_memory:
        ai_memory[user_id] = []

    messages = [
        {
            "role": "system",
            "content": (
                "Ты дружелюбный русскоязычный Telegram-бот. "
                "Отвечай понятно, интересно и без лишней воды. "
                "Если пользователь пишет на другом языке — отвечай "
                "на этом языке."
            )
        }
    ]

    messages.extend(ai_memory[user_id])

    messages.append({
        "role": "user",
        "content": text
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
            "max_tokens": 1200,
            "temperature": 0.7
        },
        timeout=90
    )

    if response.status_code != 200:
        print("HF ERROR:", response.status_code)
        print(response.text)
        raise RuntimeError("Hugging Face API error")

    data = response.json()

    answer = data["choices"][0]["message"]["content"]

    ai_memory[user_id].append({
        "role": "user",
        "content": text
    })

    ai_memory[user_id].append({
        "role": "assistant",
        "content": answer
    })

    ai_memory[user_id] = ai_memory[user_id][-MAX_MEMORY:]

    return answer


# ============================================================
# USER SYSTEM
# ============================================================

def register_user(message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    if cursor.fetchone() is None:

        cursor.execute(
            """
            INSERT INTO users
            (user_id, name, username)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                message.from_user.first_name or "Игрок",
                message.from_user.username or ""
            )
        )

        db.commit()


def get_user(user_id):

    cursor.execute(
        """
        SELECT user_id, name, username,
               coins, xp, messages,
               last_bonus, streak
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    return cursor.fetchone()


def add_xp(user_id, amount):

    cursor.execute(
        "UPDATE users SET xp=xp+? WHERE user_id=?",
        (amount, user_id)
    )

    db.commit()


def add_coins(user_id, amount):

    cursor.execute(
        "UPDATE users SET coins=coins+? WHERE user_id=?",
        (amount, user_id)
    )

    db.commit()


def add_message(user_id):

    cursor.execute(
        """
        UPDATE users
        SET messages=messages+1, xp=xp+2
        WHERE user_id=?
        """,
        (user_id,)
    )

    db.commit()


def level_from_xp(xp):

    return max(1, xp // 100 + 1)


# ============================================================
# ACHIEVEMENTS
# ============================================================

ACHIEVEMENTS = {
    "first_message": "🌱 Новичок",
    "100_messages": "💬 Болтун",
    "rust_10": "🔥 Исследователь Rust",
    "daily_7": "🎁 Постоянный",
}


def give_achievement(user_id, key):

    if key not in ACHIEVEMENTS:
        return False

    try:

        cursor.execute(
            """
            INSERT INTO achievements
            (user_id, achievement)
            VALUES (?, ?)
            """,
            (user_id, key)
        )

        db.commit()

        return True

    except sqlite3.IntegrityError:
        return False


def get_achievements(user_id):

    cursor.execute(
        """
        SELECT achievement
        FROM achievements
        WHERE user_id=?
        """,
        (user_id,)
    )

    return [x[0] for x in cursor.fetchall()]


# ============================================================
# RUST DATABASE
# ============================================================

RUST_ITEMS = {

    "building_plan": {
        "name": "📐 План строительства",
        "category": "Строительство",
        "craft": {
            "Дерево": 20
        }
    },

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

    "wood_box": {
        "name": "📦 Деревянный ящик",
        "category": "Хранение",
        "craft": {
            "Дерево": 100
        }
    },

    "small_stash": {
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

    "wooden_door": {
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
    },

    "tool_cupboard": {
        "name": "🗄 Шкаф для инструментов",
        "category": "Строительство",
        "craft": {
            "Дерево": 1000
        }
    }
}


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🤖 ИИ",
        "🔥 Rust"
    )

    kb.row(
        "🎮 Игры",
        "🏆 Достижения"
    )

    kb.row(
        "🎁 Бонус",
        "👤 Профиль"
    )

    kb.row(
        "🛠 Инструменты",
        "⚙️ Настройки"
    )

    return kb


# ============================================================
# RUST MENU
# ============================================================

def rust_menu():

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            "📦 Предметы",
            callback_data="rust_items"
        ),
        types.InlineKeyboardButton(
            "🔎 Поиск",
            callback_data="rust_search"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🔨 Крафт",
            callback_data="rust_craft"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🧱 Строительство",
            callback_data="rust_cat_Строительство"
        ),
        types.InlineKeyboardButton(
            "🏠 Постройки",
            callback_data="rust_cat_Постройки"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📦 Хранение",
            callback_data="rust_cat_Хранение"
        ),
        types.InlineKeyboardButton(
            "🌱 Фермерство",
            callback_data="rust_cat_Фермерство"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="home"
        )
    )

    return kb


# ============================================================
# RUST ITEMS MENU
# ============================================================

def rust_items_menu(items=None):

    if items is None:
        items = RUST_ITEMS.keys()

    kb = types.InlineKeyboardMarkup(row_width=2)

    for key in items:

        kb.add(
            types.InlineKeyboardButton(
                RUST_ITEMS[key]["name"],
                callback_data=f"rust_item_{key}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Rust",
            callback_data="rust"
        )
    )

    return kb


# ============================================================
# ITEM CARD
# ============================================================

def item_text(key):

    item = RUST_ITEMS[key]

    text = (
        f"{item['name']}\n\n"
        f"📂 Категория: {item['category']}\n\n"
        "🔨 Крафт:\n"
    )

    for resource, amount in item["craft"].items():

        text += f"• {resource}: {amount}\n"

    return text


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):

    register_user(message)

    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать!\n\n"
        "Это большая версия моего бота.\n"
        "Выбирай раздел 👇",
        reply_markup=main_menu()
    )


# ============================================================
# AI
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🤖 ИИ")
def ai_button(message):

    bot.send_message(
        message.chat.id,
        "🤖 Напиши мне сообщение — отвечу через Hugging Face."
    )


# ============================================================
# RUST
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🔥 Rust")
def rust_button(message):

    bot.send_message(
        message.chat.id,
        "🔥 RUST\n\nВыбери раздел:",
        reply_markup=rust_menu()
    )


# ============================================================
# PROFILE
# ============================================================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):

    register_user(message)

    user = get_user(message.from_user.id)

    level = level_from_xp(user[4])

    achievements = get_achievements(
        message.from_user.id
    )

    text = (
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"🧑 Имя: {user[1]}\n"
        f"⭐ Уровень: {level}\n"
        f"✨ XP: {user[4]}\n"
        f"🪙 Монеты: {user[3]}\n"
        f"💬 Сообщений: {user[5]}\n"
        f"🔥 Серия: {user[7]} дней\n"
        f"🏆 Достижений: {len(achievements)}"
    )

    bot.send_message(
        message.chat.id,
        text
    )


# ============================================================
# ACHIEVEMENTS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🏆 Достижения")
def achievements(message):

    keys = get_achievements(
        message.from_user.id
    )

    text = "🏆 ДОСТИЖЕНИЯ\n\n"

    for key, name in ACHIEVEMENTS.items():

        if key in keys:
            text += f"✅ {name}\n"
        else:
            text += f"🔒 {name}\n"

    bot.send_message(
        message.chat.id,
        text
    )


# ============================================================
# DAILY BONUS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🎁 Бонус")
def daily_bonus(message):

    register_user(message)

    user_id = message.from_user.id
    user = get_user(user_id)

    now = int(time.time())
    last_bonus = user[6]

    if now - last_bonus < 86400:

        remaining = 86400 - (now - last_bonus)

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        bot.send_message(
            message.chat.id,
            f"⏳ Бонус уже получен.\n"
            f"Следующий через {hours}ч {minutes}мин."
        )

        return

    reward_coins = random.randint(50, 150)
    reward_xp = random.randint(10, 30)

    streak = user[7] + 1

    cursor.execute(
        """
        UPDATE users
        SET coins=coins+?,
            xp=xp+?,
            last_bonus=?,
            streak=?
        WHERE user_id=?
        """,
        (
            reward_coins,
            reward_xp,
            now,
            streak,
            user_id
        )
    )

    db.commit()

    if streak >= 7:
        give_achievement(
            user_id,
            "daily_7"
        )

    bot.send_message(
        message.chat.id,
        "🎁 ЕЖЕДНЕВНЫЙ БОНУС\n\n"
        f"🪙 +{reward_coins} монет\n"
        f"⭐ +{reward_xp} XP\n"
        f"🔥 Серия: {streak} дней"
    )


# ============================================================
# GAMES
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🎮 Игры")
def games(message):

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎲 Угадай число",
            callback_data="game_number"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "✂️ Камень / Ножницы / Бумага",
            callback_data="game_rps"
        )
    )

    bot.send_message(
        message.chat.id,
        "🎮 ИГРЫ\n\nВыбирай игру:",
        reply_markup=kb
    )


# ============================================================
# TOOLS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "🛠 Инструменты")
def tools(message):

    bot.send_message(
        message.chat.id,
        "🛠 ИНСТРУМЕНТЫ\n\n"
        "🔢 Генератор случайного числа\n"
        "🧮 Калькулятор\n"
        "🎯 Случайный выбор"
    )


# ============================================================
# SETTINGS
# ============================================================

@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def settings(message):

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🧹 Очистить память ИИ",
            callback_data="clear_ai"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="home"
        )
    )

    bot.send_message(
        message.chat.id,
        "⚙️ НАСТРОЙКИ",
        reply_markup=kb
    )


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    data = call.data
    user_id = call.from_user.id

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    # HOME
    if data == "home":

        bot.send_message(
            call.message.chat.id,
            "🏠 Главное меню:",
            reply_markup=main_menu()
        )

        return

    # CLEAR AI
    if data == "clear_ai":

        ai_memory.pop(
            user_id,
            None
        )

        bot.answer_callback_query(
            call.id,
            "Память ИИ очищена!",
            show_alert=True
        )

        return

    # RUST
    if data == "rust":

        bot.edit_message_text(
            "🔥 RUST\n\nВыбери раздел:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=rust_menu()
        )

        return

    # ITEMS
    if data == "rust_items":

        bot.edit_message_text(
            "📦 ВСЕ ПРЕДМЕТЫ\n\nВыбери предмет:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=rust_items_menu()
        )

        return

    # CRAFT
    if data == "rust_craft":

        bot.edit_message_text(
            "🔨 КРАФТ\n\nВыбери предмет:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=rust_items_menu()
        )

        return

    # SEARCH
    if data == "rust_search":

        search_mode[user_id] = True

        bot.send_message(
            call.message.chat.id,
            "🔎 Напиши название предмета:"
        )

        return

    # CATEGORY
    if data.startswith("rust_cat_"):

        category = data.replace(
            "rust_cat_",
            "",
            1
        )

        found = []

        for key, item in RUST_ITEMS.items():

            if item["category"] == category:
                found.append(key)

        bot.edit_message_text(
            f"📂 {category}\n\n"
            "Выбери предмет:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=rust_items_menu(found)
        )

        return

    # ITEM
    if data.startswith("rust_item_"):

        key = data.replace(
            "rust_item_",
            "",
            1
        )

        if key not in RUST_ITEMS:
            return

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "🧮 Рассчитать количество",
                callback_data=f"calc_{key}"
            )
        )

        kb.add(
            types.InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="rust_items"
            )
        )

        bot.edit_message_text(
            item_text(key),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )

        return

    # CALCULATOR
    if data.startswith("calc_"):

        key = data.replace(
            "calc_",
            "",
            1
        )

        calc_mode[user_id] = key

        bot.send_message(
            call.message.chat.id,
            f"{RUST_ITEMS[key]['name']}\n\n"
            "🧮 Сколько штук нужно?\n"
            "Напиши число:"
        )

        return

    # GAME NUMBER
    if data == "game_number":

        game_number[user_id] = random.randint(
            1,
            10
        )

        bot.send_message(
            call.message.chat.id,
            "🎲 Я загадал число от 1 до 10.\n"
            "Пиши свой вариант!"
        )

        return

    # GAME RPS
    if data == "game_rps":

        kb = types.InlineKeyboardMarkup()

        kb.add(
            types.InlineKeyboardButton(
                "🪨 Камень",
                callback_data="rps_rock"
            ),
            types.InlineKeyboardButton(
                "📄 Бумага",
                callback_data="rps_paper"
            ),
            types.InlineKeyboardButton(
                "✂️ Ножницы",
                callback_data="rps_scissors"
            )
        )

        bot.send_message(
            call.message.chat.id,
            "🎮 Выбирай:",
            reply_markup=kb
        )

        return

    # RPS
    if data.startswith("rps_"):

        user_cho
