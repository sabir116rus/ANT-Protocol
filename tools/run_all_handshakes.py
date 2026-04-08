"""
Мастер-скрипт: запуск всех handshake-проверок.
Запуск: python tools/run_all_handshakes.py
"""
import subprocess
import sys
import os

HANDSHAKES = [
    ("Supabase",       "tools/handshake_supabase.py",       "MVP"),
    ("Telegram Bot",   "tools/handshake_telegram.py",       "MVP"),
    ("OpenAI API",     "tools/handshake_openai.py",         "MVP"),
    ("Google Sheets",  "tools/handshake_google_sheets.py",  "Этап 2"),
    ("Notion",         "tools/handshake_notion.py",         "Этап 2"),
    ("n8n",            "tools/handshake_n8n.py",            "MVP"),
]

def main():
    print("=" * 60)
    print("🚀 Antigravity Skills — Handshake Suite")
    print("=" * 60)

    results = {}

    for name, script, stage in HANDSHAKES:
        print(f"\n{'─' * 60}")
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), script)
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=False,
                cwd=os.path.dirname(os.path.dirname(__file__)),
                timeout=15
            )
            results[name] = "✅" if result.returncode == 0 else "❌"
        except subprocess.TimeoutExpired:
            results[name] = "⏰ Таймаут"
        except Exception as e:
            results[name] = f"❌ {e}"

    print(f"\n{'=' * 60}")
    print("📊 ИТОГО:")
    print(f"{'=' * 60}")

    for (name, _, stage), status in zip(HANDSHAKES, results.values()):
        tag = f"[{stage}]"
        print(f"  {status} {name:20s} {tag}")

    mvp_ok = all(
        results.get(name) == "✅"
        for name, _, stage in HANDSHAKES
        if stage == "MVP"
    )

    print(f"\n{'─' * 60}")
    if mvp_ok:
        print("🟢 MVP-интеграции готовы — можно переходить к Architect")
    else:
        print("🔴 Есть проблемы с MVP-интеграциями — исправьте перед продолжением")

if __name__ == "__main__":
    main()
