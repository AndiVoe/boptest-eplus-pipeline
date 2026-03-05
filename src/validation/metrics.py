"""
Validation Metrics — Micro-Step 5 Support
==========================================
ASHRAE Guideline 14 metrics for comparing simulated vs. measured data.

Functions:
  - cvrmse: Coefficient of Variation of Root Mean Square Error
  - nmbe: Normalized Mean Bias Error
  - validation_summary: Computes both and returns a pass/fail verdict
"""

import numpy as np
import pandas as pd


def cvrmse(measured: np.ndarray, simulated: np.ndarray) -> float:
    """
    Coefficient of Variation of Root Mean Square Error (CV(RMSE)).

    ASHRAE Guideline 14 threshold for hourly data: CV(RMSE) < 30%.

    Args:
        measured: Array of measured/reference values.
        simulated: Array of simulated values (same length).
    Returns:
        CV(RMSE) as a percentage (e.g., 15.2 means 15.2%).
    """
    measured = np.asarray(measured, dtype=float)
    simulated = np.asarray(simulated, dtype=float)

    n = len(measured)
    mean_measured = np.mean(measured)

    if mean_measured == 0:
        return float("inf")

    rmse = np.sqrt(np.sum((simulated - measured) ** 2) / n)
    return 100.0 * rmse / mean_measured


def nmbe(measured: np.ndarray, simulated: np.ndarray) -> float:
    """
    Normalized Mean Bias Error (NMBE).

    ASHRAE Guideline 14 threshold for hourly data: |NMBE| < 10%.

    Args:
        measured: Array of measured/reference values.
        simulated: Array of simulated values (same length).
    Returns:
        NMBE as a percentage (e.g., -3.5 means -3.5% bias).
    """
    measured = np.asarray(measured, dtype=float)
    simulated = np.asarray(simulated, dtype=float)

    n = len(measured)
    mean_measured = np.mean(measured)

    if mean_measured == 0:
        return float("inf")

    return 100.0 * np.sum(simulated - measured) / (n * mean_measured)


def validation_summary(
    measured: np.ndarray,
    simulated: np.ndarray,
    cvrmse_threshold: float = 30.0,
    nmbe_threshold: float = 10.0,
) -> dict:
    """
    Compute ASHRAE Guideline 14 metrics and return a verdict.

    Args:
        measured: Reference time series.
        simulated: Model output time series.
        cvrmse_threshold: Max CV(RMSE) in % (default 30% for hourly).
        nmbe_threshold: Max |NMBE| in % (default 10% for hourly).
    Returns:
        Dict with keys: cvrmse, nmbe, cvrmse_pass, nmbe_pass, overall_pass.
    """
    cv = cvrmse(measured, simulated)
    nb = nmbe(measured, simulated)

    cv_ok = cv < cvrmse_threshold
    nb_ok = abs(nb) < nmbe_threshold

    return {
        "cvrmse_pct": round(cv, 2),
        "nmbe_pct": round(nb, 2),
        "cvrmse_threshold": cvrmse_threshold,
        "nmbe_threshold": nmbe_threshold,
        "cvrmse_pass": cv_ok,
        "nmbe_pass": nb_ok,
        "overall_pass": cv_ok and nb_ok,
    }
