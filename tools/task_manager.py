"""
Tool: Task Manager — public facade for task workflows.

Business logic lives in `tools/task_service.py`,
data access lives in `tools/task_repository.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.task_service import (
    get_or_create_user_service,
    create_task_service,
    list_tasks_service,
    list_overdue_tasks_service,
    update_task_status_service,
)


def get_or_create_user(
    telegram_chat_id: int,
    username: str = None,
    first_name: str = None,
) -> dict:
    return get_or_create_user_service(
        telegram_chat_id=telegram_chat_id,
        username=username,
        first_name=first_name,
    )


def create_task(
    user_id: str,
    title: str,
    task_date: str = None,
    priority: str = "medium",
    description: str = None,
    estimated_minutes: int = 25,
    source: str = "telegram",
) -> dict:
    return create_task_service(
        user_id=user_id,
        title=title,
        task_date=task_date,
        priority=priority,
        description=description,
        estimated_minutes=estimated_minutes,
        source=source,
    )


def list_tasks(
    user_id: str,
    task_date: str = None,
    status_filter: str = None,
) -> dict:
    return list_tasks_service(user_id=user_id, task_date=task_date, status_filter=status_filter)


def list_overdue_tasks(user_id: str) -> dict:
    return list_overdue_tasks_service(user_id=user_id)


def update_task_status(
    user_id: str,
    task_id: str,
    new_status: str,
    actual_minutes: int = None,
) -> dict:
    return update_task_status_service(
        user_id=user_id,
        task_id=task_id,
        new_status=new_status,
        actual_minutes=actual_minutes,
    )


def get_task_by_number(user_id: str, number: int, task_date: str = None) -> dict:
    try:
        number = int(number)
    except (TypeError, ValueError):
        return {"ok": False, "task": None, "error_code": "VALIDATION_ERROR", "error": "Номер задачи должен быть числом"}

    if number < 1:
        return {"ok": False, "task": None, "error_code": "VALIDATION_ERROR", "error": "Номер задачи должен быть больше 0"}

    result = list_tasks(user_id, task_date)
    if not result["ok"]:
        return {"ok": False, "task": None, "error_code": result.get("error_code"), "error": result["error"]}

    tasks = result["tasks"]
    if number > len(tasks):
        return {
            "ok": False,
            "task": None,
            "error_code": "TASK_NOT_FOUND",
            "error": f"Нет задачи с номером {number}. Всего задач: {len(tasks)}",
        }

    return {"ok": True, "task": tasks[number - 1], "error": None, "error_code": None}


def _run_test():
    print("=" * 50)
    print("🧪 Тест: Task Manager")
    print("=" * 50)

    chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
    if chat_id == 0:
        print("❌ TELEGRAM_CHAT_ID не задан")
        sys.exit(1)

    print("\n1. Получение пользователя...")
    user = get_or_create_user(chat_id)
    user_id = user["id"]
    print(f"   User ID: {user_id}")

    print("\n2. Создание задачи...")
    r = create_task(user_id, "Тестовая задача MVP", priority="high")
    assert r["ok"], f"Ошибка: {r['error']}"
    task_id = r["task"]["id"]
    print(f"   Task ID: {task_id}")

    print("\n3. Список задач...")
    r = list_tasks(user_id)
    print(f"   Задач: {r['count']}")
    assert r["count"] > 0

    print("\n4. Статус → done...")
    r = update_task_status(user_id, task_id, "done", actual_minutes=15)
    assert r["ok"] and r["task"]["status"] == "done"
    assert r["task"]["completed_at"] is not None
    print(f"   completed_at: {r['task']['completed_at']}")

    print("\n5. Статус → pending...")
    r = update_task_status(user_id, task_id, "pending")
    assert r["ok"] and r["task"]["completed_at"] is None
    print(f"   completed_at: {r['task']['completed_at']} (OK: NULL)")

    print("\n6. Статус → cancelled...")
    r = update_task_status(user_id, task_id, "cancelled")
    assert r["ok"] and r["task"]["status"] == "cancelled"
    assert r["task"]["completed_at"] is None

    print("\n7. Валидация: короткий title...")
    r = create_task(user_id, "AB")
    assert not r["ok"]
    print(f"   Ошибка (ожидаемо): {r['error']}")

    print("\n8. Валидация: плохая дата...")
    r = create_task(user_id, "Тест даты", task_date="not-a-date")
    assert not r["ok"]
    print(f"   Ошибка (ожидаемо): {r['error']}")

    print("\n" + "=" * 50)
    print("✅ Все тесты пройдены!")
    print("=" * 50)


if __name__ == "__main__":
    if "--test" in sys.argv:
        _run_test()
    else:
        print("Использование: python tools/task_manager.py --test")
