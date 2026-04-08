"""
Tool: Daily Planner — формирование и отправка плана дня.

Контракт:
  Назначение: Собрать задачи, отформатировать, отправить в Telegram,
              сохранить в daily_reports. Каждый этап имеет свой статус.
  Вход:  user_id, task_date, telegram_chat_id
  Выход: dict с раздельными статусами: report_calculated, report_saved, telegram_sent
  Таблицы: tasks (SELECT), daily_reports (INSERT/UPSERT), activity_logs (INSERT)
  Зависимости: db.py, constants.py, utils.py, task_manager.py, activity_logger.py
  Тест:  python tools/daily_planner.py --test
"""
import os
import sys
from datetime import date
from dotenv import load_dotenv
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.db import get_supabase
from tools.constants import PRIORITY_EMOJI, MAX_TASKS_PER_DAY
from tools.utils import escape_markdown, format_minutes, validate_date, format_date_ru
from tools.activity_logger import log_action, log_error
from tools.task_manager import list_tasks, list_overdue_tasks

load_dotenv()


def get_daily_plan(user_id: str, task_date: str = None) -> dict:
    """
    Собрать план дня: задачи на дату + просроченные.

    Returns:
        dict: {
            "ok": bool,
            "tasks": list, "overdue": list,
            "total": int, "total_minutes": int,
            "error": str|None
        }
    """
    valid, task_date = validate_date(task_date)
    if not valid:
        return {"ok": False, "tasks": [], "overdue": [], "total": 0,
                "total_minutes": 0, "error": task_date}

    result = list_tasks(user_id, task_date)
    if not result["ok"]:
        return {"ok": False, "tasks": [], "overdue": [], "total": 0,
                "total_minutes": 0, "error": result["error"]}

    overdue_result = list_overdue_tasks(user_id)
    overdue = overdue_result["tasks"] if overdue_result["ok"] else []

    tasks = result["tasks"]
    total_minutes = sum(t.get("estimated_minutes", 25) for t in tasks)

    return {
        "ok": True,
        "tasks": tasks,
        "overdue": overdue,
        "total": len(tasks),
        "total_minutes": total_minutes,
        "error": None,
    }


def format_plan_message(plan: dict, task_date: str = None) -> str:
    """
    Форматировать план дня для Telegram (MarkdownV2).
    """
    if not task_date:
        task_date = date.today().isoformat()

    tasks = plan.get("tasks", [])
    overdue = plan.get("overdue", [])

    display_date = format_date_ru(task_date)

    if not tasks and not overdue:
        return (
            f"📅 *План на {escape_markdown(display_date)}*\n\n"
            "Задач нет\\. Добавьте через /add\n\n"
            "💡 _Начните с малого — одна задача лучше нуля\\!_"
        )

    lines = [f"📅 *План на {escape_markdown(display_date)}*\n"]

    for i, task in enumerate(tasks, 1):
        emoji = PRIORITY_EMOJI.get(task.get("priority", "medium"), "🟡")
        est = task.get("estimated_minutes", 25)
        status_mark = "✅" if task.get("status") == "done" else emoji
        title = escape_markdown(task["title"])
        lines.append(f"{status_mark} {i}\\. {title} \\({est} мин\\)")

    if overdue:
        lines.append("")
        for task in overdue:
            title = escape_markdown(task["title"])
            task_d = escape_markdown(format_date_ru(task.get("task_date", "?")))
            lines.append(f"⚠️ \\[{task_d}\\] {title}")

    total = plan.get("total", len(tasks))
    time_str = format_minutes(plan.get("total_minutes", 0))

    lines.append(f"\n━━━━━━━━━━━━━━━")
    lines.append(f"📊 Задач: {total}/{MAX_TASKS_PER_DAY} \\| ⏱ \\~{escape_markdown(time_str)}")

    if overdue:
        lines.append(f"⚠️ Перенесённых: {len(overdue)}")

    return "\n".join(lines)


def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "MarkdownV2",
) -> dict:
    """
    Отправить сообщение в Telegram.

    Returns:
        dict: {"ok": bool, "message_id": int|None, "error": str|None}
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"ok": False, "message_id": None, "error": "TELEGRAM_BOT_TOKEN не задан"}

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        data = resp.json()

        if data.get("ok"):
            return {"ok": True, "message_id": data["result"]["message_id"], "error": None}
        else:
            return {"ok": False, "message_id": None, "error": data.get("description", "Unknown")}

    except Exception as e:
        return {"ok": False, "message_id": None, "error": str(e)}


def save_morning_report(
    user_id: str,
    plan: dict,
    message_text: str,
    task_date: str = None,
) -> dict:
    """
    Сохранить утренний план в daily_reports.

    Returns:
        dict: {"ok": bool, "id": str|None, "error": str|None}
    """
    valid, task_date = validate_date(task_date)
    if not valid:
        return {"ok": False, "id": None, "error": task_date}

    try:
        sb = get_supabase()
        report_data = {
            "user_id": user_id,
            "report_date": task_date,
            "report_type": "morning_plan",
            "planned_tasks_count": plan.get("total", 0),
            "completed_tasks_count": 0,
            "cancelled_tasks_count": 0,
            "completion_rate": 0,
            "total_estimated_min": plan.get("total_minutes", 0),
            "total_actual_min": 0,
            "streak_snapshot": 0,
            "summary": message_text,
        }

        result = sb.table("daily_reports").upsert(
            report_data,
            on_conflict="user_id,report_date,report_type",
        ).execute()

        if result.data and len(result.data) > 0:
            return {"ok": True, "id": result.data[0]["id"], "error": None}
        return {"ok": False, "id": None, "error": "UPSERT не вернул данных"}

    except Exception as e:
        log_error("morning_report_save_failed", str(e), user_id=user_id)
        return {"ok": False, "id": None, "error": str(e)}


def send_daily_plan(
    user_id: str,
    telegram_chat_id: int,
    task_date: str = None,
) -> dict:
    """
    Полный pipeline: собрать план → форматировать → сохранить → отправить.

    Каждый этап имеет свой статус в ответе.

    Returns:
        dict: {
            "report_calculated": bool,
            "report_saved": bool,
            "telegram_sent": bool,
            "plan": dict|None,
            "message_id": int|None,
            "errors": list[str],
        }
    """
    valid, task_date = validate_date(task_date)

    result = {
        "report_calculated": False,
        "report_saved": False,
        "telegram_sent": False,
        "plan": None,
        "message_id": None,
        "errors": [],
    }

    if not valid:
        result["errors"].append(task_date)
        return result

    # 1. Собрать план
    plan = get_daily_plan(user_id, task_date)
    if not plan["ok"]:
        result["errors"].append(f"Сбор плана: {plan['error']}")
        return result
    result["report_calculated"] = True
    result["plan"] = plan

    # 2. Форматировать
    message = format_plan_message(plan, task_date)

    # 3. Сохранить отчёт
    save_result = save_morning_report(user_id, plan, message, task_date)
    result["report_saved"] = save_result["ok"]
    if not save_result["ok"]:
        result["errors"].append(f"Сохранение: {save_result.get('error')}")

    # 4. Отправить в Telegram
    send_result = send_telegram_message(telegram_chat_id, message)
    result["telegram_sent"] = send_result["ok"]
    result["message_id"] = send_result.get("message_id")
    if not send_result["ok"]:
        result["errors"].append(f"Telegram: {send_result.get('error')}")

    # 5. Логировать
    log_action(
        action_type="daily_plan_sent",
        user_id=user_id,
        entity_type="report",
        payload={
            "task_date": task_date,
            "tasks_count": plan["total"],
            "report_calculated": result["report_calculated"],
            "report_saved": result["report_saved"],
            "telegram_sent": result["telegram_sent"],
        },
        status="success" if result["telegram_sent"] else "warning",
    )

    return result


# ==================
# Тестирование
# ==================
def _run_test():
    print("=" * 50)
    print("🧪 Тест: Daily Planner")
    print("=" * 50)

    from tools.task_manager import get_or_create_user

    chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
    if chat_id == 0:
        print("❌ TELEGRAM_CHAT_ID не задан")
        sys.exit(1)

    user = get_or_create_user(chat_id)
    user_id = user["id"]
    today = date.today().isoformat()

    # 1. Сбор плана
    print("\n1. Сбор плана дня...")
    plan = get_daily_plan(user_id, today)
    print(f"   Задач: {plan['total']}, Просроченных: {len(plan['overdue'])}")
    assert plan["ok"]

    # 2. Форматирование
    print("\n2. Форматирование...")
    message = format_plan_message(plan, today)
    print(f"   Длина: {len(message)} символов")

    # 3. Полный pipeline
    print("\n3. Полный pipeline...")
    result = send_daily_plan(user_id, chat_id, today)
    print(f"   report_calculated: {result['report_calculated']}")
    print(f"   report_saved:      {result['report_saved']}")
    print(f"   telegram_sent:     {result['telegram_sent']}")
    if result["errors"]:
        print(f"   Ошибки: {result['errors']}")

    print("\n" + "=" * 50)
    print("✅ Тест завершён!")
    print("=" * 50)


if __name__ == "__main__":
    if "--test" in sys.argv:
        _run_test()
    else:
        print("Использование: python tools/daily_planner.py --test")
