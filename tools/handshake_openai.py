"""
Handshake: LLM API (ProxyAPI) — проверка подключения.
Необходимые переменные: LLM_API_URL, LLM_API_KEY
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def check_llm_api():
    api_url = os.environ.get("LLM_API_URL")
    api_key = os.environ.get("LLM_API_KEY")

    if not api_url or not api_key:
        print("❌ LLM_API_URL или LLM_API_KEY не заданы в .env")
        return False

    if api_key == "your-proxyapi-key":
        print("❌ LLM_API_KEY содержит placeholder-значение")
        return False

    # Убираем trailing slash если есть
    api_url = api_url.rstrip("/")

    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        # Проверяем доступность через список моделей
        # ProxyAPI формат: https://api.proxyapi.ru/openai/v1/models
        resp = requests.get(
            f"{api_url}/openai/v1/models",
            headers=headers,
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            model_names = [m.get("id", "?") for m in models][:5]
            print(f"✅ LLM API (ProxyAPI) подключён: {api_url}")
            print(f"   Доступных моделей: {len(models)}")
            if model_names:
                print(f"   Примеры: {', '.join(model_names)}")
            return True
        elif resp.status_code == 401:
            print(f"❌ Неверный API-ключ (401 Unauthorized)")
            print(f"   URL: {api_url}")
            return False
        elif resp.status_code == 429:
            print(f"⚠️ Rate limit (429). Ключ валиден, но превышен лимит.")
            return True
        else:
            print(f"❌ LLM API вернул код {resp.status_code}: {resp.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Нет соединения с LLM API: {api_url}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке LLM API: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Handshake: LLM API (ProxyAPI)")
    print("=" * 50)
    success = check_llm_api()
    sys.exit(0 if success else 1)
