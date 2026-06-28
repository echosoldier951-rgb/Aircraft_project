# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Use Flask's standard project layout: templates/ for HTML and static/ for assets.
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

SCHEMA_FILE = BASE_DIR.parent / "database" / "schema.sql"
LOG_PREFIX = "[Server]"


def log_print(*args):
    print(LOG_PREFIX, *args)


def log_warning(message, *args):
    app.logger.warning(f"{LOG_PREFIX} {message}", *args)


def log_exception(message, *args):
    app.logger.exception(f"{LOG_PREFIX} {message}", *args)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, DELETE, OPTIONS"
    return response


def get_db_connection():
    # Create a new PostgreSQL connection using env vars (with safe local defaults).
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "aircraft_monitoring"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def initialize_database():
    # Run schema.sql on startup so required tables exist.
    log_print("Schema path:", SCHEMA_FILE)
    log_print("Schema exists:", SCHEMA_FILE.exists())

    if not SCHEMA_FILE.exists():
        log_warning("schema.sql not found at %s", SCHEMA_FILE)
        return

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
                cursor.execute(schema_sql)
            connection.commit()
    except Exception as exc:
        log_warning("PostgreSQL initialization skipped: %s", exc)


def format_flight(row):
    # Convert database tuple to the API response shape expected by dashboards.
    push_back_time = row[6]

    return {
        "Flight Number": row[0],
        "Simple Status": row[1],
        "Detailed Status": row[2],
        "Passenger Boarding Number": row[3],
        "Fueling": row[4],
        "Door State": row[5],
        "Push Back Time": push_back_time.strftime("%H:%M") if push_back_time else None,
    }


def format_monitor_data(row):
    # Convert joined flight/event tuples into one flat monitoring payload.
    push_back_time = row[6]

    return {
        "Flight Number": row[0],
        "Simple Status": row[1],
        "Detailed Status": row[2],
        "Passenger Boarding Number": row[3],
        "Fueling": row[4],
        "Door State": row[5],
        "Push Back Time": push_back_time.strftime("%H:%M") if push_back_time else None,
        "Autopilot Status": row[7],
        "Cabin Pressure": float(row[8]),
        "WiFi Usage": row[9],
    }


def get_flight_by_number(flight_number):
    # Fetch a single flight row by its unique flight number.
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    flight_number,
                    simple_status,
                    detailed_status,
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
    # Update one flight and return the updated row.
    flight_number = str(data.get("Flight Number", "")).strip()
    simple_status = data.get("Simple Status")
    if simple_status is None:
        simple_status = data.get("Aircraft Status")

    detailed_status = data.get("Detailed Status")

    if not flight_number:
        return None

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE flights
                SET
                    simple_status = COALESCE(%s, simple_status),
                    detailed_status = COALESCE(%s, detailed_status),
                    passenger_boarding_number = %s,
                    fueling = %s,
                    door_state = %s,
                    push_back_time = %s
                WHERE flight_number = %s
                RETURNING
                    flight_number,
                    simple_status,
                    detailed_status,
                    passenger_boarding_number,
                    fueling,
                    door_state,
                    push_back_time
                """,
                (
                    simple_status,
                    detailed_status,
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
    # Return all events sorted by flight number for stable dashboard rendering.
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    flight_number,
                    autopilot_status,
                    cabin_pressure,
                    wifi_usage
                FROM events
                ORDER BY flight_number
            """)
            rows = cursor.fetchall()

    return rows


def get_all_monitor_data():
    # Return joined flight and event data sorted by flight number.
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    f.flight_number,
                    f.simple_status,
                    f.detailed_status,
                    f.passenger_boarding_number,
                    f.fueling,
                    f.door_state,
                    f.push_back_time,
                    e.autopilot_status,
                    e.cabin_pressure,
                    e.wifi_usage
                FROM flights f
                INNER JOIN events e
                    ON f.flight_number = e.flight_number
                ORDER BY f.flight_number
                """
            )
            rows = cursor.fetchall()

    return rows


def upsert_event(data):
    # Validate input and insert/update one event row.
    flight_number = str(data.get("Flight Number", "")).strip()
    autopilot_status = str(data.get("Autopilot Status", "")).strip().upper()

    try:
        cabin_pressure = float(data.get("Cabin Pressure"))
    except (TypeError, ValueError):
        return None, "Cabin Pressure must be a valid number"

    try:
        wifi_usage = int(data.get("WiFi Usage"))
    except (TypeError, ValueError):
        return None, "WiFi Usage must be a valid integer"

    if not flight_number:
        return None, "Flight Number is required"

    if autopilot_status not in {"ON", "OFF"}:
        return None, "Autopilot Status must be ON or OFF"

    if wifi_usage < 0:
        return None, "WiFi Usage must be zero or greater"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO events (
                    flight_number,
                    autopilot_status,
                    cabin_pressure,
                    wifi_usage
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (flight_number) DO UPDATE SET
                    autopilot_status = EXCLUDED.autopilot_status,
                    cabin_pressure = EXCLUDED.cabin_pressure,
                    wifi_usage = EXCLUDED.wifi_usage
                RETURNING
                    flight_number,
                    autopilot_status,
                    cabin_pressure,
                    wifi_usage
                """,
                (
                    flight_number,
                    autopilot_status,
                    cabin_pressure,
                    wifi_usage,
                ),
            )

            row = cursor.fetchone()
            connection.commit()

    return {
        "Flight Number": row[0],
        "Autopilot Status": row[1],
        "Cabin Pressure": float(row[2]),
        "WiFi Usage": row[3],
    }, None


@app.route("/client", methods=["GET"])
def index():
    return render_template("client_dashboard.html")


@app.route("/ground-controller", methods=["GET"])
def ground_controller():
    return render_template("ground_controller.html")


@app.route("/events-dashboard", methods=["GET"])
def events_dashboard():
    return render_template("events_dashboard.html")


@app.route("/flight", methods=["GET"])
def get_flight():
    # Read one flight using query string: /flight?flight_number=AC101
    flight_number = request.args.get("flight_number", "").strip()

    if not flight_number:
        return jsonify({"error": "flight_number is required"}), 400

    try:
        data = get_flight_by_number(flight_number)
    except Exception as exc:
        log_exception("Unable to load flight data: %s", exc)
        return jsonify({"error": "Unable to load flight data from database"}), 503

    if data is None:
        return jsonify({"error": f"No flight found for {flight_number}"}), 404

    return jsonify(data), 200

@app.route("/updateFlightInfo", methods=["PUT"])
def put_flight():
    # Accept JSON body and persist the flight update.
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        updated_data = update_flight(data)
    except Exception as exc:
        log_exception("Unable to update flight data: %s", exc)
        return jsonify({"error": "Unable to update flight data"}), 503

    if updated_data is None:
        return jsonify({"error": "No matching flight found to update"}), 404

    return jsonify(updated_data), 202
@app.route("/flight-file", methods=["GET"])
def get_flight_file():
    # Legacy/file-based fallback endpoint (separate from database endpoints).
    try:
        with open(BASE_DIR / "flight_data.json", "r") as file:
            data = json.load(file)

        return jsonify(data), 200

    except Exception as exc:
        log_exception("Unable to load flight data: %s", exc)
        return jsonify({"error": "Unable to load flight data"}), 500


@app.route("/events", methods=["GET"])
def get_events():
    # Convert raw DB rows to JSON-friendly dictionaries.
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
        log_exception("Unable to load event data: %s", exc)
        return jsonify({"error": "Unable to load event data"}), 500


@app.route("/monitor-data", methods=["GET"])
def get_monitor_data():
    # Return full joined flight and event data for monitoring clients.
    try:
        rows = get_all_monitor_data()
        monitor_data = [format_monitor_data(row) for row in rows]
        return jsonify(monitor_data), 200
    except Exception as exc:
        log_exception("Unable to load monitor data: %s", exc)
        return jsonify({"error": "Unable to load monitor data from database"}), 503


@app.route("/events-update", methods=["PUT", "POST"])
def put_event_update():
    # Update or insert event telemetry for a flight.
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        updated_event, validation_error = upsert_event(data)
    except Exception as exc:
        log_exception("Unable to update event data: %s", exc)
        return jsonify({"error": "Unable to update event data"}), 503

    if validation_error:
        return jsonify({"error": validation_error}), 400

    return jsonify(updated_event), 200


# Debug route for CSS
@app.route("/test")
def test():
    return {
        "BASE_DIR": str(BASE_DIR),
        "TEMPLATES_EXISTS": (BASE_DIR / "templates").exists(),
        "STATIC_EXISTS": (BASE_DIR / "static").exists(),
        "CSS_EXISTS": (BASE_DIR / "static" / "css" / "main.css").exists()
    }


if __name__ == "__main__":
    # One-time startup tasks before serving requests.
    initialize_database()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)