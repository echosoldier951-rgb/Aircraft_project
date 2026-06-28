# -*- coding: utf-8 -*-
"""
HTTP Client for In-Flight Events.
Retrieves in-flight event data (autopilot status, cabin pressure, Wi-Fi usage)
from the Flask server and displays it in a structured JSON/formatted response.
"""

import requests

def fetch_inflight_events():
    """
    Exposes an HTTP client connection to the server to fetch and print in-flight event data.
    """
    # The URL to the server's /events endpoint
    url = "http://127.0.0.1:5000/events"

    try:
        # Send HTTP GET request to retrieve event data
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            events_data = response.json()

            print("\n" + "=" * 65)
            print("                IN-FLIGHT EVENTS DATA (JSON SERVER)")
            print("=" * 65)
            
            # Print column headers
            print(f"{'Flight Number':<15} | {'Autopilot Status':<18} | {'Cabin Pressure (psi)':<22} | {'Wi-Fi Users':<10}")
            print("-" * 65)

            # Display each event record
            for event in events_data:
                flight_num = event.get("Flight Number", "N/A")
                autopilot = event.get("Autopilot Status", "N/A")
                cabin_press = event.get("Cabin Pressure", "N/A")
                wifi_users = event.get("WiFi Usage", "N/A")
                print(f"{flight_num:<15} | {autopilot:<18} | {cabin_press:<22} | {wifi_users:<10}")
            
            print("=" * 65 + "\n")

        else:
            print(f"Error: Server returned status code {response.status_code}")
            print(f"Server response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Please ensure the Flask server is running.")
    except Exception as exc:
        print(f"An unexpected error occurred: {exc}")

if __name__ == "__main__":
    fetch_inflight_events()
