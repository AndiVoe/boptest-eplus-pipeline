# BESTEST-Equivalent Model Validation Report

## EnergyPlus Naive Model Quality

| Metric | Value |
|--------|-------|
| Simulation period | Jan 1 - Mar 1, 2024 |
| Total timesteps | 8640 |
| Temperature range | 15.0C - 22.4C |
| Temperature std dev | 2.94C |
| Unique temp values | 919 |
| Total heating | 8.402 GJ |
| Total cooling | 0.000 GJ |

**Assessment**: The model shows REALISTIC dynamic behavior with 919 unique temperature values.

## BopTest Reference Data

| Metric | Value |
|--------|-------|
| Data points | 4 |
| Time span | 2024-01-01 00:15:00 - 2024-01-01 01:00:00 |
| Temperature mean | 20.01C |

## ASHRAE Guideline 14 Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| CVRMSE | 25.0% | <=30% | PASS |
| NMBE | -25.0% | +/-10% | FAIL |
| Overlap points | 2 | - | INSUFFICIENT |

## Overall: FAIL
