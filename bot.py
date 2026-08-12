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
Отвечай понятно, кратко и по делу.
Если пользователь просит написать код, предоставляй рабочий код.
Не придумывай факты.
"""


# =========================================================
# 📊 СТАТИСТИКА
# =========================================================

users = {}


def get_user(user_id):

    if user_id not in users:

        users[user_id] = {
            "messages": 0,
            "games": 0,
            "points": 0,
        }

    return users[user_id]


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
# 🔥 RUST
# =========================================================

def rust_menu():

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "📚 Справочник",
            callback_data="rust_guide"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🧮 Калькулятор ресурсов",
            callback_data="rust_calc"
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
# 🤖 ЗАПРОС К HUGGING FACE
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
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "model": HF_MODEL,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.7,
        },
        timeout=90,
    )

    if response.status_code != 200:
        print("HF ERROR:", response.status_code)
        print(response.text)

        raise Exception(
            f"Hugging Face error: {response.status_code}"
        )

    data = response.json()

    answer = data["choices"][0]["message"]["content"]

    history.append({
        "role": "user",
        "content": text
    })

    history.append({
        "role": "assistant",
        "content": answer
    })

    if len(history) > MAX_HISTORY:
        del history[:-MAX_HISTORY]

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

    def calculate_node(node):

        if isinstance(node, ast.Constant):

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError()

        if isinstance(node, ast.BinOp):

            operation = OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise ValueError()

            return operation(
                calculate_node(node.left),
                calculate_node(node.right)
            )

        if isinstance(node, ast.UnaryOp):

            value = calculate_node(
                node.operand
            )

            if isinstance(node.op, ast.USub):
                return -value

            if isinstance(node.op, ast.UAdd):
                return value

        raise ValueError()

    tree = ast.parse(
        expression,
        mode="eval"
    )

    return calculate_node(tree.body)


# =========================================================
# 🚀 START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    get_user(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,

        "👋 Привет, "
        + message.from_user.first_name
        + "!\n\n"
        "🤖 Добро пожаловать в моего "
        "многофункционального бота!\n\n"
        "Выбирай раздел ниже 👇",

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
        "Ты можешь просто написать мне "
        "сообщение.\n\n"
        "Я постараюсь помочь 👇",

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

        f"🆔 ID: {message.from_user.id}\n\n"

        f"💬 Сообщений: "
        f"{user['messages']}\n"

        f"🎮 Игр сыграно: "
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

        "⚙️ НАСТРОЙКИ\n\n"
        "Здесь можно управлять памятью ИИ.",

        reply_markup=settings_menu()
    )


# =========================================================
# 🔘 CALLBACK-КНОПКИ
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
    # 🤖 AI CHAT
    # -----------------------------------------------------

    if data == "ai_chat":

        bot.send_message(
            call.message.chat.id,

            "🤖 Напиши свой вопрос.\n\n"
            "Я отвечу через Hugging Face."
        )

        return


    # -----------------------------------------------------
    # 🧹 CLEAR MEMORY
    # -----------------------------------------------------

    if data == "ai_clear":

        user_history[user_id].clear()

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

            "📝 Сокращение текста\n\n"
            "Отправь текст следующим сообщением."
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
            "Переведи на английский:\n"
            "Привет, как дела?"
        )

        return


    # -----------------------------------------------------
    # 💡 IDEA
    # -----------------------------------------------------

    if data == "tool_idea":

        try:

            answer = ask_ai(
                user_id,
                "Придумай одну интересную и необычную идею."
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
                "Придумай короткую смешную шутку."
            )

            bot.send_message(
                call.message.chat.id,

                "😂 ШУТКА\n\n"
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
    # 🧮 CALCULATOR
    # -----------------------------------------------------

    if data == "calculator":

        bot.send_message(
            call.message.chat.id,

            "🧮 КАЛЬКУЛЯТОР\n\n"
            "Напиши пример.\n\n"
            "Например:\n"
            "250 * 4 + 100"
        )

        return


    # -----------------------------------------------------
    # 🎲 NUMBER GAME
    # -----------------------------------------------------

    if data == "game_number":

        number = random.randint(
            1,
            10
        )

        bot.send_message(
            call.message.chat.id,

            "🎲 Я загадал число от 1 до 10.\n\n"
            "Но сегодня я добрый 😎\n"
            f"Ответ: {number}"
        )

        user = get_user(user_id)

        user["games"] += 1
        user["points"] += 1

        return


    # -----------------------------------------------------
    # 🪨📄✂️ RPS
    # -----------------------------------------------------

    if data.startswith("rps_"):

        player = data.replace(
            "rps_",
            ""
        )

        computer = random.choice(
            [
                "rock",
                "paper",
                "scissors"
            ]
        )

        names = {
            "rock": "🪨 Камень",
            "paper": "📄 Бумага",
            "scissors": "✂️ Ножницы"
        }

        if player == computer:

            result = "🤝 Ничья!"

        elif (
            (player == "rock"
             and computer == "scissors")
            or
            (player == "paper"
             and computer == "rock")
            or
            (player == "scissors"
             and computer == "paper")
        ):

            result = "🏆 Ты победил!"

            get_user(
                user_id
            )["points"] += 5

        else:

            result = "😎 Я победил!"

        get_user(
            user_id
        )["games"] += 1

        bot.send_message(
            call.message.chat.id,

            f"Ты: {names[player]}\n"
            f"Я: {names[computer]}\n\n"
            f"{result}"
        )

        return


    # -----------------------------------------------------
    # 📚 RUST GUIDE
    # -----------------------------------------------------

    if data == "rust_guide":

        bot.send_message(
            call.message.chat.id,

            "📚 RUST СПРАВОЧНИК\n\n"

            "Этот раздел можно постепенно "
            "заполнить предметами, ресурсами, "
            "строительством и другой информацией."
        )

        return


    # -----------------------------------------------------
    # 🧮 RUST CALCULATOR
    # -----------------------------------------------------

    if data == "rust_calc":

        bot.send_message(
            call.message.chat.id,

            "🧮 RUST КАЛЬКУЛЯТОР\n\n"

            "Здесь можно сделать калькулятор "
            "обычных ресурсов и крафта."
        )

        return


# =========================================================
# 💬 ОБЫЧНЫЕ СООБЩЕНИЯ
# =========================================================

@bot.message_handler(
    content_types=["text"]
)
def text_handler(message):

    text = message.text.strip()

    user_id = message.from_user.id

    user = get_user(user_id)

    user["messages"] += 1


    # -----------------------------------------------------
    # 🧮 КАЛЬКУЛЯТОР
    # -----------------------------------------------------

    try:

        if any(
            symbol in text
            for symbol in [
                "+",
                "-",
                "*",
                "/",
                "%"
            ]
        ):

            result = safe_calculate(
                text
            )

            bot.reply_to(
                message,

                f"🧮 Ответ: {result}"
            )

            return

    except Exception:
        pass


    # -----------------------------------------------------
    # 🤖 AI
    # -----------------------------------------------------

    bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    try:

        answer = ask_ai(
            user_id,
            text
        )

        bot.reply_to(
            message,
            answer
        )

    except Exception as error:

        print(
            "HF ERROR:",
            error
        )

        bot.reply_to(
            message,

            "❌ Не удалось получить ответ от ИИ.\n\n"
            "Проверь HF_TOKEN и логи Render."
        )


# =========================================================
# 🚀 ЗАПУСК
# =========================================================

print("================================")
print("🤖 RUST AI BOT")
print("🚀 Бот запускается...")
print("🧠 Hugging Face подключён")
print("================================")


bot.infinity_polling(
    skip_pending=True
            )
