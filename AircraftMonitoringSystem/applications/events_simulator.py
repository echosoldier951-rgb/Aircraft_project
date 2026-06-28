import os
import json
import random
import time
from pathlib import Path

import requests

SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://127.0.0.1:5000")
MONITOR_DATA_URL = f"{SERVER_BASE_URL}/monitor-data"
EVENTS_UPDATE_URL = f"{SERVER_BASE_URL}/events-update"
PARAMETERS_FILE = Path(__file__).resolve().parents[1] / "parameters.json"
NORMAL_UPDATE_SECONDS = 5
DRIFT_INTERVAL_SECONDS = 10
DRIFT_DURATION_SECONDS = 10
LOOP_SLEEP_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 8


def load_parameters():
    with open(PARAMETERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def fetch_monitor_data():
    """Pull full joined monitoring rows so updates can respect flight status."""
    response = requests.get(MONITOR_DATA_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Monitor data response must be a JSON array")

    return data


def build_cabin_pressure(parameters):
    expected_range = parameters["Cabin Pressure"]["expected_range"]
    minimum = float(expected_range["min"])
    maximum = float(expected_range["max"])
    lower_bound = minimum + 0.1
    upper_bound = maximum - 0.1

    if lower_bound >= upper_bound:
        return round((minimum + maximum) / 2, 2)

    return round(random.uniform(lower_bound, upper_bound), 2)


def build_wifi_usage(simple_status, parameters):
    expected_by_status = parameters["WiFi Usage"]["expected_by_flight_status"]
    expected_rule = expected_by_status.get(simple_status)

    if expected_rule == "greater than 0":
        return random.randint(50, 220)

    if expected_rule == "equal to 0":
        return 0

    return random.randint(0, 220)


def build_compliant_payload(flight_data, parameters):
    simple_status = flight_data["Simple Status"]
    autopilot_expected = parameters["Autopilot Status"]["expected_by_flight_status"]


    return {
        "Flight Number": flight_data["Flight Number"],
        "Autopilot Status": autopilot_expected.get(simple_status, "OFF"),
        "Cabin Pressure": build_cabin_pressure(parameters),
        "WiFi Usage": build_wifi_usage(simple_status, parameters),
    }


def get_drift_candidates(flight_data, parameters):
    simple_status = flight_data["Simple Status"]
    candidates = ["Cabin Pressure"]

    autopilot_expected = parameters["Autopilot Status"]["expected_by_flight_status"]
    if simple_status in autopilot_expected:
        candidates.append("Autopilot Status")

    wifi_expected = parameters["WiFi Usage"]["expected_by_flight_status"]
    if simple_status in wifi_expected:
        candidates.append("WiFi Usage")

    return candidates


def build_out_of_spec_payload(flight_data, parameters):
    payload = build_compliant_payload(flight_data, parameters)
    simple_status = flight_data["Simple Status"]
    drift_field = random.choice(get_drift_candidates(flight_data, parameters))

    if drift_field == "Cabin Pressure":
        expected_range = parameters["Cabin Pressure"]["expected_range"]
        minimum = float(expected_range["min"])
        maximum = float(expected_range["max"])
        if random.choice([True, False]):
            payload["Cabin Pressure"] = round(minimum - random.uniform(0.3, 1.5), 2)
        else:
            payload["Cabin Pressure"] = round(maximum + random.uniform(0.3, 1.5), 2)
    elif drift_field == "Autopilot Status":
        autopilot_expected = parameters["Autopilot Status"]["expected_by_flight_status"]
        expected_value = autopilot_expected.get(simple_status, "OFF")
        payload["Autopilot Status"] = "OFF" if expected_value == "ON" else "ON"
    elif drift_field == "WiFi Usage":
        wifi_expected = parameters["WiFi Usage"]["expected_by_flight_status"]
        expected_rule = wifi_expected.get(simple_status)
        if expected_rule == "greater than 0":
            payload["WiFi Usage"] = 0
        elif expected_rule == "equal to 0":
            payload["WiFi Usage"] = random.randint(1, 220)

    return payload, drift_field


def select_flight(flights, excluded_flight_number=None):
    eligible_flights = [
        flight for flight in flights
        if flight.get("Flight Number") and flight.get("Flight Number") != excluded_flight_number
    ]

    if not eligible_flights:
        return None

    return random.choice(eligible_flights)


def find_flight(flights, flight_number):
    for flight in flights:
        if flight.get("Flight Number") == flight_number:
            return flight

    return None


def simulate_event_payload(flight_number):
    raise NotImplementedError("Use build_compliant_payload with full flight data instead")


def push_event_update(payload):
    # Send telemetry update to the API (upsert endpoint).
    response = requests.put(
        EVENTS_UPDATE_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def main():
    parameters = load_parameters()
    last_normal_update_at = 0.0
    last_drift_change_at = time.monotonic()
    active_drift = None

    print(
        "Simulator started. "
        f"Sending aligned updates to {EVENTS_UPDATE_URL}; "
        f"temporary drift begins every {DRIFT_INTERVAL_SECONDS}s"
    )

    while True:
        try:
            flights = fetch_monitor_data()

            if not flights:
                print("No flights available in monitor data. Retrying...")
                time.sleep(LOOP_SLEEP_SECONDS)
                continue

            now = time.monotonic()

            if active_drift and now - active_drift["started_at"] >= DRIFT_DURATION_SECONDS:
                drift_flight = find_flight(flights, active_drift["flight_number"])
                if drift_flight:
                    restored_payload = build_compliant_payload(drift_flight, parameters)
                    restored = push_event_update(restored_payload)
                    print(
                        "Restored",
                        restored["Flight Number"],
                        f"Field={active_drift['field']}",
                    )
                active_drift = None
                last_drift_change_at = now

            if not active_drift and now - last_drift_change_at >= DRIFT_INTERVAL_SECONDS:
                drift_flight = select_flight(flights)
                if drift_flight:
                    drift_payload, drift_field = build_out_of_spec_payload(drift_flight, parameters)
                    drifted = push_event_update(drift_payload)
                    active_drift = {
                        "flight_number": drifted["Flight Number"],
                        "field": drift_field,
                        "started_at": now,
                    }
                    print(
                        "Drifted",
                        drifted["Flight Number"],
                        f"Field={drift_field}",
                    )

            if now - last_normal_update_at >= NORMAL_UPDATE_SECONDS:
                excluded_flight_number = None
                if active_drift is not None:
                    excluded_flight_number = active_drift["flight_number"]

                selected_flight = select_flight(flights, excluded_flight_number=excluded_flight_number)
                if selected_flight:
                    payload = build_compliant_payload(selected_flight, parameters)
                    updated = push_event_update(payload)

                    print(
                        "Updated",
                        updated["Flight Number"],
                        f"Autopilot={updated['Autopilot Status']}",
                        f"CabinPressure={updated['Cabin Pressure']}",
                        f"WiFiUsage={updated['WiFi Usage']}",
                    )

                last_normal_update_at = now
        except requests.RequestException as exc:
            print(f"Network/API error: {exc}. Retrying...")
        except ValueError as exc:
            print(f"Simulator configuration error: {exc}. Retrying...")
        except Exception as exc:
            print(f"Unexpected simulator error: {exc}. Retrying...")

        time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    main()
