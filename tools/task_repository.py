"""
Task repository layer (data access only).
"""
from tools.db import get_supabase


def get_user_by_chat_id(telegram_chat_id: int) -> dict | None:
    sb = get_supabase()
    result = sb.table("users").select("*").eq("telegram_chat_id", telegram_chat_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


def create_user(telegram_chat_id: int, username: str = None, first_name: str = None) -> dict:
    sb = get_supabase()
    payload = {
        "telegram_chat_id": telegram_chat_id,
        "username": username,
        "first_name": first_name,
    }
    result = sb.table("users").insert(payload).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    raise RuntimeError("Не удалось создать пользователя")


def create_task_atomic(
    user_id: str,
    title: str,
    task_date: str,
    priority: str,
    description: str | None,
    estimated_minutes: int,
    source: str,
    max_tasks_per_day: int,
) -> dict:
    """
    Atomic create via DB function `create_task_atomic`.
    Returns normalized dict:
      {"ok": bool, "task": dict|None, "error_code": str|None, ...}
    """
    sb = get_supabase()
    params = {
        "p_user_id": user_id,
        "p_title": title,
        "p_task_date": task_date,
        "p_priority": priority,
        "p_description": description,
        "p_estimated_minutes": estimated_minutes,
        "p_source": source,
        "p_max_tasks_per_day": max_tasks_per_day,
    }
    try:
        result = sb.rpc("create_task_atomic", params).execute()
        payload = result.data
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            return {
                "ok": False,
                "task": None,
                "error_code": "DB_ERROR",
                "message": "Некорректный ответ DB RPC create_task_atomic",
            }
        return payload
    except Exception as e:
        message = str(e)
        if "create_task_atomic" in message and (
            "Could not find the function" in message or "function public.create_task_atomic" in message
        ):
            return {
                "ok": False,
                "task": None,
                "error_code": "DB_FUNCTION_MISSING",
                "message": message,
            }
        return {"ok": False, "task": None, "error_code": "DB_ERROR", "message": message}


def list_tasks_for_date(user_id: str, task_date: str, status_filter: str | None) -> list:
    sb = get_supabase()
    query = (
        sb.table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .eq("task_date", task_date)
    )
    if status_filter:
        query = query.eq("status", status_filter)
    result = query.order("created_at", desc=False).order("id", desc=False).execute()
    return result.data or []


def list_overdue_tasks(user_id: str, today: str) -> list:
    sb = get_supabase()
    result = (
        sb.table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .lt("task_date", today)
        .in_("status", ["pending", "in_progress"])
        .order("task_date", desc=False)
        .execute()
    )
    return result.data or []


def get_task_by_id_and_user(task_id: str, user_id: str) -> dict | None:
    sb = get_supabase()
    result = sb.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


def update_task(task_id: str, update_data: dict) -> dict | None:
    sb = get_supabase()
    result = sb.table("tasks").update(update_data).eq("id", task_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None

