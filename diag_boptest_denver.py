import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def diag():
    print("Step 1: Selecting test case...")
    try:
        r = requests.post(f"{BASE_URL}/testcases/bestest_air/select")
        r.raise_for_status()
        data = r.json()
        tid = data['testid']
        print(f"Selected TID: {tid}")
    except Exception as e:
        print(f"FAILED to select: {e}")
        return

    print("Step 2: Polling status...")
    for i in range(30):
        try:
            r = requests.get(f"{BASE_URL}/status/{tid}")
            r.raise_for_status()
            status = r.json()
            payload = status.get('payload', 'UNKNOWN')
            print(f"[{i*5}s] Status: {payload}")
            if payload == 'Running':
                print("SUCCESS! Simulation is running.")
                return
        except Exception as e:
            print(f"POLL ERROR: {e}")
        time.sleep(5)
    
    print("FAILED: Stays in Queued.")

if __name__ == "__main__":
    diag()
