"""
Tool: Google Sheets Reports — экспорт daily_reports в таблицу.

Назначение:
  Необязательный этап 2. Забирает уже сохраненный отчёт из Supabase и
  добавляет строку в Google Sheets. Не влияет на MVP-контур, если не настроен.
"""
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.db import get_supabase
from tools.utils import validate_date

load_dotenv()


REPORT_EXPORT_HEADERS = [
    "exported_at",
    "report_date",
    "report_type",
    "user_id",
    "planned_tasks_count",
    "completed_tasks_count",
    "cancelled_tasks_count",
    "completion_rate",
    "total_estimated_min",
    "total_actual_min",
    "streak_snapshot",
    "summary",
]

PERIOD_EXPORT_HEADERS = [
    "exported_at",
    "period_type",
    "period_start",
    "period_end",
    "user_id",
    "reports_count",
    "planned_tasks_total",
    "completed_tasks_total",
    "cancelled_tasks_total",
    "completion_rate_avg",
    "estimated_minutes_total",
    "actual_minutes_total",
    "best_day_completion_rate",
    "streak_last_snapshot",
]


def _get_config() -> dict:
    return {
        "credentials_path": os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH"),
        "spreadsheet_id": os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID"),
        "worksheet_title": os.environ.get("GOOGLE_SHEETS_WORKSHEET_TITLE", "Daily Reports"),
        "weekly_worksheet_title": os.environ.get("GOOGLE_SHEETS_WEEKLY_WORKSHEET_TITLE", "Weekly Reports"),
        "monthly_worksheet_title": os.environ.get("GOOGLE_SHEETS_MONTHLY_WORKSHEET_TITLE", "Monthly Reports"),
    }


def _is_placeholder(value: str | None, placeholder: str) -> bool:
    return not value or value == placeholder


def _get_worksheet():
    return _get_named_worksheet(_get_config()["worksheet_title"], len(REPORT_EXPORT_HEADERS) + 2)


def _get_named_worksheet(worksheet_title: str, columns_count: int):
    config = _get_config()
    credentials_path = config["credentials_path"]
    spreadsheet_id = config["spreadsheet_id"]

    if _is_placeholder(credentials_path, "./credentials/google_sheets.json"):
        return None, {
            "ok": True,
            "status": "skipped",
            "error": None,
            "reason": "GOOGLE_SHEETS_CREDENTIALS_PATH не настроен",
        }

    if _is_placeholder(spreadsheet_id, "your-spreadsheet-id"):
        return None, {
            "ok": True,
            "status": "skipped",
            "error": None,
            "reason": "GOOGLE_SHEETS_SPREADSHEET_ID не настроен",
        }

    if not os.path.exists(credentials_path):
        return None, {
            "ok": False,
            "status": "error",
            "error": f"Файл credentials не найден: {credentials_path}",
            "reason": None,
        }

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(spreadsheet_id)

        try:
            worksheet = spreadsheet.worksheet(worksheet_title)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_title,
                rows=1000,
                cols=columns_count,
            )

        return worksheet, None

    except ImportError as exc:
        return None, {
            "ok": False,
            "status": "error",
            "error": f"Google Sheets библиотеки не установлены: {exc}",
            "reason": None,
        }
    except Exception as exc:
        return None, {
            "ok": False,
            "status": "error",
            "error": str(exc),
            "reason": None,
        }


def get_daily_report_for_export(user_id: str, report_date: str = None, report_type: str = "evening_report") -> dict:
    valid, report_date = validate_date(report_date)
    if not valid:
        return {"ok": False, "report": None, "error": report_date}

    try:
        sb = get_supabase()
        result = (
            sb.table("daily_reports")
            .select(
                "created_at, report_date, report_type, user_id, planned_tasks_count, "
                "completed_tasks_count, cancelled_tasks_count, completion_rate, "
                "total_estimated_min, total_actual_min, streak_snapshot, summary"
            )
            .eq("user_id", user_id)
            .eq("report_date", report_date)
            .eq("report_type", report_type)
            .limit(1)
            .execute()
        )

        if not result.data:
            return {"ok": False, "report": None, "error": "Отчёт не найден в daily_reports"}

        return {"ok": True, "report": result.data[0], "error": None}

    except Exception as exc:
        return {"ok": False, "report": None, "error": str(exc)}


def get_reports_for_period(
    user_id: str,
    period_start: str,
    period_end: str,
    report_type: str = "evening_report",
) -> dict:
    try:
        sb = get_supabase()
        result = (
            sb.table("daily_reports")
            .select(
                "created_at, report_date, report_type, user_id, planned_tasks_count, "
                "completed_tasks_count, cancelled_tasks_count, completion_rate, "
                "total_estimated_min, total_actual_min, streak_snapshot, summary"
            )
            .eq("user_id", user_id)
            .eq("report_type", report_type)
            .gte("report_date", period_start)
            .lte("report_date", period_end)
            .order("report_date")
            .execute()
        )
        return {"ok": True, "reports": result.data or [], "error": None}
    except Exception as exc:
        return {"ok": False, "reports": [], "error": str(exc)}


def build_google_sheets_row(report: dict) -> list[str]:
    return [
        str(report.get("created_at") or ""),
        str(report.get("report_date") or ""),
        str(report.get("report_type") or ""),
        str(report.get("user_id") or ""),
        str(report.get("planned_tasks_count") or 0),
        str(report.get("completed_tasks_count") or 0),
        str(report.get("cancelled_tasks_count") or 0),
        str(report.get("completion_rate") or 0),
        str(report.get("total_estimated_min") or 0),
        str(report.get("total_actual_min") or 0),
        str(report.get("streak_snapshot") or 0),
        str(report.get("summary") or ""),
    ]


def _build_period_row(summary: dict) -> list[str]:
    return [
        str(summary.get("exported_at") or ""),
        str(summary.get("period_type") or ""),
        str(summary.get("period_start") or ""),
        str(summary.get("period_end") or ""),
        str(summary.get("user_id") or ""),
        str(summary.get("reports_count") or 0),
        str(summary.get("planned_tasks_total") or 0),
        str(summary.get("completed_tasks_total") or 0),
        str(summary.get("cancelled_tasks_total") or 0),
        str(summary.get("completion_rate_avg") or 0),
        str(summary.get("estimated_minutes_total") or 0),
        str(summary.get("actual_minutes_total") or 0),
        str(summary.get("best_day_completion_rate") or 0),
        str(summary.get("streak_last_snapshot") or 0),
    ]


def _calculate_week_range(anchor_date: str | None) -> tuple[str, str]:
    valid, anchor_date = validate_date(anchor_date)
    if not valid:
        raise ValueError(anchor_date)

    anchor = date.fromisoformat(anchor_date)
    period_start = anchor - timedelta(days=anchor.weekday())
    period_end = period_start + timedelta(days=6)
    return period_start.isoformat(), period_end.isoformat()


def _calculate_month_range(anchor_date: str | None) -> tuple[str, str]:
    valid, anchor_date = validate_date(anchor_date)
    if not valid:
        raise ValueError(anchor_date)

    anchor = date.fromisoformat(anchor_date)
    period_start = anchor.replace(day=1)
    if anchor.month == 12:
        next_month = anchor.replace(year=anchor.year + 1, month=1, day=1)
    else:
        next_month = anchor.replace(month=anchor.month + 1, day=1)
    period_end = next_month - timedelta(days=1)
    return period_start.isoformat(), period_end.isoformat()


def _summarize_reports(user_id: str, period_type: str, period_start: str, period_end: str, reports: list[dict]) -> dict:
    reports_count = len(reports)
    completion_rates = [float(report.get("completion_rate") or 0) for report in reports]
    return {
        "exported_at": date.today().isoformat(),
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "user_id": user_id,
        "reports_count": reports_count,
        "planned_tasks_total": sum(int(report.get("planned_tasks_count") or 0) for report in reports),
        "completed_tasks_total": sum(int(report.get("completed_tasks_count") or 0) for report in reports),
        "cancelled_tasks_total": sum(int(report.get("cancelled_tasks_count") or 0) for report in reports),
        "completion_rate_avg": round(sum(completion_rates) / reports_count, 1) if reports_count else 0,
        "estimated_minutes_total": sum(int(report.get("total_estimated_min") or 0) for report in reports),
        "actual_minutes_total": sum(int(report.get("total_actual_min") or 0) for report in reports),
        "best_day_completion_rate": max(completion_rates) if completion_rates else 0,
        "streak_last_snapshot": int(reports[-1].get("streak_snapshot") or 0) if reports else 0,
    }


def _export_period_summary(
    user_id: str,
    period_type: str,
    period_start: str,
    period_end: str,
    worksheet_title: str,
) -> dict:
    worksheet, worksheet_error = _get_named_worksheet(worksheet_title, len(PERIOD_EXPORT_HEADERS) + 2)
    if worksheet_error:
        return worksheet_error

    reports_result = get_reports_for_period(user_id, period_start, period_end)
    if not reports_result["ok"]:
        return {
            "ok": False,
            "status": "error",
            "error": reports_result["error"],
            "reason": None,
        }

    reports = reports_result["reports"]
    if not reports:
        return {
            "ok": True,
            "status": "skipped",
            "error": None,
            "reason": "Нет daily_reports для выбранного периода",
            "worksheet_title": worksheet.title,
        }

    summary = _summarize_reports(user_id, period_type, period_start, period_end, reports)

    try:
        headers = worksheet.row_values(1)
        if not headers:
            worksheet.append_row(PERIOD_EXPORT_HEADERS, value_input_option="USER_ENTERED")

        worksheet.append_row(_build_period_row(summary), value_input_option="USER_ENTERED")
        return {
            "ok": True,
            "status": "success",
            "error": None,
            "reason": None,
            "worksheet_title": worksheet.title,
            "summary": summary,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "error": str(exc),
            "reason": None,
        }


def export_daily_report_to_google_sheets(
    user_id: str,
    report_date: str = None,
    report_type: str = "evening_report",
) -> dict:
    worksheet, worksheet_error = _get_worksheet()
    if worksheet_error:
        return worksheet_error

    report_result = get_daily_report_for_export(user_id, report_date, report_type)
    if not report_result["ok"]:
        return {
            "ok": False,
            "status": "error",
            "error": report_result["error"],
            "reason": None,
        }

    report = report_result["report"]

    try:
        headers = worksheet.row_values(1)
        if not headers:
            worksheet.append_row(REPORT_EXPORT_HEADERS, value_input_option="USER_ENTERED")

        worksheet.append_row(build_google_sheets_row(report), value_input_option="USER_ENTERED")
        return {
            "ok": True,
            "status": "success",
            "error": None,
            "reason": None,
            "worksheet_title": worksheet.title,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "error": str(exc),
            "reason": None,
        }


def export_weekly_report_to_google_sheets(user_id: str, anchor_date: str = None) -> dict:
    try:
        period_start, period_end = _calculate_week_range(anchor_date)
    except ValueError as exc:
        return {"ok": False, "status": "error", "error": str(exc), "reason": None}

    return _export_period_summary(
        user_id=user_id,
        period_type="weekly",
        period_start=period_start,
        period_end=period_end,
        worksheet_title=_get_config()["weekly_worksheet_title"],
    )


def export_monthly_report_to_google_sheets(user_id: str, anchor_date: str = None) -> dict:
    try:
        period_start, period_end = _calculate_month_range(anchor_date)
    except ValueError as exc:
        return {"ok": False, "status": "error", "error": str(exc), "reason": None}

    return _export_period_summary(
        user_id=user_id,
        period_type="monthly",
        period_start=period_start,
        period_end=period_end,
        worksheet_title=_get_config()["monthly_worksheet_title"],
    )
