import requests

try:
    response = requests.get("http://127.0.0.1:5000/flight-file")

    if response.status_code == 200:
        data = response.json()

        print("\nPre-Departure Aircraft Data")
        print("-" * 30)

        for key, value in data.items():
            print(f"{key}: {value}")

    else:
        print(f"Error: Server returned status code {response.status_code}")

except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the server.")

except Exception as e:
    print(f"Unexpected error: {e}")