# telegram_polling.py — bot en local
import requests
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram_bot import BOT_TOKEN, start, myid, generate, ask, set_webhook_cmd

def delete_webhook():
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    print("🧹 Webhook supprimé :", r.json())

def main():
    delete_webhook()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("webhook", set_webhook_cmd))
    print(" Bot lancé en mode polling")
    app.run_polling()

if __name__ == "__main__":
    main()
