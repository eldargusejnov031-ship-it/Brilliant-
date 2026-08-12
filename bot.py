import telebot
from telebot import types
from openai import OpenAI

BOT_TOKEN = 'ТВОЙ_TELEGRAM_BOT_TOKEN'
OPENAI_TOKEN = 'ТВОЙ_OPENAI_API_KEY'

bot = telebot.TeleBot(BOT_TOKEN)
ai_client = OpenAI(api_key=OPENAI_TOKEN)

# Ресурсы на 1 шт. взрывчатки
EXPLOSIVES_CRAFT = {
    "satchel": {"name": "💣 Сатчель", "sulfur": 480, "charcoal": 720, "metal": 80},
    "c4": {"name": "💥 C4", "sulfur": 2200, "charcoal": 3000, "metal": 200},
    "rocket": {"name": "🚀 Ракета", "sulfur": 1400, "charcoal": 1950, "metal": 100},
    "explosive_ammo": {"name": "💥 Разрывные патроны", "sulfur": 10, "charcoal": 15, "metal": 5}
}

# Количество взрывчатки для разрушения
RAID_REQ = {
    # Двери
    "wood_door": {"name": "Деревянная дверь", "satchel": 2, "c4": 1, "rocket": 1, "explosive_ammo": 18},
    "sheet_door": {"name": "Жестяная дверь", "satchel": 4, "c4": 1, "rocket": 2, "explosive_ammo": 63},
    "garage_door": {"name": "Гаражная дверь", "satchel": 9, "c4": 2, "rocket": 3, "explosive_ammo": 150},
    "armored_door": {"name": "МВК дверь", "satchel": 12, "c4": 2, "rocket": 4, "explosive_ammo": 200},
    
    # Стены
    "wood_wall": {"name": "Деревянная стена", "satchel": 3, "c4": 1, "rocket": 2, "explosive_ammo": 49},
    "stone_wall": {"name": "Каменная стена", "satchel": 10, "c4": 2, "rocket": 4, "explosive_ammo": 185},
    "metal_wall": {"name": "Металлическая стена", "satchel": 23, "c4": 4, "rocket": 8, "explosive_ammo": 400},
    "armored_wall": {"name": "МВК стена", "satchel": 46, "c4": 8, "rocket": 15, "explosive_ammo": 799},
    
    # Окна и Решетки
    "glass_window": {"name": "Укрепленное стекло", "satchel": 4, "c4": 1, "rocket": 2, "explosive_ammo": 55},
    "grate_window": {"name": "Решётка на окно", "satchel": 4, "c4": 1, "rocket": 2, "explosive_ammo": 55}
}

# Главное меню внизу чата
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🤖 Задать вопрос ИИ", "🔥 Rust")
    return keyboard

# Меню раздела Rust
def get_rust_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💥 Рейд калькулятор", callback_data="rust_raid"))
    return kb

# Категории рейда
def get_categories_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🚪 Двери", callback_data="cat_doors"),
        types.InlineKeyboardButton("🧱 Стены", callback_data="cat_walls"),
        types.InlineKeyboardButton("🪟 Окна и Решётки", callback_data="cat_windows")
    )
    return kb

# Объекты в категориях
def get_objects_kb(category):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if category == "cat_doors":
        kb.add(
            types.InlineKeyboardButton("Деревянная", callback_data="obj_wood_door"),
            types.InlineKeyboardButton("Жестяная", callback_data="obj_sheet_door"),
            types.InlineKeyboardButton("Гаражная", callback_data="obj_garage_door"),
            types.InlineKeyboardButton("МВК", callback_data="obj_armored_door")
        )
    elif category == "cat_walls":
        kb.add(
            types.InlineKeyboardButton("Дерево", callback_data="obj_wood_wall"),
            types.InlineKeyboardButton("Камень", callback_data="obj_stone_wall"),
            types.InlineKeyboardButton("Металл", callback_data="obj_metal_wall"),
            types.InlineKeyboardButton("МВК", callback_data="obj_armored_wall")
        )
    elif category == "cat_windows":
        kb.add(
            types.InlineKeyboardButton("Стекло", callback_data="obj_glass_window"),
            types.InlineKeyboardButton("Решётка", callback_data="obj_grate_window")
        )
    kb.add(types.InlineKeyboardButton("⬅️ Назад к категориям", callback_data="rust_raid"))
    return kb

# Выбор типа взрывчатки
def get_ammo_kb(obj_key):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💣 Сатчели", callback_data=f"calc_{obj_key}_satchel"),
        types.InlineKeyboardButton("💥 C4", callback_data=f"calc_{obj_key}_c4"),
        types.InlineKeyboardButton("🚀 Ракеты", callback_data=f"calc_{obj_key}_rocket"),
        types.InlineKeyboardButton("💥 Разрывные", callback_data=f"calc_{obj_key}_explosive_ammo")
    )
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="rust_raid"))
    return kb

# --- ОБРАБОТКА КОМАНД И КНОПОК ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        "Привет! Выбери нужный раздел в меню ниже 👇",
        reply_markup=get_main_keyboard()
    )

# Кнопка ИИ
@bot.message_handler(func=lambda msg: msg.text == "🤖 Задать вопрос ИИ")
def ai_button_handler(message):
    bot.send_message(
        message.chat.id, 
        "Напиши свой вопрос, и ИИ на него ответит!"
    )

# Кнопка Rust
@bot.message_handler(func=lambda msg: msg.text == "🔥 Rust")
def rust_button_handler(message):
    bot.send_message(
        message.chat.id, 
        "Выбери раздел Rust:", 
        reply_markup=get_rust_menu()
    )

# Инлайн-переходы (Калькулятор)
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data

    if data == "rust_raid":
        bot.edit_message_text("Выбери категорию объекта:", call.message.chat.id, call.message.message_id, reply_markup=get_categories_kb())
    
    elif data.startswith("cat_"):
        bot.edit_message_text("Выбери объект:", call.message.chat.id, call.message.message_id, reply_markup=get_objects_kb(data))
    
    elif data.startswith("obj_"):
        obj_key = data.replace("obj_", "")
        obj_name = RAID_REQ[obj_key]["name"]
        bot.edit_message_text(
            f"Объект: **{obj_name}**\nЧем будешь рейдить?", 
            call.message.chat.id, 
            call.message.message_id, 
            parse_mode="Markdown",
            reply_markup=get_ammo_kb(obj_key)
        )
    
    elif data.startswith("calc_"):
        _, obj_key, ammo_type = data.split("_", 2)
        
        count = RAID_REQ[obj_key][ammo_type]
        ammo_info = EXPLOSIVES_CRAFT[ammo_type]
        obj_name = RAID_REQ[obj_key]["name"]
        
        total_sulfur = count * ammo_info["sulfur"]
        total_charcoal = count * ammo_info["charcoal"]
        total_metal = count * ammo_info["metal"]

        text = (
            f"🎯 **Цель:** {obj_name}\n"
            f"🛠 **Используем:** {ammo_info['name']}\n"
            f"----------------------------------------\n"
            f"📦 **Нужно штук:** `{count}` шт.\n\n"
            f"📄 **Ресурсы для крафта:**\n"
            f"🟡 Сера: `{total_sulfur}` шт.\n"
            f"⚫ Уголь: `{total_charcoal}` шт.\n"
            f"🔘 Металл: `{total_metal}` шт."
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Изменить взрывчатку", callback_data=f"obj_{obj_key}"))
        kb.add(types.InlineKeyboardButton("🏠 В категории", callback_data="rust_raid"))

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)

# Ответ ИИ на любой другой текст
@bot.message_handler(func=lambda msg: True)
def handle_ai(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": message.text}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception:
        bot.reply_to(message, "Ошибка при запросе к ИИ.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
    
