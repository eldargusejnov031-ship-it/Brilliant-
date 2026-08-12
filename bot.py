import os
import requests
from collections import defaultdict

import telebot
from telebot import types


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "openai/gpt-oss-120b:groq"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN не найден")

bot = telebot.TeleBot(BOT_TOKEN)


# =========================================================
# AI MEMORY
# =========================================================

history = defaultdict(list)
MAX_HISTORY = 10


def ask_ai(user_id, text):

    messages = [
        {
            "role": "system",
            "content": (
                "Ты дружелюбный Telegram ИИ-помощник. "
                "Отвечай на русском языке, если пользователь "
                "не попросил другой язык. Отвечай понятно."
            )
        }
    ]

    messages.extend(history[user_id])

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
        raise RuntimeError("Ошибка Hugging Face")

    data = response.json()

    answer = data["choices"][0]["message"]["content"]

    history[user_id].append({
        "role": "user",
        "content": text
    })

    history[user_id].append({
        "role": "assistant",
        "content": answer
    })

    history[user_id] = history[user_id][-MAX_HISTORY:]

    return answer


# =========================================================
# RUST DATABASE
# =========================================================

RUST_ITEMS = {

    "building_plan": {
        "name": "📐 План строительства",
        "category": "🧱 Строительство",
        "craft": {
            "Дерево": 20
        },
        "bench": "Не требуется"
    },

    "campfire": {
        "name": "🔥 Костёр",
        "category": "🏠 Постройки",
        "craft": {
            "Дерево": 100
        },
        "bench": "Не требуется"
    },

    "furnace": {
        "name": "🔥 Печь",
        "category": "🏠 Постройки",
        "craft": {
            "Камень": 200,
            "Дерево": 100
        },
        "bench": "Не требуется"
    },

    "wood_box": {
        "name": "📦 Деревянный ящик",
        "category": "📦 Хранение",
        "craft": {
            "Дерево": 100
        },
        "bench": "Не требуется"
    },

    "small_stash": {
        "name": "👜 Маленький тайник",
        "category": "📦 Хранение",
        "craft": {
            "Дерево": 10,
            "Камень": 10
        },
        "bench": "Не требуется"
    },

    "sleeping_bag": {
        "name": "🛏 Спальный мешок",
        "category": "🏠 Постройки",
        "craft": {
            "Ткань": 30
        },
        "bench": "Не требуется"
    },

    "wooden_door": {
        "name": "🚪 Деревянная дверь",
        "category": "🧱 Строительство",
        "craft": {
            "Дерево": 100
        },
        "bench": "Не требуется"
    },

    "lantern": {
        "name": "🏮 Фонарь",
        "category": "💡 Освещение",
        "craft": {
            "Металлические фрагменты": 20,
            "Ткань": 10
        },
        "bench": "Не требуется"
    },

    "planter": {
        "name": "🌱 Горшок",
        "category": "🌱 Фермерство",
        "craft": {
            "Дерево": 100
        },
        "bench": "Не требуется"
    }
}


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🤖 ИИ",
        "🔥 Rust"
    )

    kb.row(
        "📝 Инструменты",
        "📊 Профиль"
    )

    kb.row(
        "⚙️ Настройки"
    )

    return kb


# =========================================================
# RUST MENU
# =========================================================

def rust_menu():

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            "📦 Все предметы",
            callback_data="rust_items"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🧱 Строительство",
            callback_data="cat_build"
        ),
        types.InlineKeyboardButton(
            "🏠 Постройки",
            callback_data="cat_home"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📦 Хранение",
            callback_data="cat_storage"
        ),
        types.InlineKeyboardButton(
            "🌱 Фермерство",
            callback_data="cat_farm"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "💡 Освещение",
            callback_data="cat_light"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🔎 Поиск",
            callback_data="rust_search"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="home"
        )
    )

    return kb


# =========================================================
# ALL ITEMS
# =========================================================

def items_menu():

    kb = types.InlineKeyboardMarkup(row_width=2)

    for key, item in RUST_ITEMS.items():

        kb.add(
            types.InlineKeyboardButton(
                item["name"],
                callback_data=f"item_{key}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="rust"
        )
    )

    return kb


# =========================================================
# ITEM CARD
# =========================================================

def show_item(call, key):

    item = RUST_ITEMS[key]

    text = (
        f"{item['name']}\n\n"
        f"📂 {item['category']}\n\n"
        "🔨 Крафт на 1 шт.:\n"
    )

    for resource, amount in item["craft"].items():

        text += f"• {resource}: {amount}\n"

    text += (
        f"\n🏭 Верстак: {item['bench']}"
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🧮 Рассчитать количество",
            callback_data=f"amount_{key}"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Все предметы",
            callback_data="rust_items"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Rust",
            callback_data="rust"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


# =========================================================
# TEMP USER STATES
# =========================================================

amount_waiting = {}
search_waiting = {}


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "👋 Привет!\n\n"
        "Я твой Telegram-бот с ИИ и Rust-разделом.\n\n"
        "Выбирай раздел 👇",
        reply_markup=main_menu()
    )


# =========================================================
# AI BUTTON
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🤖 ИИ"
)
def ai_button(message):

    bot.send_message(
        message.chat.id,
        "🤖 Напиши мне любой вопрос — "
        "я постараюсь помочь."
    )


# =========================================================
# RUST BUTTON
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🔥 Rust"
)
def rust_button(message):

    bot.send_message(
        message.chat.id,
        "🔥 RUST\n\n"
        "Выбери нужный раздел:",
        reply_markup=rust_menu()
    )


# =========================================================
# TOOLS
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "📝 Инструменты"
)
def tools_button(message):

    bot.send_message(
        message.chat.id,
        "📝 Инструменты\n\n"
        "Пока доступны Rust-инструменты "
        "и ИИ."
    )


# =========================================================
# PROFILE
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "📊 Профиль"
)
def profile_button(message):

    bot.send_message(
        message.chat.id,
        "📊 ТВОЙ ПРОФИЛЬ\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"👤 Имя: {message.from_user.first_name}"
    )


# =========================================================
# SETTINGS
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "⚙️ Настройки"
)
def settings_button(message):

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🧹 Очистить память ИИ",
            callback_data="clear_memory"
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
        "⚙️ Настройки:",
        reply_markup=kb
    )


# =========================================================
# CALLBACKS
# =========================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callbacks(call):

    data = call.data
    user_id = call.from_user.id

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # HOME
    if data == "home":

        bot.send_message(
            call.message.chat.id,
            "🏠 Главное меню:",
            reply_markup=main_menu()
        )

        return

    # CLEAR MEMORY
    if data == "clear_memory":

        history[user_id].clear()

        bot.answer_callback_query(
            call.id,
            "Память очищена!",
            show_alert=True
        )

        return

    # RUST
    if data == "rust":

        bot.edit_message_text(
            "🔥 RUST\n\n"
            "Выбери нужный раздел:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=rust_menu()
        )

        return

    # ALL ITEMS
    if data == "rust_items":

        bot.edit_message_text(
            "📦 ВСЕ ПРЕДМЕТЫ\n\n"
            "Выбери предмет:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=items_menu()
        )

        return

    # ITEM
    if data.startswith("item_"):

        key = data.replace(
            "item_",
            "",
            1
        )

        if key in RUST_ITEMS:
            show_item(call, key)

        return

    # AMOUNT
    if data.startswith("amount_"):

        key = data.replace(
            "amount_",
            "",
            1
        )

        if key not in RUST_ITEMS:
            return

        amount_waiting[user_id] = key

        bot.send_message(
            call.message.chat.id,
            f"{RUST_ITEMS[key]['name']}\n\n"
            "🧮 Сколько штук нужно?\n\n"
            "Напиши число, например: 10"
        )

        return

    # SEARCH
    if data == "rust_search":

        search_waiting[user_id] = True

        bot.send_message(
            call.message.chat.id,
            "🔎 Напиши название предмета."
        )

        return

    # CATEGORIES
    categories = {
        "cat_build": "🧱 Строительство",
        "cat_home": "🏠 Постройки",
        "cat_storage": "📦 Хранение",
        "cat_farm": "🌱 Фермерство",
        "cat_light": "💡 Освещение"
    }

    if data in categories:

        category = categories[data]

        kb = types.InlineKeyboardMarkup(
            row_width=2
        )

        found = False

        for key, item in RUST_ITEMS.items():

            if item["category"] == category:

                found = True

                kb.add(
                    types.InlineKeyboardButton(
                        item["name"],
                        callback_data=f"item_{key}"
                    )
                )

        kb.add(
            types.InlineKeyboardButton(
                "⬅️ Rust",
                callback_data="rust"
            )
        )

        text = (
            f"{category}\n\n"
            "Выбери предмет:"
            if found
            else
            f"{category}\n\n"
            "Пока предметов нет."
        )

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )

        return


# =========================================================
# TEXT HANDLER
# =========================================================

@bot.message_handler(
    content_types=["text"]
)
def text_handler(message):

    user_id = message.from_user.id
    text = message.text.strip()

    # SEARCH
    if search_waiting.get(user_id):

        search_waiting.pop(user_id)

        query = text.lower()

        results = []

        for key, item in RUST_ITEMS.items():

            if (
                query in item["name"].lower()
                or query in key.lower()
                or query in item["category"].lower()
            ):
                results.append(key)

        if not results:

            bot.reply_to(
                message,
                "❌ Ничего не найдено."
            )

            return

        kb = types.InlineKeyboardMarkup(
            row_width=2
        )

        for key in results:

            kb.add(
                types.InlineKeyboardButton(
                    RUST_ITEMS[key]["name"],
                    callback_data=f"item_{key}"
                )
            )

        bot.send_message(
            message.chat.id,
            "🔎 Результаты поиска:",
            reply_markup=kb
        )

        return

    # AMOUNT CALCULATOR
    if user_id in amount_waiting:

        key = amount_waiting[user_id]

        try:
            amount = int(text)

            if amount <= 0:
                raise ValueError

        except ValueError:

            bot.reply_to(
                message,
                "❌ Введи положительное число."
            )

            return

        amount_waiting.pop(user_id)

        item = RUST_ITEMS[key]

        result = (
            "🧮 РАСЧЁТ\n\n"
            f"{item['name']}\n"
            f"📦 Количество: {amount}\n\n"
            "🔨 Нужно ресурсов:\n"
        )

        for resource, one in item["craft"].items():

            total = one * amount

            result += (
                f"• {resource}: {total}\n"
            )

        result += (
            f"\n🏭 Верстак: {item['bench']}"
        )

        bot.send_message(
            message.chat.id,
            result
        )

        return

    # AI
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
            "❌ ИИ временно недоступен. "
            "Проверь HF_TOKEN и Logs в Render."
        )


# =========================================================
# RUN
# =========================================================

print("================================")
print("🤖 BOT STARTED")
print("🧠 Hugging Face: OK")
print("🔥 Rust: OK")
print("================================")

bot.infinity_polling(
    skip_pending=True
)
