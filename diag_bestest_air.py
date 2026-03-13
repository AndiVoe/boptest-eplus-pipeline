import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from src.boptest.client import BopTestClient

def diag():
    url = "http://localhost:8000"
    client = BopTestClient(url=url)
    try:
        client.select_test_case("bestest_air")
        client.initialize(start_time=0, warmup_period=0)
        client.set_step(3600)
        print("Advancing 1 step...")
        res = client.advance({})
        print(f"Advance result keys: {list(res.keys())}")
        kpis = client.get_kpis()
        print(f"Initial KPIs: {kpis}")
        
        print("Advancing 24 steps...")
        for _ in range(24):
            client.advance({})
        kpis_final = client.get_kpis()
        print(f"Final KPIs: {kpis_final}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diag()
