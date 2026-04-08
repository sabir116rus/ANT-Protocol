"""
Tool: Activity Logger — базовый слой логирования для всех tools.

Контракт:
  Назначение: Запись действий, ошибок и событий в activity_logs (Supabase).
              Fallback в локальный файл при сбое БД.
  Вход:  user_id, action_type, entity_type, entity_id, payload, status, error_message
  Выход: dict с id записи и статусом операции
  Таблицы: activity_logs (INSERT, SELECT)
  Тест:  python tools/activity_logger.py --test
"""
import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.db import get_supabase
from tools.constants import LOG_STATUSES


def _fallback_log(entry: dict) -> None:
    """Запись в локальный файл при недоступности Supabase."""
    fallback_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".tmp")
    os.makedirs(fallback_dir, exist_ok=True)
    fallback_path = os.path.join(fallback_dir, "fallback_log.jsonl")

    entry["_fallback"] = True
    entry["_fallback_at"] = datetime.now(timezone.utc).isoformat()

    with open(fallback_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    print(f"⚠️ Fallback: запись сохранена в {fallback_path}")


def log_action(
    action_type: str,
    user_id: str = None,
    entity_type: str = None,
    entity_id: str = None,
    payload: dict = None,
    status: str = "success",
    error_message: str = None,
) -> dict:
    """
    Записать действие в activity_logs.

    Returns:
        dict: {"ok": bool, "id": str|None, "fallback": bool}
    """
    if status not in LOG_STATUSES:
        status = "success"

    entry = {
        "action_type": action_type,
        "payload": payload or {},
        "status": status,
    }

    if user_id:
        entry["user_id"] = user_id
    if entity_type:
        entry["entity_type"] = entity_type
    if entity_id:
        entry["entity_id"] = entity_id
    if error_message:
        entry["error_message"] = error_message

    try:
        sb = get_supabase()
        result = sb.table("activity_logs").insert(entry).execute()

        if result.data and len(result.data) > 0:
            return {"ok": True, "id": result.data[0]["id"], "fallback": False}
        else:
            _fallback_log(entry)
            return {"ok": False, "id": None, "fallback": True}

    except Exception as e:
        entry["_original_error"] = str(e)
        _fallback_log(entry)
        return {"ok": False, "id": None, "fallback": True}


def log_error(
    action_type: str,
    error_message: str,
    user_id: str = None,
    entity_type: str = None,
    entity_id: str = None,
    payload: dict = None,
) -> dict:
    """Shortcut для логирования ошибок."""
    return log_action(
        action_type=action_type,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        status="error",
        error_message=error_message,
    )


def get_recent_logs(user_id: str = None, limit: int = 10) -> list:
    """
    Получить последние N логов.

    Returns:
        list[dict]: Список записей из activity_logs
    """
    try:
        sb = get_supabase()
        query = sb.table("activity_logs").select("*").order("created_at", desc=True).limit(limit)

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()
        return result.data or []

    except Exception as e:
        print(f"❌ Ошибка получения логов: {e}")
        return []


# ==================
# Тестирование
# ==================
def _run_test():
    print("=" * 50)
    print("🧪 Тест: Activity Logger")
    print("=" * 50)

    # 1. Системный лог
    print("\n1. Запись системного лога...")
    result = log_action(
        action_type="system_test",
        payload={"test": True, "timestamp": datetime.now(timezone.utc).isoformat()},
    )
    print(f"   Результат: {result}")
    assert result["ok"], "Ожидался успешный INSERT"

    # 2. Чтение логов
    print("\n2. Чтение последних логов...")
    logs = get_recent_logs(limit=3)
    print(f"   Получено записей: {len(logs)}")
    assert len(logs) > 0

    last = logs[0]
    print(f"   Последний: action={last['action_type']}, status={last['status']}")
    assert last["action_type"] == "system_test"

    # 3. Запись ошибки
    print("\n3. Запись ошибки...")
    err = log_error("test_error", "Тестовая ошибка", payload={"test_error": True})
    print(f"   Результат: {err}")
    assert err["ok"]

    print("\n" + "=" * 50)
    print("✅ Все тесты пройдены!")
    print("=" * 50)


if __name__ == "__main__":
    if "--test" in sys.argv:
        _run_test()
    else:
        print("Использование: python tools/activity_logger.py --test")
