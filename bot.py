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
    filters
)


# =========================================================
# ТОКЕНЫ
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")


# =========================================================
# HUGGING FACE
# =========================================================

API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:groq"


# =========================================================
# ИИ
# =========================================================

def ask_ai(question):

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
                    "Ты дружелюбный ИИ-помощник по игре Rust. "
                    "Отвечай на русском языке."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 1000
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=data,
        timeout=60
    )

    if response.status_code != 200:
        print(response.text)
        raise Exception("Ошибка Hugging Face")

    result = response.json()

    return result["choices"][0]["message"]["content"]


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎮 RUST",
                callback_data="rust"
            )
        ],
        [
            InlineKeyboardButton(
                "🤖 ИИ-помощник",
                callback_data="ai"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ О боте",
                callback_data="about"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# МЕНЮ RUST
# =========================================================

def rust_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "💥 Рейд",
                callback_data="raid"
            )
        ],
        [
            InlineKeyboardButton(
                "🧱 Строительство",
                callback_data="building"
            )
        ],
        [
            InlineKeyboardButton(
                "🚪 Двери",
                callback_data="doors"
            )
        ],
        [
            InlineKeyboardButton(
                "🔨 Крафт",
                callback_data="craft"
            )
        ],
        [
            InlineKeyboardButton(
                "📖 Справочник",
                callback_data="guide"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="home"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# МЕНЮ РЕЙДА
# =========================================================

def raid_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🪵 Деревянная стена",
                callback_data="raid_wood"
            )
        ],
        [
            InlineKeyboardButton(
                "🪨 Каменная стена",
                callback_data="raid_stone"
            )
        ],
        [
            InlineKeyboardButton(
                "🔩 Металлическая стена",
                callback_data="raid_metal"
            )
        ],
        [
            InlineKeyboardButton(
                "🛡 Бронированная стена",
                callback_data="raid_hq"
            )
        ],
        [
            InlineKeyboardButton(
                "🚪 Двери",
                callback_data="raid_doors"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="rust"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# МЕНЮ ДВЕРЕЙ В РЕЙДЕ
# =========================================================

def raid_doors_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🚪 Деревянная дверь",
                callback_data="door_wood"
            )
        ],
        [
            InlineKeyboardButton(
                "🔩 Металлическая дверь",
                callback_data="door_metal"
            )
        ],
        [
            InlineKeyboardButton(
                "🚗 Гаражная дверь",
                callback_data="door_garage"
            )
        ],
        [
            InlineKeyboardButton(
                "🛡 Бронированная дверь",
                callback_data="door_hq"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="raid"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# СТРОИТЕЛЬСТВО
# =========================================================

def building_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🧱 Фундаменты",
                callback_data="foundations"
            )
        ],
        [
            InlineKeyboardButton(
                "🧱 Стены",
                callback_data="walls"
            )
        ],
        [
            InlineKeyboardButton(
                "🔲 Потолки",
                callback_data="ceilings"
            )
        ],
        [
            InlineKeyboardButton(
                "🪟 Проёмы",
                callback_data="openings"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="rust"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# КРАФТ
# =========================================================

def craft_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "⛏ Ресурсы",
                callback_data="resources"
            )
        ],
        [
            InlineKeyboardButton(
                "🔨 Инструменты",
                callback_data="tools"
            )
        ],
        [
            InlineKeyboardButton(
                "🔫 Оружие",
                callback_data="weapons"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Строительство",
                callback_data="building"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="rust"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "🤖 Я твой ИИ-помощник по Rust.\n\n"
        "Выбирай нужный раздел:",
        reply_markup=main_menu()
    )


# =========================================================
# /HELP
# =========================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "❓ Помощь\n\n"
        "🎮 RUST — информация об игре\n"
        "💥 Рейд — справочник построек\n"
        "🧱 Строительство — элементы строительства\n"
        "🚪 Двери — виды дверей\n"
        "🔨 Крафт — предметы и ресурсы\n"
        "🤖 ИИ — задавай вопросы"
    )


# =========================================================
# ОБРАБОТКА КНОПОК
# =========================================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data


    # =========================
    # ГЛАВНОЕ
    # =========================

    if data == "home":

        await query.edit_message_text(
            "🏠 Главное меню\n\n"
            "Выбирай раздел:",
            reply_markup=main_menu()
        )


    # =========================
    # RUST
    # =========================

    elif data == "rust":

        await query.edit_message_text(
            "🎮 RUST\n\n"
            "Выбери раздел:",
            reply_markup=rust_menu()
        )


    # =========================
    # РЕЙД
    # =========================

    elif data == "raid":

        await query.edit_message_text(
            "💥 РЕЙД\n\n"
            "Выбери объект:",
            reply_markup=raid_menu()
        )


    elif data == "raid_wood":

        await query.edit_message_text(
            "🪵 ДЕРЕВЯННАЯ СТЕНА\n\n"
            "Тип: строительный элемент\n"
            "Материал: дерево\n\n"
            "Используется для ранних построек.\n\n"
            "ℹ️ Здесь можно посмотреть "
            "характеристики объекта.",
            reply_markup=raid_menu()
        )


    elif data == "raid_stone":

        await query.edit_message_text(
            "🪨 КАМЕННАЯ СТЕНА\n\n"
            "Тип: строительный элемент\n"
            "Материал: камень\n\n"
            "Более прочный вариант стены "
            "по сравнению с деревянной.",
            reply_markup=raid_menu()
        )


    elif data == "raid_metal":

        await query.edit_message_text(
            "🔩 МЕТАЛЛИЧЕСКАЯ СТЕНА\n\n"
            "Тип: строительный элемент\n"
            "Материал: металл\n\n"
            "Используется для усиленной защиты базы.",
            reply_markup=raid_menu()
        )


    elif data == "raid_hq":

        await query.edit_message_text(
            "🛡 БРОНИРОВАННАЯ СТЕНА\n\n"
            "Тип: строительный элемент\n"
            "Материал: высококачественный металл\n\n"
            "Один из самых прочных вариантов "
            "строительства.",
            reply_markup=raid_menu()
        )


    # =========================
    # ДВЕРИ
    # =========================

    elif data == "raid_doors":

        await query.edit_message_text(
            "🚪 ДВЕРИ\n\n"
            "Выбери тип двери:",
            reply_markup=raid_doors_menu()
        )


    elif data == "door_wood":

        await query.edit_message_text(
            "🚪 ДЕРЕВЯННАЯ ДВЕРЬ\n\n"
            "Материал: дерево\n"
            "Тип: дверь\n\n"
            "Подходит для ранних этапов игры.",
            reply_markup=raid_doors_menu()
        )


    elif data == "door_metal":

        await query.edit_message_text(
            "🔩 МЕТАЛЛИЧЕСКАЯ ДВЕРЬ\n\n"
            "Материал: металл\n"
            "Тип: дверь\n\n"
            "Используется для усиленной защиты.",
            reply_markup=raid_doors_menu()
        )


    elif data == "door_garage":

        await query.edit_message_text(
            "🚗 ГАРАЖНАЯ ДВЕРЬ\n\n"
            "Тип: гаражная дверь\n"
            "Используется в больших базах.",
            reply_markup=raid_doors_menu()
        )


    elif data == "door_hq":

        await query.edit_message_text(
            "🛡 БРОНИРОВАННАЯ ДВЕРЬ\n\n"
            "Тип: бронированная дверь\n"
            "Материал: высококачественный металл.",
            reply_markup=raid_doors_menu()
        )


    # =========================
    # СТРОИТЕЛЬСТВО
    # =========================

    elif data == "building":

        await query.edit_message_text(
            "🧱 СТРОИТЕЛЬСТВО\n\n"
            "Выбери категорию:",
            reply_markup=building_menu()
        )


    elif data == "foundations":

        await query.edit_message_text(
            "🧱 ФУНДАМЕНТЫ\n\n"
            "Основные элементы основания базы.",
            reply_markup=building_menu()
        )


    elif data == "walls":

        await query.edit_message_text(
            "🧱 СТЕНЫ\n\n"
            "🪵 Дерево\n"
            "🪨 Камень\n"
            "🔩 Металл\n"
            "🛡 Бронированная",
            reply_markup=building_menu()
        )


    elif data == "ceilings":

        await query.edit_message_text(
            "🔲 ПОТОЛКИ\n\n"
            "Элементы верхней части строительной конструкции.",
            reply_markup=building_menu()
        )


    elif data == "openings":

        await query.edit_message_text(
            "🪟 ПРОЁМЫ\n\n"
            "Дверные и оконные проёмы.",
            reply_markup=building_menu()
        )


    # =========================
    # КРАФТ
    # =========================

    elif data == "craft":

        await query.edit_message_text(
            "🔨 КРАФТ\n\n"
            "Выбери категорию:",
            reply_markup=craft_menu()
        )


    elif data == "resources":

        await query.edit_message_text(
            "⛏ РЕСУРСЫ\n\n"
            "🪵 Дерево\n"
            "🪨 Камень\n"
            "🔩 Фрагменты металла\n"
            "⚙️ Металл высокого качества",
            reply_markup=craft_menu()
        )


    elif data == "tools":

        await query.edit_message_text(
            "🔨 ИНСТРУМЕНТЫ\n\n"
            "Кирки, топоры и другие инструменты.",
            reply_markup=craft_menu()
        )


    elif data == "weapons":

        await query.edit_message_text(
            "🔫 ОРУЖИЕ\n\n"
            "Справочная информация об оружии Rust.",
            reply_markup=craft_menu()
        )


    # =========================
    # СПРАВОЧНИК
    # =========================

    elif data == "guide":

        await query.edit_message_text(
            "📖 СПРАВОЧНИК RUST\n\n"
            "Здесь будет информация об игровых "
            "предметах, постройках, ресурсах "
            "и механиках.",
            reply_markup=rust_menu()
        )


    # =========================
    # ИИ
    # =========================

    elif data == "ai":

        await query.edit_message_text(
            "🤖 ИИ-ПОМОЩНИК\n\n"
            "Просто напиши сообщение в чат, "
            "и я отвечу.",
            reply_markup=main_menu()
        )


    # =========================
    # О БОТЕ
    # =========================

    elif data == "about":

        await query.edit_message_text(
            "🤖 RUST AI BOT\n\n"
            "Помощник по игре Rust.\n\n"
            "🎮 Меню Rust\n"
            "📖 Справочник\n"
            "🔨 Крафт\n"
            "🤖 ИИ-помощник",
            reply_markup=main_menu()
        )


# =========================================================
# СООБЩЕНИЯ
# =========================================================

async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    question = update.message.text

    await update.message.chat.send_action("typing")

    try:

        answer = await asyncio.to_thread(
            ask_ai,
            question
        )

        if len(answer) > 4000:

            for i in range(0, len(answer), 4000):
                await update.message.reply_text(
                    answer[i:i + 4000]
                )

        else:

            await update.message.reply_text(answer)

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
        raise Exception("TELEGRAM_TOKEN не задан")

    if not HF_TOKEN:
        raise Exception("HF_TOKEN не задан")

    app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
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
