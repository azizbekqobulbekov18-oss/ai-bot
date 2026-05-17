#!/usr/bin/env python3
"""
🤖 Universal AI Bot - 21 asr uchun
AI: OpenAI GPT-4o
Limit: Kuniga 50 ta so'rov (bepul)
"""

import os
import logging
import asyncio
import httpx
from datetime import date
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────────────────
#  SOZLAMALAR
# ─────────────────────────────────────────────────────────
BOT_TOKEN   = "8122376054:AAHRHshDb37xO87mn9kQR6AAk12u2ETXXMs"
OPENAI_KEY  = "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"
ADMIN_IDS   = [8397484222]
DAILY_LIMIT = 50

# ─────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
#  XOTIRA
# ─────────────────────────────────────────────────────────
users_db: dict = {}
stats_db = dict(total=0, users=0, images=0)

# ─────────────────────────────────────────────────────────
#  REJIMLAR
# ─────────────────────────────────────────────────────────
MODES = {
    "chat":      "💬",
    "translate": "🌐",
    "write":     "📝",
    "analyze":   "📊",
    "image":     "🎨",
    "code":      "💻",
    "summarize": "📋",
    "math":      "🔢",
}

MODE_NAMES = {
    "chat":      {"uz": "Suhbat",      "ru": "Чат",         "en": "Chat"},
    "translate": {"uz": "Tarjima",     "ru": "Перевод",     "en": "Translate"},
    "write":     {"uz": "Matn yozish", "ru": "Написать",    "en": "Write"},
    "analyze":   {"uz": "Tahlil",      "ru": "Анализ",      "en": "Analyze"},
    "image":     {"uz": "Rasm",        "ru": "Изображение", "en": "Image"},
    "code":      {"uz": "Kod",         "ru": "Код",         "en": "Code"},
    "summarize": {"uz": "Xulosa",      "ru": "Резюме",      "en": "Summarize"},
    "math":      {"uz": "Matematik",   "ru": "Математика",  "en": "Math"},
}

MODE_PROMPTS = {
    "chat":      "You are a helpful, friendly AI assistant. Answer clearly in the same language the user writes in.",
    "translate": "You are a professional translator. Detect the source language and translate to Uzbek unless user specifies otherwise. Provide only the translation.",
    "write":     "You are a professional writer. Write high-quality, engaging content based on the user's request.",
    "analyze":   "You are an expert analyst. Analyze the given text and provide clear, structured insights.",
    "code":      "You are an expert programmer. Write clean, efficient, well-commented code and briefly explain it.",
    "summarize": "You are a summarization expert. Provide a clear, concise summary with all key points.",
    "math":      "You are a mathematics expert. Solve step by step, showing all work. Verify the answer.",
    "image":     "",
}

# ─────────────────────────────────────────────────────────
#  TARJIMALAR
# ─────────────────────────────────────────────────────────
TX = {
    "uz": {
        "welcome": (
            "🤖 <b>Universal AI Botga Xush Kelibsiz!</b>\n\n"
            "💬 Suhbat va savollar\n"
            "🌐 Tarjima (100+ til)\n"
            "📝 Matn va esse yozish\n"
            "📊 Matn tahlili\n"
            "🎨 Rasm generatsiya\n"
            "💻 Kod yozish\n"
            "📋 Xulosa chiqarish\n"
            "🔢 Matematik masalalar\n\n"
            f"🎁 Kuniga <b>{DAILY_LIMIT} ta</b> so'rov bepul!\n\n"
            "👇 Rejim tanlang yoki shunchaki yozing:"
        ),
        "choose_lang":     "🌐 Tilni tanlang:",
        "choose_mode":     "🎯 Rejimni tanlang:",
        "mode_set":        "✅ Rejim: {mode}\n\nSavolingizni yuboring:",
        "thinking":        "🤔 O'ylamoqda...",
        "generating":      "🎨 Rasm yaratilmoqda...",
        "limit_reached":   f"⚠️ Kunlik limitingiz tugadi ({DAILY_LIMIT} ta).\n🕛 Ertaga yangilanadi!",
        "remaining":       "📊 Bugun qolgan: <b>{n}/{limit}</b> so'rov",
        "error":           "❌ Xatolik yuz berdi. Qaytadan urining.",
        "image_error":     "❌ Rasm yaratib bo'lmadi. Boshqa so'rov yuboring.",
        "not_admin":       "❌ Siz admin emassiz.",
        "history_cleared": "🗑 Suhbat tarixi tozalandi!",
        "help": (
            "📖 <b>Yordam</b>\n\n"
            "/start — Bosh menyu\n"
            "/mode  — Rejim tanlash\n"
            "/lang  — Til o'zgartirish\n"
            "/limit — Qolgan so'rovlar\n"
            "/clear — Tarixni tozalash\n"
            "/stats — Statistika (admin)\n\n"
            "💡 Shunchaki yozsangiz ham ishlaydi!"
        ),
        "stats": (
            "📊 <b>Statistika</b>\n\n"
            "👤 Foydalanuvchilar : {users}\n"
            "📥 Jami so'rovlar   : {total}\n"
            "🎨 Rasmlar          : {images}"
        ),
    },
    "ru": {
        "welcome": (
            "🤖 <b>Добро пожаловать в Universal AI Bot!</b>\n\n"
            "💬 Чат и вопросы\n"
            "🌐 Перевод (100+ языков)\n"
            "📝 Написание текстов\n"
            "📊 Анализ текста\n"
            "🎨 Генерация изображений\n"
            "💻 Написание кода\n"
            "📋 Резюмирование\n"
            "🔢 Математика\n\n"
            f"🎁 <b>{DAILY_LIMIT} запросов</b> в день бесплатно!\n\n"
            "👇 Выберите режим или просто напишите:"
        ),
        "choose_lang":     "🌐 Выберите язык:",
        "choose_mode":     "🎯 Выберите режим:",
        "mode_set":        "✅ Режим: {mode}\n\nОтправьте запрос:",
        "thinking":        "🤔 Думаю...",
        "generating":      "🎨 Создаю изображение...",
        "limit_reached":   f"⚠️ Лимит исчерпан ({DAILY_LIMIT} запросов).\n🕛 Обновится завтра!",
        "remaining":       "📊 Осталось: <b>{n}/{limit}</b> запросов",
        "error":           "❌ Произошла ошибка. Попробуйте снова.",
        "image_error":     "❌ Не удалось создать изображение.",
        "not_admin":       "❌ Вы не администратор.",
        "history_cleared": "🗑 История очищена!",
        "help": (
            "📖 <b>Помощь</b>\n\n"
            "/start — Главное меню\n"
            "/mode  — Выбор режима\n"
            "/lang  — Сменить язык\n"
            "/limit — Оставшиеся запросы\n"
            "/clear — Очистить историю\n"
            "/stats — Статистика (admin)\n\n"
            "💡 Просто напишите — и я отвечу!"
        ),
        "stats": (
            "📊 <b>Статистика</b>\n\n"
            "👤 Пользователи  : {users}\n"
            "📥 Всего запросов: {total}\n"
            "🎨 Изображения   : {images}"
        ),
    },
    "en": {
        "welcome": (
            "🤖 <b>Welcome to Universal AI Bot!</b>\n\n"
            "💬 Chat and questions\n"
            "🌐 Translation (100+ languages)\n"
            "📝 Writing texts\n"
            "📊 Text analysis\n"
            "🎨 Image generation\n"
            "💻 Code writing\n"
            "📋 Summarization\n"
            "🔢 Math problems\n\n"
            f"🎁 <b>{DAILY_LIMIT} requests</b> per day — free!\n\n"
            "👇 Choose a mode or just type:"
        ),
        "choose_lang":     "🌐 Choose your language:",
        "choose_mode":     "🎯 Choose a mode:",
        "mode_set":        "✅ Mode: {mode}\n\nSend your request:",
        "thinking":        "🤔 Thinking...",
        "generating":      "🎨 Generating image...",
        "limit_reached":   f"⚠️ Daily limit reached ({DAILY_LIMIT}).\n🕛 Resets tomorrow!",
        "remaining":       "📊 Remaining: <b>{n}/{limit}</b> requests",
        "error":           "❌ An error occurred. Please try again.",
        "image_error":     "❌ Could not generate image. Try another prompt.",
        "not_admin":       "❌ You are not an admin.",
        "history_cleared": "🗑 Chat history cleared!",
        "help": (
            "📖 <b>Help</b>\n\n"
            "/start — Main menu\n"
            "/mode  — Choose mode\n"
            "/lang  — Change language\n"
            "/limit — Remaining requests\n"
            "/clear — Clear history\n"
            "/stats — Statistics (admin)\n\n"
            "💡 Just type anything and I'll respond!"
        ),
        "stats": (
            "📊 <b>Statistics</b>\n\n"
            "👤 Users          : {users}\n"
            "📥 Total requests : {total}\n"
            "🎨 Images         : {images}"
        ),
    },
}

# ─────────────────────────────────────────────────────────
#  YORDAMCHI
# ─────────────────────────────────────────────────────────
def get_user(uid: int) -> dict:
    if uid not in users_db:
        users_db[uid] = {"lang": "uz", "mode": "chat", "count": 0,
                         "day": str(date.today()), "history": []}
        stats_db["users"] += 1
    u = users_db[uid]
    if u["day"] != str(date.today()):
        u["count"] = 0
        u["day"] = str(date.today())
    return u

def lng(uid): return users_db.get(uid, {}).get("lang", "uz")

def tx(uid, key, **kw):
    text = TX.get(lng(uid), TX["uz"]).get(key, key)
    return text.format(**kw) if kw else text

def mode_label(uid, mode):
    return f"{MODES.get(mode,'💬')} {MODE_NAMES.get(mode,{}).get(lng(uid), mode)}"

def lang_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇺🇿 O'zbek",  callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

def mode_kb(uid):
    keys = list(MODES.keys())
    rows = []
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(mode_label(uid, k), callback_data=f"mode_{k}")
               for k in keys[i:i+2]]
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def main_kb(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Rejim", callback_data="open_mode"),
         InlineKeyboardButton("🌐 Til",   callback_data="open_lang")],
        [InlineKeyboardButton("📊 Limit", callback_data="open_limit"),
         InlineKeyboardButton("🗑 Tozala", callback_data="do_clear")],
    ])

# ─────────────────────────────────────────────────────────
#  GPT + DALL-E
# ─────────────────────────────────────────────────────────
async def ask_gpt(system, history, user_msg):
    messages = [{"role": "system", "content": system}]
    messages += history[-10:]
    messages.append({"role": "user", "content": user_msg})
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            json={"model": "gpt-4o", "messages": messages, "max_tokens": 2000},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

async def gen_image(prompt):
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024"},
        )
        r.raise_for_status()
        return r.json()["data"][0]["url"]

# ─────────────────────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    await update.message.reply_text(tx(uid, "welcome"), parse_mode="HTML",
                                    reply_markup=main_kb(uid))

async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    await update.message.reply_text(tx(uid, "choose_mode"), reply_markup=mode_kb(uid))

async def cmd_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    await update.message.reply_text(tx(uid, "choose_lang"), reply_markup=lang_kb())

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    await update.message.reply_text(tx(uid, "help"), parse_mode="HTML")

async def cmd_limit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    await update.message.reply_text(
        tx(uid, "remaining", n=DAILY_LIMIT - u["count"], limit=DAILY_LIMIT),
        parse_mode="HTML")

async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    users_db[uid]["history"] = []
    await update.message.reply_text(tx(uid, "history_cleared"))

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    if uid not in ADMIN_IDS:
        await update.message.reply_text(tx(uid, "not_admin"))
        return
    await update.message.reply_text(
        tx(uid, "stats", users=stats_db["users"],
           total=stats_db["total"], images=stats_db["images"]),
        parse_mode="HTML")

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    text = update.message.text.strip()

    if u["count"] >= DAILY_LIMIT:
        await update.message.reply_text(tx(uid, "limit_reached"))
        return

    mode = u.get("mode", "chat")

    if mode == "image":
        msg = await update.message.reply_text(tx(uid, "generating"))
        try:
            url = await gen_image(text)
            u["count"] += 1
            stats_db["total"] += 1
            stats_db["images"] += 1
            await msg.delete()
            await update.message.reply_photo(url, caption=f"🎨 {text[:100]}")
        except Exception as e:
            logger.error(f"Image error: {e}")
            await msg.edit_text(tx(uid, "image_error"))
        return

    msg = await update.message.reply_text(tx(uid, "thinking"))
    history = u.get("history", [])

    try:
        answer = await ask_gpt(MODE_PROMPTS.get(mode, MODE_PROMPTS["chat"]), history, text)
        history.append({"role": "user",      "content": text})
        history.append({"role": "assistant", "content": answer})
        users_db[uid]["history"] = history[-20:]
        u["count"] += 1
        stats_db["total"] += 1

        remaining = DAILY_LIMIT - u["count"]
        l = lng(uid)
        if l == "uz":   footer = f"\n\n─────\n📊 {remaining}/{DAILY_LIMIT} so'rov qoldi"
        elif l == "ru": footer = f"\n\n─────\n📊 Осталось {remaining}/{DAILY_LIMIT}"
        else:           footer = f"\n\n─────\n📊 {remaining}/{DAILY_LIMIT} left"

        await msg.edit_text(answer + footer)
    except Exception as e:
        logger.error(f"GPT error: {e}")
        await msg.edit_text(tx(uid, "error"))

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    get_user(uid)
    await query.answer()

    if data == "open_mode":
        await query.edit_message_text(tx(uid, "choose_mode"), reply_markup=mode_kb(uid))
    elif data == "open_lang":
        await query.edit_message_text(tx(uid, "choose_lang"), reply_markup=lang_kb())
    elif data == "open_limit":
        u = users_db[uid]
        await query.edit_message_text(
            tx(uid, "remaining", n=DAILY_LIMIT - u["count"], limit=DAILY_LIMIT),
            parse_mode="HTML")
    elif data == "do_clear":
        users_db[uid]["history"] = []
        await query.edit_message_text(tx(uid, "history_cleared"))
    elif data.startswith("lang_"):
        users_db[uid]["lang"] = data.split("_")[1]
        await query.edit_message_text(tx(uid, "welcome"), parse_mode="HTML",
                                      reply_markup=main_kb(uid))
    elif data.startswith("mode_"):
        mode = data.split("_", 1)[1]
        users_db[uid]["mode"] = mode
        await query.edit_message_text(
            tx(uid, "mode_set", mode=mode_label(uid, mode)), parse_mode="HTML")

# ─────────────────────────────────────────────────────────
#  ISHGA TUSHIRISH
# ─────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("mode",  cmd_mode))
    app.add_handler(CommandHandler("lang",  cmd_lang))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("limit", cmd_limit))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    logger.info("🤖 Universal AI Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
