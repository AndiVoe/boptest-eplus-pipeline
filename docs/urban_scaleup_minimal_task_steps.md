# Minimal Task Steps: Urban Archetype Scaleup

This checklist is the minimum implementation path once the current pipeline is validated and strengthened.

## Preconditions
- Core single-building pipeline is stable and reproducible.
- Control benchmark settings are fixed.
- Data schemas for existing artifacts are frozen.

## In-Progress Steps Identified from Current Pipeline
These steps are partially done and should be completed before urban scaleup:
1. BOPTEST runtime resilience for batch mode (startup queue handling, retries, and timeout policy).
2. Direct local execution path stabilization (dependencies and execution environment consistency).
3. Unified contract enforcement for inputs, signals, and KPI outputs.
4. Full provenance logging for every run (hashes, versions, seed, config snapshot).

## Next Steps (Prioritized)
1. Complete all in-progress items above and define objective pass criteria for each.
2. Run a 20-building pilot and require all quality gates to pass.
3. Expand to 200 to 500 buildings only after two consecutive successful pilot runs.
4. Freeze archetype and campaign versions before full-neighborhood execution.

## Minimal Steps
1. Freeze benchmark configuration
- Lock control horizon, KPI definitions, weather source, and reporting format.

2. Define urban input schema
- Create a strict schema for building_id, use_type, construction_period, floor_area, height or floors, climate region, and optional retrofit flags.

3. Build dataset validator
- Implement fail-fast checks for missing fields, unit mismatches, out-of-range values, and duplicate building_id.

4. Create archetype mapping table
- Map each input building to an archetype using deterministic rules (use_type plus age class plus climate).

5. Version archetype parameter library
- Store U-values, infiltration, internal gains, HVAC defaults, and schedules per archetype with explicit version tags.

6. Implement naive IDF generator
- Generate one IDF per building with simplified geometry assumptions and archetype parameters.

7. Run static QA on generated IDFs
- Check for invalid objects, missing schedules, bad node references, and impossible values.

8. Instrument IDFs for external control
- Inject ExternalInterface hooks for setpoints and required observations.

9. Batch export FMUs
- Export FMUs in parallel with retry and per-building error logs.

10. Register and run campaign batches
- Run baseline and MPC campaigns with identical scenario settings and fixed seeds.

11. Aggregate KPIs
- Compute per-building and district metrics: energy, comfort, cost, and emissions.

12. Produce reproducibility manifest
- Save hashes, archetype version, config snapshot, run timestamp, and software versions.

13. Run spot-check validation
- Randomly select buildings and compare simulated behavior against archetype expectations.

14. Approve pilot gate
- Proceed to larger scale only if success-rate and quality thresholds are met.

## Minimum Artifacts to Store
- urban_input_validated.csv
- archetype_assignments.csv
- idf_generation_report.json
- fmu_export_report.json
- campaign_manifest.yaml
- district_kpi_summary.csv
- reproducibility_manifest.json

## Suggested Quality Gates
- Gate 1: Input validation pass rate equals 100 percent.
- Gate 2: IDF generation success rate at least 99 percent.
- Gate 3: FMU export success rate at least 95 percent.
- Gate 4: Campaign completion rate at least 95 percent.
- Gate 5: KPI schema compliance equals 100 percent.

## First Expansion Rule
Only increase scale after two consecutive pilot runs pass all quality gates.
