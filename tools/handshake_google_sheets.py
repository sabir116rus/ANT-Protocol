"""
Handshake: Google Sheets API — проверка доступа.
Необходимые переменные: GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SHEETS_SPREADSHEET_ID

⚠️ Этап 2 — не критично для MVP
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_google_sheets():
    creds_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH")
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")

    if not creds_path or not spreadsheet_id:
        print("⏭️ Google Sheets — переменные не заданы (Этап 2, не критично для MVP)")
        return None  # Skip

    if spreadsheet_id == "your-spreadsheet-id":
        print("⏭️ Google Sheets — placeholder-значения (Этап 2, пропускаем)")
        return None

    if not os.path.exists(creds_path):
        print(f"❌ Файл credentials не найден: {creds_path}")
        return False

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id)

        print(f"✅ Google Sheets подключён:")
        print(f"   Таблица: {sheet.title}")
        print(f"   Листов: {len(sheet.worksheets())}")
        return True

    except ImportError:
        print("❌ Библиотеки не установлены. Выполните: pip install gspread google-auth")
        return False
    except Exception as e:
        print(f"❌ Ошибка Google Sheets: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Handshake: Google Sheets (Этап 2)")
    print("=" * 50)
    result = check_google_sheets()
    sys.exit(0 if result is not False else 1)
