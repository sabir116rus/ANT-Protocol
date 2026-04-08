"""
Общий модуль: Supabase client (singleton).

Все tools импортируют клиент отсюда:
  from tools.db import get_supabase
"""
import os
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_supabase():
    """
    Получить Supabase-клиент (singleton).
    Использует SERVICE_ROLE_KEY для полного доступа без RLS.

    Raises:
        ConnectionError: если переменные окружения не заданы.

    Returns:
        supabase.Client
    """
    global _client
    if _client is not None:
        return _client

    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ConnectionError(
            "SUPABASE_URL или SUPABASE_SERVICE_ROLE_KEY не заданы в .env"
        )

    _client = create_client(url, key)
    return _client


def reset_client():
    """Сбросить singleton (для тестов или переподключения)."""
    global _client
    _client = None
