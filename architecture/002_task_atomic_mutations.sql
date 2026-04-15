-- ============================================
-- Atomic task creation for daily-limit enforcement
-- Date: 2026-04-12
-- ============================================

CREATE OR REPLACE FUNCTION public.create_task_atomic(
  p_user_id UUID,
  p_title TEXT,
  p_task_date DATE,
  p_priority TEXT,
  p_description TEXT,
  p_estimated_minutes INTEGER,
  p_source TEXT,
  p_max_tasks_per_day INTEGER DEFAULT 7
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_count INTEGER;
  v_task tasks%ROWTYPE;
BEGIN
  -- Serialize create requests per user+date within transaction.
  PERFORM pg_advisory_xact_lock(
    hashtextextended(p_user_id::TEXT || ':' || p_task_date::TEXT, 0)
  );

  SELECT COUNT(*) INTO v_count
  FROM tasks
  WHERE user_id = p_user_id
    AND task_date = p_task_date;

  IF v_count >= p_max_tasks_per_day THEN
    RETURN jsonb_build_object(
      'ok', FALSE,
      'error_code', 'TASK_LIMIT_REACHED',
      'current_count', v_count,
      'max_tasks', p_max_tasks_per_day,
      'task', NULL
    );
  END IF;

  INSERT INTO tasks (
    user_id,
    title,
    description,
    task_date,
    priority,
    estimated_minutes,
    source
  )
  VALUES (
    p_user_id,
    p_title,
    p_description,
    p_task_date,
    p_priority,
    p_estimated_minutes,
    p_source
  )
  RETURNING * INTO v_task;

  RETURN jsonb_build_object(
    'ok', TRUE,
    'task', to_jsonb(v_task),
    'current_count', v_count + 1,
    'max_tasks', p_max_tasks_per_day
  );
END;
$$;
