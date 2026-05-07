import subprocess
import sys
import os

required_packages = ["python-telegram-bot==20.6", "openai"]
for package in required_packages:
    try:
        module_name = package.split("==")[0]
        if module_name == "python-telegram-bot":
            module_name = "telegram"
        elif module_name == "openai":
            module_name = "openai"
        
        __import__(module_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import json
import asyncio
import random
import functools
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

BOT_TOKEN = "your_bot_token"
OPENROUTER_API_KEY = "your_openrouter_api_key"
DEVELOPER_NAME = "developer_name"
BOT_NAME = "NOVALIS"
GROUP_FILE = "bot_group.json"
MEMORY_FOLDER = "user_memory"
os.makedirs(MEMORY_FOLDER, exist_ok=True)

SYSTEM_PROMPT = f"""
أنت بوت مطوّرك هو {DEVELOPER_NAME}.
عرّف باسمك : {BOT_NAME}.
كن ذكياً ومفيداً في ردودك.
"""

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

def get_memory_path(user_id):
    return os.path.join(MEMORY_FOLDER, f"{user_id}.json")

def load_memory(user_id):
    path = get_memory_path(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def add_to_memory(user_id, user_msg, bot_msg, user_name):
    memory = load_memory(user_id)
    memory.append({"user": user_msg, "bot": bot_msg, "name": user_name})
    if len(memory) > 10:
        memory.pop(0)
    with open(get_memory_path(user_id), "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"أهلاً! أنا {BOT_NAME}. كيف يمكنني مساعدتك اليوم؟")

async def developer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"هذا البوت تم تطويره بواسطة {DEVELOPER_NAME}.")

async def what_is_this(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أنا نموذج ذكاء اصطناعي مخصص للدردشة والمساعدة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_text = update.message.text

    typing_task = asyncio.create_task(context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING))
    
    try:
        memory = load_memory(user_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for entry in memory:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["bot"]})

        messages.append({"role": "user", "content": user_text})

        reply_text = await asyncio.to_thread(functools.partial(
            lambda: client.chat.completions.create(
                model="x-ai/grok-beta:free",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            ).choices[0].message.content
        ))
    except Exception as e:
        reply_text = f"حدث خطأ: {e}"
    finally:
        typing_task.cancel()

    add_to_memory(user_id, user_text, reply_text, user_name)
    await update.message.reply_text(reply_text)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("Developer", developer))
    app.add_handler(CommandHandler("what_is_this", what_is_this))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
