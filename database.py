import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL
)

@contextmanager
def get_db_connection():
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            yield cursor
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def init_db():
    with get_db_connection() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'agent','customer')),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            ''')
         # categories
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
             ''')
          # ticket_assignments
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                customer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                assigned_to BIGINT REFERENCES users(id) ON DELETE SET NULL,
                category_id INT REFERENCES categories(id) ON DELETE SET NULL,
                priority VARCHAR(20) NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                status VARCHAR(20) NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMPTZ
                );
            ''')

            # 4. ticket_status_history — satisfies "status updates" + powers reporting (time-to-resolve, audit trail)
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_status_history (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    ticket_id BIGINT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                    old_status VARCHAR(20),
                    new_status VARCHAR(20) NOT NULL,
                    changed_by_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    note TEXT
                );
            ''')
            # 5. ticket_comments — communication thread between customer and admin on a ticket
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_comments (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    ticket_id BIGINT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                    body TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            ''')