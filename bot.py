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
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден")


bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect("bot.db", check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    crystals INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    games INTEGER DEFAULT 0,
    ai_questions INTEGER DEFAULT 0,
    raids INTEGER DEFAULT 0,
    last_bonus INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    url TEXT NOT NULL,
    price INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    task_type TEXT NOT NULL,
    target INTEGER NOT NULL,
    reward INTEGER NOT NULL
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS task_progress (
    user_id INTEGER,
    task_id INTEGER,
    progress INTEGER DEFAULT 0,
    claimed INTEGER DEFAULT 0,
    PRIMARY KEY(user_id, task_id)
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    user_id INTEGER,
    video_id INTEGER,
    PRIMARY KEY(user_id, video_id)
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS promo_codes (
    code TEXT PRIMARY KEY,
    reward INTEGER NOT NULL,
    uses INTEGER DEFAULT 0,
    max_uses INTEGER DEFAULT 1
)
""")

db.commit()


# =========================================================
# RUST DATA
# =========================================================

from rust_data import RAID_TARGETS, EXPLOSIVES, RUST_ITEMS


# =========================================================
# USER FUNCTIONS
# =========================================================

def register(user):
    row = db.execute(
        "SELECT id FROM users WHERE id=?",
        (user.id,)
    ).fetchone()

    if not row:
        db.execute(
            "INSERT INTO users(id, name) VALUES(?, ?)",
            (user.id, user.first_name or "Игрок")
        )
        db.commit()


def get_user(user_id):
    return db.execute(
        """
        SELECT id,name,crystals,xp,wins,games,
               ai_questions,raids,last_bonus,banned
        FROM users WHERE id=?
        """,
        (user_id,)
    ).fetchone()


def add_crystals(user_id, amount):
    db.execute(
        "UPDATE users SET crystals=crystals+? WHERE id=?",
        (amount, user_id)
    )
    db.commit()


def add_xp(user_id, amount):
    db.execute(
        "UPDATE users SET xp=xp+? WHERE id=?",
        (amount, user_id)
    )
    db.commit()


def increment(user_id, field, amount=1):
    allowed = {
        "wins",
        "games",
        "ai_questions",
        "raids"
    }

    if field not in allowed:
        return

    db.execute(
        f"UPDATE users SET {field}={field}+? WHERE id=?",
        (amount, user_id)
    )
    db.commit()

    update_tasks(user_id, field, amount)


def update_tasks(user_id, task_type, amount):
    tasks = db.execute(
        """
        SELECT id,target
        FROM tasks
        WHERE task_type=?
        """,
        (task_type,)
    ).fetchall()

    for task_id, target in tasks:

        row = db.execute(
            """
            SELECT progress,claimed
            FROM task_progress
            WHERE user_id=? AND task_id=?
            """,
            (user_id, task_id)
        ).fetchone()

        if not row:
            progress = 0
            claimed = 0

            db.execute(
                """
                INSERT INTO task_progress
                (user_id,task_id,progress,claimed)
                VALUES(?,?,?,?)
                """,
                (user_id, task_id, amount, 0)
            )

        else:
            progress, claimed = row

            if claimed:
                continue

            progress = min(progress + amount, target)

            db.execute(
                """
                UPDATE task_progress
                SET progress=?
                WHERE user_id=? AND task_id=?
                """,
                (progress, user_id, task_id)
            )

    db.commit()


def is_banned(user_id):
    row = get_user(user_id)
    return row and row[9] == 1


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        "🔥 Rust",
        "🤖 ИИ"
    )

    kb.row(
        "💎 Кристаллы",
        "🎬 Магазин"
    )

    kb.row(
        "👤 Профиль",
        "🏆 Рейтинг"
    )

    kb.row(
        "🎮 Игры",
        "🎁 Бонус"
    )

    return kb


def rust_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            "💥 Рейд",
            callback_data="raid"
        ),
        types.InlineKeyboardButton(
            "🔨 Крафт",
            callback_data="craft"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📦 Предметы",
            callback_data="items"
        ),
        types.InlineKeyboardButton(
            "🔎 Поиск",
            callback_data="rust_search"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Меню",
            callback_data="main"
        )
    )

    return kb


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    register(message.from_user)

    if is_banned(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🚫 Вы заблокированы."
        )
        return

    bot.send_message(
        message.chat.id,
        "🔥 Добро пожаловать в Rust Bot!\n\n"
        "Здесь есть Rust-калькулятор, крафт, "
        "задания, кристаллы, магазин видео и ИИ.",
        reply_markup=main_menu()
    )


# =========================================================
# RUST
# =========================================================

@bot.message_handler(func=lambda m: m.text == "🔥 Rust")
def rust(message):
    bot.send_message(
        message.chat.id,
        "🔥 RUST\n\nВыбирай:",
        reply_markup=rust_menu()
    )


# =========================================================
# RAID
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "raid")
def raid_menu(call):

    kb = types.InlineKeyboardMarkup(row_width=2)

    categories = {}

    for key, item in RAID_TARGETS.items():
        category = item.get("category", "Другое")
        categories.setdefault(category, []).append(key)

    for category in categories:
        kb.add(
            types.InlineKeyboardButton(
                category,
                callback_data=f"raidcat:{category}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="rust"
        )
    )

    bot.edit_message_text(
        "💥 РЕЙД-КАЛЬКУЛЯТОР\n\nВыбери категорию:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("raidcat:"))
def raid_category(call):

    category = call.data.split(":", 1)[1]

    kb = types.InlineKeyboardMarkup(row_width=2)

    for key, item in RAID_TARGETS.items():
        if item.get("category", "Другое") == category:
            kb.add(
                types.InlineKeyboardButton(
                    item["name"],
                    callback_data=f"raidtarget:{key}"
                )
            )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="raid"
        )
    )

    bot.edit_message_text(
        f"💥 {category}\n\nВыбери объект:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("raidtarget:"))
def raid_target(call):

    target = call.data.split(":", 1)[1]

    kb = types.InlineKeyboardMarkup(row_width=2)

    for key, item in EXPLOSIVES.items():
        if key in RAID_TARGETS[target]:
            kb.add(
                types.InlineKeyboardButton(
                    item["name"],
                    callback_data=f"raidcalc:{target}:{key}"
                )
            )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="raid"
        )
    )

    bot.edit_message_text(
        f"🎯 {RAID_TARGETS[target]['name']}\n\n"
        "Чем будешь рейдить?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("raidcalc:"))
def raid_calculate(call):

    _, target, explosive = call.data.split(":")

    target_data = RAID_TARGETS[target]
    explosive_data = EXPLOSIVES[explosive]

    amount = target_data[explosive]

    text = (
        "💥 РЕЗУЛЬТАТ РЕЙДА\n\n"
        f"🎯 Цель: {target_data['name']}\n"
        f"💣 Взрывчатка: {explosive_data['name']}\n"
        f"📦 Нужно: {amount} шт.\n\n"
        "🔨 РЕСУРСЫ НА КРАФТ:\n"
    )

    for resource, value in explosive_data["craft"].items():
        text += f"• {resource}: {value * amount}\n"

    increment(call.from_user.id, "raids")
    add_xp(call.from_user.id, 3)

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Новый рейд",
            callback_data="raid"
        ),
        types.InlineKeyboardButton(
            "🏠 Меню",
            callback_data="main"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


# =========================================================
# RUST ITEMS / CRAFT
# =========================================================

@bot.callback_query_handler(
    func=lambda c: c.data in ("items", "craft")
)
def items_menu(call):

    kb = types.InlineKeyboardMarkup(row_width=2)

    for key, item in RUST_ITEMS.items():
        kb.add(
            types.InlineKeyboardButton(
                item["name"],
                callback_data=f"item:{key}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="rust"
        )
    )

    bot.edit_message_text(
        "📦 Выбери предмет:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("item:")
)
def item_info(call):

    key = call.data.split(":", 1)[1]
    item = RUST_ITEMS.get(key)

    if not item:
        return

    text = (
        f"{item['name']}\n\n"
        f"📂 Категория: {item.get('category', 'Другое')}\n\n"
        "🔨 КРАФТ:\n"
    )

    for resource, amount in item["craft"].items():
        text += f"• {resource}: {amount}\n"

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="items"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


# =========================================================
# CRYSTALS
# =========================================================

@bot.message_handler(func=lambda m: m.text == "💎 Кристаллы")
def crystals(message):

    user = get_user(message.from_user.id)

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎯 Задания",
            callback_data="tasks"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🎬 Магазин",
            callback_data="shop"
        )
    )

    bot.send_message(
        message.chat.id,
        f"💎 Твои кристаллы: {user[2]}\n\n"
        "Выполняй задания и покупай эксклюзивные видео!",
        reply_markup=kb
    )


# =========================================================
# TASKS
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data == "tasks")
def tasks(call):

    rows = db.execute(
        "SELECT id,title,target,reward,task_type FROM tasks"
    ).fetchall()

    if not rows:
        bot.edit_message_text(
            "🎯 Пока нет активных заданий.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    text = "🎯 ЗАДАНИЯ\n\n"

    kb = types.InlineKeyboardMarkup()

    for task_id, title, target, reward, task_type in rows:

        progress_row = db.execute(
            """
            SELECT progress,claimed
            FROM task_progress
            WHERE user_id=? AND task_id=?
            """,
            (call.from_user.id, task_id)
        ).fetchone()

        progress = progress_row[0] if progress_row else 0
        claimed = progress_row[1] if progress_row else 0

        text += (
            f"🎯 {title}\n"
            f"📊 {min(progress, target)}/{target}\n"
            f"💎 Награда: {reward}\n\n"
        )

        if progress >= target and not claimed:
            kb.add(
                types.InlineKeyboardButton(
                    f"💎 Забрать: {title[:18]}",
                    callback_data=f"claim:{task_id}"
                )
            )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="main"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("claim:")
)
def claim_task(call):

    task_id = int(call.data.split(":")[1])

    task = db.execute(
        """
        SELECT title,target,reward
        FROM tasks WHERE id=?
        """,
        (task_id,)
    ).fetchone()

    if not task:
        return

    title, target, reward = task

    progress = db.execute(
        """
        SELECT progress,claimed
        FROM task_progress
        WHERE user_id=? AND task_id=?
        """,
        (call.from_user.id, task_id)
    ).fetchone()

    if not progress:
        return

    if progress[1] or progress[0] < target:
        bot.answer_callback_query(
            call.id,
            "Награда недоступна.",
            show_alert=True
        )
        return

    db.execute(
        """
        UPDATE task_progress
        SET claimed=1
        WHERE user_id=? AND task_id=?
        """,
        (call.from_user.id, task_id)
    )

    db.commit()

    add_crystals(call.from_user.id, reward)

    bot.answer_callback_query(
        call.id,
        f"+{reward} 💎"
    )

    tasks(call)


# =========================================================
# VIDEO SHOP
# =========================================================

@bot.message_handler(func=lambda m: m.text == "🎬 Магазин")
def shop_message(message):
    send_shop(message.chat.id)


def send_shop(chat_id):

    videos = db.execute(
        """
        SELECT id,title,description,price
        FROM videos
        ORDER BY id DESC
        """
    ).fetchall()

    if not videos:
        bot.send_message(
            chat_id,
            "🎬 Магазин пока пуст."
        )
        return

    kb = types.InlineKeyboardMarkup(row_width=1)

    text = "🎬 МАГАЗИН ВИДЕО\n\n"

    for video_id, title, description, price in videos:

        text += (
            f"🎬 {title}\n"
            f"{description}\n"
            f"💎 Цена: {price}\n\n"
        )

        kb.add(
            types.InlineKeyboardButton(
                f"💎 Купить «{title[:20]}»",
                callback_data=f"buy:{video_id}"
            )
        )

    bot.send_message(
        chat_id,
        text,
        reply_markup=kb
    )


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("buy:")
)
def buy_video(call):

    video_id = int(call.data.split(":")[1])

    video = db.execute(
        """
        SELECT title,description,url,price
        FROM videos WHERE id=?
        """,
        (video_id,)
    ).fetchone()

    if not video:
        return

    title, description, url, price = video

    owned = db.execute(
        """
        SELECT 1 FROM purchases
        WHERE user_id=? AND video_id=?
        """,
        (call.from_user.id, video_id)
    ).fetchone()

    if owned:
        bot.send_message(
            call.message.chat.id,
            f"🎬 Ты уже купил «{title}»:\n{url}"
        )
        return

    user = get_user(call.from_user.id)

    if user[2] < price:
        bot.answer_callback_query(
            call.id,
            f"Не хватает {price - user[2]} 💎",
            show_alert=True
        )
        return

    db.execute(
        """
        UPDATE users
        SET crystals=crystals-?
        WHERE id=?
        """,
        (price, call.from_user.id)
    )

    db.execute(
        """
        INSERT INTO purchases(user_id,video_id)
        VALUES(?,?)
        """,
        (call.from_user.id, video_id)
    )

    db.commit()

    bot.send_message(
        call.message.chat.id,
        f"✅ Видео «{title}» разблокировано!\n\n"
        f"▶️ Смотреть:\n{url}"
    )


# =========================================================
# PROMOCODE
# =========================================================

@bot.message_handler(commands=["promo"])
def promo(message):

    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "Использование:\n/promo КОД"
        )
        return

    code = parts[1].upper()

    row = db.execute(
        """
        SELECT reward,uses,max_uses
        FROM promo_codes
        WHERE code=?
        """,
        (code,)
    ).fetchone()

    if not row:
        bot.reply_to(
            message,
            "❌ Такого промокода нет."
        )
        return

    reward, uses, max_uses = row

    if uses >= max_uses:
        bot.reply_to(
            message,
            "❌ Промокод закончился."
        )
        return

    db.execute(
        """
        UPDATE promo_codes
        SET uses=uses+1
        WHERE code=?
        """,
        (code,)
    )

    db.commit()

    add_crystals(
        message.from_user.id,
        reward
    )

    bot.reply_to(
        message,
        f"🎉 Промокод активирован!\n"
        f"💎 +{reward}"
    )


# =========================================================
# PROFILE
# =========================================================

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):

    user = get_user(message.from_user.id)

    level = user[3] // 100 + 1

    bot.send_message(
        message.chat.id,
        "👤 ПРОФИЛЬ\n\n"
        f"🧑 {user[1]}\n"
        f"⭐ Уровень: {level}\n"
        f"✨ XP: {user[3]}\n"
        f"💎 Кристаллы: {user[2]}\n"
        f"🎮 Победы: {user[4]}\n"
        f"🎲 Игр: {user[5]}\n"
        f"🤖 Вопросов ИИ: {user[6]}\n"
        f"💥 Рейдов рассчитано: {user[7]}"
    )


# =========================================================
# RATING
# =====================================
