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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "openai/gpt-oss-120b:groq"


# =========================================================
# ДАННЫЕ RUST
# =========================================================

ITEMS = {
    "wood_door": {
        "name": "🪵 Деревянная дверь",
        "category": "Двери",
        "health": "200 HP",
        "craft": {
            "Дерево": 300
        },
    },

    "sheet_door": {
        "name": "🔩 Металлическая дверь",
        "category": "Двери",
        "health": "250 HP",
        "craft": {
            "Фрагменты металла": 150
        },
    },

    "garage_door": {
        "name": "🚗 Гаражная дверь",
        "category": "Двери",
        "health": "600 HP",
        "craft": {
            "Фрагменты металла": 300,
            "Шестерёнки": 2,
        },
    },

    "armored_door": {
        "name": "🛡 МВК дверь",
        "category": "Двери",
        "health": "800 HP",
        "craft": {
            "Металл высокого качества": 20,
        },
    },

    "wood_wall": {
        "name": "🪵 Деревянная стена",
        "category": "Стены",
        "health": "250 HP",
        "craft": {
            "Дерево": 100,
        },
    },

    "stone_wall": {
        "name": "🪨 Каменная стена",
        "category": "Стены",
        "health": "500 HP",
        "craft": {
            "Камень": 300,
        },
    },

    "metal_wall": {
        "name": "🔩 Металлическая стена",
        "category": "Стены",
        "health": "1000 HP",
        "craft": {
            "Фрагменты металла": 200,
        },
    },

    "armored_wall": {
        "name": "🛡 МВК стена",
        "category": "Стены",
        "health": "2000 HP",
        "craft": {
            "Металл высокого качества": 25,
        },
    },
}


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ КНОПКИ
# =========================================================

def button(text, callback):
    return InlineKeyboardButton(text, callback_data=callback)


def navigation(back="rust"):
    return [
        [
            button("⬅️ Назад", back),
            button("🏠 Меню", "home"),
        ]
    ]


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def main_menu():
    return InlineKeyboardMarkup([
        [button("🎮 RUST", "rust")],
        [button("🤖 ИИ-помощник", "ai")],
        [button("ℹ️ О боте", "about")],
    ])


# =========================================================
# МЕНЮ RUST
# =========================================================

def rust_menu():
    return InlineKeyboardMarkup([
        [button("💥 Рейд", "raid")],
        [button("🔨 Крафт", "craft")],
        [button("🏗 Строительство", "building")],
        [button("📖 Справочник", "guide")],
        [button("🏠 Главное меню", "home")],
    ])


# =========================================================
# МЕНЮ РЕЙДА
# =========================================================

def raid_menu():
    return InlineKeyboardMarkup([
        [button("🚪 Двери", "raid_doors")],
        [button("🧱 Стены", "raid_walls")],
        [button("🪟 Окна", "raid_windows")],
        [button("🛡 Решётки", "raid_bars")],
        *navigation("rust"),
    ])


# =========================================================
# ДВЕРИ
# =========================================================

def doors_menu():
    return InlineKeyboardMarkup([
        [button("🪵 Деревянная дверь", "item_wood_door")],
        [button("🔩 Металлическая дверь", "item_sheet_door")],
        [button("🚗 Гаражная дверь", "item_garage_door")],
        [button("🛡 МВК дверь", "item_armored_door")],
        *navigation("raid"),
    ])


# =========================================================
# СТЕНЫ
# =========================================================

def walls_menu():
    return InlineKeyboardMarkup([
        [button("🪵 Деревянная стена", "item_wood_wall")],
        [button("🪨 Каменная стена", "item_stone_wall")],
        [button("🔩 Металлическая стена", "item_metal_wall")],
        [button("🛡 МВК стена", "item_armored_wall")],
        *navigation("raid"),
    ])


# =========================================================
# ОКНА
# =========================================================

def windows_menu():
    return InlineKeyboardMarkup([
        [button("🪵 Деревянный проём", "window_wood")],
        [button("🪨 Каменный проём", "window_stone")],
        [button("🔩 Металлический проём", "window_metal")],
        [button("🛡 МВК проём", "window_armored")],
        *navigation("raid"),
    ])


# =========================================================
# РЕШЁТКИ
# =========================================================

def bars_menu():
    return InlineKeyboardMarkup([
        [button("🔩 Металлическая решётка", "bars_metal")],
        [button("🛡 Усиленная решётка", "bars_armored")],
        *navigation("raid"),
    ])


# =========================================================
# КРАФТ
# =========================================================

def craft_menu():
    return InlineKeyboardMarkup([
        [button("⛏ Ресурсы", "resources")],
        [button("🔨 Инструменты", "tools")],
        [button("🔫 Оружие", "weapons")],
        [button("🏠 Строительство", "building")],
        *navigation("rust"),
    ])


# =========================================================
# СТРОИТЕЛЬСТВО
# =========================================================

def building_menu():
    return InlineKeyboardMarkup([
        [button("🧱 Фундаменты", "foundations")],
        [button("🧱 Стены", "raid_walls")],
        [button("🔲 Потолки", "ceilings")],
        [button("🪟 Проёмы", "raid_windows")],
        *navigation("rust"),
    ])


# =========================================================
# ПОКАЗ ПРЕДМЕТА
# =========================================================

def item_keyboard(item_id):
    return InlineKeyboardMarkup([
        [
            button("➕ Количество", f"qty_{item_id}")
        ],
        [
            button("🔨 Крафт", f"craft_item_{item_id}")
        ],
        [
            button("⬅️ Назад", "raid"),
            button("🏠 Меню", "home"),
        ]
    ])


def item_text(item_id):
    item = ITEMS[item_id]

    text = (
        f"{item['name']}\n\n"
        f"📂 Категория: {item['category']}\n"
        f"❤️ Прочность: {item['health']}\n\n"
        f"🔨 Рецепт крафта:\n"
    )

    for resource, amount in item["craft"].items():
        text += f"• {resource}: {amount}\n"

    text += "\nВыбери действие ниже."

    return text


# =========================================================
# КОЛИЧЕСТВО
# =========================================================

def quantity_menu(item_id):
    return InlineKeyboardMarkup([
        [
            button("1", f"calc_{item_id}_1"),
            button("2", f"calc_{item_id}_2"),
            button("5", f"calc_{item_id}_5"),
        ],
        [
            button("10", f"calc_{item_id}_10"),
            button("20", f"calc_{item_id}_20"),
        ],
        [
            button("⬅️ Назад", f"item_{item_id}"),
            button("🏠 Меню", "home"),
        ],
    ])


# =========================================================
# КАЛЬКУЛЯТОР КРАФТА
# =========================================================

def calculate_craft(item_id, quantity):
    item = ITEMS[item_id]

    text = (
        f"🧮 КАЛЬКУЛЯТОР КРАФТА\n\n"
        f"{item['name']}\n"
        f"Количество: {quantity}\n\n"
        f"📦 Всего понадобится:\n"
    )

    for resource, amount in item["craft"].items():
        total = amount * quantity
        text += f"• {resource}: {total}\n"

    return text


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "🤖 Я помощник по Rust.\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu()
    )


# =========================================================
# ОБРАБОТКА КНОПОК
# =========================================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data


    # Главное меню
    if data == "home":

        await query.edit_message_text(
            "🏠 ГЛАВНОЕ МЕНЮ\n\n"
            "Выбери раздел:",
            reply_markup=main_menu()
        )

        return


    # RUST
    if data == "rust":

        await query.edit_message_text(
            "🎮 RUST\n\n"
            "Выбери раздел:",
            reply_markup=rust_menu()
        )

        return


    # РЕЙД
    if data == "raid":

        await query.edit_message_text(
            "💥 РЕЙД\n\n"
            "Выбери категорию:",
            reply_markup=raid_menu()
        )

        return


    # ДВЕРИ
    if data == "raid_doors":

        await query.edit_message_text(
            "🚪 ДВЕРИ\n\n"
            "Выбери дверь:",
            reply_markup=doors_menu()
        )

        return


    # СТЕНЫ
    if data == "raid_walls":

        await query.edit_message_text(
            "🧱 СТЕНЫ\n\n"
            "Выбери стену:",
            reply_markup=walls_menu()
        )

        return


    # ОКНА
    if data == "raid_windows":

        await query.edit_message_text(
            "🪟 ОКНА И ПРОЁМЫ\n\n"
            "Выбери объект:",
            reply_markup=windows_menu()
        )

        return


    # РЕШЁТКИ
    if data == "raid_bars":

        await query.edit_message_text(
            "🛡 РЕШЁТКИ\n\n"
            "Выбери объект:",
            reply_markup=bars_menu()
        )

        return


    # ПРЕДМЕТЫ
    if data.startswith("item_"):

        item_id = data.replace("item_", "")

        if item_id in ITEMS:

            await query.edit_message_text(
                item_text(item_id),
                reply_markup=item_keyboard(item_id)
            )

            return


    # КОЛИЧЕСТВО
    if data.startswith("qty_"):

        item_id = data.replace("qty_", "")

        if item_id in ITEMS:

            await query.edit_message_text(
                "🧮 Выбери количество:",
                reply_markup=quantity_menu(item_id)
            )

            return


    # РАСЧЁТ
    if data.startswith("calc_"):

        parts = data.split("_")

        item_id = "_".join(parts[1:-1])
        quantity = int(parts[-1])

        if item_id in ITEMS:

            await query.edit_message_text(
                calculate_craft(item_id, quantity),
                reply_markup=InlineKeyboardMarkup([
                    [
                        button("🔄 Ещё раз", f"qty_{item_id}")
                    ],
                    [
                        button("⬅️ Назад", f"item_{item_id}"),
                        button("🏠 Меню", "home"),
                    ]
                ])
            )

            return


    # КРАФТ
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
            "Кирка\n"
            "Каменный топор\n"
            "Металлическая кирка\n"
            "Металлический топор",
            reply_markup=craft_menu()
        )

        return


    if data == "weapons":

        await query.edit_message_text(
            "🔫 ОРУЖИЕ\n\n"
            "Здесь будет справочник оружия Rust.",
            reply_markup=craft_menu()
        )

        return


    # СТРОИТЕЛЬСТВО
    if data == "building":

        await query.edit_message_text(
            "🏗 СТРОИТЕЛЬСТВО\n\n"
            "Выбери раздел:",
            reply_markup=building_menu()
        )

        return


    if data == "foundations":

        await query.edit_message_text(
            "🧱 ФУНДАМЕНТЫ\n\n"
            "Основные элементы строительства базы.",
            reply_markup=building_menu()
        )

        return


    if data == "ceilings":

        await query.edit_message_text(
            "🔲 ПОТОЛКИ\n\n"
            "Элементы верхней части базы.",
            reply_markup=building_menu()
        )

        return


    # СПРАВОЧНИК
    if data == "guide":

        await query.edit_message_text(
            "📖 СПРАВОЧНИК RUST\n\n"
            "Здесь находятся игровые характеристики,\n"
            "ресурсы и рецепты.",
            reply_markup=rust_menu()
        )

        return


    # ИИ
    if data == "ai":

        await query.edit_message_text(
            "🤖 ИИ-ПОМОЩНИК\n\n"
            "Напиши мне любой вопрос сообщением.\n\n"
            "Например:\n"
            "«Как работает верстак в Rust?»",
            reply_markup=InlineKeyboardMarkup([
                [
                    button("🏠 Меню", "home")
                ]
            ])
        )

        return


    # О БОТЕ
    if data == "about":

        await query.edit_message_text(
            "🤖 RUST AI BOT\n\n"
            "Помощник по Rust с меню,\n"
            "справочником и ИИ.",
            reply_markup=InlineKeyboardMarkup([
                [
                    button("🏠 Меню", "home")
                ]
            ])
        )

        return


    # ОКНА
    if data.startswith("window_"):

        await query.edit_message_text(
            "🪟 ОБЪЕКТ\n\n"
            "Справочная информация об элементе "
            "строительства.",
            reply_markup=windows_menu()
        )

        return


    # РЕШЁТКИ
    if data.startswith("bars_"):

        await query.edit_message_text(
            "🛡 РЕШЁТКА\n\n"
            "Справочная информация об элементе "
            "строительства.",
            reply_markup=bars_menu()
        )

        return


# =========================================================
# ИИ
# =========================================================

def ask_ai(question):

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
                    "Ты дружелюбный помощник по Rust. "
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
            f"Hugging Face HTTP {response.status_code}: "
            f"{response.text}"
        )

    result = response.json()

    return result["choices"][0]["message"]["content"]


# =========================================================
# СООБЩЕНИЯ ДЛЯ ИИ
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

            for i in range(0, len(answer), 4000):

                await update.message.reply_text(
                    answer[i:i + 4000]
                )

    except Exception as error:

        print("ОШИБКА ИИ:")
        print(error)

        await update.message.reply_text(
            "❌ ИИ временно не смог ответить.\n\n"
            "Проверь HF_TOKEN и попробуй ещё раз."
        )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN не найден.")
        return

    if not HF_TOKEN:
        print("❌ HF_TOKEN не найден.")
        return

    app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ai_message
        )
    )

    print("================================")
    print("🤖 RUST AI BOT ЗАПУЩЕН!")
    print("================================")

    app.run_polling()


if __name__ == "__main__":
    main()
