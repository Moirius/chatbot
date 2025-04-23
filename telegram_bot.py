# telegram_bot.py (version webhook pour Render)

import os
import subprocess
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
from fastapi import FastAPI, Request

# 🔐 Charger les variables d’environnement
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = "https://chatbot-o4gm.onrender.com"
ADMIN_ID = 5059224642

# FastAPI app pour Render (et webhook)
fastapi_app = FastAPI()

# Fonction d'admin
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 Hello {update.effective_user.first_name} ! Bot webhook opérationnel.")

# Commande /myid
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Ton ID Telegram : {update.effective_user.id}")

# Commande /generate
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Accès refusé.")
        return

    await update.message.reply_text("⏳ Lancement de la génération d'e-mails...")

    try:
        result = subprocess.run([
            "python", "generate_batch_emails.py"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            await update.message.reply_text(f"❌ Erreur dans le script :\n{result.stderr}")
        else:
            output = result.stdout[-1000:] if result.stdout else "(Aucune sortie)"
            await update.message.reply_text(f"✅ Script terminé.\n📄 Résultat :\n{output}")
    except Exception as e:
        await update.message.reply_text(f"❌ Exception : {str(e)}")

# Commande /ask
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Accès refusé.")
        return

    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("❓ Utilise : /ask <ta question>")
        return

    try:
        response = requests.post(f"{API_BASE_URL}/ask", json={"query": question})
        data = response.json()
        await update.message.reply_text(f"🧠 Réponse :\n{data.get('answer', '❌ Aucune réponse reçue')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur de requête : {str(e)}")

# Commande /webhook
async def set_webhook_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🔒 Accès refusé.")
        return

    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": webhook_url})

    if r.status_code == 200:
        await update.message.reply_text("✅ Webhook activé avec succès.")
    else:
        await update.message.reply_text(f"❌ Erreur : {r.status_code} → {r.text}")

# Initialisation du bot Telegram
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("myid", myid))
application.add_handler(CommandHandler("generate", generate))
application.add_handler(CommandHandler("ask", ask))
application.add_handler(CommandHandler("webhook", set_webhook_cmd))

# Route webhook pour Telegram
@fastapi_app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    await application.update_queue.put(update)
    return {"status": "ok"}