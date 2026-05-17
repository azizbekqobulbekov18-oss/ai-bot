# AI Super Bot 🤖

A powerful Telegram AI bot with Gemini AI, image generation, voice-to-text, translation, weather and an admin panel.

## Features

| Feature | Command |
|---|---|
| 🧠 AI Chat (Gemini 2.5 Flash) | Send any message |
| 🎨 Image Generation (Pollinations.ai) | `/image [description]` |
| 🎙 Voice to Text | Send a voice message |
| 🔊 Text to Voice | `/speak [text]` |
| 🌐 Translator | `/translate [lang] [text]` |
| 🌤 Weather | `/weather [city]` |
| 🛡 Admin Panel | `/admin` |
| 🌍 Multilingual (UZ/RU/EN) | `/lang` |

## Setup

### Install dependencies

```bash
pip install -r requirements.txt
```

Also requires **ffmpeg** installed on the system.

### Environment variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather |
| `AI_INTEGRATIONS_GEMINI_BASE_URL` | Gemini API base URL |
| `AI_INTEGRATIONS_GEMINI_API_KEY` | Gemini API key |
| `ADMIN_IDS` | Comma-separated admin Telegram user IDs |

### Run

```bash
python bot.py
```

## All Commands

- `/start` — Welcome screen with feature buttons
- `/help` — Full help menu
- `/image [desc]` — Generate an image
- `/speak [text]` — Convert text to audio
- `/translate [lang] [text]` — Translate text (e.g. `/translate es Hello`)
- `/weather [city]` — Live weather data
- `/lang` — Change language (Uzbek / Russian / English)
- `/clear` — Clear AI chat history
- `/admin` — Admin panel (admins only)
- `/ban [user_id]` — Ban a user
- `/unban [user_id]` — Unban a user

## Stack

- Python 3.11
- python-telegram-bot 22.x
- Google Gemini 2.5 Flash
- Pollinations.ai (free image generation)
- gTTS (text-to-speech)
- SpeechRecognition + pydub (voice-to-text)
- deep-translator (translations)
- wttr.in (weather)
