# Project Overview: Large-Scale Urban Modeling with Archetype Scaling

## Purpose
Scale the validated single-building workflow to neighborhood and district level by automatically generating and simulating many simplified ("naive") building models from urban inventory data.

## Problem Statement
After the current pipeline is validated and strengthened at building scale, the next objective is to run the same process at urban scale:
- Convert city-scale building inventory records into archetype-based IDFs.
- Instrument and export models in batch mode.
- Deploy and evaluate many cases with standardized control and KPI reporting.

## Target Outcome
A reproducible urban-scale pipeline that can:
- Generate thousands of naive IDFs from GIS/cadastral or archaeological urban data.
- Group buildings into archetypes and apply parameter templates.
- Run automated simulation and control campaigns.
- Produce district-level KPI dashboards and uncertainty ranges.

## Scope
In scope:
- Data ingestion from urban building datasets (geometry proxies, age class, usage, floor area, envelope indicators).
- Archetype mapping logic.
- Batch IDF generation and quality checks.
- Batch FMU export and BOPTEST orchestration.
- Standardized KPI aggregation at building and district level.

Out of scope (first iteration):
- Full detailed geometry reconstruction for each building.
- Full occupant behavior realism.
- Real-time digital twin operation.

## Core Work Packages
1. Urban Data Contract
- Define required columns, units, and validation rules for urban input datasets.

2. Archetype Library
- Define archetype parameter sets by building type, era, climate zone, and retrofit state.

3. Naive IDF Generator
- Implement deterministic IDF generation from archetype plus minimal geometry proxies.

4. Batch Instrumentation and Export
- Apply external control hooks and export FMUs in parallel with robust error handling.

5. Simulation and Control Campaign Engine
- Run RBC and MPC campaigns with fixed benchmark settings and repeatable seeds.

6. Aggregation and Reporting
- Aggregate KPIs across buildings, blocks, and district scenarios.

## Standardization Principles
- Same weather and disturbance forecast source for all compared controllers.
- Same scenario definitions, horizons, KPI formulas, and comfort constraints.
- Same data schema and naming conventions across all generated artifacts.
- Full run provenance: model hash, archetype version, config snapshot, and seed.

## Data Flow
Urban dataset -> Archetype assignment -> Naive IDFs -> Instrumented IDFs -> FMUs -> BOPTEST campaigns -> KPI aggregation -> District report

## Current Pipeline Status (as of 2026-03-13)
Status labels:
- Completed: step executed end-to-end for current benchmark scope.
- In progress: partly validated, unstable, or missing standardization for scaleup.
- Next: not yet implemented for urban scale.

| Pipeline step | Status | Notes |
|---|---|---|
| IDF parsing and instrumentation | Completed | Core single-building workflow documented and running. |
| FMU export for benchmark cases | Completed | Working for current validation scope. |
| BOPTEST deployment and runtime stability | In progress | Queue/startup handling improved, but robustness should be hardened further for large batches. |
| MPC closed-loop runs (RC and PINN) | Completed | Campaign runs completed for standard and future sets under current setup. |
| Direct local BOPTEST/TestCase mode | In progress | Direct mode dependency/runtime path still not fully stable in current environment. |
| Reproducibility manifests and strict contracts | In progress | Baseline reproducibility exists, but stronger run manifests and contract gates are still needed. |
| Urban-scale data contract and archetype mapping | Next | Not yet implemented for neighborhood-level scaleup. |
| Batch district-scale orchestration | Next | Requires queueing, retries, checkpointing, and throughput tuning. |

## In-Progress Steps to Carry into Next Phase
1. Harden BOPTEST startup and queue recovery for high-volume batch execution.
2. Stabilize direct execution path and dependency setup for local FMU/TestCase workflows.
3. Enforce strict data and KPI contracts before and after each run.
4. Add run-level provenance capture (config hash, model hash, seed, software version).

## Prioritized Next Steps
1. Define and freeze an urban input data contract with unit checks and required fields.
2. Implement deterministic archetype assignment with versioned mapping rules.
3. Build naive IDF batch generator plus static QA report.
4. Add resilient FMU export queue (retry, timeout, resume by building_id).
5. Add campaign orchestrator for RBC vs MPC with fixed benchmark settings.
6. Add district KPI aggregation and automated quality-gate report.

## Key Deliverables
- Urban input schema and validator.
- Versioned archetype catalog.
- Batch naive IDF generator with QA report.
- Batch simulation runner and failure-resume mechanism.
- District KPI summary tables and plots.
- Reproducibility manifest for each campaign.

## Success Criteria
- At least 95 percent successful end-to-end runs on a pilot neighborhood.
- Reproducible KPI outputs under repeated runs with fixed seeds.
- Clear cost-comfort comparison between baseline and optimized control at district scale.
- Runtime and storage budget documented for scaling decisions.

## Main Risks and Mitigations
- Risk: Missing or noisy urban inputs.
  Mitigation: strict schema checks, fallback defaults, and confidence flags.

- Risk: Batch export/runtime instability.
  Mitigation: queueing, retries, checkpointing, and resume-by-building-id.

- Risk: Non-comparable results across runs.
  Mitigation: locked benchmark configs and immutable campaign manifests.

## Pipeline Improvement Suggestions
1. Add a formal state machine per building (queued, running, failed, completed, retried) to make recovery deterministic.
2. Add a single run manifest format shared by generation, export, control, and KPI stages.
3. Introduce contract tests in CI for schemas, required signals, and KPI payload shapes.
4. Add warm-start and timeout diagnostics as first-class KPI fields to track controller operability at scale.
5. Add stratified pilot sampling (by archetype, age class, and climate) before full-neighborhood runs.
6. Add a failure taxonomy (dependency, export, runtime, control infeasibility, KPI parse) with per-class remediation.
7. Add immutable version tags for archetype libraries and weather sources to improve cross-campaign comparability.
8. Add cost and carbon normalization layers (per area, per occupancy, per weather severity) for fair district comparisons.
9. Add automated post-run anomaly checks (flat-line temperatures, missing controls, impossible energy spikes).
10. Add a scale-readiness gate requiring two consecutive successful pilot runs before increasing batch size.

## Suggested Pilot Sequence
1. Small pilot (20 to 50 buildings).
2. Medium pilot (200 to 500 buildings).
3. Full neighborhood (1000 plus buildings).

Each phase should include QA gates before scaling up.
