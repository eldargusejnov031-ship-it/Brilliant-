import os
import asyncio
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# НАСТРОЙКИ
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "openai/gpt-oss-120b:groq"


# =========================================================
# ДАННЫЕ ПРЕДМЕТОВ
# Ресурсы здесь используются ТОЛЬКО для калькулятора КРАФТА
# =========================================================

ITEMS = {
    # ---------------- ДВЕРИ ----------------

    "wood_door": {
        "name": "🪵 Деревянная дверь",
        "category": "Двери",
        "resources": {
            "Дерево": 300,
        },
    },

    "metal_door": {
        "name": "🔩 Металлическая дверь",
        "category": "Двери",
        "resources": {
            "Фрагменты металла": 150,
        },
    },

    "garage_door": {
        "name": "🚗 Гаражная дверь",
        "category": "Двери",
        "resources": {
            "Фрагменты металла": 300,
            "Шестерёнки": 2,
        },
    },

    "armored_door": {
        "name": "🛡 МВК дверь",
        "category": "Двери",
        "resources": {
            "Металл высокого качества": 20,
        },
    },

    # ---------------- СТЕНЫ ----------------

    "wood_wall": {
        "name": "🪵 Деревянная стена",
        "category": "Стены",
        "resources": {
            "Дерево": 100,
        },
    },

    "stone_wall": {
        "name": "🪨 Каменная стена",
        "category": "Стены",
        "resources": {
            "Камень": 300,
        },
    },

    "metal_wall": {
        "name": "🔩 Металлическая стена",
        "category": "Стены",
        "resources": {
            "Фрагменты металла": 200,
        },
    },

    "armored_wall": {
        "name": "🛡 МВК стена",
        "category": "Стены",
        "resources": {
            "Металл высокого качества": 25,
        },
    },

    # ---------------- ОКНА ----------------

    "wood_window": {
        "name": "🪵 Деревянный оконный проём",
        "category": "Окна",
        "resources": {
            "Дерево": 100,
        },
    },

    "stone_window": {
        "name": "🪨 Каменный оконный проём",
        "category": "Окна",
        "resources": {
            "Камень": 300,
        },
    },

    "metal_window": {
        "name": "🔩 Металлический оконный проём",
        "category": "Окна",
        "resources": {
            "Фрагменты металла": 200,
        },
    },

    "armored_window": {
        "name": "🛡 МВК оконный проём",
        "category": "Окна",
        "resources": {
            "Металл высокого качества": 25,
        },
    },

    # ---------------- РЕШЁТКИ ----------------

    "metal_bars": {
        "name": "🔩 Металлическая решётка",
        "category": "Решётки",
        "resources": {
            "Фрагменты металла": 100,
        },
    },

    "armored_bars": {
        "name": "🛡 Усиленная решётка",
        "category": "Решётки",
        "resources": {
            "Металл высокого качества": 15,
        },
    },
}


# =========================================================
# КНОПКИ
# =========================================================

def btn(text, callback):
    return InlineKeyboardButton(
        text=text,
        callback_data=callback
    )


def markup(rows):
    return InlineKeyboardMarkup(rows)


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def main_menu():
    return markup([
        [
            btn("🎮 RUST", "rust")
        ],
        [
            btn("🤖 ИИ-помощник", "ai")
        ],
        [
            btn("ℹ️ О боте", "about")
        ],
    ])


# =========================================================
# RUST
# =========================================================

def rust_menu():
    return markup([
        [
            btn("🧮 Калькулятор", "calculator")
        ],
        [
            btn("🔨 Крафт", "craft")
        ],
        [
            btn("🏗 Строительство", "building")
        ],
        [
            btn("📖 Справочник", "guide")
        ],
        [
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# КАЛЬКУЛЯТОР
# =========================================================

def calculator_menu():
    return markup([
        [
            btn("🚪 Двери", "calc_doors")
        ],
        [
            btn("🧱 Стены", "calc_walls")
        ],
        [
            btn("🪟 Окна", "calc_windows")
        ],
        [
            btn("🛡 Решётки", "calc_bars")
        ],
        [
            btn("⬅️ Назад", "rust"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# ДВЕРИ
# =========================================================

def doors_menu():
    return markup([
        [
            btn("🪵 Деревянная", "item_wood_door")
        ],
        [
            btn("🔩 Металлическая", "item_metal_door")
        ],
        [
            btn("🚗 Гаражная", "item_garage_door")
        ],
        [
            btn("🛡 МВК", "item_armored_door")
        ],
        [
            btn("⬅️ Назад", "calculator"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# СТЕНЫ
# =========================================================

def walls_menu():
    return markup([
        [
            btn("🪵 Деревянная", "item_wood_wall")
        ],
        [
            btn("🪨 Каменная", "item_stone_wall")
        ],
        [
            btn("🔩 Металлическая", "item_metal_wall")
        ],
        [
            btn("🛡 МВК", "item_armored_wall")
        ],
        [
            btn("⬅️ Назад", "calculator"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# ОКНА
# =========================================================

def windows_menu():
    return markup([
        [
            btn("🪵 Деревянное", "item_wood_window")
        ],
        [
            btn("🪨 Каменное", "item_stone_window")
        ],
        [
            btn("🔩 Металлическое", "item_metal_window")
        ],
        [
            btn("🛡 МВК", "item_armored_window")
        ],
        [
            btn("⬅️ Назад", "calculator"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# РЕШЁТКИ
# =========================================================

def bars_menu():
    return markup([
        [
            btn("🔩 Металлическая", "item_metal_bars")
        ],
        [
            btn("🛡 Усиленная", "item_armored_bars")
        ],
        [
            btn("⬅️ Назад", "calculator"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# МЕНЮ КОЛИЧЕСТВА
# =========================================================

def quantity_menu(item_id):
    return markup([
        [
            btn("1", f"quantity:{item_id}:1"),
            btn("2", f"quantity:{item_id}:2"),
            btn("5", f"quantity:{item_id}:5"),
        ],
        [
            btn("10", f"quantity:{item_id}:10"),
            btn("20", f"quantity:{item_id}:20"),
            btn("50", f"quantity:{item_id}:50"),
        ],
        [
            btn("⬅️ Назад", "calculator"),
            btn("🏠 Меню", "home"),
        ],
    ])


# =========================================================
# ПОКАЗ ПРЕДМЕТА
# =========================================================

def item_menu(item_id):
    return markup([
        [
            btn("🧮 Рассчитать", f"choose:{item_id}")
        ],
        [
            btn("⬅️ Назад", "calculator"),
            btn("🏠 Меню", "home")
        ],
    ])


def item_text(item_id):
    item = ITEMS[item_id]

    text = (
        f"{item['name']}\n\n"
        f"📂 Категория: {item['category']}\n\n"
        f"🔨 Рецепт крафта:\n"
    )

    for resource, amount in item["resources"].items():
        text += f"• {resource}: {amount}\n"

    text += "\nНажми «🧮 Рассчитать», чтобы выбрать количество."

    return text


# =========================================================
# РАСЧЁТ
# =========================================================

def calculate(item_id, quantity):
    item = ITEMS[item_id]

    text = (
        "🧮 РЕЗУЛЬТАТ\n\n"
        f"{item['name']}\n"
        f"Количество: {quantity}\n\n"
        "📦 ВСЕГО РЕСУРСОВ:\n"
    )

    for resource, amount in item["resources"].items():
        total = amount * quantity
        text += f"• {resource}: {total}\n"

    return text


def result_menu(item_id):
    return markup([
        [
            btn("🔄 Изменить количество", f"choose:{item_id}")
        ],
        [
            btn("⬅️ К калькулятору", "calculator"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# КРАФТ
# =========================================================

def craft_menu():
    return markup([
        [
            btn("⛏ Ресурсы", "resources")
        ],
        [
            btn("🔨 Инструменты", "tools")
        ],
        [
            btn("🔫 Оружие", "weapons")
        ],
        [
            btn("🏗 Строительство", "building")
        ],
        [
            btn("⬅️ Назад", "rust"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# СТРОИТЕЛЬСТВО
# =========================================================

def building_menu():
    return markup([
        [
            btn("🧱 Стены", "calc_walls")
        ],
        [
            btn("🚪 Двери", "calc_doors")
        ],
        [
            btn("🪟 Окна", "calc_windows")
        ],
        [
            btn("🛡 Решётки", "calc_bars")
        ],
        [
            btn("⬅️ Назад", "rust"),
            btn("🏠 Меню", "home")
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "🎮 Я помощник по Rust.\n\n"
        "Выбери раздел:",
        reply_markup=main_menu()
    )


# =========================================================
# КНОПКИ
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # ---------------- HOME ----------------

    if data == "home":

        await query.edit_message_text(
            "🏠 ГЛАВНОЕ МЕНЮ\n\n"
            "Выбери раздел:",
            reply_markup=main_menu()
        )
        return

    # ---------------- RUST ----------------

    if data == "rust":

        await query.edit_message_text(
            "🎮 RUST\n\n"
            "Выбери раздел:",
            reply_markup=rust_menu()
        )
        return

    # ---------------- CALCULATOR ----------------

    if data == "calculator":

        await query.edit_message_text(
            "🧮 КАЛЬКУЛЯТОР\n\n"
            "Что рассчитываем?",
            reply_markup=calculator_menu()
        )
        return

    # ---------------- DOORS ----------------

    if data == "calc_doors":

        await query.edit_message_text(
            "🚪 ДВЕРИ\n\n"
            "Выбери дверь:",
            reply_markup=doors_menu()
        )
        return

    # ---------------- WALLS ----------------

    if data == "calc_walls":

        await query.edit_message_text(
            "🧱 СТЕНЫ\n\n"
            "Выбери стену:",
            reply_markup=walls_menu()
        )
        return

    # ---------------- WINDOWS ----------------

    if data == "calc_windows":

        await query.edit_message_text(
            "🪟 ОКНА\n\n"
            "Выбери объект:",
            reply_markup=windows_menu()
        )
        return

    # ---------------- BARS ----------------

    if data == "calc_bars":

        await query.edit_message_text(
            "🛡 РЕШЁТКИ\n\n"
            "Выбери объект:",
            reply_markup=bars_menu()
        )
        return

    # ---------------- ITEM ----------------

    if data.startswith("item_"):

        item_id = data[5:]

        if item_id not in ITEMS:
            await query.edit_message_text(
                "❌ Предмет не найден.",
                reply_markup=calculator_menu()
            )
            return

        await query.edit_message_text(
            item_text(item_id),
            reply_markup=item_menu(item_id)
        )
        return

    # ---------------- CHOOSE QUANTITY ----------------

    if data.startswith("choose:"):

        item_id = data.split(":", 1)[1]

        if item_id not in ITEMS:
            await query.edit_message_text(
                "❌ Предмет не найден.",
                reply_markup=calculator_menu()
            )
            return

        await query.edit_message_text(
            "🔢 Выбери количество:",
            reply_markup=quantity_menu(item_id)
        )
        return

    # ---------------- CALCULATE ----------------

    if data.startswith("quantity:"):

        parts = data.split(":")

        if len(parts) != 3:
            return

        item_id = parts[1]

        try:
            quantity = int(parts[2])
        except ValueError:
            return

        if item_id not in ITEMS:
            return

        if quantity <= 0:
            return

        text = calculate(
            item_id,
            quantity
        )

        await query.edit_message_text(
            text,
            reply_markup=result_menu(item_id)
        )
        return

    # ---------------- CRAFT ----------------

    if data == "craft":

        await query.edit_message_text(
            "🔨 КРАФТ\n\n"
            "Выбери категорию:",
            reply_markup=craft_menu()
        )
        return

    if data == "resources":

        await query.edit_message_text(
            "⛏ РЕСУРСЫ\n\n"
            "🪵 Дерево\n"
            "🪨 Камень\n"
            "🔩 Фрагменты металла\n"
            "⚙️ Металл высокого качества",
            reply_markup=craft_menu()
        )
        return

    if data == "tools":

        await query.edit_message_text(
            "🔨 ИНСТРУМЕНТЫ\n\n"
            "Кирки, топоры и другие инструменты.",
            reply_markup=craft_menu()
        )
        return

    if data == "weapons":

        await query.edit_message_text(
            "🔫 ОРУЖИЕ\n\n"
            "Справочный раздел оружия Rust.",
            reply_markup=craft_menu()
        )
        return

    # ---------------- BUILDING ----------------

    if data == "building":

        await query.edit_message_text(
            "🏗 СТРОИТЕЛЬСТВО\n\n"
            "Выбери категорию:",
            reply_markup=building_menu()
        )
        return

    # ---------------- GUIDE ----------------

    if data == "guide":

        await query.edit_message_text(
            "📖 СПРАВОЧНИК RUST\n\n"
            "Здесь будет справочная информация "
            "об игровых предметах и механиках.",
            reply_markup=rust_menu()
        )
        return

    # ---------------- AI ----------------

    if data == "ai":

        await query.edit_message_text(
            "🤖 ИИ-ПОМОЩНИК\n\n"
            "Напиши вопрос обычным сообщением.",
            reply_markup=markup([
                [
                    btn("🏠 Меню", "home")
                ]
            ])
        )
        return

    # ---------------- ABOUT ----------------

    if data == "about":

        await query.edit_message_text(
            "🤖 RUST AI BOT\n\n"
            "Telegram-бот с меню Rust,\n"
            "калькулятором ресурсов и ИИ.",
            reply_markup=markup([
                [
                    btn("🏠 Меню", "home")
                ]
            ])
        )
        return


# =========================================================
# HUGGING FACE
# =========================================================

def ask_ai(question):

    if not HF_TOKEN:
        raise Exception("HF_TOKEN не установлен")

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": HF_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты дружелюбный помощник по игре Rust. "
                    "Отвечай на русском языке."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "max_tokens": 1000,
    }

    response = requests.post(
        HF_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise Exception(
            f"HF error {response.status_code}: "
            f"{response.text}"
        )

    result = response.json()

    return result["choices"][0]["message"]["content"]


# =========================================================
# СООБЩЕНИЯ
# =========================================================

async def ai_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    question = update.message.text

    try:

        await update.message.chat.send_action("typing")

        answer = await asyncio.to_thread(
            ask_ai,
            question
        )

        if len(answer) <= 4000:

            await update.message.reply_text(answer)

        else:

            for start in range(
                0,
                len(answer),
                4000
            ):

                await update.message.reply_text(
                    answer[start:start + 4000]
                )

    except Exception as error:

        print("ОШИБКА ИИ:", error)

        await update.message.reply_text(
            "❌ Не удалось получить ответ от ИИ."
        )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    if not TELEGRAM_TOKEN:

        print(
            "❌ ОШИБКА: "
            "TELEGRAM_TOKEN не установлен."
        )

        return

    print("================================")
    print("🤖 RUST BOT ЗАПУСКАЕТСЯ")
    print("================================")

    application = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ai_message
        )
    )

    print("🤖 БОТ ЗАПУЩЕН!")
    print("================================")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
