# Title: Automated Semantic Mapping of Building Automation Systems to Low-Order RC Thermal Networks

## Abstract
Recent advances in Model Predictive Control (MPC) and grid-interactive efficient buildings rely heavily on accurate, computationally efficient energy models. While white-box models (e.g., EnergyPlus) are highly detailed, their computational cost renders them unsuitable for real-time control. Conversely, gray-box Resistor-Capacitor (RC) models strike an ideal balance but require significant manual effort to map raw Building Automation System (BAS) datastreams to the underlying physical topology. This paper proposes a fully automated pipeline that ingest raw BAS point lists, utilizes the standardized Brick Schema ontology to generate an active building topology graph, and programmatically distills this semantic graph into modular, low-order RC templates (e.g., 3R1C). We demonstrate this pipeline on an operational commercial framework, showing that semantic standardization can eliminate weeks of manual model setup and pave the way for automated calibration and real-time inference.

## 1. Introduction
- **The Gap:** The difficulty of scaling Model Predictive Control (MPC) across diverse building portfolios because every Building Automation System (BAS) has a unique naming convention and topology.
- **The Need for Gray-Box Models:** Low-order Resistor-Capacitor (RC) models are needed for MPC execution speed, but assembling them manually from BAS data is error-prone and labor-intensive.
- **The Solution:** Semantic web technologies, specifically Brick Schema, offer a way to standardize building metadata. By mapping raw points to an ontology, physics-based RC structures can be auto-generated.
- **Contributions:**
  1. An automated text-to-ontology ingestion script mapping proprietary BAS points to Brick Schema.
  2. A graph traversal algorithm to distill HVAC topologies into discrete RC sub-models.
  3. A robust configuration engine that generates physics-informed JSON parameter sets ready for calibration engines (e.g., parameter estimation using differentiable physics).

## 2. Background and Related Work
### 2.1 Low-Order Thermal Networks (RC Models)
- Comparison of common architectures: 1R1C, 3R1C, 5R1C.
- Why 3R1C (3-Resistance, 1-Capacitance) per zone was selected for this study as a foundational template.

### 2.2 Semantic Metadata in Buildings
- Project Haystack vs. Brick Schema.
- Why Brick Schema is superior for physics-based modeling due to its explicit topological relationships (`brick:feeds`, `brick:hasPart`).

## 3. Methodology: The Automated Mapping Pipeline
### 3.1 BAS Point List Ingestion
- Methods for parsing standard BAS export formats (CSV/JSON).
- Heuristic and substring matching techniques employed to assign semantic classes to raw descriptions (e.g., converting "VAV-101 Zone Temp" to `brick:Zone_Air_Temperature_Sensor`).

### 3.2 Brick Schema Graph Generation
- Construction of the Resource Description Framework (RDF) graph using the `brickschema` library.
- Establishing the spatial and logical hierarchies: Building -> HVAC_Zone -> Equipment -> Points.

### 3.3 Dynamic RC Model Templating
- How the pipeline queries the `building_topology.ttl` (Turtle) file using SPARQL-like queries.
- Transforming `brick:HVAC_Zone` nodes into isolated thermal capacitance centers ($C_{air}$).
- Linking external influences ($T_{out}$, $Q_{sol}$) and feeding equipment ($Q_{hvac}$ from VAV heating coils) via boundary resistances ($R_{env}, R_{vent}, R_{int}$).

## 4. Implementation and Results
### 4.1 Case Study Description
- Application of the pipeline to a commercial building topology (1 AHU, 5 VAV zones, centralized hot/chilled water plant).
- Successful mapping of raw datastreams to 223 valid RDF triples.

### 4.2 Auto-Generated Model Architectures
- Analysis of the generated `rc_3r1c_template.json` structure.
- Verification that all thermodynamic boundaries and inputs were correctly associated with their physical hardware counterparts.

## 5. Discussion
*(To be populated as we reflect on the pipeline)*
- **Strengths:** Rapid deployment, elimination of human error in mapping.
- **Limitations:** Currently relies on heuristic mapping for the initial CSV-to-Brick step. Real-world BAS systems might have highly obscure naming conventions requiring Large Language Model (LLM) assistance for initial mapping. Furthermore, RC architectures (e.g., 3R1C vs 5R1C) currently need to be hardcoded as templates rather than derived dynamically from the physical fabric data.

## 6. Conclusion and Future Work
- The semantic mapping pipeline successfully bridges the gap between raw hardware telemetry and mathematical modeling environments.
- **Future Work (Phase 3):** Hooking these auto-generated RC templates into a differentiable physics solver (e.g., Julia/SciML or PyTorch) for automated parameter calibration using historical BAS telemetry data.

## References
1. Balaji, Bharathan, et al. "Brick: Metadata schema for portable smart building applications." Applied energy 226 (2018): 1273-1292.
2. ... (more to be added)
