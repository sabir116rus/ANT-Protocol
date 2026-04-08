"""
Handshake: Notion API — проверка доступа.
Необходимые переменные: NOTION_API_KEY, NOTION_DATABASE_ID

⚠️ Этап 2 — не критично для MVP
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def check_notion():
    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not api_key:
        print("⏭️ Notion — API-ключ не задан (Этап 2, не критично для MVP)")
        return None

    if api_key == "secret_your-notion-key":
        print("⏭️ Notion — placeholder-значение (Этап 2, пропускаем)")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28"
        }
        # Проверяем токен через /users/me
        resp = requests.get(
            "https://api.notion.com/v1/users/me",
            headers=headers,
            timeout=10
        )

        if resp.status_code == 200:
            user = resp.json()
            print(f"✅ Notion API подключён:")
            print(f"   Тип: {user.get('type')}")
            print(f"   Имя: {user.get('name', 'N/A')}")

            # Проверяем базу данных если задана
            if database_id and database_id != "your-database-id":
                db_resp = requests.get(
                    f"https://api.notion.com/v1/databases/{database_id}",
                    headers=headers,
                    timeout=10
                )
                if db_resp.status_code == 200:
                    db = db_resp.json()
                    title = db.get("title", [{}])
                    db_title = title[0].get("plain_text", "N/A") if title else "N/A"
                    print(f"   База данных: {db_title}")
                else:
                    print(f"   ⚠️ База данных не доступна: {db_resp.status_code}")

            return True
        elif resp.status_code == 401:
            print("❌ Неверный API-ключ Notion (401)")
            return False
        else:
            print(f"❌ Notion вернул код {resp.status_code}")
            return False

    except Exception as e:
        print(f"❌ Ошибка Notion: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Handshake: Notion (Этап 2)")
    print("=" * 50)
    result = check_notion()
    sys.exit(0 if result is not False else 1)
