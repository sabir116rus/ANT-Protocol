"""
Утилиты MVP: валидация, форматирование, хелперы.

Все tools импортируют отсюда:
  from tools.utils import validate_title, validate_date, escape_markdown, ...
"""
from datetime import date, datetime
from tools.constants import (
    TASK_STATUSES, TASK_PRIORITIES, TASK_SOURCES,
    TITLE_MIN_LENGTH, ESTIMATED_MIN, ESTIMATED_MAX,
    DEFAULT_PRIORITY, DEFAULT_ESTIMATED_MINUTES, DEFAULT_SOURCE,
)


# ==================
# Валидация
# ==================

def validate_title(title: str) -> tuple[bool, str]:
    """
    Проверить название задачи.

    Returns:
        (is_valid, cleaned_title_or_error_message)
    """
    if not title or not title.strip():
        return False, "Название задачи не может быть пустым"

    cleaned = title.strip()
    if len(cleaned) < TITLE_MIN_LENGTH:
        return False, f"Название задачи должно быть ≥ {TITLE_MIN_LENGTH} символов"

    return True, cleaned


def validate_date(task_date: str) -> tuple[bool, str]:
    """
    Проверить и нормализовать дату (YYYY-MM-DD).

    Returns:
        (is_valid, normalized_date_or_error_message)
    """
    if not task_date:
        return True, date.today().isoformat()

    try:
        parsed = date.fromisoformat(task_date)
        return True, parsed.isoformat()
    except (ValueError, TypeError):
        return False, f"Неверный формат даты: {task_date}. Ожидается YYYY-MM-DD"


def validate_priority(priority: str) -> str:
    """Нормализовать приоритет. Возвращает валидное значение."""
    if priority in TASK_PRIORITIES:
        return priority
    return DEFAULT_PRIORITY


def validate_status(status: str) -> tuple[bool, str]:
    """Проверить статус задачи."""
    if status in TASK_STATUSES:
        return True, status
    return False, f"Неверный статус: {status}. Допустимые: {', '.join(TASK_STATUSES)}"


def validate_estimated_minutes(minutes) -> int:
    """Нормализовать оценку времени. Возвращает валидное значение."""
    try:
        m = int(minutes)
    except (ValueError, TypeError):
        return DEFAULT_ESTIMATED_MINUTES

    if m < ESTIMATED_MIN:
        return ESTIMATED_MIN
    if m > ESTIMATED_MAX:
        return ESTIMATED_MAX
    return m


def validate_source(source: str) -> str:
    """Нормализовать источник."""
    if source in TASK_SOURCES:
        return source
    return DEFAULT_SOURCE


# ==================
# Форматирование
# ==================

def escape_markdown(text: str) -> str:
    """Экранирование спецсимволов для Telegram MarkdownV2."""
    special = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#',
               '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


def format_minutes(total_minutes: int) -> str:
    """Форматировать минуты в читаемую строку: '1ч 30мин' или '25мин'."""
    if total_minutes <= 0:
        return "0мин"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}ч {mins}мин"
    elif hours > 0:
        return f"{hours}ч"
    else:
        return f"{mins}мин"


def format_date_ru(iso_date: str) -> str:
    """
    Форматировать дату для отображения пользователю.
    YYYY-MM-DD → DD.MM.YYYY

    Хранение в БД остаётся YYYY-MM-DD (ISO).
    """
    try:
        parsed = date.fromisoformat(iso_date)
        return parsed.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return iso_date  # fallback: вернуть как есть
