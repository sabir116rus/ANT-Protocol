"""
Миграция: применение SQL-схемы к Supabase PostgreSQL.
Необходимые переменные: SUPABASE_DB_URL
Запуск: python tools/run_migration.py architecture/001_mvp_schema.sql
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migration(sql_file: str) -> bool:
    db_url = os.environ.get("SUPABASE_DB_URL", "").strip()

    if not db_url:
        print("❌ SUPABASE_DB_URL не задан в .env")
        print("   Формат: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres")
        print("   Найти: Supabase Dashboard → Settings → Database → Connection string → URI")
        return False

    if "[PROJECT_REF]" in db_url or "[PASSWORD]" in db_url:
        print("❌ SUPABASE_DB_URL содержит placeholder-значения")
        print(f"   Текущее значение: {db_url[:40]}...")
        print("   Замените [PROJECT_REF] и [PASSWORD] на реальные данные из Supabase Dashboard")
        return False

    if not db_url.startswith("postgresql://"):
        print(f"❌ SUPABASE_DB_URL должен начинаться с postgresql://")
        print(f"   Текущее значение: {db_url[:40]}...")
        return False

    if not os.path.exists(sql_file):
        print(f"❌ SQL-файл не найден: {sql_file}")
        return False

    with open(sql_file, "r", encoding="utf-8") as f:
        sql = f.read()

    print(f"📄 Читаю: {sql_file}")
    print(f"📊 Размер SQL: {len(sql)} символов")
    print(f"🔗 Подключаюсь к Supabase PostgreSQL...")

    conn = None
    cur = None

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cur = conn.cursor()

        print("⚙️  Выполняю миграцию...")
        cur.execute(sql)
        conn.commit()

        print("✅ Миграция успешно применена!")

        # Проверяем созданные таблицы
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"📋 Таблицы в public: {', '.join(tables)}")
        return True

    except psycopg2.OperationalError as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        print("   Проверьте: пароль, PROJECT_REF, доступность БД")
        return False
    except psycopg2.Error as e:
        print(f"❌ Ошибка PostgreSQL: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python tools/run_migration.py <path_to_sql>")
        sys.exit(1)

    sql_path = sys.argv[1]
    success = run_migration(sql_path)
    sys.exit(0 if success else 1)
