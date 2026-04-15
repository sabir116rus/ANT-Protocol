"""
Task service layer (domain logic + validation).
"""
from datetime import date, datetime, timezone

from tools.constants import (
    MAX_TASKS_PER_DAY,
    DEFAULT_PRIORITY,
    DEFAULT_ESTIMATED_MINUTES,
    DEFAULT_SOURCE,
    ACTUAL_MAX,
)
from tools.utils import (
    validate_title,
    validate_date,
    validate_priority,
    validate_status,
    validate_estimated_minutes,
    validate_source,
)
from tools.activity_logger import log_action, log_error
from tools import task_repository as repo


def get_or_create_user_service(
    telegram_chat_id: int,
    username: str = None,
    first_name: str = None,
) -> dict:
    user = repo.get_user_by_chat_id(telegram_chat_id)
    if user:
        return user

    created = repo.create_user(telegram_chat_id, username=username, first_name=first_name)
    log_action(
        action_type="user_created",
        user_id=created["id"],
        entity_type="user",
        entity_id=created["id"],
        payload={"telegram_chat_id": telegram_chat_id, "username": username},
    )
    return created


def create_task_service(
    user_id: str,
    title: str,
    task_date: str = None,
    priority: str = DEFAULT_PRIORITY,
    description: str = None,
    estimated_minutes: int = DEFAULT_ESTIMATED_MINUTES,
    source: str = DEFAULT_SOURCE,
) -> dict:
    valid, title_or_err = validate_title(title)
    if not valid:
        return {"ok": False, "task": None, "error_code": "VALIDATION_ERROR", "error": title_or_err}
    title = title_or_err

    valid, date_or_err = validate_date(task_date)
    if not valid:
        return {"ok": False, "task": None, "error_code": "VALIDATION_ERROR", "error": date_or_err}
    task_date = date_or_err

    priority = validate_priority(priority)
    estimated_minutes = validate_estimated_minutes(estimated_minutes)
    source = validate_source(source)

    rpc_result = repo.create_task_atomic(
        user_id=user_id,
        title=title,
        task_date=task_date,
        priority=priority,
        description=description,
        estimated_minutes=estimated_minutes,
        source=source,
        max_tasks_per_day=MAX_TASKS_PER_DAY,
    )

    if not rpc_result.get("ok"):
        error_code = rpc_result.get("error_code", "DB_ERROR")
        if error_code == "TASK_LIMIT_REACHED":
            current = rpc_result.get("current_count", MAX_TASKS_PER_DAY)
            log_action(
                action_type="task_limit_reached",
                user_id=user_id,
                payload={"task_date": task_date, "count": current},
                status="warning",
            )
            return {
                "ok": False,
                "task": None,
                "error_code": "TASK_LIMIT_REACHED",
                "error": (
                    f"На {task_date} уже создано {current}/{MAX_TASKS_PER_DAY} задач. "
                    "Нельзя добавить новую задачу на этот день."
                ),
            }

        if error_code == "DB_FUNCTION_MISSING":
            log_error("task_create_rpc_missing", rpc_result.get("message", ""), user_id=user_id)
            return {
                "ok": False,
                "task": None,
                "error_code": "DB_FUNCTION_MISSING",
                "error": (
                    "База данных не обновлена: отсутствует функция create_task_atomic. "
                    "Примените SQL-миграцию для атомарного создания задач."
                ),
            }

        log_error("task_create_failed", rpc_result.get("message", "unknown"), user_id=user_id, payload={"title": title})
        return {
            "ok": False,
            "task": None,
            "error_code": "DB_ERROR",
            "error": rpc_result.get("message", "Ошибка БД при создании задачи"),
        }

    task = rpc_result.get("task")
    if not task:
        return {"ok": False, "task": None, "error_code": "DB_ERROR", "error": "INSERT не вернул данных"}

    log_action(
        action_type="task_created",
        user_id=user_id,
        entity_type="task",
        entity_id=task["id"],
        payload={"title": title, "priority": priority, "task_date": task_date},
    )
    return {"ok": True, "task": task, "error": None, "error_code": None}


def list_tasks_service(user_id: str, task_date: str = None, status_filter: str = None) -> dict:
    valid, task_date = validate_date(task_date)
    if not valid:
        return {"ok": False, "tasks": [], "count": 0, "error_code": "VALIDATION_ERROR", "error": task_date}

    try:
        tasks = repo.list_tasks_for_date(user_id=user_id, task_date=task_date, status_filter=status_filter)
        return {"ok": True, "tasks": tasks, "count": len(tasks), "error": None, "error_code": None}
    except Exception as e:
        log_error("task_list_failed", str(e), user_id=user_id)
        return {"ok": False, "tasks": [], "count": 0, "error_code": "DB_ERROR", "error": str(e)}


def list_overdue_tasks_service(user_id: str) -> dict:
    today = date.today().isoformat()
    try:
        tasks = repo.list_overdue_tasks(user_id=user_id, today=today)
        return {"ok": True, "tasks": tasks, "count": len(tasks), "error": None, "error_code": None}
    except Exception as e:
        log_error("task_overdue_list_failed", str(e), user_id=user_id)
        return {"ok": False, "tasks": [], "count": 0, "error_code": "DB_ERROR", "error": str(e)}


def update_task_status_service(
    user_id: str,
    task_id: str,
    new_status: str,
    actual_minutes: int = None,
) -> dict:
    valid, status_or_err = validate_status(new_status)
    if not valid:
        return {"ok": False, "task": None, "error_code": "VALIDATION_ERROR", "error": status_or_err}

    try:
        old_task = repo.get_task_by_id_and_user(task_id=task_id, user_id=user_id)
        if not old_task:
            return {"ok": False, "task": None, "error_code": "TASK_NOT_FOUND", "error": "Задача не найдена"}

        old_status = old_task["status"]
        if old_status == new_status:
            if new_status == "done":
                return {"ok": False, "task": old_task, "error_code": "TASK_ALREADY_DONE", "error": "Задача уже выполнена"}
            return {
                "ok": False,
                "task": old_task,
                "error_code": "TASK_STATUS_UNCHANGED",
                "error": f"Задача уже имеет статус '{new_status}'",
            }

        if old_status == "done" and new_status == "cancelled":
            return {
                "ok": False,
                "task": old_task,
                "error_code": "TASK_DONE_CANNOT_CANCEL",
                "error": "Нельзя отменить выполненную задачу",
            }

        update_data = {"status": new_status}
        if new_status == "done":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            if actual_minutes is not None:
                update_data["actual_minutes"] = max(0, min(ACTUAL_MAX, int(actual_minutes)))
        else:
            update_data["completed_at"] = None
            # Если задача больше не done, фактическое время не должно учитываться в отчётах.
            update_data["actual_minutes"] = None

        task = repo.update_task(task_id=task_id, update_data=update_data)
        if not task:
            return {"ok": False, "task": None, "error_code": "DB_ERROR", "error": "UPDATE не вернул данных"}

        log_action(
            action_type=f"task_{new_status}",
            user_id=user_id,
            entity_type="task",
            entity_id=task_id,
            payload={"old_status": old_status, "new_status": new_status, "title": old_task["title"]},
        )
        return {"ok": True, "task": task, "error": None, "error_code": None}
    except Exception as e:
        log_error("task_status_update_failed", str(e), user_id=user_id, entity_type="task", entity_id=task_id)
        return {"ok": False, "task": None, "error_code": "DB_ERROR", "error": str(e)}
