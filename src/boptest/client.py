"""
BopTest API Client
==================
Thin wrapper around the BopTest REST API for interacting with building
simulation test cases.

Usage:
    client = BopTestClient(url="http://localhost:5000")
    client.select_test_case("bestest_air")
    client.initialize(start_time=0, warmup_period=0)
    result = client.advance({"oveAct_u": 293.15, "oveAct_activate": 1})
    kpis = client.get_kpis()
"""

import requests
import pandas as pd
import numpy as np
from typing import Optional


class BopTestClient:
    """Client for the BopTest REST API."""

    def __init__(self, url: str = "http://localhost:5000"):
        """
        Args:
            url: Base URL of the BopTest API (no trailing slash).
        """
        self.url = url.rstrip("/")
        self.testid = None
        self._verify_connection()

    def _verify_connection(self):
        """Check that the BopTest API is reachable."""
        try:
            resp = requests.get(f"{self.url}/version", timeout=5)
            resp.raise_for_status()
            version = resp.json().get("version", "unknown")
            print(f"[BopTestClient] Connected — BopTest v{version}")
        except requests.ConnectionError:
            raise ConnectionError(
                f"Cannot reach BopTest at {self.url}. "
                "Is the Docker container running? Try: docker compose up -d"
            )

    def _check_testid(self):
        """Ensure a test case has been selected."""
        if self.testid is None:
            raise RuntimeError(
                "No test case selected. Call select_test_case() first."
            )

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    def select_test_case(self, test_case: str, async_select: bool = False) -> str:
        """
        Select / load a test case by name (e.g. 'bestest_air').
        Returns the testid.
        """
        print(f"[BopTestClient] Selecting test case '{test_case}' (async={async_select}) ...")
        url = f"{self.url}/testcases/{test_case}/select"
        if async_select:
            url += "-true"
        
        resp = requests.post(url, timeout=900)
        resp.raise_for_status()
        self.testid = resp.json().get("testid")
        print(f"[BopTestClient] Selected — TestID: {self.testid}")
        
        if not async_select:
            self.wait_for_status("Running")
            
        return self.testid

    def get_status(self) -> str:
        """Check the status of the current test."""
        self._check_testid()
        resp = requests.get(f"{self.url}/status/{self.testid}", timeout=60)
        resp.raise_for_status()
        # The API returns the status as a quoted string in a JSON response
        # or sometimes just a string. requests.json() might fail if it's just "Running".
        try:
            return resp.json()
        except:
            return resp.text.strip('"')

    def wait_for_status(self, desired_status: str, timeout: int = 300):
        """Wait for the test to reach a certain status."""
        import time
        print(f"[BopTestClient] Waiting for status '{desired_status}' ...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if status == desired_status:
                print(f"[BopTestClient] Status reached: {status}")
                return
            time.sleep(2)
        raise TimeoutError(f"Timed out waiting for status '{desired_status}'")

    def get_test_case_name(self) -> str:
        """Return the name of the currently loaded test case."""
        self._check_testid()
        resp = requests.get(f"{self.url}/name/{self.testid}", timeout=60)
        resp.raise_for_status()
        return resp.json().get("payload", {}).get("name", "unknown")

    def initialize(
        self,
        start_time: float = 0,
        warmup_period: float = 0,
    ) -> dict:
        """Initialize (reset) the simulation."""
        self._check_testid()
        resp = requests.put(
            f"{self.url}/initialize/{self.testid}",
            json={
                "start_time": start_time,
                "warmup_period": warmup_period,
            },
            timeout=3600,
        )
        resp.raise_for_status()
        return resp.json()

    def get_step(self) -> float:
        """Return current simulation step size in seconds."""
        self._check_testid()
        resp = requests.get(f"{self.url}/step/{self.testid}", timeout=60)
        resp.raise_for_status()
        return resp.json().get("payload", 60)

    def set_step(self, step: float) -> dict:
        """Set the simulation step size in seconds."""
        self._check_testid()
        resp = requests.put(
            f"{self.url}/step/{self.testid}", json={"step": step}, timeout=60
        )
        resp.raise_for_status()
        return resp.json()

    def advance(self, control_inputs: Optional[dict] = None) -> dict:
        """Advance the simulation by one step."""
        self._check_testid()
        if control_inputs is None:
            control_inputs = {}
        resp = requests.post(
            f"{self.url}/advance/{self.testid}",
            json=control_inputs,
            timeout=3600,
        )
        resp.raise_for_status()
        return resp.json().get("payload", {})

    def get_results(
        self,
        point_names: list,
        start_time: float,
        final_time: float,
    ) -> pd.DataFrame:
        """Retrieve time-series results for specific points."""
        self._check_testid()
        resp = requests.put(
            f"{self.url}/results/{self.testid}",
            json={
                "point_names": point_names,
                "start_time": start_time,
                "final_time": final_time,
            },
            timeout=3600,
        )
        resp.raise_for_status()
        payload = resp.json().get("payload", {})
        return pd.DataFrame(payload)

    def get_kpis(self) -> pd.DataFrame:
        """Retrieve BopTest KPIs."""
        self._check_testid()
        resp = requests.get(f"{self.url}/kpi/{self.testid}", timeout=300)
        resp.raise_for_status()
        raw = resp.json().get("payload", {})
        # Replace None with NaN for clean downstream processing
        clean = {k: (v if v is not None else np.nan) for k, v in raw.items()}
        return pd.DataFrame([clean])

    def get_inputs(self) -> dict:
        """Return available control input points."""
        self._check_testid()
        resp = requests.get(f"{self.url}/inputs/{self.testid}", timeout=60)
        resp.raise_for_status()
        return resp.json().get("payload", {})

    def get_measurements(self) -> dict:
        """Return available measurement output points."""
        self._check_testid()
        resp = requests.get(f"{self.url}/measurements/{self.testid}", timeout=60)
        resp.raise_for_status()
        return resp.json().get("payload", {})

    def get_forecast_points(self) -> dict:
        """Return available forecast points."""
        self._check_testid()
        resp = requests.get(f"{self.url}/forecast_points/{self.testid}", timeout=60)
        resp.raise_for_status()
        return resp.json().get("payload", {})
