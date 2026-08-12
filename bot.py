import os
import json
import time
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import telebot
from telebot import types


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", "10000"))
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
DB_FILE = "data.json"
lock = threading.Lock()


# =========================
# БАЗА
# =========================

def default_db():
    return {
        "users": {},
        "videos": {
            "1": {"name": "🎬 Видео #1", "price": 50, "url": "https://example.com"},
            "2": {"name": "🔥 Видео #2", "price": 100, "url": "https://example.com"}
        },
        "tasks": {}
    }


def load():
    if not os.path.exists(DB_FILE):
        return default_db()

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)

        base = default_db()
        for k, v in base.items():
            if k not in d:
                d[k] = v

        return d
    except Exception:
        return default_db()


db = load()


def save():
    with lock:
        with open(DB_FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        os.replace(DB_FILE + ".tmp", DB_FILE)


def user(uid, name="", username=""):
    uid = str(uid)

    if uid not in db["users"]:
        db["users"][uid] = {
            "id": int(uid),
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
            "achievements": [],
            "tasks": [],
            "videos": [],
            "last_bonus": 0
        }
        save()

    u = db["users"][uid]

    if name:
        u["name"] = name

    if username is not None:
        u["username"] = username

    return u


def admin(uid):
    return ADMIN_ID and int(uid) == ADMIN_ID


# =========================
# НАГРАДЫ
# =========================

def xp(u, amount):
    u["xp"] += amount
    messages = []

    while u["xp"] >= u["level"] * 100:
        u["xp"] -= u["level"] * 100
        u["level"] += 1

        reward = u["level"] * 5
        u["crystals"] += reward

        messages.append(
            f"🎉 Новый уровень <b>{u['level']}</b>!\n"
            f"💎 +{reward} кристаллов"
        )

    return messages


def achievements(u):
    checks = [
        ("game1", "🎮 Первая игра", u["games"] >= 1),
        ("win1", "🏆 Первая победа", u["wins"] >= 1),
        ("games10", "🎮 10 игр", u["games"] >= 10),
        ("wins10", "🏆 10 побед", u["wins"] >= 10),
        ("games50", "🔥 50 игр", u["games"] >= 50),
        ("streak5", "🔥 Серия 5", u["best_streak"] >= 5),
        ("level5", "⭐ Уровень 5", u["level"] >= 5)
    ]

    text = []

    for aid, name, ok in checks:
        if ok and aid not in u["achievements"]:
            u["achievements"].append(aid)
            u["crystals"] += 10
            text.append(f"🏅 {name}\n💎 +10")

    return text


# =========================
# КЛАВИАТУРЫ
# =========================

def main_kb(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)

    buttons = [
        ("🤖 ИИ", "ai"),
        ("🎮 Игры", "games"),
        ("💎 Кристаллы", "crystals"),
        ("🎯 Задания", "tasks"),
        ("🎬 Видео", "videos"),
        ("🏆 ТОП", "top"),
        ("👤 Профиль", "profile"),
        ("🎁 Бонус", "bonus")
    ]

    for text, data in buttons:
        kb.insert(types.InlineKeyboardButton(text, callback_data=data))

    if admin(uid):
        kb.add(types.InlineKeyboardButton("👑 Админка", callback_data="admin"))

    return kb


def back():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Главное меню", callback_data="main"))
    return kb


def games_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)

    for text, data in [
        ("🪙 Монетка", "coin"),
        ("🎲 Кубик", "dice"),
        ("🔢 Число", "number"),
        ("🎰 Слоты", "slots")
    ]:
        kb.insert(types.InlineKeyboardButton(text, callback_data=data))

    kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main"))
    return kb


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(m):
    user(
        m.from_user.id,
        m.from_user.first_name,
        m.from_user.username
    )

    bot.send_message(
        m.chat.id,
        f"👋 <b>Привет, {m.from_user.first_name}!</b>\n\n"
        "🔥 Добро пожаловать в бота!\n\n"
        "🤖 ИИ • 🎮 игры • 💎 кристаллы\n"
        "🎯 задания • 🎬 видео • 🏆 рейтинг",
        reply_markup=main_kb(m.from_user.id)
    )


# =========================
# CALLBACK
# =========================

@bot.callback_query_handler(func=lambda c: True)
def callback(c):

    u = user(
        c.from_user.id,
        c.from_user.first_name,
        c.from_user.username
    )

    d = c.data

    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass

    chat = c.message.chat.id
    msg = c.message.message_id

    # ---------- MAIN ----------

    if d == "main":
        bot.edit_message_text(
            "🏠 <b>Главное меню</b>",
            chat, msg,
            reply_markup=main_kb(c.from_user.id)
        )

    # ---------- GAMES ----------

    elif d == "games":
        bot.edit_message_text(
            "🎮 <b>Игры</b>\n\n"
            "Играй → получай XP → повышай уровень → получай кристаллы.",
            chat, msg,
            reply_markup=games_kb()
        )

    elif d == "coin":
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🦅 Орёл", callback_data="coin_h"),
            types.InlineKeyboardButton("🪙 Решка", callback_data="coin_t")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Игры", callback_data="games"))

        bot.edit_message_text(
            "🪙 <b>Монетка</b>\n\nВыбирай:",
            chat, msg, reply_markup=kb
        )

    elif d in ("coin_h", "coin_t"):

        choice = "h" if d == "coin_h" else "t"
        result = random.choice(["h", "t"])

        u["games"] += 1

        if choice == result:
            reward = random.randint(5, 12)
            u["wins"] += 1
            u["streak"] += 1
            u["best_streak"] = max(u["best_streak"], u["streak"])
            u["crystals"] += reward
            xp(u, 10)

            result_text = f"🎉 <b>Победа!</b>\n💎 +{reward}\n⭐ +10 XP"
        else:
            u["losses"] += 1
            u["streak"] = 0
            xp(u, 3)

            result_text = "😅 Не угадал.\n⭐ +3 XP"

        achievements(u)
        save()

        bot.edit_message_text(
            "🪙 <b>Монетка</b>\n\n"
            f"Твой выбор: {'🦅 Орёл' if choice == 'h' else '🪙 Решка'}\n"
            f"Выпало: {'🦅 Орёл' if result == 'h' else '🪙 Решка'}\n\n"
            f"{result_text}\n\n"
            f"💎 Баланс: {u['crystals']}\n"
            f"🔥 Серия: {u['streak']}",
            chat, msg,
            reply_markup=games_kb()
        )

    # ---------- DICE ----------

    elif d == "dice":
        kb = types.InlineKeyboardMarkup(row_width=3)

        for i in range(1, 7):
            kb.insert(
                types.InlineKeyboardButton(
                    str(i),
                    callback_data=f"dice_{i}"
                )
            )

        kb.add(types.InlineKeyboardButton("⬅️ Игры", callback_data="games"))

        bot.edit_message_text(
            "🎲 <b>Угадай число кубика</b>",
            chat, msg,
            reply_markup=kb
        )

    elif d.startswith("dice_"):

        choice = int(d.split("_")[1])
        result = random.randint(1, 6)

        u["games"] += 1

        if choice == result:
            reward = 15
            u["wins"] += 1
            u["streak"] += 1
            u["best_streak"] = max(u["best_streak"], u["streak"])
            u["crystals"] += reward
            xp(u, 15)

            text = f"🎉 <b>Угадал!</b>\n🎲 Выпало: {result}\n💎 +{reward}"
        else:
            u["losses"] += 1
            u["streak"] = 0
            xp(u, 3)

            text = f"😅 Выпало <b>{result}</b>\n⭐ +3 XP"

        achievements(u)
        save()

        bot.edit_message_text(
            text + f"\n\n💎 Баланс: {u['crystals']}",
            chat, msg,
            reply_markup=games_kb()
        )

    # ---------- NUMBER ----------

    elif d == "number":

        u["secret"] = random.randint(1, 10)
        save()

        kb = types.InlineKeyboardMarkup(row_width=5)

        for i in range(1, 11):
            kb.insert(
                types.InlineKeyboardButton(
                    str(i),
                    callback_data=f"num_{i}"
                )
            )

        kb.add(types.InlineKeyboardButton("⬅️ Игры", callback_data="games"))

        bot.edit_message_text(
            "🔢 <b>Угадай число</b>\n\n"
            "Я загадал число от 1 до 10.",
            chat, msg,
            reply_markup=kb
        )

    elif d.startswith("num_"):

        choice = int(d.split("_")[1])
        secret = u.get("secret", random.randint(1, 10))

        u["games"] += 1

        if choice == secret:
            reward = 20
            u["wins"] += 1
            u["streak"] += 1
            u["best_streak"] = max(u["best_streak"], u["streak"])
            u["crystals"] += reward
            xp(u, 20)

            text = f"🎯 <b>Угадал!</b>\n🔢 Было: {secret}\n💎 +{reward}"
        else:
            u["losses"] += 1
            u["streak"] = 0
            xp(u, 3)

            text = f"❌ Не угадал.\n🔢 Было: {secret}\n⭐ +3 XP"

        u.pop("secret", None)
        achievements(u)
        save()

        bot.edit_message_text(
            text + f"\n\n💎 Баланс: {u['crystals']}",
            chat, msg,
            reply_markup=games_kb()
        )

    # ---------- SLOTS ----------

    elif d == "slots":

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎰 Крутить", callback_data="spin"))
        kb.add(types.InlineKeyboardButton("⬅️ Игры", callback_data="games"))

        bot.edit_message_text(
            "🎰 <b>Слоты</b>\n\n"
            "Это бесплатная мини-игра без реальных ставок.",
            chat, msg,
            reply_markup=kb
        )

    elif d == "spin":

        s = ["🍒", "🍋", "🍉", "⭐", "7️⃣"]
        a, b, c = random.choices(s, k=3)

        u["games"] += 1

        if a == b == c:
            reward = 50
            u["wins"] += 1
            u["streak"] += 1
            u["best_streak"] = max(u["best_streak"], u["streak"])
            u["crystals"] += reward
            xp(u, 25)
            text = f"🔥 <b>ДЖЕКПОТ!</b>\n💎 +{reward}"

        elif a == b or b == c or a == c:
            reward = 10
            u["wins"] += 1
            u["streak"] += 1
            u["crystals"] += reward
            xp(u, 10)
            text = f"✨ <b>Совпадение!</b>\n💎 +{reward}"

        else:
            u["losses"] += 1
            u["streak"] = 0
            xp(u, 3)
            text = "😅 Мимо.\n⭐ +3 XP"

        achievements(u)
        save()

        bot.edit_message_text(
            f"🎰 <b>СЛОТЫ</b>\n\n"
            f"│ {a} │ {b} │ {c} │\n\n"
            f"{text}\n\n"
            f"💎 {u['crystals']}",
            chat, msg,
            reply_markup=games_kb()
        )

    # ---------- STATS ----------

    elif d == "stats":

        bot.edit_message_text(
            "📊 <b>Статистика</b>\n\n"
            f"🎮 Игр: {u['games']}\n"
            f"🏆 Побед: {u['wins']}\n"
            f"❌ Поражений: {u['losses']}\n"
            f"🔥 Серия: {u['streak']}\n"
            f"🔥 Лучшая: {u['best_streak']}\n"
            f"⭐ Уровень: {u['level']}\n"
            f"✨ XP: {u['xp']}",
            chat, msg,
            reply_markup=back()
        )

    # ---------- PROFILE ----------

    elif d == "profile":

        bot.edit_message_text(
            "👤 <b>Профиль</b>\n\n"
            f"👤 {u['name']}\n"
            f"🆔 <code>{u['id']}</code>\n\n"
            f"💎 Кристаллы: <b>{u['crystals']}</b>\n"
            f"⭐ Уровень: <b>{u['level']}</b>\n"
            f"✨ XP: <b>{u['xp']}</b>\n"
            f"🏆 Побед: <b>{u['wins']}</b>\n"
            f"🎮 Игр: <b>{u['games']}</b>\n"
            f"🏅 Достижений: <b>{len(u['achievements'])}</b>",
            chat, msg,
            reply_markup=back()
        )

    # ---------- CRYSTALS ----------

    elif d == "crystals":

        bot.edit_message_text(
            "💎 <b>Кристаллы</b>\n\n"
            f"Твой баланс: <b>{u['crystals']}</b>\n\n"
            "Получать их можно за игры, задания,\n"
            "достижения, уровни и ежедневный бонус.",
            chat, msg,
            reply_markup=back()
        )

    # ---------- BONUS ----------

    elif d == "bonus":

        now = int(time.time())

        if now - u["last_bonus"] < 86400:
            left = 86400 - (now - u["last_bonus"])
            hours = left // 3600

            text = f"⏳ Бонус уже получен.\nПопробуй снова примерно через {hours} ч."

        else:
            reward = random.randint(10, 30)
            u["last_bonus"] = now
            u["crystals"] += reward
            xp(u, 10)
            save()

            text = (
                "🎁 <b>Ежедневный бонус!</b>\n\n"
                f"💎 +{reward} кристаллов\n"
                "⭐ +10 XP"
            )

        bot.edit_message_text(
            text,
            chat, msg,
            reply_markup=back()
        )

    # ---------- TASKS ----------

    elif d == "tasks":

        task_list = [
            ("game5", "🎮 Сыграй 5 раз", 5, 20, u["games"] >= 5),
            ("win5", "🏆 Выиграй 5 раз", 5, 30, u["wins"] >= 5),
            ("win20", "🔥 Выиграй 20 раз", 20, 100, u["wins"] >= 20),
            ("level5", "⭐ Достигни 5 уровня", 5, 50, u["level"] >= 5)
        ]

        lines = ["🎯 <b>Задания</b>\n"]

        for tid, name, goal, reward, done in task_list:

            if tid in u["tasks"]:
                status = "✅ Получено"
            elif done:
                u["tasks"].append(tid)
                u["crystals"] += reward
                status = f"🎁 +{reward} 💎"
            else:
                status = f"🎁 {reward} 💎"

            lines.append(f"{name} — {status}")

        save()

        bot.edit_message_text(
            "\n".join(lines),
            chat, msg,
            reply_markup=back()
        )

    # ---------- TOP ----------

    elif d == "top":

        users = sorted(
            db["users"].values(),
            key=lambda x: (x["crystals"], x["level"]),
            reverse=True
        )[:10]

        text = "🏆 <b>ТОП-10</b>\n\n"

        for i, x in enumerate(users, 1):
            text += (
                f"{i}. {x['name']} — "
                f"💎 {x['crystals']} | ⭐ {x['level']}\n"
            )

        bot.edit_message_text(
            text,
            chat, msg,
            reply_markup=back()
        )

    # ---------- ACHIEVEMENTS ----------

    elif d == "achievements":

        bot.edit_message_text(
            "🏅 <b>Достижения</b>\n\n"
            f"Получено: {len(u['achievements'])}/7\n\n"
            "🎮 Первая игра\n"
            "🏆 Первая победа\n"
            "🎮 10 игр\n"
            "🏆 10 побед\n"
            "🔥 50 игр\n"
            "🔥 Серия 5\n"
            "⭐ Уровень 5",
            chat, msg,
            reply_markup=back()
        )

    # ---------- VIDEOS ----------

    elif d == "videos":

        kb = types.InlineKeyboardMarkup(row_width=1)

        for vid, v in db["videos"].items():
            kb.add(
                types.InlineKeyboardButton(
                    f"{v['name']} — 💎{v['price']}",
                    callback_data=f"video_{vid}"
                )
            )

        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main"))

        bot.edit_message_text(
            "🎬 <b>Магазин видео</b>\n\n"
            "Покупай видео за виртуальные кристаллы:",
            chat, msg,
            reply_markup=kb
        )

    elif d.startswith("video_"):

        vid = d.split("_", 1)[1]
        v = db["videos"].get(vid)

        if not v:
            return

        if vid in u["videos"]:
            text = f"🎬 <b>{v['name']}</b>\n\n🔗 {v['url']}"

        elif u["crystals"] < v["price"]:
            text = (
                f"🎬 <b>{v['name']}</b>\n\n"
                f"💎 Цена: {v['price']}\n"
                f"💎 У тебя: {u['crystals']}\n\n"
                "❌ Недостаточно кристаллов."
            )

        else:
            u["crystals"] -= v["price"]
            u["videos"].append(vid)
            save()

            text = (
                f"🎉 <b>Покупка успешна!</b>\n\n"
                f"🎬 {v['name']}\n"
                f"🔗 {v['url']}\n\n"
                f"💎 Осталось: {u['crystals']}"
            )

        bot.edit_message_text(
            text,
            chat, msg,
            reply_markup=back()
        )

    # ---------- AI ----------

    elif d == "ai":

        bot.send_message(
            chat,
            "🤖 <b>ИИ активирован!</b>\n\n"
            "Просто напиши мне сообщение."
        )

    # ---------- ADMIN ----------

    elif d == "admin" and admin(user_id):

        kb = types.InlineKeyboardMarkup(row_width=2)

        kb.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="adm_stats"),
            types.InlineKeyboardButton("💎 Выдать", callback_data="adm_give")
        )

        kb.add(
            types.InlineKeyboardButton("🎬 Добавить видео", callback_data="adm_video")
        )

        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main"))

        bot.edit_message_text(
            "👑 <b>Панель администратора</b>\n\n"
            "Выбери действие:",
            chat, msg,
            reply_markup=kb
        )

    elif d == "adm_stats" and admin(user_id):

        total = len(db["users"])
        crystals = sum(x["crystals"] for x in db["users"].values())

        bot.edit_message_text(
            "📊 <b>Статистика бота</b>\n\n"
            f"👥 Пользователей: {total}\n"
            f"💎 Кристаллов в системе: {crystals}\n"
            f"🎬 Видео: {len(db['videos'])}",
            chat, msg,
            reply_markup=back()
        )


# =========================
# AI
# =========================

@bot.message_handler(func=lambda m: True)
def ai_message(m):

    u = user(
        m.from_user.id,
        m.from_user.first_name,
        m.from_user.username
    )

    try:
        r = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": HF_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты дружелюбный русскоязычный ИИ-помощник. "
                            "Отвечай понятно и не слишком длинно."
                        )
                    },
                    {
                        "role": "user",
                        "content": m.text
                    }
                ],
                "max_tokens": 700,
                "temperature": 0.7
            },
            timeout=60
        )

        if r.status_code != 200:
            print("HF ERROR:", r.status_code, r.text)
            bot.reply_to(m, "🤖 ИИ временно недоступен.")
            return

        data = r.json()
        answer = data["choices"][0]["message"]["content"]

        bot.reply_to(m, answer)

    except Exception as e:
        print("AI ERROR:", e)
        bot.reply_to(m, "⚠️ Ошибка при обращении к ИИ.")


# =========================
# RENDER WEB SERVER
# =========================

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, *args):
        pass


def web_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Web server started on {PORT}")
    server.serve_forever()


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":

    threading.Thread(
        target=web_server,
        daemon=True
    ).start()

    print("BOT STARTED")

    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30
            )
        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(5)
