# boptest-eplus-pipeline

Automated pipeline for creating, simulating, and validating EnergyPlus building energy models against [BopTest](https://github.com/ibpsa/project1-boptest) baselines.

Part of a PhD project on automated building energy model creation & calibration.

## Overview

```
Archetype IDF ──► parse_archetype.py ──► archetype_params.json
                                              │
                                              ▼
                                      generate_model.py ──► naive_baseline.idf
                                                                   │
                                                                   ▼
                                              EnergyPlus (Docker) ──► eplusout.csv
                                                                         │
BopTest (Docker) ──► extract_baseline_kpis.py ──► baseline_kpis.csv      │
                         │                                               │
                         ▼                                               ▼
                  boptest_baseline_*.csv ──────────► validate_model.py ──► report + plots
```

## Project Structure

```
src/
├── archetype/
│   ├── parse_archetype.py      # Parse IDF → JSON parameters
│   ├── generate_model.py       # Generate naive IDF from archetype JSON
│   └── bestest_naive.py        # BESTEST Case 600-equivalent IDF generator
├── boptest/
│   ├── client.py               # BopTest API client
│   ├── boptest_hello.py        # Quick connectivity test
│   └── extract_baseline_kpis.py # Run baseline + extract KPIs & time-series
└── validation/
    ├── metrics.py              # ASHRAE Guideline 14 metrics (CVRMSE, NMBE)
    ├── validate_model.py       # CLI validation tool
    ├── smoke_test.py           # End-to-end pipeline test
    ├── bestest_validation.py   # BESTEST-specific validation analysis
    └── critical_analysis.py    # Data quality diagnostics
data/
├── archetype/                  # Source IDF files
└── results/                    # Simulation outputs, KPIs, reports
plots/                          # Generated validation plots
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (for EnergyPlus and BopTest)
- [BopTest](https://github.com/ibpsa/project1-boptest) running locally on port 8000

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# 1. Parse an archetype IDF
python src/archetype/parse_archetype.py --idf data/archetype/Model_Thesis_MPC_Optimized.idf

# 2. Generate a naive model
python src/archetype/generate_model.py

# 3. Simulate with EnergyPlus (Docker)
docker run --rm -v "${PWD}/data/results:/sim" --entrypoint energyplus \
    nrel/energyplus:23.2.0 -r -w /sim/weather.epw -d /sim/out /sim/naive_baseline.idf

# 4. Extract BopTest baseline (requires BopTest running)
python src/boptest/extract_baseline_kpis.py --url http://127.0.0.1:8000 --hours 6

# 5. Validate
python src/validation/bestest_validation.py
```

## Current Status

| Milestone | Status |
|-----------|--------|
| MS1.1 BopTest connectivity | ✅ Done |
| MS1.2 Baseline KPI extraction | ✅ Done |
| MS1.3 Archetype IDF parsing | ✅ Done |
| MS1.4 Naive model generation | ✅ Done |
| MS1.5 ASHRAE-14 validation | 🔄 In progress |

## Tech Stack

- **EnergyPlus 23.2** (via Docker `nrel/energyplus:23.2.0`)
- **BopTest** (service-oriented API)
- **Python**: pandas, numpy, matplotlib, jinja2
- **ASHRAE Guideline 14** for CVRMSE/NMBE validation metrics

## License

MIT
