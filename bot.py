import os
import random
import ast
import operator
from collections import defaultdict

import telebot
from telebot import types
from openai import OpenAI


# =========================================================
# 🔐 НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

if not OPENAI_TOKEN:
    raise RuntimeError("OPENAI_TOKEN не найден")


bot = telebot.TeleBot(BOT_TOKEN)
ai = OpenAI(api_key=OPENAI_TOKEN)


# =========================================================
# 🧠 ПАМЯТЬ ИИ
# =========================================================

user_history = defaultdict(list)

MAX_HISTORY = 12


SYSTEM_PROMPT = """
Ты полезный Telegram ИИ-помощник.

Отвечай на русском языке, если пользователь не попросил другой язык.
Отвечай понятно и дружелюбно.
Не придумывай факты.
Если пользователь просит код — давай рабочий код.
"""


# =========================================================
# 🏆 СТАТИСТИКА
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
            "🏠 Меню",
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
            "🏠 Меню",
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
            "🪨 Камень 🗞 Ножницы",
            callback_data="game_rps"
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "🏠 Меню",
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
            "🏠 Меню",
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
            "🏠 Меню",
            callback_data="home"
        )
    )

    return kb


# =========================================================
# 🤖 ЗАПРОС К ИИ
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

    response = ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1500
    )

    answer = response.choices[0].message.content

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

    def calc(node):

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError()

        if isinstance(node, ast.BinOp):

            op = OPERATORS.get(type(node.op))

            if not op:
                raise ValueError()

            return op(
                calc(node.left),
                calc(node.right)
            )

        if isinstance(node, ast.UnaryOp):

            value = calc(node.operand)

            if isinstance(node.op, ast.USub):
                return -value

            if isinstance(node.op, ast.UAdd):
                return value

        raise ValueError()

    tree = ast.parse(
        expression,
        mode="eval"
    )

    return calc(tree.body)


# =========================================================
# 🚀 START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    user = get_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 Это многофункциональный бот.\n\n"
        "Выбирай раздел 👇",
        reply_markup=main_menu()
    )


# =========================================================
# 🤖 КНОПКА ИИ
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🤖 ИИ"
)
def ai_button(message):

    bot.send_message(
        message.chat.id,
        "🤖 Раздел ИИ\n\n"
        "Выбери действие:",
        reply_markup=ai_menu()
    )


# =========================================================
# 🎮 ИГРЫ
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🎮 Игры"
)
def games_button(message):

    bot.send_message(
        message.chat.id,
        "🎮 ИГРЫ\n\n"
        "Выбирай:",
        reply_markup=games_menu()
    )


# =========================================================
# 📝 ИНСТРУМЕНТЫ
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "📝 Инструменты"
)
def tools_button(message):

    bot.send_message(
        message.chat.id,
        "📝 ИНСТРУМЕНТЫ",
        reply_markup=tools_menu()
    )


# =========================================================
# 📊 ПРОФИЛЬ
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "📊 Профиль"
)
def profile_button(message):

    user = get_user(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"💬 Сообщений: {user['messages']}\n"
        f"🎮 Игр: {user['games']}\n"
        f"🏆 Очков: {user['points']}",
        reply_markup=main_menu()
    )


# =========================================================
# 🔥 RUST
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🔥 Rust"
)
def rust_button(message):

    bot.send_message(
        message.chat.id,
        "🔥 RUST\n\n"
        "Выбери раздел:",
        reply_markup=rust_menu()
    )


# =========================================================
# ⚙️ НАСТРОЙКИ
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "⚙️ Настройки"
)
def settings_button(message):

    bot.send_message(
        message.chat.id,
        "⚙️ НАСТРОЙКИ",
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

    # HOME
    if data == "home":

        bot.edit_message_text(
            "🏠 ГЛАВНОЕ МЕНЮ",
            call.message.chat.id,
            call.message.message_id
        )

        bot.send_message(
            call.message.chat.id,
            "Выбирай раздел 👇",
            reply_markup=main_menu()
        )

        return


    # AI
    if data == "ai_chat":

        bot.send_message(
            call.message.chat.id,
            "🤖 Напиши свой вопрос:"
        )

        return


    # CLEAR MEMORY
    if data == "ai_clear":

        user_history[user_id].clear()

        bot.answer_callback_query(
            call.id,
            "🧹 Память очищена!",
            show_alert=True
        )

        return


    # SUMMARY
    if data == "tool_summary":

        bot.send_message(
            call.message.chat.id,
            "📝 Отправь текст, который нужно сократить."
        )

        return


    # TRANSLATE
    if data == "tool_translate":

        bot.send_message(
            call.message.chat.id,
            "🌐 Напиши текст и язык перевода.\n\n"
            "Например:\n"
            "Переведи на английский: Привет!"
        )

        return


    # IDEA
    if data == "tool_idea":

        try:

            answer = ask_ai(
                user_id,
                "Придумай одну интересную идею."
            )

            bot.send_message(
                call.message.chat.id,
                "💡 ИДЕЯ\n\n" + answer
            )

        except Exception:
            bot.send_message(
                call.message.chat.id,
                "❌ Не удалось получить идею."
            )

        return


    # JOKE
    if data == "tool_joke":

        try:

            answer = ask_ai(
                user_id,
                "Придумай короткую смешную шутку."
            )

            bot.send_message(
                call.message.chat.id,
                "😂 ШУТКА\n\n" + answer
            )

        except Exception:
            bot.send_message(
                call.message.chat.id,
                "❌ Не удалось придумать шутку."
            )

        return


    # CALCULATOR
    if data == "calculator":

        bot.send_message(
            call.message.chat.id,
            "🧮 Отправь математический пример.\n\n"
            "Например:\n"
            "25 * 4 + 10"
        )

        return


    # NUMBER GAME
    if data == "game_number":

        number = random.randint(1, 10)

        bot.send_message(
            call.message.chat.id,
            f"🎲 Я загадал число от 1 до 10.\n\n"
            f"Подсказка: это было **{number}** 😄",
            parse_mode="Markdown"
        )

        get_user(user_id)["games"] += 1
        get_user(user_id)["points"] += 1

        return


    # RPS
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


    if data.startswith("rps_"):

        choices = [
            "rock",
            "paper",
            "scissors"
        ]

        player = data.replace(
            "rps_",
            ""
        )

        computer = random.choice(
            choices
        )

        names = {
            "rock": "🪨 Камень",
            "paper": "📄 Бумага",
            "scissors": "✂️ Ножницы"
        }

        if player == computer:
            result = "🤝 Ничья!"

        elif (
            (player == "rock" and computer == "scissors")
            or
            (player == "paper" and computer == "rock")
            or
            (player == "scissors" and computer == "paper")
        ):
            result = "🏆 Ты победил!"
            get_user(user_id)["points"] += 5

        else:
            result = "😢 Я победил!"

        get_user(user_id)["games"] += 1

        bot.send_message(
            call.message.chat.id,
            f"Ты: {names[player]}\n"
            f"Я: {names[computer]}\n\n"
            f"{result}"
        )

        return


    # RUST
    if data == "rust_guide":

        bot.send_message(
            call.message.chat.id,
            "📚 RUST СПРАВОЧНИК\n\n"
            "Сюда можно добавить предметы, "
            "ресурсы, оружие, строительство "
            "и другую информацию."
        )

        return


    if data == "rust_calc":

        bot.send_message(
            call.message.chat.id,
            "🧮 RUST КАЛЬКУЛЯТОР\n\n"
            "Сюда можно добавить безопасный "
            "калькулятор ресурсов и крафта."
        )

        return


# =========================================================
# 💬 ОБРАБОТКА ТЕКСТА
# =========================================================

@bot.message_handler(
    content_types=["text"]
)
def text_handler(message):

    text = message.text
    user_id = message.from_user.id

    user = get_user(user_id)

    user["messages"] += 1


    # МЕНЮ
    if text == "🏠 Меню":

        bot.send_message(
            message.chat.id,
            "🏠 Главное меню:",
            reply_markup=main_menu()
        )

        return


    # КАЛЬКУЛЯТОР
    try:

        if any(
            symbol in text
            for symbol in ["+", "-", "*", "/", "%"]
        ):

            result = safe_calculate(text)

            bot.reply_to(
                message,
                f"🧮 Ответ: {result}"
            )

            return

    except Exception:
        pass


    # AI
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
            answer,
            reply_markup=main_menu()
        )

    except Exception as error:

        print(
            "AI ERROR:",
            error
        )

        bot.reply_to(
            message,
            "❌ Ошибка при обращении к ИИ."
        )


# =========================================================
# 🚀 ЗАПУСК
# =========================================================

print("🤖 Бот запускается...")

bot.infinity_polling(
    skip_pending=True
    )
