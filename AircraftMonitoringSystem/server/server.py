# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path

import psycopg2
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'flight_data.json'
SCHEMA_FILE = BASE_DIR.parent / 'database' / 'schema.sql'


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'aircraft_monitoring'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
    )


def initialize_database():
    if not SCHEMA_FILE.exists():
        return

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                schema_sql = SCHEMA_FILE.read_text(encoding='utf-8')
                for statement in [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]:
                    cursor.execute(statement)
            connection.commit()
    except Exception as exc:
        app.logger.warning('PostgreSQL initialization skipped: %s', exc)


def get_flight_by_number(flight_number: str):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    flight_number,
                    aircraft_status,
                    passenger_boarding_number,
                    fueling,
                    door_state,
                    push_back_time
                FROM flights
                WHERE flight_number = %s
                """,
                (flight_number,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        'Aircraft Status': row[1],
        'Passenger Boarding Number': row[2],
        'Fueling': row[3],
        'Door State': row[4],
        'Push Back Time': row[5],
        'Flight number': row[0],
    }


@app.route('/', methods=['GET'])
def index():
    return send_file(BASE_DIR / 'flight_dashboard.html')


@app.route('/flight', methods=['GET'])
def get_flight():
    flight_number = request.args.get('flight_number', '').strip() or os.getenv('DEFAULT_FLIGHT_NUMBER', 'AB1234')

    initialize_database()

    try:
        data = get_flight_by_number(flight_number)
    except Exception as exc:
        app.logger.warning('Falling back to JSON data because PostgreSQL is unavailable: %s', exc)
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)

    if data is None:
        return jsonify({'error': f'No flight found for {flight_number}'}), 404

    return jsonify(data), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)