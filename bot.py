import os
import requests
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL = os.getenv("MODEL", "openai/gpt-oss-120b:groq")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Память пользователей
memory = {}

MAX_MESSAGES = 12


# =========================
# КЛАВИАТУРЫ
# =========================

def main_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton("💬 Задать вопрос", callback_data="ask"),
        types.InlineKeyboardButton("🧠 Память", callback_data="memory")
    )

    kb.add(
        types.InlineKeyboardButton("🗑 Очистить чат", callback_data="clear"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )

    kb.add(
        types.InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
    )

    return kb


def back_button():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️ Главное меню", callback_data="main")
    )
    return kb


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    memory.setdefault(message.from_user.id, [])

    name = message.from_user.first_name or "друг"

    bot.send_message(
        message.chat.id,
        f"👋 <b>Привет, {name}!</b>\n\n"
        "🤖 Я твой ИИ-помощник.\n\n"
        "Выбери действие ниже 👇",
        reply_markup=main_menu()
    )


# =========================
# КНОПКИ
# =========================

@bot.callback_query_handler(func=lambda call: True)
def buttons(call):

    uid = call.from_user.id

    if call.data == "main":

        bot.edit_message_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Что будем делать?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )

    elif call.data == "ask":

        bot.edit_message_text(
            "💬 <b>Задай мне вопрос</b>\n\n"
            "Просто напиши сообщение следующим сообщением.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

    elif call.data == "memory":

        count = len(memory.get(uid, [])) // 2

        bot.edit_message_text(
            "🧠 <b>Память</b>\n\n"
            f"Сообщений в памяти: <b>{count}</b>\n\n"
            "ИИ использует предыдущие сообщения "
            "этого диалога для контекста.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

    elif call.data == "clear":

        memory[uid] = []

        bot.edit_message_text(
            "🗑 <b>Память очищена!</b>\n\n"
            "Начинаем разговор с чистого листа.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

    elif call.data == "profile":

        count = len(memory.get(uid, [])) // 2

        bot.edit_message_text(
            "👤 <b>Профиль</b>\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🧠 Сообщений: <b>{count}</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

    elif call.data == "help":

        bot.edit_message_text(
            "ℹ️ <b>Помощь</b>\n\n"
            "💬 <b>Задать вопрос</b> — поговорить с ИИ\n"
            "🧠 <b>Память</b> — посмотреть контекст\n"
            "🗑 <b>Очистить чат</b> — начать заново\n"
            "👤 <b>Профиль</b> — посмотреть свой ID",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=back_button()
        )

    try:
        bot.answer_callback_query(call.id)
    except:
        pass


# =========================
# HF AI
# =========================

def ask_ai(uid, text):

    if uid not in memory:
        memory[uid] = []

    memory[uid].append({
        "role": "user",
        "content": text
    })

    # Ограничиваем память
    memory[uid] = memory[uid][-MAX_MESSAGES:]

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты полезный русскоязычный Telegram AI-помощник. "
                    "Отвечай понятно, дружелюбно и по делу."
                )
            }
        ] + memory[uid],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    response = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=120
    )

    if response.status_code != 200:
        print("HF ERROR:", response.status_code)
        print(response.text)
        return "❌ Не удалось получить ответ от ИИ."

    result = response.json()

    answer = result["choices"][0]["message"]["content"]

    memory[uid].append({
        "role": "assistant",
        "content": answer
    })

    memory[uid] = memory[uid][-MAX_MESSAGES:]

    return answer


# =========================
# СООБЩЕНИЯ
# =========================

@bot.message_handler(func=lambda message: True)
def message_handler(message):

    text = message.text.strip()

    if not text:
        return

    uid = message.from_user.id

    bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    try:
        answer = ask_ai(uid, text)

        bot.send_message(
            message.chat.id,
            answer,
            reply_markup=main_menu()
        )

    except requests.Timeout:
        bot.send_message(
            message.chat.id,
            "⏳ ИИ отвечает слишком долго. Попробуй ещё раз."
        )

    except Exception as e:
        print("ERROR:", e)

        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при обращении к ИИ."
        )


# =========================
# ЗАПУСК
# =========================

print("🤖 BOT STARTED")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )
