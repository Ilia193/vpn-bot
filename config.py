import os
# Токен бота — получить у @id199142634 (@BotFather) в Telegram
BOT_TOKEN = os.getenv("8730107914:AAFltLnXRFlMN5qwiTMuFRRu0EzRLAomZjk")
ADMIN_IDS = [int(x) for x in os.getenv("839849374").split(",") if x.strip()]
DB_PATH = "vpn_bot.db"
