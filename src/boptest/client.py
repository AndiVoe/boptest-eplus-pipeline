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

from typing import Optional
import time

import numpy as np
import pandas as pd
import requests


class BopTestClient:
    """Client for the BopTest REST API."""

    def __init__(self, url: str = "http://localhost:5000"):
        """
        Args:
            url: Base URL of the BopTest API (no trailing slash).
        """
        self.url = url.rstrip("/")
        self.testid = None
        self.request_retries = 3
        self.retry_backoff_s = 2.0
        self._verify_connection()

    def _request_with_retry(self, method: str, endpoint: str, timeout: int = 60, **kwargs):
        """Issue HTTP request with lightweight retry/backoff for transient failures."""
        last_exc = None
        url = f"{self.url}{endpoint}"
        for attempt in range(1, self.request_retries + 1):
            try:
                resp = requests.request(method=method, url=url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == self.request_retries:
                    break
                sleep_s = self.retry_backoff_s * attempt
                print(
                    f"[BopTestClient] {method} {endpoint} failed "
                    f"(attempt {attempt}/{self.request_retries}): {exc}. "
                    f"Retrying in {sleep_s:.1f}s"
                )
                time.sleep(sleep_s)
        raise RuntimeError(
            f"BOPTEST request failed after {self.request_retries} attempts: {method} {endpoint}"
        ) from last_exc

    def _verify_connection(self):
        """Check that the BopTest API is reachable."""
        try:
            resp = self._request_with_retry("GET", "/version", timeout=5)
            version = resp.json().get("version", "unknown")
            print(f"[BopTestClient] Connected - BopTest v{version}")
        except requests.ConnectionError:
            raise ConnectionError(
                f"Cannot reach BopTest at {self.url}. "
                "Is the Docker container running? Try: docker compose up -d"
            )

    def _check_testid(self):
        """Ensure a test case has been selected."""
        if self.testid is None:
            raise RuntimeError("No test case selected. Call select_test_case() first.")

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    def select_test_case(self, test_case: str, async_select: bool = False) -> str:
        """
        Select / load a test case by name (e.g. 'bestest_air').
        Returns the testid.
        """
        print(f"[BopTestClient] Selecting test case '{test_case}' (async={async_select}) ...")
        endpoint = f"/testcases/{test_case}/select"
        if async_select:
            endpoint += "-true"

        resp = self._request_with_retry("POST", endpoint, timeout=900)
        self.testid = resp.json().get("testid")
        print(f"[BopTestClient] Selected - TestID: {self.testid}")

        if not async_select:
            self.wait_for_status("Running")

        return self.testid

    def get_status(self) -> str:
        """Check the status of the current test."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/status/{self.testid}", timeout=60)
        try:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("payload", data.get("status", "Unknown"))
            return data
        except Exception:
            return resp.text.strip('"')

    def wait_for_status(self, desired_status: str, timeout: int = 300):
        """Wait for the test to reach a certain status."""
        print(f"[BopTestClient] Waiting for status '{desired_status}' ...")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            status = self.get_status()
            print(f"[BopTestClient] Current status: '{status}' (Waiting for '{desired_status}')")
            if status == desired_status:
                print(f"[BopTestClient] Status reached: {status}")
                return
            time.sleep(5)
        raise TimeoutError(f"Timed out waiting for status '{desired_status}'")

    def get_test_case_name(self) -> str:
        """Return the name of the currently loaded test case."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/name/{self.testid}", timeout=60)
        return resp.json().get("payload", {}).get("name", "unknown")

    def initialize(self, start_time: float = 0, warmup_period: float = 0) -> dict:
        """Initialize (reset) the simulation."""
        self._check_testid()
        resp = self._request_with_retry(
            "PUT",
            f"/initialize/{self.testid}",
            json={"start_time": start_time, "warmup_period": warmup_period},
            timeout=3600,
        )
        return resp.json()

    def get_step(self) -> float:
        """Return current simulation step size in seconds."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/step/{self.testid}", timeout=60)
        return resp.json().get("payload", 60)

    def set_step(self, step: float) -> dict:
        """Set the simulation step size in seconds."""
        self._check_testid()
        resp = self._request_with_retry("PUT", f"/step/{self.testid}", json={"step": step}, timeout=60)
        return resp.json()

    def set_scenario(self, scenario: str) -> dict:
        """
        Set the simulation scenario (time period).
        Args:
            scenario: Name of the scenario (e.g. 'typical_heat_day').
        """
        self._check_testid()
        data = {
            "time_period": scenario,
            "electricity_price": "constant",
            "temperature_uncertainty": None,
            "solar_uncertainty": None,
            "seed": None,
        }
        resp = self._request_with_retry("PUT", f"/scenario/{self.testid}", json=data, timeout=300)
        return resp.json().get("payload", {})

    def advance(self, control_inputs: Optional[dict] = None) -> dict:
        """Advance the simulation by one step."""
        self._check_testid()
        if control_inputs is None:
            control_inputs = {}
        resp = self._request_with_retry("POST", f"/advance/{self.testid}", json=control_inputs, timeout=3600)
        return resp.json().get("payload", {})

    def get_results(self, point_names: list, start_time: float, final_time: float) -> pd.DataFrame:
        """Retrieve time-series results for specific points."""
        self._check_testid()
        resp = self._request_with_retry(
            "PUT",
            f"/results/{self.testid}",
            json={
                "point_names": point_names,
                "start_time": start_time,
                "final_time": final_time,
            },
            timeout=3600,
        )
        payload = resp.json().get("payload", {})
        return pd.DataFrame(payload)

    def get_kpis(self) -> pd.DataFrame:
        """Retrieve BopTest KPIs."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/kpi/{self.testid}", timeout=300)
        raw = resp.json().get("payload", {})
        clean = {k: (v if v is not None else np.nan) for k, v in raw.items()}
        return pd.DataFrame([clean])

    def get_inputs(self) -> dict:
        """Return available control input points."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/inputs/{self.testid}", timeout=60)
        return resp.json().get("payload", {})

    def get_measurements(self) -> dict:
        """Return available measurement output points."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/measurements/{self.testid}", timeout=60)
        return resp.json().get("payload", {})

    def get_forecast_points(self) -> dict:
        """Return available forecast points."""
        self._check_testid()
        resp = self._request_with_retry("GET", f"/forecast_points/{self.testid}", timeout=60)
        return resp.json().get("payload", {})

    def get_forecast(self, point_names: list, horizon: float, interval: float) -> pd.DataFrame:
        """
        Retrieve forecast data for specific points over a future horizon.
        Args:
            point_names: List of forecast point names (e.g. ['TDryBul', 'HGloHor']).
            horizon: Forecast horizon in seconds.
            interval: Data interval in seconds.
        """
        self._check_testid()
        resp = self._request_with_retry(
            "PUT",
            f"/forecast/{self.testid}",
            json={"point_names": point_names, "horizon": horizon, "interval": interval},
            timeout=300,
        )
        payload = resp.json().get("payload", {})
        return pd.DataFrame(payload)
