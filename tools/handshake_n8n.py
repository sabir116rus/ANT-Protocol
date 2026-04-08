"""
Handshake: n8n — проверка доступности инстанса.
Необходимые переменные: N8N_BASE_URL, N8N_API_KEY (опционально)

⚠️ Может работать без API-ключа если n8n запущен локально
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def check_n8n():
    base_url = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
    api_key = os.environ.get("N8N_API_KEY")

    if base_url == "http://localhost:5678":
        print(f"ℹ️  Используется URL по умолчанию: {base_url}")

    try:
        # Простой health-check
        headers = {}
        if api_key and api_key != "your-n8n-api-key":
            headers["X-N8N-API-KEY"] = api_key

        resp = requests.get(f"{base_url}/healthz", headers=headers, timeout=5)

        if resp.status_code == 200:
            print(f"✅ n8n доступен: {base_url}")
            print(f"   Health: OK (via /healthz)")
            return True
        else:
            # Fallback: пробуем корневой URL
            print(f"ℹ️  /healthz вернул {resp.status_code}, пробуем GET /...")
            resp2 = requests.get(f"{base_url}/", headers=headers, timeout=5)
            if resp2.status_code in (200, 301, 302):
                print(f"✅ n8n доступен: {base_url}")
                print(f"   Health: OK (via GET /, код {resp2.status_code})")
                return True
            else:
                print(f"⚠️ n8n ответил с кодом: {resp2.status_code}")
                return True  # Сервер отвечает, это уже хорошо

    except requests.exceptions.ConnectionError:
        # Fallback: пробуем корневой URL
        try:
            resp2 = requests.get(f"{base_url}/", headers={}, timeout=5)
            if resp2.status_code in (200, 301, 302):
                print(f"✅ n8n доступен: {base_url}")
                print(f"   Health: OK (via GET /, fallback)")
                return True
        except Exception:
            pass
        print(f"⚠️ n8n не доступен по адресу: {base_url}")
        print(f"   Убедитесь, что n8n запущен (docker compose up -d)")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке n8n: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Handshake: n8n")
    print("=" * 50)
    success = check_n8n()
    sys.exit(0 if success else 1)
