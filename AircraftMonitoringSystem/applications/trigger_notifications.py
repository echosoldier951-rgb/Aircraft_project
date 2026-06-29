import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://127.0.0.1:5000")
MONITOR_DATA_URL = f"{SERVER_BASE_URL}/monitor-data"
PARAMETERS_FILE = Path(__file__).resolve().parents[1] / "parameters.json"
NOTIFICATION_LOG_FILE = Path(__file__).resolve().parents[1] / "TriggerNotifications.txt"
POLL_INTERVAL_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 8
LOG_PREFIX = "[Trigger]"


active_incidents = {}


def now_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_message(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"{timestamp} {LOG_PREFIX} {message}"
    print(full_message)
    with NOTIFICATION_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")


def load_parameters():
    with PARAMETERS_FILE.open("r", encoding="utf-8") as parameters_file:
        return json.load(parameters_file)


def fetch_monitor_data():
    response = requests.get(MONITOR_DATA_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Monitor data response must be a JSON array")

    return data


def normalize_autopilot_status(value, normalization):
    normalized_value = str(value).strip().upper()
    on_values = {str(item).strip().upper() for item in normalization.get("on_values", [])}
    off_values = {str(item).strip().upper() for item in normalization.get("off_values", [])}

    if normalized_value in on_values:
        return "ON"

    if normalized_value in off_values:
        return "OFF"

    return normalized_value


def evaluate_cabin_pressure(flight_data, parameters):
    cabin_pressure = flight_data.get("Cabin Pressure")
    expected_range = parameters["Cabin Pressure"]["expected_range"]
    minimum = expected_range["min"]
    maximum = expected_range["max"]
    flight_number = flight_data.get("Flight Number", "UNKNOWN")

    if cabin_pressure is None:
        return [
            {
                "flight_number": flight_number,
                "error_type": "Cabin Pressure",
                "message": f"Flight {flight_number}: Cabin Pressure current=None expected min={minimum} max={maximum}",
                "simple_status": flight_data.get("Simple Status"),
            }
        ]

    if cabin_pressure < minimum or cabin_pressure > maximum:
        return [
            {
                "flight_number": flight_number,
                "error_type": "Cabin Pressure",
                "message": f"Flight {flight_number}: Cabin Pressure current={cabin_pressure} expected min={minimum} max={maximum}",
                "simple_status": flight_data.get("Simple Status"),
            }
        ]

    return []


def evaluate_autopilot_status(flight_data, parameters):
    simple_status = flight_data.get("Simple Status")
    autopilot_status = flight_data.get("Autopilot Status")
    autopilot_rules = parameters["Autopilot Status"]
    expected_by_status = autopilot_rules["expected_by_flight_status"]
    expected_status = expected_by_status.get(simple_status)

    if expected_status is None:
        return []

    normalized_status = normalize_autopilot_status(
        autopilot_status,
        autopilot_rules.get("normalization", {}),
    )

    if normalized_status != expected_status:
        flight_number = flight_data.get("Flight Number", "UNKNOWN")
        return [
            {
                "flight_number": flight_number,
                "error_type": "Autopilot Status",
                "message": f"Flight {flight_number}: Autopilot Status current={autopilot_status} expected={expected_status} for status={simple_status}",
                "simple_status": simple_status,
            }
        ]

    return []


def evaluate_wifi_usage(flight_data, parameters):
    simple_status = flight_data.get("Simple Status")
    wifi_usage = flight_data.get("WiFi Usage")
    expected_condition = parameters["WiFi Usage"]["expected_by_flight_status"].get(simple_status)

    if expected_condition is None:
        return []

    flight_number = flight_data.get("Flight Number", "UNKNOWN")

    if expected_condition == "greater than 0" and wifi_usage <= 0:
        return [
            {
                "flight_number": flight_number,
                "error_type": "WiFi Usage",
                "message": f"Flight {flight_number}: WiFi Usage current={wifi_usage} expected min=1 for status={simple_status}",
                "simple_status": simple_status,
            }
        ]

    if expected_condition == "equal to 0" and wifi_usage != 0:
        return [
            {
                "flight_number": flight_number,
                "error_type": "WiFi Usage",
                "message": f"Flight {flight_number}: WiFi Usage current={wifi_usage} expected max=0 for status={simple_status}",
                "simple_status": simple_status,
            }
        ]

    return []


def evaluate_flight(flight_data, parameters):
    alerts = []
    alerts.extend(evaluate_cabin_pressure(flight_data, parameters))
    alerts.extend(evaluate_autopilot_status(flight_data, parameters))
    alerts.extend(evaluate_wifi_usage(flight_data, parameters))
    return alerts


def build_dedup_key(alert):
    return f"{alert['flight_number']}|{alert['error_type']}"


def build_notification_payload(new_alert, active_for_flight):
    return {
        "timestamp": now_timestamp(),
        "flight_number": new_alert["flight_number"],
        "simple_status": new_alert.get("simple_status"),
        "new_error_type": new_alert["error_type"],
        "new_error_message": new_alert["message"],
        "active_errors_for_flight": [
            {
                "error_type": incident["error_type"],
                "message": incident["message"],
                "first_detected": incident["first_detected"],
            }
            for incident in active_for_flight
        ],
    }


def process_cycle(parameters):
    monitor_data = fetch_monitor_data()
    current_alerts_by_key = {}

    for flight_data in monitor_data:
        for alert in evaluate_flight(flight_data, parameters):
            key = build_dedup_key(alert)
            if key not in current_alerts_by_key:
                current_alerts_by_key[key] = alert

    current_keys = set(current_alerts_by_key.keys())
    existing_keys = set(active_incidents.keys())

    resolved_keys = existing_keys - current_keys
    for key in resolved_keys:
        del active_incidents[key]

    new_keys = sorted(current_keys - existing_keys)

    for key in new_keys:
        alert = current_alerts_by_key[key]
        flight_number = alert["flight_number"]

        already_active_for_flight = [
            incident
            for incident in active_incidents.values()
            if incident["flight_number"] == flight_number
        ]

        first_detected = now_timestamp()
        new_incident = {
            "flight_number": flight_number,
            "error_type": alert["error_type"],
            "message": alert["message"],
            "simple_status": alert.get("simple_status"),
            "first_detected": first_detected,
            "last_seen": first_detected,
        }

        payload = build_notification_payload(
            alert,
            already_active_for_flight + [new_incident],
        )
        log_message(f"NOTIFICATION {json.dumps(payload, ensure_ascii=True)}")

        active_incidents[key] = new_incident

    cycle_seen_timestamp = now_timestamp()
    for key in current_keys:
        incident = active_incidents.get(key)
        if incident:
            incident["last_seen"] = cycle_seen_timestamp



def main():
    parameters = load_parameters()
    log_message(f"Trigger app started; polling {MONITOR_DATA_URL}")

    while True:
        try:
            process_cycle(parameters)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log_message(f"EXCEPTION Trigger cycle failed: {exc}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
