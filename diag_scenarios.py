from boptest.lib.testcase import TestCase
import json

fmu_path = "/worker/jobs/models/bestest_air.fmu"
forecast_path = "/worker/jobs/forecast/forecast_uncertainty_params.json"

tc = TestCase(fmupath=fmu_path, forecast_uncertainty_params_path=forecast_path)
print("--- SCENARIO LIST ---")
# Try to find scenario info
try:
    print(f"Scenario Info: {tc.get_scenario()}")
except:
    print("Could not get scenario info")

try:
    import pandas as pd
    # Check forecast names
    print(f"Forecast Names: {tc.get_forecast_points()}")
except:
    pass

# Try to set typical_cool_day with various settings
settings = [
    {'time_period': 'typical_cool_day'},
    {'time_period': 'typical_cool_day', 'temperature_uncertainty': 'low', 'solar_uncertainty': 'low', 'electricity_price': 'constant'},
    {'time_period': 'typical_cool_day', 'temperature_uncertainty': None, 'solar_uncertainty': None, 'electricity_price': 'constant'}
]

for s in settings:
    print(f"\nTesting config: {s}")
    try:
        res = tc.set_scenario(s)
        print(f"Success! Result keys: {res[2].keys() if res[0]==200 else res}")
    except Exception as e:
        print(f"Failed: {e}")
