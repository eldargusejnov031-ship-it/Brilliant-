import os
import json
import time
import threading
import telebot
from telebot import types

# ================= НАСТРОЙКИ =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

FILE = "data.json"
lock = threading.Lock()

# ================= БАЗА =================

def load():
    if not os.path.exists(FILE):
        return {
            "users": {},
            "videos": {},
            "tasks": {
                "games": {
                    "name": "Сыграй 10 раз",
                    "reward": 30,
                    "goal": 10
                },
                "wins": {
                    "name": "Выиграй 5 раз",
                    "reward": 50,
                    "goal": 5
                },
                "messages": {
                    "name": "Отправь 20 сообщений боту",
                    "reward": 35,
                    "goal": 20
                }
            }
        }

    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "users": {},
            "videos": {},
            "tasks": {}
        }


db = load()


def save():
    with lock:
        with open(FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        os.replace(FILE + ".tmp", FILE)


def user(uid, name="Игрок"):
    uid = str(uid)

    if uid not in db["users"]:
        db["users"][uid] = {
            "name": name,
            "crystals": 0,
            "games": 0,
            "wins": 0,
            "messages": 0,
            "completed": [],
            "videos": []
        }
        save()

    db["users"][uid]["name"] = name
    return db["users"][uid]


def admin(uid):
    return ADMIN_ID != 0 and int(uid) == ADMIN_ID


# ================= МЕНЮ =================

def menu(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton("🎯 Задания", callback_data="tasks"),
        types.InlineKeyboardButton("🎬 Видео", callback_data="videos")
    )

    kb.add(
        types.InlineKeyboardButton("🎮 Игра", callback_data="game"),
        types.InlineKeyboardButton("💎 Баланс", callback_data="balance")
    )

    kb.add(
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )

    if admin(uid):
        kb.add(
            types.InlineKeyboardButton("👑 Админка", callback_data="admin")
        )

    return kb


def back():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main"))
    return kb


# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):
    u = user(
        message.from_user.id,
        message.from_user.first_name or "Игрок"
    )

    u["messages"] += 1
    save()

    bot.send_message(
        message.chat.id,
        f"👋 <b>Привет, {u['name']}!</b>\n\n"
        "💎 Выполняй задания → получай кристаллы → покупай видео.\n\n"
        "Выбирай раздел 👇",
        reply_markup=menu(message.from_user.id)
    )


# ================= БАЛАНС =================

def balance_text(u):
    return (
        f"💎 <b>Твой баланс</b>\n\n"
        f"💎 Кристаллы: <b>{u['crystals']}</b>"
    )


@bot.callback_query_handler(func=lambda c: c.data == "balance")
def balance(call):
    u = user(call.from_user.id, call.from_user.first_name)

    bot.edit_message_text(
        balance_text(u),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back()
    )


# ================= ПРОФИЛЬ =================

@bot.callback_query_handler(func=lambda c: c.data == "profile")
def profile(call):
    u = user(call.from_user.id, call.from_user.first_name)

    text = (
        f"👤 <b>{u['name']}</b>\n\n"
        f"💎 Кристаллы: <b>{u['crystals']}</b>\n"
        f"🎮 Игр: <b>{u['games']}</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>\n"
        f"🎬 Куплено видео: <b>{len(u['videos'])}</b>"
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back()
    )


# ================= ИГРА =================

game_data = {}


@bot.callback_query_handler(func=lambda c: c.data == "game")
def game(call):
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton("1", callback_data="answer_1"),
        types.InlineKeyboardButton("2", callback_data="answer_2"),
        types.InlineKeyboardButton("3", callback_data="answer_3"),
        types.InlineKeyboardButton("4", callback_data="answer_4")
    )

    game_data[call.from_user.id] = 3

    bot.edit_message_text(
        "🎮 <b>Мини-викторина</b>\n\n"
        "Сколько будет 1 + 2?\n\n"
        "Правильный ответ даст 💎 кристаллы.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("answer_"))
def answer(call):
    uid = call.from_user.id
    u = user(uid, call.from_user.first_name)

    answer = int(call.data.split("_")[1])
    correct = game_data.get(uid, 3)

    u["games"] += 1

    if answer == correct:
        reward = 10
        u["wins"] += 1
        u["crystals"] += reward

        text = (
            "🎉 <b>Правильно!</b>\n\n"
            f"💎 +{reward} кристаллов"
        )
    else:
        text = (
            "❌ Неправильно!\n\n"
            "Правильный ответ: <b>3</b>"
        )

    save()

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back()
    )


# ================= ЗАДАНИЯ =================

@bot.callback_query_handler(func=lambda c: c.data == "tasks")
def tasks(call):
    uid = str(call.from_user.id)
    u = user(call.from_user.id, call.from_user.first_name)

    kb = types.InlineKeyboardMarkup()

    for key, task in db["tasks"].items():
        progress = 0

        if key == "games":
            progress = u["games"]
        elif key == "wins":
            progress = u["wins"]
        elif key == "messages":
            progress = u["messages"]

        done = key in u["completed"]

        if done:
            text = f"✅ {task['name']}"
        else:
            text = (
                f"🎯 {task['name']} "
                f"({min(progress, task['goal'])}/{task['goal']})"
            )

        kb.add(
            types.InlineKeyboardButton(
                text,
                callback_data=f"task_{key}"
            )
        )

    kb.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="main")
    )

    bot.edit_message_text(
        "🎯 <b>Задания</b>\n\n"
        "Выполняй задания и получай кристаллы.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("task_"))
def task_claim(call):
    key = call.data[5:]
    u = user(call.from_user.id, call.from_user.first_name)

    if key not in db["tasks"]:
        return

    task = db["tasks"][key]

    if key == "games":
        progress = u["games"]
    elif key == "wins":
        progress = u["wins"]
    elif key == "messages":
        progress = u["messages"]
    else:
        progress = 0

    if key in u["completed"]:
        text = "✅ Это задание уже выполнено."
    elif progress < task["goal"]:
        text = (
            f"❌ Пока не выполнено.\n\n"
            f"Прогресс: {progress}/{task['goal']}"
        )
    else:
        u["completed"].append(key)
        u["crystals"] += task["reward"]
        save()

        text = (
            "🎉 <b>Задание выполнено!</b>\n\n"
            f"💎 +{task['reward']} кристаллов"
        )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back()
    )


# ================= МАГАЗИН ВИДЕО =================

@bot.callback_query_handler(func=lambda c: c.data == "videos")
def videos(call):
    kb = types.InlineKeyboardMarkup()

    if not db["videos"]:
        text = (
            "🎬 <b>Магазин видео</b>\n\n"
            "Пока видео нет."
        )
    else:
        text = "🎬 <b>Магазин видео</b>\n\n"

        for vid, data in db["videos"].items():
            kb.add(
                types.InlineKeyboardButton(
                    f"🎬 {data['title']} — 💎 {data['price']}",
                    callback_data=f"video_{vid}"
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


@bot.callback_query_handler(func=lambda c: c.data.startswith("video_"))
def video(call):
    vid = call.data[6:]

    if vid not in db["videos"]:
        return

    u = user(call.from_user.id, call.from_user.first_name)
    v = db["videos"][vid]

    if vid in u["videos"]:
        text = (
            f"🎬 <b>{v['title']}</b>\n\n"
            f"🔗 {v['url']}"
        )

    elif u["crystals"] < v["price"]:
        text = (
            f"🎬 <b>{v['title']}</b>\n\n"
            f"💎 Цена: {v['price']}\n"
            f"💎 У тебя: {u['crystals']}\n\n"
            "❌ Недостаточно кристаллов."
        )

    else:
        u["crystals"] -= v["price"]
        u["videos"].append(vid)
        save()

        text = (
            "🎉 <b>Видео куплено!</b>\n\n"
            f"🎬 {v['title']}\n"
            f"🔗 {v['url']}\n\n"
            f"💎 Осталось: {u['crystals']}"
        )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back()
    )


# ================= АДМИНКА =================

@bot.callback_query_handler(func=lambda c: c.data == "admin")
def admin_panel(call):
    if not admin(call.from_user.id):
        return

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "➕ Добавить видео",
            callback_data="admin_add"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📊 Статистика",
            callback_data="admin_stats"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="main"
        )
    )

    bot.edit_message_text(
        "👑 <b>Админ-панель</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


# ================= ДОБАВЛЕНИЕ ВИДЕО =================

waiting_video = set()


@bot.callback_query_handler(func=lambda c: c.data == "admin_add")
def admin_add(call):
    if not admin(call.from_user.id):
        return

    waiting_video.add(call.from_user.id)

    bot.send_message(
        call.message.chat.id,
        "➕ <b>Добавление видео</b>\n\n"
        "Отправь одной строкой:\n\n"
        "<code>Название | Цена | Ссылка</code>\n\n"
        "Пример:\n"
        "<code>Мой ролик | 100 | https://example.com/video</code>"
    )


@bot.message_handler(func=lambda m: m.from_user.id in waiting_video)
def add_video(message):
    if not admin(message.from_user.id):
        return

    parts = [x.strip() for x in message.text.split("|")]

    if len(parts) != 3:
        bot.reply_to(
            message,
            "❌ Формат:\n"
            "<code>Название | Цена | Ссылка</code>"
        )
        return

    title, price, url = parts

    try:
        price = int(price)
    except:
        bot.reply_to(message, "❌ Цена должна быть числом.")
        return

    vid = str(int(time.time()))

    db["videos"][vid] = {
        "title": title,
        "price": price,
        "url": url
    }

    waiting_video.discard(message.from_user.id)
    save()

    bot.reply_to(
        message,
        f"✅ Видео добавлено!\n\n"
        f"🎬 {title}\n"
        f"💎 Цена: {price}"
    )


# ================= СТАТИСТИКА АДМИНА =================

@bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
def admin_stats(call):
    if not admin(call.from_user.id):
        return

    users = len(db["users"])
    videos = len(db["videos"])

    crystals = sum(
        u["crystals"]
        for u in db["users"].values()
    )

    bot.edit_message_text(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"🎬 Видео: <b>{videos}</b>\n"
        f"💎 Кристаллов у игроков: <b>{crystals}</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back()
    )


# ================= ГЛАВНОЕ МЕНЮ =================

@bot.callback_query_handler(func=lambda c: c.data == "main")
def main(call):
    bot.edit_message_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выбирай раздел 👇",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=menu(call.from_user.id)
    )


# ================= СООБЩЕНИЯ =================

@bot.message_handler(func=lambda m: True)
def messages(message):
    u = user(
        message.from_user.id,
        message.from_user.first_name
    )

    u["messages"] += 1
    save()

    bot.send_message(
        message.chat.id,
        "Используй /start 👆"
    )


# ================= ЗАПУСК =================

print("BOT STARTED")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
)
