import os
import requests
import threading
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application
)
from fastapi import APIRouter, Request
from generate_batch_emails import main as generate_main

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = "https://chatbot-o4gm.onrender.com"
ADMIN_ID = 5059224642
WEBHOOK_URL = "https://chatbot-o4gm.onrender.com/webhook"

# === Bot Logic ===

def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Commande /start reçue")
    await update.message.reply_text(f"🤖 Hello {update.effective_user.first_name} ! Bot actif.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Commande /myid reçue")
    await update.message.reply_text(f"🆔 Ton ID Telegram : {update.effective_user.id}")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Commande /generate reçue")
    if not is_admin(update):
        print("🚫 Utilisateur non autorisé")
        await update.message.reply_text("🔒 Accès refusé.")
        return

    await update.message.reply_text("⏳ Script lancé...")

    bot = context.bot
    chat_id = update.effective_chat.id

    def run_script():
        print("🚀 Démarrage du script avec messages Telegram")
        try:
            generate_main(bot=bot, chat_id=chat_id)
            bot.send_message(chat_id=chat_id, text="✅ Script terminé.")
        except Exception as e:
            bot.send_message(chat_id=chat_id, text=f"❌ Erreur dans le script : {e}")
            print(f"❌ Erreur dans le thread generate : {e}")

    threading.Thread(target=run_script).start()

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Commande /ask reçue")
    if not is_admin(update):
        print("🚫 Utilisateur non autorisé")
        await update.message.reply_text("🔒 Accès refusé.")
        return

    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("❓ Utilise : /ask <question>")
        return

    try:
        print(f"🔍 Requête API /ask avec : {question}")
        response = requests.post(f"{API_BASE_URL}/ask", json={"query": question}, timeout=15)
        response.raise_for_status()
        result = response.json().get("answer", "❌ Aucune réponse")
        await update.message.reply_text(f"🧠 Réponse : {result}")
    except Exception as e:
        print(f"❌ Erreur API /ask : {e}")
        await update.message.reply_text(f"❌ Erreur API : {str(e)}")

async def set_webhook_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Commande /webhook reçue")
    if not is_admin(update):
        print("🚫 Utilisateur non autorisé")
        await update.message.reply_text("🔒 Accès refusé.")
        return

    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": WEBHOOK_URL})
    if r.status_code == 200:
        print("✅ Webhook Telegram défini avec succès")
        await update.message.reply_text("✅ Webhook activé.")
    else:
        print(f"❌ Erreur lors du setWebhook : {r.text}")
        await update.message.reply_text(f"❌ Erreur : {r.text}")

# === FastAPI Router for Telegram Webhook ===
telegram_router = APIRouter()

# Crée le bot Telegram
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("myid", myid))
application.add_handler(CommandHandler("generate", generate))
application.add_handler(CommandHandler("ask", ask))
application.add_handler(CommandHandler("webhook", set_webhook_cmd))

@telegram_router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        json_data = await request.json()
        print("✅ Webhook reçu :", json_data)

        update = Update.de_json(json_data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}

    except Exception as e:
        print("❌ Erreur dans le webhook :", str(e))
        return {"status": "error", "message": str(e)}

# Appelé depuis api.py
async def start_bot():
    print("🚀 Initialisation du bot Telegram...")
    if not application._initialized:
        await application.initialize()
    if not application._running:
        await application.start()
    print("✅ Bot Telegram démarré.")

async def set_webhook_startup():
    print("🎯 Lancement du bot Telegram...")
    await start_bot()

    print("🌐 Enregistrement du webhook Telegram...")
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        data={"url": WEBHOOK_URL, "drop_pending_updates": True}
    )
    print("🎯 Webhook setup response:", response.json())
