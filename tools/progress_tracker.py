"""
Tool: Progress Tracker — вечерний отчёт, streak, статистика.

Контракт:
  Назначение: Сбор статистики за день, обновление streak, формирование
              и отправка вечернего отчёта. Каждый этап имеет свой статус.
  Вход:  user_id, task_date, telegram_chat_id
  Выход: dict с раздельными статусами: report_calculated, report_saved, telegram_sent
  Таблицы: tasks (SELECT), users (SELECT, UPDATE), daily_reports (UPSERT), activity_logs (INSERT)
  Зависимости: db.py, constants.py, utils.py, task_manager.py, daily_planner.py, activity_logger.py
  Тест:  python tools/progress_tracker.py --test
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.db import get_supabase
from tools.utils import escape_markdown, format_minutes, validate_date, format_date_ru
from tools.activity_logger import log_action, log_error
from tools.task_manager import list_tasks
from tools.daily_planner import send_telegram_message


def get_daily_stats(user_id: str, task_date: str = None) -> dict:
    """
    Собрать статистику за день.

    Returns:
        dict: {
            "ok": bool,
            "task_date": str,
            "tasks_total": int, "tasks_done": int,
            "tasks_cancelled": int, "tasks_pending": int,
            "completion_rate": float,
            "total_estimated_min": int, "total_actual_min": int,
            "done_tasks": list, "undone_tasks": list,
            "error": str|None,
        }
    """
    valid, task_date = validate_date(task_date)
    if not valid:
        return {"ok": False, "error": task_date}

    result = list_tasks(user_id, task_date)
    if not result["ok"]:
        return {"ok": False, "error": result["error"]}

    tasks = result["tasks"]
    total = len(tasks)

    done = [t for t in tasks if t.get("status") == "done"]
    cancelled = [t for t in tasks if t.get("status") == "cancelled"]
    pending = [t for t in tasks if t.get("status") in ("pending", "in_progress")]

    tasks_done = len(done)
    tasks_cancelled = len(cancelled)
    countable = total - tasks_cancelled
    completion_rate = round((tasks_done / countable * 100), 1) if countable > 0 else 0.0

    total_estimated = sum(t.get("estimated_minutes", 0) for t in tasks)
    total_actual = sum(t.get("actual_minutes", 0) for t in done if t.get("actual_minutes"))
    if total_actual == 0 and tasks_done > 0:
        total_actual = sum(t.get("estimated_minutes", 0) for t in done)

    return {
        "ok": True,
        "task_date": task_date,
        "tasks_total": total,
        "tasks_done": tasks_done,
        "tasks_cancelled": tasks_cancelled,
        "tasks_pending": len(pending),
        "completion_rate": completion_rate,
        "total_estimated_min": total_estimated,
        "total_actual_min": total_actual,
        "done_tasks": done,
        "undone_tasks": pending,
        "error": None,
    }


def update_streak(user_id: str, stats: dict) -> dict:
    """
    Обновить streak пользователя.

    Логика (детерминированная, в Python):
      tasks_total == 0 → выходной, streak не меняется
      tasks_done > 0, last == вчера → streak += 1
      tasks_done > 0, last == сегодня → без изменений
      tasks_done > 0, last == NULL/старше → streak = 1
      tasks_done == 0, total > 0 → streak = 0

    Returns:
        dict: {"ok": bool, "streak_days": int, "changed": bool, "error": str|None}
    """
    task_date_str = stats.get("task_date", date.today().isoformat())
    task_date_obj = date.fromisoformat(task_date_str)
    yesterday = task_date_obj - timedelta(days=1)

    try:
        sb = get_supabase()

        user_result = sb.table("users") \
            .select("streak_days, streak_last_date") \
            .eq("id", user_id).execute()

        if not user_result.data:
            return {"ok": False, "streak_days": 0, "changed": False, "error": "User not found"}

        user = user_result.data[0]
        current_streak = user.get("streak_days", 0)
        last_date_str = user.get("streak_last_date")
        last_date = date.fromisoformat(last_date_str) if last_date_str else None

        tasks_total = stats.get("tasks_total", 0)
        tasks_done = stats.get("tasks_done", 0)

        # Выходной
        if tasks_total == 0:
            return {"ok": True, "streak_days": current_streak, "changed": False, "error": None}

        new_streak = current_streak
        new_last_date = last_date_str
        changed = False

        if tasks_done > 0:
            if last_date == task_date_obj:
                pass  # Уже обновлён
            elif last_date == yesterday:
                new_streak = current_streak + 1
                new_last_date = task_date_str
                changed = True
            else:
                new_streak = 1
                new_last_date = task_date_str
                changed = True
        else:
            # 0 выполненных при наличии задач → сброс
            new_streak = 0
            new_last_date = None
            changed = True

        if changed:
            sb.table("users").update({
                "streak_days": new_streak,
                "streak_last_date": new_last_date,
            }).eq("id", user_id).execute()

            log_action(
                action_type="streak_updated",
                user_id=user_id,
                entity_type="user",
                payload={
                    "old_streak": current_streak,
                    "new_streak": new_streak,
                    "task_date": task_date_str,
                },
            )

        return {"ok": True, "streak_days": new_streak, "changed": changed, "error": None}

    except Exception as e:
        log_error("streak_update_failed", str(e), user_id=user_id)
        return {"ok": False, "streak_days": 0, "changed": False, "error": str(e)}


def format_evening_report(stats: dict, streak_days: int) -> str:
    """
    Форматировать вечерний отчёт для Telegram (MarkdownV2).
    """
    task_date = stats.get("task_date", date.today().isoformat())
    display_date = format_date_ru(task_date)
    tasks_total = stats.get("tasks_total", 0)
    tasks_done = stats.get("tasks_done", 0)
    tasks_cancelled = stats.get("tasks_cancelled", 0)
    rate = stats.get("completion_rate", 0)
    actual_min = stats.get("total_actual_min", 0)

    if tasks_total == 0:
        return (
            f"🌙 *Итоги дня {escape_markdown(display_date)}*\n\n"
            "Сегодня был выходной\\. Отдохни\\! 😴"
        )

    time_str = format_minutes(actual_min)

    streak_str = str(streak_days)
    if streak_days >= 7:
        streak_str += " 🏆"
    elif streak_days >= 3:
        streak_str += " 🔥"

    lines = [f"🌙 *Итоги дня {escape_markdown(display_date)}*\n"]
    lines.append(f"✅ Выполнено: {tasks_done}/{tasks_total} \\({escape_markdown(str(rate))}%\\)")
    if tasks_cancelled > 0:
        lines.append(f"🚫 Отменено: {tasks_cancelled}")
    lines.append(f"⏱ Время: \\~{escape_markdown(time_str)}")
    lines.append(f"🔥 Streak: {escape_markdown(streak_str)} дней подряд")

    done_tasks = stats.get("done_tasks", [])
    if done_tasks:
        lines.append("\n*Выполненные:*")
        for t in done_tasks:
            lines.append(f"✅ {escape_markdown(t['title'])}")

    undone_tasks = stats.get("undone_tasks", [])
    if undone_tasks:
        lines.append("\n*Не выполненные:*")
        for t in undone_tasks:
            lines.append(f"❌ {escape_markdown(t['title'])}")

    lines.append(f"\n━━━━━━━━━━━━━━━")
    if rate >= 100:
        lines.append("🎉 Все задачи выполнены\\! Отличный день\\!")
    elif rate >= 70:
        lines.append("💪 Хорошая работа\\! Продолжай\\!")
    elif rate >= 40:
        lines.append("🌱 Неплохо\\! Завтра будет лучше\\!")
    else:
        lines.append("🌅 Завтра новый день\\. Начни с одной задачи\\!")

    return "\n".join(lines)


def save_evening_report(
    user_id: str,
    stats: dict,
    streak_days: int,
    message_text: str,
    task_date: str = None,
) -> dict:
    """
    Сохранить вечерний отчёт в daily_reports.

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
            "report_type": "evening_report",
            "planned_tasks_count": stats.get("tasks_total", 0),
            "completed_tasks_count": stats.get("tasks_done", 0),
            "cancelled_tasks_count": stats.get("tasks_cancelled", 0),
            "completion_rate": stats.get("completion_rate", 0),
            "total_estimated_min": stats.get("total_estimated_min", 0),
            "total_actual_min": stats.get("total_actual_min", 0),
            "streak_snapshot": streak_days,
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
        log_error("evening_report_save_failed", str(e), user_id=user_id)
        return {"ok": False, "id": None, "error": str(e)}


def send_evening_report(
    user_id: str,
    telegram_chat_id: int,
    task_date: str = None,
) -> dict:
    """
    Полный pipeline: статистика → streak → формат → сохранение → отправка.

    Каждый этап имеет свой статус.

    Returns:
        dict: {
            "report_calculated": bool,
            "report_saved": bool,
            "telegram_sent": bool,
            "stats": dict|None,
            "streak_days": int,
            "message_id": int|None,
            "errors": list[str],
        }
    """
    valid, task_date = validate_date(task_date)

    result = {
        "report_calculated": False,
        "report_saved": False,
        "telegram_sent": False,
        "stats": None,
        "streak_days": 0,
        "message_id": None,
        "errors": [],
    }

    if not valid:
        result["errors"].append(task_date)
        return result

    # 1. Статистика
    stats = get_daily_stats(user_id, task_date)
    if not stats["ok"]:
        result["errors"].append(f"Статистика: {stats['error']}")
        return result
    result["report_calculated"] = True
    result["stats"] = stats

    # 2. Streak
    streak_result = update_streak(user_id, stats)
    streak_days = streak_result.get("streak_days", 0)
    result["streak_days"] = streak_days
    if not streak_result["ok"]:
        result["errors"].append(f"Streak: {streak_result.get('error')}")

    # 3. Формат
    message = format_evening_report(stats, streak_days)

    # 4. Сохранить
    save_result = save_evening_report(user_id, stats, streak_days, message, task_date)
    result["report_saved"] = save_result["ok"]
    if not save_result["ok"]:
        result["errors"].append(f"Сохранение: {save_result.get('error')}")

    # 5. Отправить
    send_result = send_telegram_message(telegram_chat_id, message)
    result["telegram_sent"] = send_result["ok"]
    result["message_id"] = send_result.get("message_id")
    if not send_result["ok"]:
        result["errors"].append(f"Telegram: {send_result.get('error')}")

    # 6. Лог
    log_action(
        action_type="evening_report_sent",
        user_id=user_id,
        entity_type="report",
        payload={
            "task_date": task_date,
            "tasks_done": stats["tasks_done"],
            "tasks_total": stats["tasks_total"],
            "completion_rate": stats["completion_rate"],
            "streak_days": streak_days,
            "report_calculated": result["report_calculated"],
            "report_saved": result["report_saved"],
            "telegram_sent": result["telegram_sent"],
        },
        status="success" if result["telegram_sent"] else "warning",
    )

    return result


def get_quick_stats(user_id: str) -> dict:
    """
    Быстрая статистика для /status.

    Returns:
        dict: краткая статистика сегодняшнего дня
    """
    today = date.today().isoformat()
    stats = get_daily_stats(user_id, today)
    if not stats["ok"]:
        return stats

    try:
        sb = get_supabase()
        user_result = sb.table("users").select("streak_days").eq("id", user_id).execute()
        streak = user_result.data[0]["streak_days"] if user_result.data else 0
    except Exception:
        streak = 0

    return {
        "ok": True,
        "date": today,
        "tasks_done": stats["tasks_done"],
        "tasks_total": stats["tasks_total"],
        "completion_rate": stats["completion_rate"],
        "streak_days": streak,
    }


# ==================
# Тестирование
# ==================
def _run_test():
    print("=" * 50)
    print("🧪 Тест: Progress Tracker")
    print("=" * 50)

    from tools.task_manager import get_or_create_user

    chat_id = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
    if chat_id == 0:
        print("❌ TELEGRAM_CHAT_ID не задан")
        sys.exit(1)

    user = get_or_create_user(chat_id)
    user_id = user["id"]
    today = date.today().isoformat()

    # 1. Статистика
    print("\n1. Статистика дня...")
    stats = get_daily_stats(user_id, today)
    print(f"   Задач: {stats['tasks_total']}, Выполнено: {stats['tasks_done']}")
    print(f"   Процент: {stats['completion_rate']}%")
    assert stats["ok"]

    # 2. Streak
    print("\n2. Streak...")
    streak = update_streak(user_id, stats)
    print(f"   Дней: {streak['streak_days']} (changed={streak['changed']})")

    # 3. Pipeline
    print("\n3. Полный pipeline...")
    result = send_evening_report(user_id, chat_id, today)
    print(f"   report_calculated: {result['report_calculated']}")
    print(f"   report_saved:      {result['report_saved']}")
    print(f"   telegram_sent:     {result['telegram_sent']}")
    if result["errors"]:
        print(f"   Ошибки: {result['errors']}")

    # 4. Quick stats
    print("\n4. Quick stats...")
    quick = get_quick_stats(user_id)
    print(f"   {quick}")

    print("\n" + "=" * 50)
    print("✅ Тест завершён!")
    print("=" * 50)


if __name__ == "__main__":
    if "--test" in sys.argv:
        _run_test()
    else:
        print("Использование: python tools/progress_tracker.py --test")
