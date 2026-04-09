# 📋 Task Plan — B.L.A.S.T. Protocol

## Статус проекта: 🟡 ФАЗА 3 — ARCHITECT (Инструменты и интеграция)

---

## Фаза 0: Инициализация ✅
- [x] Создать `task_plan.md`
- [x] Создать `findings.md`
- [x] Создать `progress.md`
- [x] Инициализировать `GEMINI.md` (Конституция проекта)
- [x] Ответы на Discovery-вопросы получены
- [x] Data Schema определена (6 сущностей)
- [x] **Blueprint утверждён пользователем** ✅

---

## Фаза 1: Blueprint (Видение и логика) ✅
- [x] North Star определена
- [x] Интеграции определены
- [x] Источник данных определён (Supabase)
- [x] Формат доставки определён
- [x] Поведенческие правила определены
- [x] Исследование ресурсов проведено

### Архитектура системы

```
┌─────────────┐     ┌──────────┐     ┌────────────┐
│  Telegram   │◄───►│   n8n    │◄───►│  Supabase  │
│  (UI/Bot)   │     │(Orchestr)│     │  (Source    │
│             │     │          │     │   of Truth) │
└─────────────┘     └────┬─────┘     └────────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼──┐ ┌─────▼──┐ ┌────▼───┐
        │ Google │ │ Notion │ │ OpenAI │
        │ Sheets │ │  API   │ │  API   │
        │(отчёты)│ │(портф.)│ │(тексты)│
        └────────┘ └────────┘ └────────┘
```

### Модули системы (по порядку сборки):

#### Модуль 1: 🗄️ База данных (Supabase)
1. Создать таблицы: `tasks`, `projects`, `clients`, `portfolio_items`
2. Настроить RLS-политики
3. Создать handshake-скрипт для проверки соединения

#### Модуль 2: 🤖 Telegram Bot (n8n)
1. Создать бота через @BotFather
2. Workflow: Telegram Trigger → Command Router → Supabase CRUD → Response
3. Команды: `/add`, `/list`, `/done`, `/projects`, `/report`, `/help`

#### Модуль 3: 📅 Daily Planner (n8n Cron)
1. Утренний план — Cron → Supabase → Формат → Telegram
2. Вечерний итог — Cron → Supabase → Stats → Telegram + Google Sheets
3. Лимит: max 7 задач в день

#### Модуль 4: 📊 Progress Tracker
1. Сбор статистики выполнения
2. Streak-трекер (дни подряд)
3. Еженедельные/месячные отчёты → Google Sheets

#### Модуль 5: 💼 Portfolio Builder (Notion)
1. При завершении проекта → автоматическое создание страницы портфолио
2. Формирование резюме на основе завершённых проектов

#### Модуль 6: 🧠 AI Helper (OpenAI)
1. Парсинг голосовых/текстовых заметок в структурированные задачи
2. Генерация описаний для портфолио
3. Помощь с текстами для клиентов

---

## Фаза 2: Link (Связность) ✅
- [x] Создать `.env.example` с описанием переменных
- [x] Создать `.env` с реальными ключами
- [x] Проверить Supabase подключение (MVP)
- [x] Проверить Telegram Bot API (MVP)
- [x] Проверить OpenAI API (MVP)
- [x] Проверить n8n доступность (MVP)
- [ ] Проверить Google Sheets API (Этап 2)
- [ ] Проверить Notion API (Этап 2)
- [x] Handshake-скрипты для каждого сервиса

## Фаза 3: Architect (Архитектура A.N.T.) — В ПРОЦЕССЕ
- [x] SOPs для каждого модуля в `architecture/`
- [x] SQL-схема v2 утверждена и применена (`001_mvp_schema.sql`)
- [x] Python-инструменты в `tools/` (activity_logger, task_manager, daily_planner, progress_tracker)
- [x] Рефакторинг: db.py (singleton), constants.py, utils.py (валидация + форматирование)
- [x] task_manager.py — стабильный порядок, лимит всех статусов, защита от дублей
- [x] n8n подключён к Python backend
- [ ] Тестирование tools через `--test` ← ⏳ ТЕКУЩИЙ ШАГ
- [ ] n8n workflows финализированы и протестированы

## Фаза 4: Stylize (Стилизация) — TODO
- [ ] Формат Telegram-сообщений (Markdown)
- [ ] Шаблоны Notion-страниц
- [ ] Формат Google Sheets отчётов
- [ ] Обратная связь от пользователя

## Фаза 5: Trigger (Деплой) — TODO
- [ ] n8n workflows активированы
- [ ] Cron-триггеры настроены
- [ ] Документация в GEMINI.md
