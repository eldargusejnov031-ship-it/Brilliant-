import os
import random
import ast
import operator
import requests
from collections import defaultdict

import telebot
from telebot import types


# =========================================================
# 🔐 НАСТРОЙКИ
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
# 🧠 ПАМЯТЬ ИИ
# =========================================================

user_history = defaultdict(list)
MAX_HISTORY = 12

SYSTEM_PROMPT = """
Ты дружелюбный ИИ-помощник в Telegram.

Отвечай на русском языке, если пользователь не попросил другой язык.
Отвечай понятно и по делу.
Если пользователь просит код — предоставляй рабочий код.
Не придумывай факты.
"""


# =========================================================
# 📊 ПОЛЬЗОВАТЕЛИ
# =========================================================

users = {}

# Пользователи, которые сейчас считают количество предметов
rust_calculating = {}

# Пользователи, которые сейчас используют поиск Rust
rust_searching = {}


def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "messages": 0,
            "games": 0,
            "points": 0,
        }

    return users[user_id]


# =========================================================
# 🔥 RUST — БАЗА ОБЫЧНЫХ ПРЕДМЕТОВ
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

    "wood_box": {
        "name": "📦 Деревянный ящик",
        "category": "📦 Хранение",
        "craft": {
            "Дерево": 100
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

    "furnace": {
        "name": "🔥 Печь",
        "category": "🏠 Постройки",
        "craft": {
            "Камень": 200,
            "Дерево": 100
        },
        "bench": "Не требуется"
    },

    "small_stash": {
        "name": "👜 Маленький тайник",
        "category": "📦 Хранение",
        "craft": {
            "Камень": 10,
            "Дерево": 10
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
        "name": "🌱 Маленький горшок",
        "category": "🌱 Фермерство",
        "craft": {
            "Дерево": 100
        },
        "bench": "Не требуется"
    },

    "wooden_sign": {
        "name": "🪧 Деревянная табличка",
        "category": "🏠 Постройки",
        "craft": {
            "Дерево": 50
        },
        "bench": "Не требуется"
    },

    "barrel": {
        "name": "🛢 Бочка",
        "category": "📦 Хранение",
        "craft": {
            "Дерево": 50
        },
        "bench": "Не требуется"
    }
}


# =========================================================
# 🏠 ГЛАВНОЕ МЕНЮ
# =========================================================

def main_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🤖 ИИ",
        "🎮 Игры"
    )

    kb.row(
        "📝 Инструменты",
        "📊 Профиль"
    )

    kb.row(
        "🔥 Rust",
        "⚙️ Настройки"
    )

    return kb


# =========================================================
# 🤖 МЕНЮ ИИ
# =========================================================

def ai_menu():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "💬 Задать вопрос",
            callback_data="ai_chat"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🧹 Очистить память",
            callback_data="ai_clear"
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
# 📝 ИНСТРУМЕНТЫ
# =========================================================

def tools_menu():

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            "📝 Сократить текст",
            callback_data="tool_summary"
        ),
        types.InlineKeyboardButton(
            "🌐 Перевести",
            callback_data="tool_translate"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "💡 Идея",
            callback_data="tool_idea"
        ),
        types.InlineKeyboardButton(
            "😂 Шутка",
            callback_data="tool_joke"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🧮 Калькулятор",
            callback_data="calculator"
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
# 🎮 ИГРЫ
# =========================================================

def games_menu():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🎲 Угадай число",
            callback_data="game_number"
        )
    )

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

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Главное меню",
            callback_data="home"
        )
    )

    return kb


# =========================================================
# 🔥 RUST — ГЛАВНОЕ МЕНЮ
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
            callback_data="rust_cat_build"
        ),
        types.InlineKeyboardButton(
            "🏠 Постройки",
            callback_data="rust_cat_home"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "📦 Хранение",
            callback_data="rust_cat_storage"
        ),
        types.InlineKeyboardButton(
            "🌱 Фермерство",
            callback_data="rust_cat_farm"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "💡 Освещение",
            callback_data="rust_cat_light"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🔎 Поиск предмета",
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
# 📦 СПИСОК RUST
# =========================================================

def rust_items_menu():

    kb = types.InlineKeyboardMarkup(row_width=2)

    for key, item in RUST_ITEMS.items():

        kb.add(
            types.InlineKeyboardButton(
                item["name"],
                callback_data=f"rust_item_{key}"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="rust_main"
        )
    )

    return kb


# =========================================================
# 📋 КАРТОЧКА ПРЕДМЕТА
# =========================================================

def show_rust_item(
    chat_id,
    message_id,
    key
):

    item = RUST_ITEMS[key]

    text = (
        f"{item['name']}\n\n"
        f"📂 Категория: {item['category']}\n\n"
        "🔨 КРАФТ\n"
    )

    for resource, amount in item["craft"].items():

        text += (
            f"• {resource}: "
            f"{amount}\n"
        )

    text += (
        f"\n🏭 Верстак: "
        f"{item['bench']}"
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🧮 Рассчитать количество",
            callback_data=f"rust_amount_{key}"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⬅️ К предметам",
            callback_data="rust_items"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Rust",
            callback_data="rust_main"
        )
    )

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=kb
    )


# =========================================================
# 🔎 ПОИСК RUST
# =========================================================

def search_rust_items(query):

    query = query.lower().strip()

    result = []

    for key, item in RUST_ITEMS.items():

        name = item["name"].lower()
        category = item["category"].lower()

        if (
            query in name
            or query in category
            or query in key.lower()
        ):
            result.append(key)

    return result


# =========================================================
# ⚙️ НАСТРОЙКИ
# =========================================================

def settings_menu():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🧹 Очистить память ИИ",
            callback_data="ai_clear"
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
# 🤖 HUGGING FACE
# =========================================================

def ask_ai(user_id, text):

    history = user_history[user_id]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": text
    })

    response = requests.post(
        HF_URL,

        headers={
            "Authorization":
                f"Bearer {HF_TOKEN}",

            "Content-Type":
                "application/json"
        },

        json={
            "model": HF_MODEL,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.7
        },

        timeout=90
    )

    if response.status_code != 200:

        print(
            "HF ERROR:",
            response.status_code
        )

        print(
            response.text
        )

        raise Exception(
            "Hugging Face error"
        )

    data = response.json()

    answer = (
        data["choices"][0]
        ["message"]["content"]
    )

    history.append({
        "role": "user",
        "content": text
    })

    history.append({
        "role": "assistant",
        "content": answer
    })

    if len(history) > MAX_HISTORY:

        del history[
            :-MAX_HISTORY
        ]

    return answer


# =========================================================
# 🧮 БЕЗОПАСНЫЙ КАЛЬКУЛЯТОР
# =========================================================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def safe_calculate(expression):

    def calculate(node):

        if isinstance(
            node,
            ast.Constant
        ):

            if isinstance(
                node.value,
                (int, float)
            ):
                return node.value

            raise ValueError()

        if isinstance(
            node,
            ast.BinOp
        ):

            operation = OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise ValueError()

            return operation(
                calculate(node.left),
                calculate(node.right)
            )

        if isinstance(
            node,
            ast.UnaryOp
        ):

            value = calculate(
                node.operand
            )

            if isinstance(
                node.op,
                ast.USub
            ):
                return -value

            if isinstance(
                node.op,
                ast.UAdd
            ):
                return value

        raise ValueError()

    tree = ast.parse(
        expression,
        mode="eval"
    )

    return calculate(
        tree.body
    )


# =========================================================
# 🚀 START
# =========================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    get_user(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,

        "👋 Привет, "
        + message.from_user.first_name
        + "!\n\n"
        "🤖 Добро пожаловать!\n\n"
        "Здесь есть ИИ, игры, "
        "инструменты и большая "
        "база Rust.\n\n"
        "Выбирай раздел 👇",

        reply_markup=main_menu()
    )


# =========================================================
# 🤖 ИИ
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text == "🤖 ИИ"
)
def ai_button(message):

    bot.send_message(
        message.chat.id,

        "🤖 ИИ-ПОМОЩНИК\n\n"
        "Просто напиши мне сообщение "
        "после этого — я отвечу.",

        reply_markup=ai_menu()
    )


# =========================================================
# 🎮 ИГРЫ
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text == "🎮 Игры"
)
def games_button(message):

    bot.send_message(
        message.chat.id,

        "🎮 ИГРЫ\n\n"
        "Выбирай игру:",

        reply_markup=games_menu()
    )


# =========================================================
# 📝 ИНСТРУМЕНТЫ
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text == "📝 Инструменты"
)
def tools_button(message):

    bot.send_message(
        message.chat.id,

        "📝 ИНСТРУМЕНТЫ\n\n"
        "Выбери нужный инструмент:",

        reply_markup=tools_menu()
    )


# =========================================================
# 📊 ПРОФИЛЬ
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text == "📊 Профиль"
)
def profile_button(message):

    user = get_user(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,

        "👤 ТВОЙ ПРОФИЛЬ\n\n"

        f"🆔 ID: "
        f"{message.from_user.id}\n\n"

        f"💬 Сообщений: "
        f"{user['messages']}\n"

        f"🎮 Игр: "
        f"{user['games']}\n"

        f"🏆 Очков: "
        f"{user['points']}",

        reply_markup=main_menu()
    )


# =========================================================
# 🔥 RUST
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text == "🔥 Rust"
)
def rust_button(message):

    bot.send_message(
        message.chat.id,

        "🔥 RUST\n\n"
        "📦 База предметов\n"
        "🔨 Крафт\n"
        "🧮 Расчёт ресурсов\n"
        "🔎 Поиск\n\n"
        "Выбирай раздел:",

        reply_markup=rust_menu()
    )


# =========================================================
# ⚙️ НАСТРОЙКИ
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text == "⚙️ Настройки"
)
def settings_button(message):

    bot.send_message(
        message.chat.id,

        "⚙️ НАСТРОЙКИ",

        reply_markup=settings_menu()
    )


# =========================================================
# 🔘 CALLBACK
# =========================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callbacks(call):

    data = call.data
    user_id = call.from_user.id

    try:
        bot.answer_callback_query(
            call.id
        )
    except Exception:
        pass


    # -----------------------------------------------------
    # 🏠 HOME
    # -----------------------------------------------------

    if data == "home":

        bot.send_message(
            call.message.chat.id,

            "🏠 Главное меню:",

            reply_markup=main_menu()
        )

        return


    # -----------------------------------------------------
    # 🤖 AI
    # -----------------------------------------------------

    if data == "ai_chat":

        bot.send_message(
            call.message.chat.id,

            "🤖 Напиши свой вопрос."
        )

        return


    # -----------------------------------------------------
    # 🧹 CLEAR MEMORY
    # -----------------------------------------------------

    if data == "ai_clear":

        user_history[
            user_id
        ].clear()

        bot.answer_callback_query(
            call.id,
            "🧹 Память очищена!",
            show_alert=True
        )

        return


    # -----------------------------------------------------
    # 📝 SUMMARY
    # -----------------------------------------------------

    if data == "tool_summary":

        bot.send_message(
            call.message.chat.id,

            "📝 Сократить текст\n\n"
            "Отправь текст следующим "
            "сообщением."
        )

        return


    # -----------------------------------------------------
    # 🌐 TRANSLATE
    # -----------------------------------------------------

    if data == "tool_translate":

        bot.send_message(
            call.message.chat.id,

            "🌐 Переводчик\n\n"
            "Напиши, например:\n\n"
            "Переведи на английский: "
            "Привет!"
        )

        return


    # -----------------------------------------------------
    # 💡 IDEA
    # -----------------------------------------------------

    if data == "tool_idea":

        try:

            answer = ask_ai(
                user_id,
                "Придумай интересную "
                "необычную идею."
            )

            bot.send_message(
                call.message.chat.id,

                "💡 ИДЕЯ\n\n"
                + answer
            )

        except Exception as error:

            print(error)

            bot.send_message(
                call.message.chat.id,
                "❌ ИИ временно недоступен."
            )

        return


    # -----------------------------------------------------
    # 😂 JOKE
    # -----------------------------------------------------

    if data == "tool_joke":

        try:

            answer = ask_ai(
                user_id,
                "Придумай короткую "
                "смешную шутку."
       
