import os
import time

import requests


SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://127.0.0.1:5000")
MONITOR_DATA_URL = f"{SERVER_BASE_URL}/monitor-data"
POLL_INTERVAL_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 8


def fetch_monitor_data():
    response = requests.get(MONITOR_DATA_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Monitor data response must be a JSON array")

    return data


def main():
    while True:
        try:
            fetch_monitor_data()
        except KeyboardInterrupt:
            raise
        except requests.RequestException as exc:
            print(f"Monitor request failed: {exc}")
        except ValueError as exc:
            print(f"Monitor response failed validation: {exc}")
        except Exception as exc:
            print(f"Monitor failed unexpectedly: {exc}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Monitor stopped.")