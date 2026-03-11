import requests
import time

URL = "http://127.0.0.1:8000"

print("Step 1: Selecting test case...")
resp = requests.post(f"{URL}/testcases/bestest_air/select")
if resp.status_code != 200:
    print(f"FAILED: {resp.status_code} - {resp.text}")
    exit(1)

testid = resp.json().get('testid')
print(f"TestID: {testid}")

print("Step 2: Polling status...")
for i in range(20):
    status_resp = requests.get(f"{URL}/status/{testid}")
    status = "Unknown"
    try:
        data = status_resp.json()
        if isinstance(data, dict):
            status = data.get('payload', data.get('status', 'Unknown'))
        else:
            status = data
    except:
        status = status_resp.text.strip('"')
    
    print(f"  Attempt {i+1}: {status}")
    if status == "Running":
        print("SUCCESS!")
        break
    time.sleep(5)
else:
    print("FAILED: Timed out waiting for Running status.")
