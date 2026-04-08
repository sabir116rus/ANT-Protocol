# SOP: Telegram Interface (Интерфейс Telegram-бота)

## Цель
Обеспечить приём команд от пользователя через Telegram, маршрутизацию к соответствующим tools и возврат форматированных ответов.

---

## Входные данные
- Telegram-сообщение (text или команда)
- `chat_id` — для идентификации пользователя
- `message_id` — для контекста

## Выходные данные
- Форматированный ответ в Telegram (Markdown)
- Вызов соответствующего tool
- Лог действия в `activity_logs`

---

## Команды MVP

| Команда | Формат | Действие |
|---------|--------|----------|
| `/start` | `/start` | Регистрация/приветствие |
| `/help` | `/help` | Список команд |
| `/add` | `/add Название задачи` | Создать задачу на сегодня |
| `/add_tomorrow` | `/add_tomorrow Задача` | Создать задачу на завтра |
| `/list` | `/list` или `/list YYYY-MM-DD` | Показать задачи на день |
| `/done` | `/done ID` или `/done номер` | Отметить задачу выполненной |
| `/skip` | `/skip ID` | Пропустить задачу |
| `/plan` | `/plan` | Показать план на сегодня |
| `/report` | `/report` | Показать вечерний отчёт |
| `/status` | `/status` | Краткая статистика |

---

## Маршрутизация (n8n)

```
Telegram Trigger
  → If: chat_id == AUTHORIZED_CHAT_ID
    → Switch: command
      → /add     → tools/task_manager.py::create_task
      → /list    → tools/task_manager.py::list_tasks
      → /done    → tools/task_manager.py::update_task_status
      → /skip    → tools/task_manager.py::update_task_status
      → /plan    → tools/daily_planner.py::get_daily_plan
      → /report  → tools/progress_tracker.py::get_daily_stats
      → /status  → tools/progress_tracker.py::get_quick_stats
      → /help    → статический текст
      → default  → «Неизвестная команда. /help для списка»
    → Telegram: отправить ответ
  → Else: игнорировать (логировать попытку)
```

---

## Бизнес-правила

1. **Авторизация:** только chat_id из .env (TELEGRAM_CHAT_ID) имеет доступ
2. **Формат ответов:** Telegram Markdown V2
3. **Ошибки:** пользователь видит человекочитаемое сообщение, не stack trace
4. **Таймаут:** если ответ > 5 сек → «⏳ Обрабатываю...» → затем результат
5. **Inline-нумерация:** задачи в /list нумеруются 1-7, /done принимает номер

---

## Edge Cases

| Ситуация | Поведение |
|----------|-----------|
| Неавторизованный пользователь | Игнор + лог |
| Пустая команда `/add` без текста | «Укажите название задачи: /add Название» |
| `/done` без номера | Показать список задач с номерами |
| Неизвестная команда | «Неизвестная команда. Введите /help» |
| Telegram API rate limit | Задержка между сообщениями |
| Бот перезапущен | Webhook автоматически восстанавливается через n8n |

---

## Используемые Tools

Telegram Interface сам не содержит tools — это слой маршрутизации (n8n).
Он вызывает tools из других модулей:
- `tools/task_manager.py`
- `tools/daily_planner.py`
- `tools/progress_tracker.py`
- `tools/activity_logger.py`

---

## Успешный результат
- Команда распознана и маршрутизирована
- Ответ доставлен пользователю < 5 сек
- Неавторизованный доступ заблокирован
- Все действия залогированы
