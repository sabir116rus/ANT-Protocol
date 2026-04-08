-- ============================================
-- Antigravity Skills — MVP Schema v2
-- Дата: 2026-04-07
-- Статус: ОЖИДАНИЕ УТВЕРЖДЕНИЯ
-- RLS: отключён (backend через SERVICE_ROLE_KEY)
-- ============================================

-- ==================
-- 1. USERS
-- ==================
CREATE TABLE users (
  id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_chat_id BIGINT      NOT NULL,
  telegram_user_id BIGINT,
  username         TEXT,
  first_name       TEXT,
  timezone         TEXT        NOT NULL DEFAULT 'Europe/Moscow',
  streak_days      INTEGER     NOT NULL DEFAULT 0,
  streak_last_date DATE,
  is_active        BOOLEAN     NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT uq_users_chat_id UNIQUE (telegram_chat_id),
  CONSTRAINT uq_users_user_id UNIQUE (telegram_user_id),
  CONSTRAINT chk_streak_days  CHECK  (streak_days >= 0)
);

CREATE INDEX idx_users_chat_id ON users(telegram_chat_id);

-- ==================
-- 2. TASKS
-- ==================
CREATE TABLE tasks (
  id                UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id           UUID        NOT NULL,
  title             TEXT        NOT NULL,
  description       TEXT,
  task_date         DATE        NOT NULL DEFAULT CURRENT_DATE,
  priority          TEXT        NOT NULL DEFAULT 'medium',
  status            TEXT        NOT NULL DEFAULT 'pending',
  estimated_minutes INTEGER     NOT NULL DEFAULT 25,
  actual_minutes    INTEGER,
  source            TEXT        NOT NULL DEFAULT 'telegram',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at      TIMESTAMPTZ,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT fk_tasks_user   FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_title_len   CHECK (char_length(title) >= 3),
  CONSTRAINT chk_priority    CHECK (priority IN ('low', 'medium', 'high')),
  CONSTRAINT chk_status      CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
  CONSTRAINT chk_est_minutes CHECK (estimated_minutes BETWEEN 5 AND 240),
  CONSTRAINT chk_act_minutes CHECK (actual_minutes IS NULL OR actual_minutes BETWEEN 0 AND 480),
  CONSTRAINT chk_source      CHECK (source IN ('telegram', 'system', 'api'))
);

CREATE INDEX idx_tasks_user_date   ON tasks(user_id, task_date);
CREATE INDEX idx_tasks_status      ON tasks(status);
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);

-- ==================
-- 3. DAILY REPORTS
-- ==================
CREATE TABLE daily_reports (
  id                    UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id               UUID         NOT NULL,
  report_date           DATE         NOT NULL,
  report_type           TEXT         NOT NULL,
  planned_tasks_count   INTEGER      NOT NULL DEFAULT 0,
  completed_tasks_count INTEGER      NOT NULL DEFAULT 0,
  cancelled_tasks_count INTEGER      NOT NULL DEFAULT 0,
  completion_rate       NUMERIC(5,2) NOT NULL DEFAULT 0,
  total_estimated_min   INTEGER      NOT NULL DEFAULT 0,
  total_actual_min      INTEGER      NOT NULL DEFAULT 0,
  streak_snapshot       INTEGER      NOT NULL DEFAULT 0,
  summary               TEXT,
  created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT fk_reports_user   FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_report_type   CHECK (report_type IN ('morning_plan', 'evening_report')),
  CONSTRAINT chk_planned       CHECK (planned_tasks_count >= 0),
  CONSTRAINT chk_completed     CHECK (completed_tasks_count >= 0),
  CONSTRAINT chk_cancelled     CHECK (cancelled_tasks_count >= 0),
  CONSTRAINT chk_rate          CHECK (completion_rate BETWEEN 0 AND 100),
  CONSTRAINT uq_report_per_day UNIQUE (user_id, report_date, report_type)
);

CREATE INDEX idx_reports_user_date ON daily_reports(user_id, report_date);

-- ==================
-- 4. ACTIVITY LOGS
-- ==================
CREATE TABLE activity_logs (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id       UUID,
  action_type   TEXT        NOT NULL,
  entity_type   TEXT,
  entity_id     UUID,
  payload       JSONB       NOT NULL DEFAULT '{}',
  status        TEXT        NOT NULL DEFAULT 'success',
  error_message TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT fk_logs_user   FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_log_status CHECK (status IN ('success', 'error', 'warning'))
);

CREATE INDEX idx_logs_user    ON activity_logs(user_id);
CREATE INDEX idx_logs_action  ON activity_logs(action_type);
CREATE INDEX idx_logs_entity  ON activity_logs(entity_type, entity_id);
CREATE INDEX idx_logs_created ON activity_logs(created_at);

-- ==================
-- 5. TRIGGERS
-- ==================
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
