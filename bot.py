import os
import json
import time
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATA_FILE = "data.json"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Environment Variables")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден в Environment Variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

db_lock = threading.Lock()


# ============================================================
# БАЗА
# ============================================================

def default_db():
    return {
        "users": {},
        "videos": {},
        "tasks": {
            "daily": {
                "name": "Зайди в бота",
                "reward": 5
            },
            "activity": {
                "name": "Сыграй 3 раза",
                "reward": 15
            },
            "winner": {
                "name": "Выиграй 5 игр",
                "reward": 30
            }
        }
    }


def load_db():
    if not os.path.exists(DATA_FILE):
        return default_db()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        base = default_db()

        for key in base:
            if key not in data:
                data[key] = base[key]

        return data

    except Exception as e:
        print("Ошибка загрузки базы:", e)
        return default_db()


db = load_db()


def save_db():
    with db_lock:
        tmp = DATA_FILE + ".tmp"

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                db,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(tmp, DATA_FILE)


# ============================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================

def get_user(user_id, name=None, username=None):

    uid = str(user_id)

    if uid not in db["users"]:

        db["users"][uid] = {
            "id": int(user_id),
            "name": name or "Игрок",
            "username": username or "",

            "crystals": 0,
            "xp": 0,
            "level": 1,

            "games": 0,
            "wins": 0,
            "losses": 0,

            "streak": 0,
            "best_streak": 0,

            "activity": 0,

            "last_bonus": 0,

            "completed_tasks": [],

            "purchased_videos": [],

            "achievements": [],

            "created": int(time.time())
        }

        save_db()

    user = db["users"][uid]

    if name:
        user["name"] = name

    if username is not None:
        user["username"] = username

    return user


def is_admin(user_id):
    return ADMIN_ID != 0 and int(user_id) == ADMIN_ID


# ============================================================
# XP / УРОВЕНЬ
# ============================================================

def xp_for_level(level):
    return level * 100


def add_xp(user, amount):

    user["xp"] += amount

    messages = []

    while user["xp"] >= xp_for_level(user["level"]):

        user["xp"] -= xp_for_level(user["level"])
        user["level"] += 1

        reward = user["level"] * 5
        user["crystals"] += reward

        messages.append(
            f"🎉 Новый уровень: <b>{user['level']}</b>!\n"
            f"💎 Бонус: +{reward}"
        )

    return messages


# ============================================================
# ДОСТИЖЕНИЯ
# ============================================================

def check_achievements(user):

    achievements = []

    checks = [
        ("first_game", "🎮 Первая игра", user["games"] >= 1),
        ("first_win", "🏆 Первая победа", user["wins"] >= 1),
        ("ten_games", "🎮 10 игр", user["games"] >= 10),
        ("fifty_games", "🎮 50 игр", user["games"] >= 50),
        ("ten_wins", "🏆 10 побед", user["wins"] >= 10),
        ("hundred_xp", "⭐ 100 XP", user["level"] >= 2),
        ("streak5", "🔥 Серия из 5", user["best_streak"] >= 5),
    ]

    for aid, name, condition in checks:

        if condition and aid not in user["achievements"]:

            user["achievements"].append(aid)
            user["crystals"] += 10

            achievements.append(
                f"🏅 <b>{name}</b>\n"
                f"💎 Награда: +10"
            )

    return achievements


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard(user_id):

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            "🤖 ИИ",
            callback_data="ai"
        ),
        types.InlineKeyboardButton(
            "🎮 Игры",
            callback_data="games"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "💎 Кристаллы",
            callback_data="crystals"
        ),
        types.InlineKeyboardButton(
            "🎯 Задания",
            callback_data="tasks"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🎬 Видео",
            callback_data="videos"
        ),
        types.InlineKeyboardButton(
            "🏆 ТОП",
            callback_data="top"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "👤 Профиль",
            callback_data="profile"
        ),
        types.InlineKeyboardButton(
            "🎁 Бонус",
            callback_data="bonus"
        )
    )

    if is_admin(user_id):
        kb.add(
            types.InlineKeyboardButton(
                "👑 Админка",
                callback_data="admin"
            )
        )

    return kb


def back_menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Главное меню",
            callback_data="main"
        )
    )

    return kb


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):

    user = get_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username
    )

    user["activity"] += 1

    save_db()

    bot.send_message(
        message.chat.id,
        f"👋 <b>Привет, {user['name']}!</b>\n\n"
        "🔥 Добро пожаловать!\n\n"
        "Здесь тебя ждут:\n"
        "🤖 ИИ\n"
        "🎮 игры\n"
        "💎 кристаллы\n"
        "🎯 задания\n"
        "🎬 магазин видео\n"
        "🏆 рейтинги\n"
        "🏅 достижения\n"
        "🎁 ежедневные бонусы\n\n"
        "Выбирай раздел 👇",
        reply_markup=main_keyboard(message.from_user.id)
    )


# ============================================================
# ИГРЫ
# ============================================================

def games_keyboard():

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            "🪙 Монетка",
            callback_data="game_coin"
        ),
        types.InlineKeyboardButton(
            "🎲 Кубик",
            callback_data="game_dice"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🔢 Угадай число",
            callback_data="game_number"
        ),
        types.InlineKeyboardButton(
            "🎰 Слоты",
            callback_data="game_slots"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏆 Моя статистика",
            callback_data="game_stats"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="main"
        )
    )

    return kb


# ============================================================
# ИГРА: МОНЕТКА
# ============================================================

def coin_keyboard():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🦅 Орёл",
            callback_data="coin_heads"
        ),
        types.InlineKeyboardButton(
            "🪙 Решка",
            callback_data="coin_tails"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Игры",
            callback_data="games"
        )
    )

    return kb


# ============================================================
# ИГРА: КУБИК
# ============================================================

def dice_keyboard():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "1️⃣",
            callback_data="dice_1"
        ),
        types.InlineKeyboardButton(
            "2️⃣",
            callback_data="dice_2"
        ),
        types.InlineKeyboardButton(
            "3️⃣",
            callback_data="dice_3"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "4️⃣",
            callback_data="dice_4"
        ),
        types.InlineKeyboardButton(
            "5️⃣",
            callback_data="dice_5"
        ),
        types.InlineKeyboardButton(
            "6️⃣",
            callback_data="dice_6"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Игры",
            callback_data="games"
        )
    )

    return kb


# ============================================================
# ИГРА: ЧИСЛО
# ============================================================

def number_keyboard():

    kb = types.InlineKeyboardMarkup(row_width=3)

    for i in range(1, 11):

        kb.insert(
            types.InlineKeyboardButton(
                str(i),
                callback_data=f"number_{i}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Игры",
            callback_data="games"
        )
    )

    return kb


# ============================================================
# ИГРА: СЛОТЫ
# ============================================================

def slots_keyboard():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎰 Крутить!",
            callback_data="slots_spin"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Игры",
            callback_data="games"
        )
    )

    return kb


# ============================================================
# CALLBACKS
# ============================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    user_id = call.from_user.id

    user = get_user(
        user_id,
        call.from_user.first_name,
        call.from_user.username
    )

    data = call.data

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    # --------------------------------------------------------
    # MAIN
    # --------------------------------------------------------

    if data == "main":

        bot.edit_message_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выбирай раздел:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_keyboard(user_id)
        )

    # --------------------------------------------------------
    # ИГРЫ
    # --------------------------------------------------------

    elif data == "games":

        bot.edit_message_text(
            "🎮 <b>Игры</b>\n\n"
            "Играй, получай XP и соревнуйся с другими.\n\n"
            "💎 Здесь нет ставок на реальные деньги.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_keyboard()
        )

    # --------------------------------------------------------
    # МОНЕТКА
    # --------------------------------------------------------

    elif data == "game_coin":

        bot.edit_message_text(
            "🪙 <b>Монетка</b>\n\n"
            "Выбери сторону:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=coin_keyboard()
        )

    elif data in ("coin_heads", "coin_tails"):

        choice = (
            "heads"
            if data == "coin_heads"
            else "tails"
        )

        result = random.choice(
            ["heads", "tails"]
        )

        user["games"] += 1

        if choice == result:

            reward = random.randint(5, 12)

            user["wins"] += 1
            user["streak"] += 1

            user["best_streak"] = max(
                user["best_streak"],
                user["streak"]
            )

            user["crystals"] += reward

            xp_messages = add_xp(user, 10)
            achievements = check_achievements(user)

            result_text = (
                "🎉 <b>Ты угадал!</b>\n"
                f"💎 +{reward}\n"
                "⭐ +10 XP"
            )

        else:

            user["losses"] += 1
            user["streak"] = 0

            add_xp(user, 3)
            achievements = check_achievements(user)

            result_text = (
                "😅 Не угадал!\n"
                "⭐ +3 XP за игру"
            )

        save_db()

        bot.edit_message_text(
            "🪙 <b>Монетка</b>\n\n"
            f"Твой выбор: "
            f"{'🦅 Орёл' if choice == 'heads' else '🪙 Решка'}\n"
            f"Выпало: "
            f"{'🦅 Орёл' if result == 'heads' else '🪙 Решка'}\n\n"
            f"{result_text}\n\n"
            f"💎 Баланс: {user['crystals']}\n"
            f"🔥 Серия: {user['streak']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=coin_keyboard()
        )

    # --------------------------------------------------------
    # КУБИК
    # --------------------------------------------------------

    elif data == "game_dice":

        bot.edit_message_text(
            "🎲 <b>Угадай число</b>\n\n"
            "Какое число выпадет?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=dice_keyboard()
        )

    elif data.startswith("dice_"):

        chosen = int(data.split("_")[1])
        result = random.randint(1, 6)

        user["games"] += 1

        if chosen == result:

            reward = 15

            user["wins"] += 1
            user["streak"] += 1
            user["best_streak"] = max(
                user["best_streak"],
                user["streak"]
            )

            user["crystals"] += reward

            add_xp(user, 15)

            text = (
                "🎉 <b>Точно!</b>\n\n"
                f"🎲 Выпало: <b>{result}</b>\n"
                f"💎 +{reward}"
            )

        else:

            user["losses"] += 1
            user["streak"] = 0

            add_xp(user, 3)

            text = (
                "😅 Не угадал!\n\n"
                f"🎲 Выпало: <b>{result}</b>\n"
                "⭐ +3 XP"
            )

        check_achievements(user)
        save_db()

        bot.edit_message_text(
            text +
            f"\n\n💎 Баланс: {user['crystals']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=dice_keyboard()
        )

    # --------------------------------------------------------
    # ЧИСЛО
    # --------------------------------------------------------

    elif data == "game_number":

        user["number_game"] = random.randint(1, 10)
        save_db()

        bot.edit_message_text(
            "🔢 <b>Угадай число</b>\n\n"
            "Я загадал число от 1 до 10.\n"
            "Попробуй угадать:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=number_keyboard()
        )

    elif data.startswith("number_"):

        chosen = int(data.split("_")[1])

        secret = user.get(
            "number_game",
            random.randint(1, 10)
        )

        user["games"] += 1

        if chosen == secret:

            reward = 20

            user["wins"] += 1
            user["streak"] += 1
            user["best_streak"] = max(
                user["best_streak"],
                user["streak"]
            )

            user["crystals"] += reward

            add_xp(user, 20)

            text = (
                "🎯 <b>Ты угадал!</b>\n\n"
                f"🔢 Число: <b>{secret}</b>\n"
                f"💎 +{reward}\n"
                "⭐ +20 XP"
            )

        else:

            user["losses"] += 1
            user["streak"] = 0

            add_xp(user, 3)

            text = (
                "❌ Не угадал!\n\n"
                f"Я загадал: <b>{secret}</b>\n"
                "⭐ +3 XP"
            )

        user.pop("number_game", None)

        check_achievements(user)
        save_db()

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=number_keyboard()
        )

    # --------------------------------------------------------
    # СЛОТЫ
    # --------------------------------------------------------

    elif data == "game_slots":

        bot.edit_message_text(
            "🎰 <b>Слоты</b>\n\n"
            "Нажми кнопку и посмотри комбинацию!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=slots_keyboard()
        )

    elif data == "slots_spin":

        symbols = [
            "🍒",
            "🍋",
            "🍉",
            "⭐",
            "7️⃣"
        ]

        a = random.choice(symbols)
        b = random.choice(symbols)
        c = random.choice(symbols)

        user["games"] += 1

        if a == b == c:

            reward = 50

            user["wins"] += 1
            user["streak"] += 1

            user["best_streak"] = max(
                user["best_streak"],
                user["streak"]
            )

            user["crystals"] += reward

            add_xp(user, 25)

            result = (
                "🔥 <b>ДЖЕКПОТ!</b>\n"
                f"💎 +{reward}"
            )

        elif a == b or b == c or a == c:

            reward = 10

            user["wins"] += 1
            user["streak"] += 1
            user["crystals"] += reward

            add_xp(user, 10)

            result = (
                "✨ <b>Совпадение!</b>\n"
                f"💎 +{reward}"
            )

        else:

            user["losses"] += 1
            user["streak"] = 0

            add_xp(user, 3)

            result = "😅 В этот раз мимо.\n⭐ +3 XP"

        check_achievements(user)
        save_db()

        bot.edit_message_text(
            "🎰 <b>СЛОТЫ</b>\n\n"
            f"│ {a} │ {b} │ {c} │\n\n"
            f"{result}\n\n"
            f"💎 Баланс: {user['crystals']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=slots_keyboard()
        )

    # --------------------------------------------------------
    # СТАТИСТИКА ИГР
    # --------------------------------------------------------

    elif data == "game_stats":

        bot.edit_message_text(
            "📊 <b>Игровая статистика</b>\n\n"
            f"🎮 Игр: {user['games']}\n"
            f"🏆 Побед: {user['wins']}\n"
            f"❌ Поражений: {user['losses']}\n"
            f"🔥 Текущая серия: {user['streak']}\n"
            f"🔥 Лучшая серия: {user['best_streak']}\n"
            f"⭐ Уровень: {user['level']}\n"
            f"✨ XP: {user['xp']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_menu()
        )

    # --------------------------------------------------------
    # ПРОФИЛЬ
    # --------------------------------------------------------

    elif data == "profile":

        achievements = len(user["achievements"])

        bot.edit
