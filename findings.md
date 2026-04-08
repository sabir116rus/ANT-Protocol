# 🔍 Findings — Исследования и открытия

## Дата создания: 2026-04-06

---

## Архитектурные решения

### 1. Стек технологий
- **Telegram Bot API** → основной UI через @BotFather
- **n8n (self-hosted)** → оркестратор: связь Telegram ↔ Supabase ↔ Google Sheets
- **Supabase (PostgreSQL)** → Source of Truth для задач, проектов, клиентов
- **Python** → детерминированные инструменты (tools/)
- **OpenAI API** → генерация текстов (через n8n Code/HTTP ноды)
- **Notion API** → портфолио, резюме, база знаний
- **Google Sheets API** → отчёты и учёт

### 2. Архитектура n8n-воркфлоуов
По результатам исследования, оптимальная структура:

**Workflow 1 — Telegram Command Router:**
- Telegram Trigger → If (авторизация chat_id) → Switch (команды) → Supabase CRUD → Telegram ответ
- Команды: `/add`, `/list`, `/done`, `/projects`, `/report`

**Workflow 2 — Daily Planner (Cron):**
- Cron (утро) → Supabase SELECT (задачи на сегодня) → Format → Telegram сообщение

**Workflow 3 — Progress Tracker (Cron):**
- Cron (вечер) → Supabase SELECT (выполненные задачи) → Calculate stats → Google Sheets + Telegram

**Workflow 4 — Portfolio Builder:**
- Trigger (проект завершён) → Supabase SELECT → Format → Notion API → Portfolio page

### 3. Суpabase Schema (SQL)
```sql
-- Таблица клиентов
CREATE TABLE clients (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  contact TEXT,
  platform TEXT DEFAULT 'direct',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Таблица проектов
CREATE TABLE projects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  client_id UUID REFERENCES clients(id),
  category TEXT DEFAULT 'other',
  status TEXT DEFAULT 'idea',
  deadline DATE,
  budget NUMERIC,
  currency TEXT DEFAULT 'RUB',
  tasks_total INTEGER DEFAULT 0,
  tasks_done INTEGER DEFAULT 0,
  progress_percent INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Таблица задач
CREATE TABLE tasks (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  project_id UUID REFERENCES projects(id),
  date DATE DEFAULT CURRENT_DATE,
  time_slot TEXT,
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending',
  estimated_minutes INTEGER DEFAULT 25,
  actual_minutes INTEGER,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  source TEXT DEFAULT 'user'
);

-- Таблица портфолио
CREATE TABLE portfolio_items (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  title TEXT NOT NULL,
  description TEXT,
  category TEXT DEFAULT 'other',
  technologies TEXT[] DEFAULT '{}',
  result_url TEXT,
  screenshots TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  is_published BOOLEAN DEFAULT false
);
```

### 4. Python-клиент Supabase
```bash
pip install supabase python-dotenv
```
```python
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)
```

---

## Ограничения и риски

1. **RLS (Row Level Security)** — нужно настроить в Supabase для безопасности
2. **Rate limits** — Telegram API: 30 сообщений/сек; OpenAI: зависит от тарифа
3. **n8n self-hosted** — нужен стабильный хостинг (Docker на VPS или локально)
4. **Notion API** — ограничения на количество запросов (3 req/sec)
5. **Макс. 7 задач в день** — жёсткий лимит нашей системы

---

## Полезные ресурсы

- [n8n Telegram + Supabase шаблоны](https://n8n.io/workflows/)
- [Supabase Python Client Docs](https://supabase.com/docs/reference/python/introduction)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Notion API](https://developers.notion.com/)
