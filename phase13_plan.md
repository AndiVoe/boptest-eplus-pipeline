# Phase 13: Controller Sensitivity Analysis Plan

The goal is to quantify the trade-off between Energy consumption and Thermal Comfort by varying the objective function weights in the MPC controller.

## Proposed Changes

### Controller
#### [MODIFY] [controller.py](file:///C:/Users/AVoelser/.gemini/antigravity/scratch/phd-energy-model/src/mpc/controller.py)
- Parameterize `alpha_energy` and `beta_comfort` in `optimize_trajectory` to allow external control.

### Sensitivity Study
#### [NEW] [sensitivity_study.py](file:///C:/Users/AVoelser/.gemini/antigravity/scratch/phd-energy-model/src/mpc/sensitivity_study.py)
- A script to sweep through a range of weights (e.g., $\alpha \in [10^{-6}, 10^{-2}]$).
- Execute closed-loop simulations for each weight pair.
- Save result matrix (Energy, Discomfort) for Pareto analysis.

### Visualization
#### [NEW] [plot_pareto.py](file:///C:/Users/AVoelser/.gemini/antigravity/scratch/phd-energy-model/plot_pareto.py)
- Generate a 2D scatter plot showing the Pareto frontier.

## Verification Plan
### Automated Tests
- Run a 3-point weight sweep to verify the script execution chain.
- Check that higher `beta_comfort` consistently reduces discomfort Kh.
