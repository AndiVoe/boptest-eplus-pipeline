# PhD Building Energy Modeling & MPC Pipeline

An end-to-end automated pipeline for building energy model (BEM) creation, hybrid system identification, and model predictive control (MPC) optimization. This repository translates high-fidelity EnergyPlus archetypes into fast-executing RC models calibrated against [BopTest](https://github.com/ibpsa/project1-boptest) standards.

## 🚀 Pipeline Overview

The project is structured into functional phases:

### 1. Archetype Extraction & Generative Modeling
*   **Purpose**: Convert legacy `.idf` files into structured building parameters.
*   **Key Scripts**: `src/archetype/parse_archetype.py`, `src/archetype/generate_model.py`.
*   **Logic**: Uses a custom text-based parser to bypass EnergyPlus installation requirements, extracting $R$ (resistance) and $C$ (capacitance) foundations.

### 2. Hybrid System Identification (SysID)
*   **Purpose**: Calibrate thermal parameters ($R_{env}, C_{air}$) and inter-zonal coupling.
*   **Key Scripts**: `src/mpc/system_id_multizone.py`.
*   **Engines**: Dual-engine approach using **SciPy (L-BFGS-B)** for fast initialization and **PyTorch (Adam)** for deep calibration ($CVRMSE < 2\%$).

### 3. Multi-Zone Thermal Coupling
*   **Purpose**: Modeling complex heat transfer between adjacent zones.
*   **Logic**: Builds an admittance Laplacian matrix ($L_{ij}$) from identified zonal coupling resistances to enable high-fidelity multi-zone trajectory prediction.

### 4. PyTorch-based Model Predictive Control (MPC)
*   **Purpose**: Real-time optimization of heating/cooling setpoints for energy and comfort.
*   **Key Script**: `src/mpc/closed_loop_runner.py`.
*   **Features**: Leverages PyTorch's autograd to solve the optimization problem (minimizing $Energy^2 + ComfortPenalty^2$) across seasonal and regional horizons.

### 5. Automated Analytics & Benchmarking
*   **Purpose**: Rigorous extraction of Energy (kWh) and Thermal Discomfort (Kh).
*   **Key Script**: `calculate_final_kpis_v2.py`.
*   **Validation**: Built-in physics audit to verify power densities against building envelope properties.

## 📁 Project Structure

```
├── src/
│   ├── archetype/         # IDF Parsing & Model Generation
│   ├── boptest/           # API Client & Baseline Extraction
│   ├── mpc/               # SysID, Controller & Closed-Loop Runner
│   └── validation/        # Metrics & Data Quality Audits
├── data/
│   ├── archetypes/        # Input IDF files
│   └── results/           # Calibrated parameters & MPC trajectories
├── plots/                 # Visualizations of trajectories & comfort
└── docs/                  # Design documents and PhD article drafts
```

## 📊 Performance Benchmarks
The pipeline has been verified across multiple climates (Chicago, Copenhagen, Denver) and seasonal scenarios. For a highly efficient building ($U \approx 0.15 \text{ W/m}^2\text{K}$), the MPC achieves:
- **Discomfort Reduction**: Maintains setpoints within $\pm 0.5$K of comfort bounds.
- **Energy Efficiency**: Optimized trajectories exploit thermal mass to reduce peak load.

## 🛠 Setup & Usage
1. **Prepare Environment**: `pip install -r requirements.txt`
2. **Setup BopTest**: Ensure Docker containers are running on port 8000.
3. **Execute Runner**:
   ```bash
   python -m src.mpc.closed_loop_runner --model multizone_office_simple_air --scenario typical_heat_day
   ```

## License
MIT
