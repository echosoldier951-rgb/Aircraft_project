# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# IMPORTANT: Explicitly tell Flask where static folder is
app = Flask(__name__, static_folder=str(BASE_DIR / "static"))

SCHEMA_FILE = BASE_DIR.parent / "database" / "schema.sql"


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "aircraft_monitoring"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def initialize_database():
    print("Schema path:", SCHEMA_FILE)
    print("Schema exists:", SCHEMA_FILE.exists())

    if not SCHEMA_FILE.exists():
        app.logger.warning("schema.sql not found at %s", SCHEMA_FILE)
        return

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
                cursor.execute(schema_sql)
            connection.commit()
    except Exception as exc:
        app.logger.warning("PostgreSQL initialization skipped: %s", exc)


def format_flight(row):
    return {
        "Flight Number": row[0],
        "Aircraft Status": row[1],
        "Passenger Boarding Number": row[2],
        "Fueling": row[3],
        "Door State": row[4],
        "Push Back Time": row[5],
    }


def get_flight_by_number(flight_number):
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

    return format_flight(row)


def update_flight(data):
    flight_number = str(data.get("Flight Number", "")).strip()

    if not flight_number:
        return None

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE flights
                SET
                    aircraft_status = %s,
                    passenger_boarding_number = %s,
                    fueling = %s,
                    door_state = %s,
                    push_back_time = %s
                WHERE flight_number = %s
                RETURNING
                    flight_number,
                    aircraft_status,
                    passenger_boarding_number,
                    fueling,
                    door_state,
                    push_back_time
                """,
                (
                    data.get("Aircraft Status"),
                    data.get("Passenger Boarding Number"),
                    data.get("Fueling"),
                    data.get("Door State"),
                    data.get("Push Back Time"),
                    flight_number,
                ),
            )

            row = cursor.fetchone()
            connection.commit()

    if row is None:
        return None

    return format_flight(row)


def get_all_events():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    flight_number,
                    autopilot_status,
                    cabin_pressure,
                    wifi_usage
                FROM events
            """)
            rows = cursor.fetchall()

    return rows


@app.route("/client", methods=["GET"])
def index():
    return send_file(BASE_DIR / "client_dashboard.html")


@app.route("/ground-controller", methods=["GET"])
def ground_controller():
    return send_file(BASE_DIR / "ground_controller.html")


@app.route("/flight", methods=["GET"])
def get_flight():
    flight_number = request.args.get("flight_number", "").strip()

    if not flight_number:
        return jsonify({"error": "flight_number is required"}), 400

    try:
        data = get_flight_by_number(flight_number)
    except Exception as exc:
        app.logger.exception("Unable to load flight data: %s", exc)
        return jsonify({"error": "Unable to load flight data from database"}), 503

    if data is None:
        return jsonify({"error": f"No flight found for {flight_number}"}), 404

    return jsonify(data), 200

@app.route("/updateFlightInfo", methods=["PUT"])
def put_flight():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        updated_data = update_flight(data)
    except Exception as exc:
        app.logger.exception("Unable to update flight data: %s", exc)
        return jsonify({"error": "Unable to update flight data"}), 503

    if updated_data is None:
        return jsonify({"error": "No matching flight found to update"}), 404

    return jsonify(updated_data), 202
@app.route("/flight-file", methods=["GET"])
def get_flight_file():
    try:
        with open(BASE_DIR / "flight_data.json", "r") as file:
            data = json.load(file)

        return jsonify(data), 200

    except Exception as exc:
        app.logger.exception("Unable to load flight data: %s", exc)
        return jsonify({"error": "Unable to load flight data"}), 500


@app.route("/events", methods=["GET"])
def get_events():
    try:
        rows = get_all_events()

        events = []
        for row in rows:
            events.append({
                "Flight Number": row[0],
                "Autopilot Status": row[1],
                "Cabin Pressure": float(row[2]),
                "WiFi Usage": row[3]
            })

        return jsonify(events), 200

    except Exception as exc:
        app.logger.exception("Unable to load event data: %s", exc)
        return jsonify({"error": "Unable to load event data"}), 500


# Debug route for CSS
@app.route("/test")
def test():
    return {
        "BASE_DIR": str(BASE_DIR),
        "STATIC_EXISTS": (BASE_DIR / "static").exists(),
        "CSS_EXISTS": (BASE_DIR / "static" / "styles.css").exists()
    }


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)