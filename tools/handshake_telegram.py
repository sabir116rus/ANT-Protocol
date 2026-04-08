"""
Handshake: Telegram Bot — проверка токена бота.
Необходимые переменные: TELEGRAM_BOT_TOKEN
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def check_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не задан в .env")
        return False

    if token == "your-bot-token-from-botfather":
        print("❌ TELEGRAM_BOT_TOKEN содержит placeholder-значение")
        return False

    try:
        # getMe — проверяет валидность токена
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        data = resp.json()

        if data.get("ok"):
            bot_info = data["result"]
            print(f"✅ Telegram Bot подключён:")
            print(f"   Имя: {bot_info.get('first_name')}")
            print(f"   Username: @{bot_info.get('username')}")
            print(f"   Bot ID: {bot_info.get('id')}")
        else:
            print(f"❌ Telegram вернул ошибку: {data.get('description')}")
            return False

        # Проверяем CHAT_ID если задан
        if chat_id and chat_id != "your-personal-chat-id":
            print(f"   Chat ID: {chat_id} (задан)")
        else:
            print(f"   ⚠️ TELEGRAM_CHAT_ID не задан — нужен для отправки сообщений")
            print(f"   Совет: отправьте /start боту, затем откройте:")
            print(f"   https://api.telegram.org/bot{token}/getUpdates")

        return True

    except requests.exceptions.ConnectionError:
        print("❌ Нет интернет-соединения или Telegram API недоступен")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке Telegram: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Handshake: Telegram Bot")
    print("=" * 50)
    success = check_telegram()
    sys.exit(0 if success else 1)
