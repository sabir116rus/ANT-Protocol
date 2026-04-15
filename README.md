# A.N.T. Protocol — AI Freelance Assistant

**A.N.T. Protocol** — это персональная система управления карьерой фрилансера, построенная на принципе «никогда не забывай, всегда доводи до конца». Система интегрирует Telegram, n8n и Supabase для создания бесшовного рабочего процесса.

---

## 🚀 Основные возможности (MVP)

*   **Telegram-интерфейс**: Полное управление задачами через бота.
*   **Автоматическое планирование**:
    *   **08:00 (MSK)**: Приходит план на день с текущими задачами и списком просроченных.
    *   **21:00 (MSK)**: Приходит вечерний отчет со статистикой выполнения и вашим текущим Streak (серией дней).
*   **Лимиты и Дисциплина**: Жесткое ограничение до 7 задач в день для предотвращения выгорания.
*   **Учет времени**: Оценка и фиксация времени выполнения задач.

---

## 🧩 Этап 2 — что уже добавлено

*   **Google Sheets exports**: доступны daily, weekly и monthly выгрузки на основе `daily_reports` в отдельные листы Google Sheets.
*   **Notion portfolio write**: добавлены детерминированный шаблон и реальное создание страницы в Notion Database через мягкий schema-mapping.
*   **API для этапа 2**:
    *   `POST /api/report/export/google-sheets` — экспорт сохранённого отчёта в Google Sheets.
    *   `POST /api/report/export/google-sheets/weekly` — экспорт недельной сводки в Google Sheets.
    *   `POST /api/report/export/google-sheets/monthly` — экспорт месячной сводки в Google Sheets.
    *   `POST /api/portfolio/notion-template` — генерация шаблона записи для Notion.
    *   `POST /api/portfolio/notion-page` — создание страницы в Notion Database.
*   **n8n orchestration**: `evening_report_workflow.json` теперь после вечернего отчёта автоматически пытается запускать weekly export по воскресеньям и monthly export в последний день месяца.
*   **Handshake-готовность**: в проекте уже есть проверки подключения для Google Sheets и Notion.

---

## 🛠 Технологический стек

*   **Backend**: Python 3.10+ (FastAPI)
*   **БД**: Supabase (PostgreSQL)
*   **Оркестрация**: n8n (автоматизация workflow)
*   **Бот**: Telegram Bot API
*   **Инфраструктура**: ngrok (для локальных вебхуков)

---

## 📖 Команды бота

*   `/start` — Приветствие и краткое описание.
*   `/help` — Полный список команд.
*   `/add <текст>` — Добавить новую задачу на сегодня.
*   `/list` — Показать список задач на сегодня.
*   `/done <номер>` — Отметить задачу из списка как выполненную.
*   `/cancel <номер>` — Отменить задачу (блокируется для уже выполненных).
*   `/status` — Быстрая статистика за текущий день.

---

## 📂 Структура проекта

*   `api/` — FastAPI сервер (транспортный слой).
*   `tools/` — Бизнес-логика системы:
    *   `task_manager.py` — Управление задачами и лимитами.
    *   `daily_planner.py` — Генерация утренних планов.
    *   `progress_tracker.py` — Статистика, Streak и вечерние отчеты.
    *   `google_sheets_reports.py` — Экспорт отчётов в Google Sheets.
    *   `notion_portfolio.py` — Шаблон данных для портфолио в Notion.
    *   `activity_logger.py` — Логирование всех действий в БД.
*   `architecture/` — Рабочие n8n workflow.
*   `.env` — Конфигурация API ключей и доступов.

---

## ⚙️ Установка и запуск

1.  **Клонирование**:
    ```bash
    git clone https://github.com/sabir116rus/Antigravity-Skills.git
    cd Antigravity-Skills
    ```

2.  **Настройка окружения**:
    Создайте `.env` на базе `.env.example` и заполните:
    *   `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`
    *   `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
    *   `API_SECRET_KEY` (любой надежный пароль)
    *   Для этапа 2 дополнительно:
        *   `GOOGLE_SHEETS_CREDENTIALS_PATH` / `GOOGLE_SHEETS_SPREADSHEET_ID`
        *   `GOOGLE_SHEETS_WORKSHEET_TITLE`
        *   `GOOGLE_SHEETS_WEEKLY_WORKSHEET_TITLE`
        *   `GOOGLE_SHEETS_MONTHLY_WORKSHEET_TITLE`
        *   `NOTION_API_KEY` / `NOTION_DATABASE_ID`

3.  **Запуск API**:
    ```bash
    pip install -r requirements.txt
    uvicorn api.server:app --port 8000
    ```

4.  **n8n Workflow**:
    *   Импортируйте JSON-файлы из `architecture/` в ваш n8n.
    *   Настройте переменные окружения в n8n (`FASTAPI_URL`, `API_SECRET_KEY`, `TELEGRAM_CHAT_ID`).

---

## 🔌 Stage 2 API

*   `POST /api/report/export/google-sheets`
    *   Вход: `telegram_chat_id`, `task_date`, `report_type`
    *   Назначение: экспорт уже сохранённого daily report в Google Sheets
*   `POST /api/report/export/google-sheets/weekly`
    *   Вход: `telegram_chat_id`, `anchor_date`
    *   Назначение: экспорт недельной сводки по `daily_reports` в Google Sheets
*   `POST /api/report/export/google-sheets/monthly`
    *   Вход: `telegram_chat_id`, `anchor_date`
    *   Назначение: экспорт месячной сводки по `daily_reports` в Google Sheets
*   `POST /api/portfolio/notion-template`
    *   Вход: `title`, `description`, `category`, `technologies`, `result_url`, `source`, `status`
    *   Назначение: построение шаблона записи портфолио для Notion без привязки к конкретной схеме БД
*   `POST /api/portfolio/notion-page`
    *   Вход: `title`, `description`, `category`, `technologies`, `result_url`, `source`, `status`, `database_id`
    *   Назначение: создание страницы в Notion Database с автоматическим подбором совместимых свойств

---

## 📊 Streak System
Система отслеживает вашу активность. Выполнение хотя бы одной задачи в день поддерживает ваш Streak. Пропуск рабочего дня (если задачи были поставлены) сбрасывает Streak до нуля. Выходные (когда задач нет) не прерывают серию.

---

**North Star:** Система снижает прокрастинацию, структурирует работу и помогает фрилансеру доводить проекты до результата.
