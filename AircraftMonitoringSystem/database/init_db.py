import os
from pathlib import Path

import psycopg2

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / 'schema.sql'


def initialize_database():
    db_name = os.getenv('DB_NAME', 'aircraft_monitoring')
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname='postgres',
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(f'CREATE DATABASE "{db_name}"')
        conn.commit()
    finally:
        conn.close()

    target_conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=db_name,
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
    )

    try:
        with target_conn.cursor() as cursor:
            schema_sql = SCHEMA_FILE.read_text(encoding='utf-8')
            for statement in [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]:
                cursor.execute(statement)
        target_conn.commit()
    finally:
        target_conn.close()


if __name__ == '__main__':
    initialize_database()
    print(f'Initialized PostgreSQL database: {os.getenv("DB_NAME", "aircraft_monitoring")}')
