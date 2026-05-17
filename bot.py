import os
import io
import logging
import asyncio
import re
import shutil
import json
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
import speech_recognition as sr
from gtts import gTTS
from deep_translator import GoogleTranslator
from pydub import AudioSegment
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_BASE_URL = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
GEMINI_API_KEY = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

_admin_env = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()}

DOWNLOAD_DIR = Path("/tmp/aibot_downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ─── Translations ────────────────────────────────────────────────────────────

TEXTS = {
    "uz": {
        "start": (
            "🤖 <b>AI Super Bot</b>ga xush kelibsiz!\n\n"
            "Men sizga quyidagilarda yordam bera olaman:\n\n"
            "🧠 <b>AI Suhbat</b> — istalgan savol bering, aqlli javob olasiz\n"
            "🎨 <b>Rasm yaratish</b> — /image [tavsif] — AI rasm chizadi\n"
            "🎙 <b>Ovozdan matn</b> — ovozli xabar yuboring, matn olasiz\n"
            "🔊 <b>Matndan ovoz</b> — /speak [matn] — ovozli xabar qaytadi\n"
            "🌐 <b>Tarjima</b> — /translate [til] [matn]\n"
            "🌤 <b>Ob-havo</b> — /weather [shahar]\n"
            "🛡 <b>Admin panel</b> — /admin\n"
            "🌍 <b>Til</b> — /lang\n\n"
            "Boshlash uchun xabar yozing yoki buyruq tanlang!"
        ),
        "help": (
            "📖 <b>Yordam</b>\n\n"
            "🧠 <b>AI Suhbat:</b>\n"
            "Har qanday savol yoki gapni yozing — Gemini AI javob beradi.\n"
            "Suhbat tarixi saqlanadi.\n\n"
            "🎨 <b>Rasm yaratish:</b>\n"
            "/image [tavsif] — masalan: /image tog'lar orasidagi ko'l\n\n"
            "🎙 <b>Ovozdan matn:</b>\n"
            "Ovozli xabar yuboring — bot uni matnga aylantirib beradi.\n\n"
            "🔊 <b>Matndan ovoz:</b>\n"
            "/speak [matn] — bot ovozli xabar yuboradi\n\n"
            "🌐 <b>Tarjima:</b>\n"
            "/translate uz Salom dunyo!\n"
            "/translate en Привет мир\n\n"
            "🌤 <b>Ob-havo:</b>\n"
            "/weather Toshkent\n\n"
            "🧹 <b>Tarixni tozalash:</b>\n"
            "/clear — AI suhbat tarixini o'chirish"
        ),
        "thinking": "🤔 O'ylamoqda...",
        "generating_image": "🎨 Rasm yaratilmoqda...",
        "speaking": "🔊 Ovoz tayyorlanmoqda...",
        "translating": "🌐 Tarjima qilinmoqda...",
        "transcribing": "🎙 Matn ajratilmoqda...",
        "weather_fetching": "🌤 Ob-havo ma'lumotlari olinmoqda...",
        "error": "❌ Xatolik: {}",
        "ai_error": "❌ AI javob bera olmadi. Qayta urinib ko'ring.",
        "image_error": "❌ Rasm yaratishda xatolik yuz berdi.",
        "voice_error": "❌ Ovozni matnga aylantirib bo'lmadi.",
        "speak_usage": "❌ Foydalanish: /speak [matn]",
        "translate_usage": "❌ Foydalanish: /translate [til_kodi] [matn]\nMasalan: /translate en Salom",
        "weather_usage": "❌ Foydalanish: /weather [shahar]",
        "image_usage": "❌ Foydalanish: /image [tavsif]",
        "history_cleared": "🧹 Suhbat tarixi tozalandi.",
        "lang_chosen": "✅ Til: O'zbek",
        "choose_lang": "🌍 Tilni tanlang:",
        "banned": "🚫 Siz botdan foydalana olmaysiz.",
        "no_access": "⛔ Sizda bu buyruqni bajarish huquqi yo'q.",
        "transcript_prefix": "📝 <b>Matnga aylangan ovoz:</b>\n",
        "image_caption": "🎨 <b>Yaratilgan rasm:</b> ",
        "translate_result": "🌐 <b>Tarjima natijasi ({lang}):</b>\n",
        "weather_error": "❌ Ob-havo ma'lumotlarini olib bo'lmadi.",
        "broadcast_prompt": "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:",
        "broadcast_sent": "✅ Xabar {count} foydalanuvchiga yuborildi.",
        "ban_usage": "Foydalanish: /ban [user_id]",
        "unban_usage": "Foydalanish: /unban [user_id]",
        "banned_msg": "🚫 Foydalanuvchi {uid} bloklandi.",
        "unbanned_msg": "✅ Foydalanuvchi {uid} blokdan chiqarildi.",
        "not_banned": "ℹ️ Foydalanuvchi {uid} bloklanmagan.",
    },
    "ru": {
        "start": (
            "🤖 Добро пожаловать в <b>AI Super Bot</b>!\n\n"
            "Я могу помочь вам с:\n\n"
            "🧠 <b>AI Чат</b> — задавайте любые вопросы, получайте умные ответы\n"
            "🎨 <b>Генерация изображений</b> — /image [описание]\n"
            "🎙 <b>Голос в текст</b> — отправьте голосовое сообщение\n"
            "🔊 <b>Текст в голос</b> — /speak [текст]\n"
            "🌐 <b>Переводчик</b> — /translate [язык] [текст]\n"
            "🌤 <b>Погода</b> — /weather [город]\n"
            "🛡 <b>Панель администратора</b> — /admin\n"
            "🌍 <b>Язык</b> — /lang\n\n"
            "Напишите сообщение или выберите команду!"
        ),
        "help": (
            "📖 <b>Справка</b>\n\n"
            "🧠 <b>AI Чат:</b>\n"
            "Напишите любой вопрос — Gemini AI ответит.\n"
            "История чата сохраняется.\n\n"
            "🎨 <b>Генерация изображений:</b>\n"
            "/image [описание] — например: /image закат над морем\n\n"
            "🎙 <b>Голос в текст:</b>\n"
            "Отправьте голосовое — бот переведёт в текст.\n\n"
            "🔊 <b>Текст в голос:</b>\n"
            "/speak [текст] — бот отправит аудио\n\n"
            "🌐 <b>Переводчик:</b>\n"
            "/translate ru Hello world\n"
            "/translate en Привет мир\n\n"
            "🌤 <b>Погода:</b>\n"
            "/weather Москва\n\n"
            "🧹 <b>Очистить историю:</b>\n"
            "/clear — очистить историю AI чата"
        ),
        "thinking": "🤔 Думаю...",
        "generating_image": "🎨 Генерирую изображение...",
        "speaking": "🔊 Готовлю аудио...",
        "translating": "🌐 Перевожу...",
        "transcribing": "🎙 Распознаю речь...",
        "weather_fetching": "🌤 Получаю данные о погоде...",
        "error": "❌ Ошибка: {}",
        "ai_error": "❌ AI не смог ответить. Попробуйте ещё раз.",
        "image_error": "❌ Ошибка при генерации изображения.",
        "voice_error": "❌ Не удалось распознать голос.",
        "speak_usage": "❌ Использование: /speak [текст]",
        "translate_usage": "❌ Использование: /translate [код_языка] [текст]\nНапример: /translate en Привет",
        "weather_usage": "❌ Использование: /weather [город]",
        "image_usage": "❌ Использование: /image [описание]",
        "history_cleared": "🧹 История чата очищена.",
        "lang_chosen": "✅ Язык: Русский",
        "choose_lang": "🌍 Выберите язык:",
        "banned": "🚫 Вы заблокированы.",
        "no_access": "⛔ У вас нет прав для этой команды.",
        "transcript_prefix": "📝 <b>Распознанный текст:</b>\n",
        "image_caption": "🎨 <b>Сгенерированное изображение:</b> ",
        "translate_result": "🌐 <b>Перевод ({lang}):</b>\n",
        "weather_error": "❌ Не удалось получить данные о погоде.",
        "broadcast_prompt": "📢 Напишите сообщение для рассылки всем пользователям:",
        "broadcast_sent": "✅ Сообщение отправлено {count} пользователям.",
        "ban_usage": "Использование: /ban [user_id]",
        "unban_usage": "Использование: /unban [user_id]",
        "banned_msg": "🚫 Пользователь {uid} заблокирован.",
        "unbanned_msg": "✅ Пользователь {uid} разблокирован.",
        "not_banned": "ℹ️ Пользователь {uid} не заблокирован.",
    },
    "en": {
        "start": (
            "🤖 Welcome to <b>AI Super Bot</b>!\n\n"
            "I can help you with:\n\n"
            "🧠 <b>AI Chat</b> — ask anything, get smart answers\n"
            "🎨 <b>Image Generation</b> — /image [description]\n"
            "🎙 <b>Voice to Text</b> — send a voice message\n"
            "🔊 <b>Text to Voice</b> — /speak [text]\n"
            "🌐 <b>Translator</b> — /translate [lang] [text]\n"
            "🌤 <b>Weather</b> — /weather [city]\n"
            "🛡 <b>Admin Panel</b> — /admin\n"
            "🌍 <b>Language</b> — /lang\n\n"
            "Send a message or pick a command to get started!"
        ),
        "help": (
            "📖 <b>Help</b>\n\n"
            "🧠 <b>AI Chat:</b>\n"
            "Type any question — Gemini AI will reply.\n"
            "Chat history is remembered per session.\n\n"
            "🎨 <b>Image Generation:</b>\n"
            "/image [description] — e.g. /image sunset over the ocean\n\n"
            "🎙 <b>Voice to Text:</b>\n"
            "Send a voice message — bot converts it to text.\n\n"
            "🔊 <b>Text to Voice:</b>\n"
            "/speak [text] — bot sends back an audio file\n\n"
            "🌐 <b>Translator:</b>\n"
            "/translate es Hello world\n"
            "/translate en Hola mundo\n\n"
            "🌤 <b>Weather:</b>\n"
            "/weather London\n\n"
            "🧹 <b>Clear history:</b>\n"
            "/clear — clear AI chat history"
        ),
        "thinking": "🤔 Thinking...",
        "generating_image": "🎨 Generating image...",
        "speaking": "🔊 Preparing audio...",
        "translating": "🌐 Translating...",
        "transcribing": "🎙 Transcribing voice...",
        "weather_fetching": "🌤 Fetching weather data...",
        "error": "❌ Error: {}",
        "ai_error": "❌ AI couldn't respond. Please try again.",
        "image_error": "❌ Failed to generate image.",
        "voice_error": "❌ Could not transcribe voice message.",
        "speak_usage": "❌ Usage: /speak [text]",
        "translate_usage": "❌ Usage: /translate [lang_code] [text]\nExample: /translate es Hello",
        "weather_usage": "❌ Usage: /weather [city]",
        "image_usage": "❌ Usage: /image [description]",
        "history_cleared": "🧹 Chat history cleared.",
        "lang_chosen": "✅ Language: English",
        "choose_lang": "🌍 Choose language:",
        "banned": "🚫 You are banned from this bot.",
        "no_access": "⛔ You don't have permission for this command.",
        "transcript_prefix": "📝 <b>Transcribed text:</b>\n",
        "image_caption": "🎨 <b>Generated image:</b> ",
        "translate_result": "🌐 <b>Translation ({lang}):</b>\n",
        "weather_error": "❌ Could not fetch weather data.",
        "broadcast_prompt": "📢 Write the message to broadcast to all users:",
        "broadcast_sent": "✅ Message sent to {count} users.",
        "ban_usage": "Usage: /ban [user_id]",
        "unban_usage": "Usage: /unban [user_id]",
        "banned_msg": "🚫 User {uid} has been banned.",
        "unbanned_msg": "✅ User {uid} has been unbanned.",
        "not_banned": "ℹ️ User {uid} is not banned.",
    },
}

# ─── State ────────────────────────────────────────────────────────────────────

user_langs: dict[int, str] = {}
chat_histories: dict[int, list[dict]] = {}
registered_users: dict[int, dict] = {}
banned_users: set[int] = set()
awaiting_broadcast: set[int] = set()
stats = {
    "messages": 0,
    "images": 0,
    "voice": 0,
    "translations": 0,
    "weather": 0,
    "users": 0,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_lang(uid: int) -> str:
    return user_langs.get(uid, "en")


def t(uid: int, key: str) -> str:
    lang = get_lang(uid)
    return TEXTS[lang].get(key, TEXTS["en"].get(key, key))


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def register_user(user) -> None:
    is_new = user.id not in registered_users
    registered_users[user.id] = {
        "username": user.username or user.first_name or str(user.id),
        "first_name": user.first_name or "",
        "joined": registered_users.get(user.id, {}).get("joined", datetime.now()),
        "last_seen": datetime.now(),
    }
    if is_new:
        stats["users"] += 1


def check_access(uid: int) -> str | None:
    if uid in banned_users:
        return "banned"
    return None


# ─── Gemini AI ────────────────────────────────────────────────────────────────

def gemini_chat(uid: int, user_message: str) -> str:
    history = chat_histories.setdefault(uid, [])
    history.append({"role": "user", "parts": [{"text": user_message}]})

    contents = history[-40:]

    url = f"{GEMINI_BASE_URL}/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 8192,
            "temperature": 0.7,
        },
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are a helpful, friendly, and knowledgeable AI assistant. "
                    "Answer questions clearly and concisely. Be conversational and engaging. "
                    "Support multiple languages — respond in the same language the user writes in."
                )
            }]
        },
    }

    resp = requests.post(url, headers=headers, params=params, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    candidate = data["candidates"][0]
    reply_text = candidate["content"]["parts"][0]["text"]

    history.append({"role": "model", "parts": [{"text": reply_text}]})
    chat_histories[uid] = history

    return reply_text


# ─── Image Generation (Pollinations.ai) ───────────────────────────────────────

def generate_image(prompt: str) -> bytes:
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&enhance=true"
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content


# ─── Voice to Text ────────────────────────────────────────────────────────────

def voice_to_text(ogg_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
        ogg_file.write(ogg_bytes)
        ogg_path = ogg_file.name

    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
            except sr.UnknownValueError:
                try:
                    text = recognizer.recognize_google(audio_data, language="uz-UZ")
                except sr.UnknownValueError:
                    text = ""
        return text
    finally:
        try:
            os.unlink(ogg_path)
        except Exception:
            pass
        try:
            os.unlink(wav_path)
        except Exception:
            pass


# ─── Text to Voice ────────────────────────────────────────────────────────────

def text_to_voice(text: str, lang: str = "en") -> bytes:
    lang_map = {"uz": "uz", "ru": "ru", "en": "en"}
    tts_lang = lang_map.get(lang, "en")
    tts = gTTS(text=text, lang=tts_lang)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


# ─── Translator ───────────────────────────────────────────────────────────────

def translate_text(text: str, target_lang: str) -> str:
    translator = GoogleTranslator(source="auto", target=target_lang)
    return translator.translate(text)


# ─── Weather ──────────────────────────────────────────────────────────────────

def get_weather(city: str) -> str:
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=v2&lang=en"
    resp = requests.get(url, headers={"User-Agent": "curl/7.68.0"}, timeout=15)
    resp.raise_for_status()
    return resp.text.strip()


# ─── Commands ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧠 AI Chat", callback_data="feat_chat"),
            InlineKeyboardButton("🎨 Image", callback_data="feat_image"),
        ],
        [
            InlineKeyboardButton("🎙 Voice→Text", callback_data="feat_voice"),
            InlineKeyboardButton("🔊 Text→Voice", callback_data="feat_speak"),
        ],
        [
            InlineKeyboardButton("🌐 Translate", callback_data="feat_translate"),
            InlineKeyboardButton("🌤 Weather", callback_data="feat_weather"),
        ],
        [InlineKeyboardButton("🌍 Language / Til / Язык", callback_data="open_lang")],
    ])
    await update.message.reply_html(t(uid, "start"), reply_markup=kb)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    await update.message.reply_html(t(uid, "help"))


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])
    await update.message.reply_text(t(uid, "choose_lang"), reply_markup=kb)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    chat_histories.pop(uid, None)
    await update.message.reply_text(t(uid, "history_cleared"))


async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    prompt = " ".join(context.args).strip() if context.args else ""
    if not prompt:
        await update.message.reply_text(t(uid, "image_usage"))
        return

    status = await update.message.reply_text(t(uid, "generating_image"))
    try:
        img_bytes = await asyncio.get_event_loop().run_in_executor(
            None, lambda: generate_image(prompt)
        )
        stats["images"] += 1
        await status.delete()
        await update.message.reply_photo(
            photo=io.BytesIO(img_bytes),
            caption=f"{t(uid, 'image_caption')}{prompt}"
        )
    except Exception as e:
        logger.exception("Image generation failed")
        await status.edit_text(t(uid, "image_error"))


async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await update.message.reply_text(t(uid, "speak_usage"))
        return

    status = await update.message.reply_text(t(uid, "speaking"))
    try:
        lang = get_lang(uid)
        audio_bytes = await asyncio.get_event_loop().run_in_executor(
            None, lambda: text_to_voice(text, lang)
        )
        await status.delete()
        await update.message.reply_voice(
            voice=io.BytesIO(audio_bytes),
            caption=f"🔊 {text[:100]}{'...' if len(text) > 100 else ''}"
        )
    except Exception as e:
        logger.exception("TTS failed")
        await status.edit_text(t(uid, "error").format(str(e)[:100]))


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(t(uid, "translate_usage"))
        return

    target_lang = args[0].lower()
    text = " ".join(args[1:])

    status = await update.message.reply_text(t(uid, "translating"))
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: translate_text(text, target_lang)
        )
        stats["translations"] += 1
        await status.edit_text(
            t(uid, "translate_result").format(lang=target_lang) + result,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception("Translation failed")
        await status.edit_text(t(uid, "error").format(str(e)[:100]))


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    city = " ".join(context.args).strip() if context.args else ""
    if not city:
        await update.message.reply_text(t(uid, "weather_usage"))
        return

    status = await update.message.reply_text(t(uid, "weather_fetching"))
    try:
        weather = await asyncio.get_event_loop().run_in_executor(
            None, lambda: get_weather(city)
        )
        stats["weather"] += 1
        await status.edit_text(f"🌤 <b>{city}</b>\n\n<pre>{weather}</pre>", parse_mode="HTML")
    except Exception as e:
        logger.exception("Weather fetch failed")
        await status.edit_text(t(uid, "weather_error"))


# ─── Admin Commands ────────────────────────────────────────────────────────────

def build_admin_panel() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "🛡 <b>Admin Panel</b>\n\n"
        f"👥 Users: <b>{stats['users']}</b>\n"
        f"🚫 Banned: <b>{len(banned_users)}</b>\n"
        f"💬 AI messages: <b>{stats['messages']}</b>\n"
        f"🎨 Images: <b>{stats['images']}</b>\n"
        f"🎙 Voice: <b>{stats['voice']}</b>\n"
        f"🌐 Translations: <b>{stats['translations']}</b>\n"
        f"🌤 Weather: <b>{stats['weather']}</b>\n"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 User List", callback_data="admin_users"),
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🚫 Banned List", callback_data="admin_banned"),
        ],
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")],
    ])
    return text, kb


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    text, kb = build_admin_panel()
    await update.message.reply_html(text, reply_markup=kb)


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text(t(uid, "ban_usage"))
        return
    target = int(args[0])
    if target in ADMIN_IDS:
        await update.message.reply_text("⛔ Cannot ban an admin.")
        return
    banned_users.add(target)
    await update.message.reply_html(t(uid, "banned_msg").format(uid=target))


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text(t(uid, "unban_usage"))
        return
    target = int(args[0])
    if target in banned_users:
        banned_users.discard(target)
        await update.message.reply_html(t(uid, "unbanned_msg").format(uid=target))
    else:
        await update.message.reply_text(t(uid, "not_banned").format(uid=target))


# ─── Message Handlers ─────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    text = update.message.text or ""

    if uid in awaiting_broadcast:
        awaiting_broadcast.discard(uid)
        count = 0
        for target_uid in registered_users:
            if target_uid not in banned_users:
                try:
                    await context.bot.send_message(chat_id=target_uid, text=text)
                    count += 1
                except Exception:
                    pass
        await update.message.reply_text(t(uid, "broadcast_sent").format(count=count))
        return

    status = await update.message.reply_text(t(uid, "thinking"))
    try:
        reply = await asyncio.get_event_loop().run_in_executor(
            None, lambda: gemini_chat(uid, text)
        )
        stats["messages"] += 1
        await status.edit_text(reply)
    except Exception as e:
        logger.exception("Gemini chat failed")
        await status.edit_text(t(uid, "ai_error"))


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    status = await update.message.reply_text(t(uid, "transcribing"))
    try:
        voice_file = await update.message.voice.get_file()
        ogg_bytes = await voice_file.download_as_bytearray()

        text = await asyncio.get_event_loop().run_in_executor(
            None, lambda: voice_to_text(bytes(ogg_bytes))
        )

        if not text:
            await status.edit_text(t(uid, "voice_error"))
            return

        stats["voice"] += 1

        transcript_msg = t(uid, "transcript_prefix") + text
        await status.edit_text(transcript_msg, parse_mode="HTML")

        ai_status = await update.message.reply_text(t(uid, "thinking"))
        try:
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: gemini_chat(uid, text)
            )
            stats["messages"] += 1
            await ai_status.edit_text(reply)
        except Exception:
            await ai_status.delete()

    except Exception as e:
        logger.exception("Voice handling failed")
        await status.edit_text(t(uid, "voice_error"))


# ─── Callback Handler ─────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_langs[uid] = lang
        chosen = t(uid, "lang_chosen")
        await query.edit_message_text(chosen)

    elif data == "open_lang":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]])
        await query.edit_message_text(t(uid, "choose_lang"), reply_markup=kb)

    elif data.startswith("feat_"):
        feature = data.split("_")[1]
        hints = {
            "chat": "🧠 Just type any message and I'll reply with AI!",
            "image": "🎨 Use /image [description]\nExample: /image a cat in space",
            "voice": "🎙 Send me a voice message and I'll convert it to text + reply!",
            "speak": "🔊 Use /speak [text]\nExample: /speak Hello world",
            "translate": "🌐 Use /translate [lang] [text]\nExample: /translate es Hello",
            "weather": "🌤 Use /weather [city]\nExample: /weather London",
        }
        await query.edit_message_text(hints.get(feature, "Send a message!"))

    elif data == "admin_refresh":
        if not is_admin(uid):
            return
        text, kb = build_admin_panel()
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

    elif data == "admin_stats":
        if not is_admin(uid):
            return
        text = (
            "📊 <b>Detailed Stats</b>\n\n"
            f"👥 Total users: <b>{stats['users']}</b>\n"
            f"🚫 Banned users: <b>{len(banned_users)}</b>\n"
            f"💬 AI messages: <b>{stats['messages']}</b>\n"
            f"🎨 Images generated: <b>{stats['images']}</b>\n"
            f"🎙 Voice transcribed: <b>{stats['voice']}</b>\n"
            f"🌐 Translations: <b>{stats['translations']}</b>\n"
            f"🌤 Weather queries: <b>{stats['weather']}</b>\n\n"
            f"🕐 Uptime since: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="admin_refresh")]])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

    elif data == "admin_users":
        if not is_admin(uid):
            return
        lines = []
        for i, (user_id, info) in enumerate(list(registered_users.items())[:30], 1):
            username = info.get("username", "Unknown")
            banned = "🚫" if user_id in banned_users else "✅"
            lines.append(f"{i}. {banned} <code>{user_id}</code> @{username}")
        text = "👥 <b>Users (last 30):</b>\n\n" + ("\n".join(lines) if lines else "No users yet.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="admin_refresh")]])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

    elif data == "admin_banned":
        if not is_admin(uid):
            return
        if banned_users:
            lines = [f"🚫 <code>{bid}</code>" for bid in banned_users]
            text = "🚫 <b>Banned Users:</b>\n\n" + "\n".join(lines)
        else:
            text = "✅ No banned users."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="admin_refresh")]])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

    elif data == "admin_broadcast":
        if not is_admin(uid):
            return
        awaiting_broadcast.add(uid)
        await query.edit_message_text(t(uid, "broadcast_prompt"))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("image", cmd_image))
    app.add_handler(CommandHandler("speak", cmd_speak))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("AI Super Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
