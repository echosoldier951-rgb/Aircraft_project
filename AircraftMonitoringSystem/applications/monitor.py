import json
import os
import time
from pathlib import Path

import requests


# Base API URL (can be overridden by environment variable).
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://127.0.0.1:5000")
# Endpoint used by this script to read the latest joined monitoring data.
MONITOR_DATA_URL = f"{SERVER_BASE_URL}/monitor-data"
# Shared rule/config file used to validate incoming values.
PARAMETERS_FILE = Path(__file__).resolve().parents[1] / "parameters.json"
# How often to run one monitor cycle.
POLL_INTERVAL_SECONDS = 1
# Maximum wait time for API requests.
REQUEST_TIMEOUT_SECONDS = 8
LOG_PREFIX = "[Monitor]"


def log_message(message):
    # Add a timestamp so logs are easier to read and debug.
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} {LOG_PREFIX} {message}")


def log_exception(message):
    # Keep exception-style logs consistent.
    log_message(f"EXCEPTION {message}")


def fetch_monitor_data():
    # Read current flight rows from the API.
    log_message(f"Calling API {MONITOR_DATA_URL}")
    response = requests.get(MONITOR_DATA_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Monitor data response must be a JSON array")

    return data


def load_parameters():
    # Load threshold and expected-value rules from parameters.json.
    with PARAMETERS_FILE.open("r", encoding="utf-8") as parameters_file:
        return json.load(parameters_file)


def normalize_autopilot_status(value, normalization):
    # Normalize different text forms like "on", "ON", "enabled" to one standard value.
    normalized_value = str(value).strip().upper()
    on_values = {str(item).strip().upper() for item in normalization.get("on_values", [])}
    off_values = {str(item).strip().upper() for item in normalization.get("off_values", [])}

    if normalized_value in on_values:
        return "ON"

    if normalized_value in off_values:
        return "OFF"

    return normalized_value


def evaluate_cabin_pressure(flight_data, parameters):
    # Check if cabin pressure is missing or outside the allowed range.
    cabin_pressure = flight_data.get("Cabin Pressure")
    expected_range = parameters["Cabin Pressure"]["expected_range"]
    minimum = expected_range["min"]
    maximum = expected_range["max"]

    if cabin_pressure is None:
        return [
            f"Flight {flight_data.get('Flight Number', 'UNKNOWN')}: Cabin Pressure current=None expected min={minimum} max={maximum}"
        ]

    if cabin_pressure < minimum or cabin_pressure > maximum:
        return [
            f"Flight {flight_data.get('Flight Number', 'UNKNOWN')}: Cabin Pressure current={cabin_pressure} expected min={minimum} max={maximum}"
        ]

    return []


def evaluate_autopilot_status(flight_data, parameters):
    # Check if autopilot state matches what is expected for the flight phase.
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
        return [
            f"Flight {flight_data.get('Flight Number', 'UNKNOWN')}: Autopilot Status current={autopilot_status} expected={expected_status} for status={simple_status}"
        ]

    return []


def evaluate_wifi_usage(flight_data, parameters):
    # Check WiFi usage rule for the current flight status.
    simple_status = flight_data.get("Simple Status")
    wifi_usage = flight_data.get("WiFi Usage")
    expected_condition = parameters["WiFi Usage"]["expected_by_flight_status"].get(simple_status)

    if expected_condition is None:
        return []

    if expected_condition == "greater than 0" and wifi_usage <= 0:
        return [
            f"Flight {flight_data.get('Flight Number', 'UNKNOWN')}: WiFi Usage current={wifi_usage} expected min=1 for status={simple_status}"
        ]

    if expected_condition == "equal to 0" and wifi_usage != 0:
        return [
            f"Flight {flight_data.get('Flight Number', 'UNKNOWN')}: WiFi Usage current={wifi_usage} expected max=0 for status={simple_status}"
        ]

    return []


def evaluate_flight(flight_data, parameters):
    # Run all checks and collect every alert for a single flight.
    alerts = []
    alerts.extend(evaluate_cabin_pressure(flight_data, parameters))
    alerts.extend(evaluate_autopilot_status(flight_data, parameters))
    alerts.extend(evaluate_wifi_usage(flight_data, parameters))
    return alerts


def monitor_flights():
    # One full monitor cycle: load rules, fetch data, print any alerts.
    parameters = load_parameters()
    monitor_data = fetch_monitor_data()

    for flight_data in monitor_data:
        for alert_message in evaluate_flight(flight_data, parameters):
            log_exception(alert_message)


def main():
    # Keep monitoring forever until user stops the script.
    while True:
        try:
            monitor_flights()
        except KeyboardInterrupt:
            raise
        except Exception:
            # Continue running even if one cycle fails.
            pass

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass