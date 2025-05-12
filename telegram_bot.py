import os
import subprocess
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
from fastapi import APIRouter, Request

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = "https://chatbot-o4gm.onrender.com"
ADMIN_ID = 5059224642

# === Bot Logic ===

def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 Hello {update.effective_user.first_name} ! Bot actif.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Ton ID Telegram : {update.effective_user.id}")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Accès refusé.")
        return

    await update.message.reply_text("⏳ Lancement de la génération d'e-mails...")
    try:
        result = subprocess.run(
            ["python", "generate_batch_emails.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"  # 🔧 pour éviter l'erreur charmap
        )
        output = result.stdout[-4000:] if result.stdout else "(Aucune sortie)"
        await update.message.reply_text(f"✅ Script terminé :\n{output}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {str(e)}")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Accès refusé.")
        return
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("❓ Utilise : /ask <question>")
        return
    try:
        response = requests.post(f"{API_BASE_URL}/ask", json={"query": question})
        await update.message.reply_text(f"🧠 Réponse : {response.json().get('answer', '❌')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur API : {str(e)}")

async def set_webhook_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Accès refusé.")
        return
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": webhook_url})
    if r.status_code == 200:
        await update.message.reply_text("✅ Webhook activé.")
    else:
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
    json_data = await request.json()
    print("✅ Webhook reçu :", json_data)  # 👈 ajoute cette ligne
    update = Update.de_json(json_data, application.bot)
    await application.update_queue.put(update)
    return {"status": "ok"}

@telegram_router.on_event("startup")
async def set_webhook_startup():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        data={"url": webhook_url}
    )
    print("Webhook setup response:", response.json())
