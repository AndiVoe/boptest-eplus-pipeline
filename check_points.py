import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from src.boptest.client import BopTestClient

def check_points():
    client = BopTestClient(url="http://localhost:8000")
    client.select_test_case("bestest_air")
    print(f"Inputs: {list(client.get_inputs().keys())[:10]}")
    print(f"Measurements: {list(client.get_measurements().keys())[:10]}")
    print(f"Forecast Points: {list(client.get_forecast_points().keys())}")

if __name__ == "__main__":
    check_points()
