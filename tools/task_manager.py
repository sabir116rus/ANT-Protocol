"""
Tool: Task Manager — CRUD-операции с задачами.

Контракт:
  Назначение: Создание, чтение, обновление статуса и удаление задач.
              Лимит 7 задач/день, валидация через utils.
  Вход:  user_id, title, task_date, priority, status
  Выход: dict с результатом операции и данными задачи
  Таблицы: tasks (SELECT, INSERT, UPDATE, DELETE), users (SELECT, INSERT)
  Зависимости: db.py, constants.py, utils.py, activity_logger.py
  Тест:  python tools/task_manager.py --test
"""
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.db import get_supabase
from tools.constants import (
    MAX_TASKS_PER_DAY, PRIORITY_ORDER,
    DEFAULT_PRIORITY, DEFAULT_ESTIMATED_MINUTES, DEFAULT_SOURCE,
)
from tools.utils import (
    validate_title, validate_date, validate_priority,
    validate_status, validate_estimated_minutes, validate_source,
)
from tools.activity_logger import log_action, log_error


def get_or_create_user(
    telegram_chat_id: int,
    username: str = None,
    first_name: str = None,
) -> dict:
    """
    Получить пользователя по chat_id, или создать нового.

    Returns:
        dict: данные пользователя из users
    """
    sb = get_supabase()

    result = sb.table("users").select("*").eq("telegram_chat_id", telegram_chat_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]

    new_user = {
        "telegram_chat_id": telegram_chat_id,
        "username": username,
        "first_name": first_name,
    }
    result = sb.table("users").insert(new_user).execute()

    if result.data and len(result.data) > 0:
        user = result.data[0]
        log_action(
            action_type="user_created",
            user_id=user["id"],
            entity_type="user",
            entity_id=user["id"],
            payload={"telegram_chat_id": telegram_chat_id, "username": username},
        )
        return user

    raise RuntimeError("Не удалось создать пользователя")


def create_task(
    user_id: str,
    title: str,
    task_date: str = None,
    priority: str = DEFAULT_PRIORITY,
    description: str = None,
    estimated_minutes: int = DEFAULT_ESTIMATED_MINUTES,
    source: str = DEFAULT_SOURCE,
) -> dict:
    """
    Создать новую задачу.

    Returns:
        dict: {"ok": bool, "task": dict|None, "error": str|None}
    """
    # Валидация title
    valid, title_or_err = validate_title(title)
    if not valid:
        return {"ok": False, "task": None, "error": title_or_err}
    title = title_or_err

    # Валидация task_date
    valid, date_or_err = validate_date(task_date)
    if not valid:
        return {"ok": False, "task": None, "error": date_or_err}
    task_date = date_or_err

    # Нормализация
    priority = validate_priority(priority)
    estimated_minutes = validate_estimated_minutes(estimated_minutes)
    source = validate_source(source)

    # Проверка лимита
    try:
        sb = get_supabase()
        existing = sb.table("tasks") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .eq("task_date", task_date) \
            .execute()

        total_count = existing.count if existing.count is not None else len(existing.data)

        if total_count >= MAX_TASKS_PER_DAY:
            log_action(
                action_type="task_limit_reached",
                user_id=user_id,
                payload={"task_date": task_date, "count": total_count},
                status="warning",
            )
            return {
                "ok": False,
                "task": None,
                "error": f"На {task_date} уже создано "
                         f"{total_count}/{MAX_TASKS_PER_DAY} задач. "
                         f"Нельзя добавить новую задачу на этот день.",
            }
    except Exception as e:
        log_error("task_create_check_failed", str(e), user_id=user_id)
        return {"ok": False, "task": None, "error": f"Ошибка проверки лимита: {e}"}

    # Создание
    try:
        task_data = {
            "user_id": user_id,
            "title": title,
            "task_date": task_date,
            "priority": priority,
            "estimated_minutes": estimated_minutes,
            "source": source,
        }
        if description:
            task_data["description"] = description

        result = sb.table("tasks").insert(task_data).execute()

        if result.data and len(result.data) > 0:
            task = result.data[0]
            log_action(
                action_type="task_created",
                user_id=user_id,
                entity_type="task",
                entity_id=task["id"],
                payload={"title": title, "priority": priority, "task_date": task_date},
            )
            return {"ok": True, "task": task, "error": None}

        return {"ok": False, "task": None, "error": "INSERT не вернул данных"}

    except Exception as e:
        log_error("task_create_failed", str(e), user_id=user_id, payload={"title": title})
        return {"ok": False, "task": None, "error": str(e)}


def list_tasks(
    user_id: str,
    task_date: str = None,
    status_filter: str = None,
) -> dict:
    """
    Получить задачи пользователя в стабильном порядке.

    Логика:
    - порядок фиксированный
    - статус не влияет на позицию в списке
    - задачи не "прыгают" после done/cancelled
    - сортировка: сначала по created_at, потом по id

    Returns:
        dict: {"ok": bool, "tasks": list, "count": int, "error": str|None}
    """
    valid, task_date = validate_date(task_date)
    if not valid:
        return {"ok": False, "tasks": [], "count": 0, "error": task_date}

    try:
        sb = get_supabase()

        query = (
            sb.table("tasks")
            .select("*")
            .eq("user_id", user_id)
            .eq("task_date", task_date)
        )

        if status_filter:
            query = query.eq("status", status_filter)

        # СТАБИЛЬНЫЙ порядок на стороне БД
        result = (
            query
            .order("created_at", desc=False)
            .order("id", desc=False)
            .execute()
        )

        tasks = result.data or []

        return {
            "ok": True,
            "tasks": tasks,
            "count": len(tasks),
            "error": None,
        }

    except Exception as e:
        log_error("task_list_failed", str(e), user_id=user_id)
        return {"ok": False, "tasks": [], "count": 0, "error": str(e)}


def list_overdue_tasks(user_id: str) -> dict:
    """
    Получить просроченные задачи (pending/in_progress в прошлых днях).

    Returns:
        dict: {"ok": bool, "tasks": list, "count": int, "error": str|None}
    """
    today = date.today().isoformat()
    try:
        sb = get_supabase()
        result = sb.table("tasks") \
            .select("*") \
            .eq("user_id", user_id) \
            .lt("task_date", today) \
            .in_("status", ["pending", "in_progress"]) \
            .order("task_date", desc=False) \
            .execute()

        tasks = result.data or []
        return {"ok": True, "tasks": tasks, "count": len(tasks), "error": None}

    except Exception as e:
        log_error("task_overdue_list_failed", str(e), user_id=user_id)
        return {"ok": False, "tasks": [], "count": 0, "error": str(e)}


def update_task_status(
    user_id: str,
    task_id: str,
    new_status: str,
    actual_minutes: int = None,
) -> dict:
    """
    Обновить статус задачи.

    Правило completed_at:
      done → timestamp
      любой другой статус → NULL

    Returns:
        dict: {"ok": bool, "task": dict|None, "error": str|None}
    """
    valid, status_or_err = validate_status(new_status)
    if not valid:
        return {"ok": False, "task": None, "error": status_or_err}

    try:
        sb = get_supabase()

        # Проверка владельца
        check = sb.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
        if not check.data or len(check.data) == 0:
            return {"ok": False, "task": None, "error": "Задача не найдена"}

        old_task = check.data[0]
        old_status = old_task["status"]

        if old_status == new_status:
            if new_status == "done":
                return {
                    "ok": False,
                    "task": old_task,
                    "error": "Задача уже выполнена",
                }
            return {
                "ok": False,
                "task": old_task,
                "error": f"Задача уже имеет статус '{new_status}'",
            }

        # Нельзя отменить выполненную задачу
        if old_status == "done" and new_status == "cancelled":
            return {
                "ok": False,
                "task": old_task,
                "error": "Нельзя отменить выполненную задачу",
            }

        # Формируем update
        update_data = {"status": new_status}

        if new_status == "done":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            if actual_minutes is not None:
                update_data["actual_minutes"] = max(0, min(480, int(actual_minutes)))
        else:
            # Все остальные статусы → completed_at = NULL
            update_data["completed_at"] = None

        result = sb.table("tasks").update(update_data).eq("id", task_id).execute()

        if result.data and len(result.data) > 0:
            task = result.data[0]
            log_action(
                action_type=f"task_{new_status}",
                user_id=user_id,
                entity_type="task",
                entity_id=task_id,
                payload={
                    "old_status": old_status,
                    "new_status": new_status,
                    "title": old_task["title"],
                },
            )
            return {"ok": True, "task": task, "error": None}

        return {"ok": False, "task": None, "error": "UPDATE не вернул данных"}

    except Exception as e:
        log_error(
            "task_status_update_failed", str(e),
            user_id=user_id, entity_type="task", entity_id=task_id,
        )
        return {"ok": False, "task": None, "error": str(e)}


def get_task_by_number(user_id: str, number: int, task_date: str = None) -> dict:
    """
    Получить задачу по номеру в списке (1-based).

    Пример:
        /done 3 -> берём 3-ю задачу из стабильного списка

    Returns:
        dict: {"ok": bool, "task": dict|None, "error": str|None}
    """
    try:
        number = int(number)
    except (TypeError, ValueError):
        return {"ok": False, "task": None, "error": "Номер задачи должен быть числом"}

    if number < 1:
        return {"ok": False, "task": None, "error": "Номер задачи должен быть больше 0"}

    result = list_tasks(user_id, task_date)

    if not result["ok"]:
        return {"ok": False, "task": None, "error": result["error"]}

    tasks = result["tasks"]

    if number > len(tasks):
        return {
            "ok": False,
            "task": None,
            "error": f"Нет задачи с номером {number}. Всего задач: {len(tasks)}",
        }

    task = tasks[number - 1]

    return {"ok": True, "task": task, "error": None}


# ==================
# Тестирование
# ==================
def _run_test():
    print("=" * 50)
    print("🧪 Тест: Task Manager")
    print("=" * 50)

    chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
    if chat_id == 0:
        print("❌ TELEGRAM_CHAT_ID не задан")
        sys.exit(1)

    # 1. Пользователь
    print("\n1. Получение пользователя...")
    user = get_or_create_user(chat_id)
    user_id = user["id"]
    print(f"   User ID: {user_id}")

    # 2. Создание задачи
    print("\n2. Создание задачи...")
    r = create_task(user_id, "Тестовая задача MVP", priority="high")
    assert r["ok"], f"Ошибка: {r['error']}"
    task_id = r["task"]["id"]
    print(f"   Task ID: {task_id}")

    # 3. Список задач
    print("\n3. Список задач...")
    r = list_tasks(user_id)
    print(f"   Задач: {r['count']}")
    assert r["count"] > 0

    # 4. Статус → done (completed_at заполняется)
    print("\n4. Статус → done...")
    r = update_task_status(user_id, task_id, "done", actual_minutes=15)
    assert r["ok"] and r["task"]["status"] == "done"
    assert r["task"]["completed_at"] is not None
    print(f"   completed_at: {r['task']['completed_at']}")

    # 5. Статус → pending (completed_at = NULL)
    print("\n5. Статус → pending...")
    r = update_task_status(user_id, task_id, "pending")
    assert r["ok"] and r["task"]["completed_at"] is None
    print(f"   completed_at: {r['task']['completed_at']} (OK: NULL)")

    # 6. Отмена
    print("\n6. Статус → cancelled...")
    r = update_task_status(user_id, task_id, "cancelled")
    assert r["ok"] and r["task"]["status"] == "cancelled"
    assert r["task"]["completed_at"] is None

    # 7. Валидация: короткий title
    print("\n7. Валидация: короткий title...")
    r = create_task(user_id, "AB")
    assert not r["ok"]
    print(f"   Ошибка (ожидаемо): {r['error']}")

    # 8. Валидация: плохая дата
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
