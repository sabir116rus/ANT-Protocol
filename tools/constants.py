"""
Константы MVP: статусы, приоритеты, лимиты.

Все tools импортируют отсюда:
  from tools.constants import TASK_STATUSES, TASK_PRIORITIES, ...
"""

# --- Задачи ---
TASK_STATUSES = ("pending", "in_progress", "done", "cancelled")
TASK_PRIORITIES = ("low", "medium", "high")
TASK_SOURCES = ("telegram", "system", "api")

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}

MAX_TASKS_PER_DAY = 7

TITLE_MIN_LENGTH = 3
ESTIMATED_MIN = 5
ESTIMATED_MAX = 240
ACTUAL_MAX = 480

DEFAULT_PRIORITY = "medium"
DEFAULT_ESTIMATED_MINUTES = 25
DEFAULT_SOURCE = "telegram"

# --- Отчёты ---
REPORT_TYPES = ("morning_plan", "evening_report")

# --- Логирование ---
LOG_STATUSES = ("success", "error", "warning")

# --- Пользователь ---
DEFAULT_TIMEZONE = "Europe/Moscow"
