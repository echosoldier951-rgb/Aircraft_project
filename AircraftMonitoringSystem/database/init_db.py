import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

#load .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "schema.sql"


def initialize_database():
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "aircraft_monitoring")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD")

    if not db_password:
        raise RuntimeError(
            "DB_PASSWORD is not set. Create a .env file or set the DB_PASSWORD environment variable."
        )

    #connect to the default postgres database
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname="postgres",
        user=db_user,
        password=db_password,
    )

    conn.autocommit = True

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,),
            )

            if cursor.fetchone() is None:
                print(f"Creating database '{db_name}'...")
                cursor.execute(f'CREATE DATABASE "{db_name}"')
            else:
                print(f"Database '{db_name}' already exists.")
    finally:
        conn.close()

    #connect to the application database
    target_conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    )

    try:
        with target_conn.cursor() as cursor:
            schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
            cursor.execute(schema_sql)

        target_conn.commit()
        print("Database schema initialized successfully.")
    except Exception:
        target_conn.rollback()
        raise
    finally:
        target_conn.close()


if __name__ == "__main__":
    initialize_database()