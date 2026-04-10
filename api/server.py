"""
Antigravity Skills — FastAPI Server (MVP)

Тонкий transport layer для вызова tools из n8n.
Бизнес-логика остаётся в tools/*.py.

Запуск: uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import sys
from datetime import date
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from tools.task_manager import create_task, list_tasks, update_task_status, get_or_create_user, get_task_by_number
from tools.daily_planner import send_daily_plan
from tools.progress_tracker import send_evening_report, get_quick_stats
from tools.activity_logger import log_action


# ==================
# Auth
# ==================
API_KEY = os.environ.get("API_SECRET_KEY", "")


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Проверка API-ключа. Все запросы должны содержать заголовок X-API-Key."""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_SECRET_KEY не задан на сервере")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")
    return True


# ==================
# App
# ==================
@asynccontextmanager
async def lifespan(app: FastAPI):
    log_action(action_type="api_started", payload={"host": "0.0.0.0", "port": 8000})
    yield
    log_action(action_type="api_stopped")


app = FastAPI(
    title="Antigravity Skills API",
    version="0.1.0",
    description="MVP API для управления задачами через n8n + Telegram",
    lifespan=lifespan,
)


# ==================
# Models (Pydantic)
# ==================
class TaskCreateRequest(BaseModel):
    telegram_chat_id: int = Field(..., description="Telegram chat ID пользователя")
    title: str = Field(..., min_length=3, description="Название задачи")
    task_date: str | None = Field(None, description="Дата задачи (YYYY-MM-DD)")
    priority: str = Field("medium", description="low / medium / high")
    estimated_minutes: int = Field(25, ge=5, le=240)


class TaskStatusRequest(BaseModel):
    telegram_chat_id: int
    task_number: int = Field(..., ge=1, le=7, description="Номер задачи в списке (1-7)")
    new_status: str = Field(..., description="done / cancelled / pending")
    task_date: str | None = None


class ListRequest(BaseModel):
    telegram_chat_id: int
    task_date: str | None = None


# ==================
# Helpers
# ==================
def _get_user(telegram_chat_id: int) -> dict:
    """Получить user_id по chat_id."""
    try:
        user = get_or_create_user(telegram_chat_id)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения пользователя: {e}")


# ==================
# Endpoints
# ==================

@app.get("/health")
async def health():
    """Health check для n8n и мониторинга."""
    return {"status": "ok", "service": "antigravity-api", "version": "0.1.0"}


@app.post("/api/tasks", dependencies=[Depends(verify_api_key)])
async def api_create_task(req: TaskCreateRequest):
    """
    Создать задачу.
    n8n вызывает при команде /add.
    """
    user = _get_user(req.telegram_chat_id)

    result = create_task(
        user_id=user["id"],
        title=req.title,
        task_date=req.task_date,
        priority=req.priority,
        estimated_minutes=req.estimated_minutes,
    )

    if not result["ok"]:
        return {"ok": False, "error": result["error"]}

    task = result["task"]
    return {
        "ok": True,
        "action": "task_created",
        "task": {
            "id": task["id"],
            "title": task["title"],
            "task_date": task["task_date"],
            "priority": task["priority"],
            "estimated_minutes": task["estimated_minutes"],
        },
    }


@app.post("/api/tasks/list", dependencies=[Depends(verify_api_key)])
async def api_list_tasks(req: ListRequest):
    """
    Получить задачи на день.
    n8n вызывает при команде /list.
    """
    user = _get_user(req.telegram_chat_id)
    task_date = req.task_date or date.today().isoformat()

    result = list_tasks(user["id"], task_date)

    if not result["ok"]:
        return {"ok": False, "error": result["error"]}

    tasks = []
    for i, t in enumerate(result["tasks"], 1):
        tasks.append({
            "number": i,
            "id": t["id"],
            "title": t["title"],
            "priority": t["priority"],
            "status": t["status"],
            "estimated_minutes": t.get("estimated_minutes", 25),
        })

    return {
        "ok": True,
        "task_date": task_date,
        "count": result["count"],
        "tasks": tasks,
    }


@app.post("/api/tasks/status", dependencies=[Depends(verify_api_key)])
async def api_update_task_status(req: TaskStatusRequest):
    """
    Обновить статус задачи по номеру в списке.
    n8n вызывает при команде /done или /skip.
    """
    user = _get_user(req.telegram_chat_id)
    task_date = req.task_date or date.today().isoformat()

    # Найти задачу по номеру
    found = get_task_by_number(user["id"], req.task_number, task_date)
    if not found["ok"]:
        return {"ok": False, "error": found["error"]}

    task = found["task"]

    # Обновить статус
    result = update_task_status(user["id"], task["id"], req.new_status)
    if not result["ok"]:
        return {"ok": False, "error": result["error"]}

    return {
        "ok": True,
        "action": "task_status_updated",
        "task_number": req.task_number,
        "title": task["title"],
        "task_id": task["id"],
        "new_status": req.new_status,
    }


@app.post("/api/status", dependencies=[Depends(verify_api_key)])
async def api_quick_stats(req: ListRequest):
    """
    Быстрая статистика дня.
    n8n вызывает при команде /status.
    """
    user = _get_user(req.telegram_chat_id)
    result = get_quick_stats(user["id"])

    if not result["ok"]:
        return {"ok": False, "error": result.get("error", "Ошибка статистики")}

    return result
