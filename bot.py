import os
import asyncio
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:groq"


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
                    "Ты дружелюбный ИИ-помощник. "
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
        print("Hugging Face:", response.status_code)
        print(response.text)
        raise Exception("Ошибка Hugging Face")

    result = response.json()

    return result["choices"][0]["message"]["content"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я твой ИИ-помощник 🤖\n\n"
        "Напиши мне любой вопрос."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Помощь\n\n"
        "Просто напиши мне сообщение, "
        "и я постараюсь ответить."
    )


async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text

    await update.message.chat.send_action("typing")

    try:
        answer = await asyncio.to_thread(
            ask_ai,
            question
        )

        await update.message.reply_text(answer)

    except Exception as error:
        print("ОШИБКА:", error)

        await update.message.reply_text(
            "❌ Не удалось получить ответ от ИИ."
        )


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
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ai_message
        )
    )

    print("🤖 БОТ ЗАПУЩЕН!")

    app.run_polling()


if __name__ == "__main__":
    main()
