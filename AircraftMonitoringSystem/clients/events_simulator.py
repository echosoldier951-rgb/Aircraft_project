import os
import random
import time
import requests

SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://127.0.0.1:5000")
EVENTS_URL = f"{SERVER_BASE_URL}/events"
EVENTS_UPDATE_URL = f"{SERVER_BASE_URL}/events-update"
SLEEP_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 8


def fetch_flight_numbers():
    """Pull flight identifiers from current events so updates target known rows."""
    # Read current flights from the server to avoid sending unknown IDs.
    response = requests.get(EVENTS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    events = response.json()
    return [event.get("Flight Number") for event in events if event.get("Flight Number")]


def simulate_event_payload(flight_number):
    # Generate realistic random telemetry for one flight.
    autopilot_status = random.choice(["ON", "OFF"])
    cabin_pressure = round(random.uniform(9.5, 10.8), 2)
    wifi_usage = random.randint(20, 220)

    return {
        "Flight Number": flight_number,
        "Autopilot Status": autopilot_status,
        "Cabin Pressure": cabin_pressure,
        "WiFi Usage": wifi_usage,
    }


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
    # Infinite loop: fetch flights, choose one, post new random telemetry.
    print(f"Simulator started. Sending updates to {EVENTS_UPDATE_URL} every {SLEEP_SECONDS}s")

    while True:
        try:
            flight_numbers = fetch_flight_numbers()

            if not flight_numbers:
                # Nothing to update yet; wait and retry.
                print("No flights available in events. Retrying...")
                time.sleep(SLEEP_SECONDS)
                continue

            selected_flight = random.choice(flight_numbers)
            payload = simulate_event_payload(selected_flight)
            updated = push_event_update(payload)

            print(
                "Updated",
                updated["Flight Number"],
                f"Autopilot={updated['Autopilot Status']}",
                f"CabinPressure={updated['Cabin Pressure']}",
                f"WiFiUsage={updated['WiFi Usage']}",
            )
        except requests.RequestException as exc:
            print(f"Network/API error: {exc}. Retrying...")
        except Exception as exc:
            print(f"Unexpected simulator error: {exc}. Retrying...")

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
