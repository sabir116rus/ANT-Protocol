"""
Handshake: Supabase — проверка подключения к базе данных.
Необходимые переменные: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("❌ SUPABASE_URL или SUPABASE_SERVICE_ROLE_KEY не заданы в .env")
        return False

    if url == "https://your-project.supabase.co" or key == "your-service-role-key":
        print("❌ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY содержат placeholder-значения")
        return False

    try:
        from supabase import create_client, Client
        supabase: Client = create_client(url, key)

        # Простой запрос для проверки соединения через REST API
        import requests
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}"
        }
        resp = requests.get(f"{url}/rest/v1/", headers=headers)

        if resp.status_code == 200:
            print(f"✅ Supabase подключён: {url}")
            print(f"   Статус: {resp.status_code}")
            print(f"   Ключ: SERVICE_ROLE_KEY")
            return True
        else:
            print(f"⚠️ Supabase ответил, но с кодом: {resp.status_code}")
            print(f"   Ответ: {resp.text[:200]}")
            return False

    except ImportError:
        print("❌ Библиотека supabase не установлена. Выполните: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения к Supabase: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Handshake: Supabase")
    print("=" * 50)
    success = check_supabase()
    sys.exit(0 if success else 1)
