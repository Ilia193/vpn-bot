import os
# Токен бота — получить у @id199142634 (@BotFather) в Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMINS_IDS", "839849374").split(",") if x.strip()]
DB_PATH = "vpn_bot.db"
