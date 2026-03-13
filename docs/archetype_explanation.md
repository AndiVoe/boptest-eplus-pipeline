# Archetypes: The Bridge Between Boptest and EnergyPlus

In this project, **Archetypes** are intermediate, vendor-neutral data structures that represent the DNA of a building. They decouple the *specification* of a building (how many zones, what area, what climate) from its *implementation* (EnergyPlus IDF, Modelica, etc.).

## 1. What is an Archetype?
An archetype is physically stored as a structured JSON file (usually `archetype_params.json`). It contains:
- **Geometry**: Zone names, counts, ceiling heights, and floor areas.
- **Thermal Props**: U-values, R-values, and thermal capacitance ($C$).
- **Schedules**: Heating/Cooling setpoints and occupancy profiles.
- **HVAC Type**: A flag indicating if it uses Ideal Loads, VAV, or Radiant systems.

## 2. How are they Created?
The pipeline uses two automated paths to generate archetype parameters:

### Path A: Harvesting from Existing Models (Top-Down)
- **Tool**: `parse_archetype.py`
- **Logic**: It "reverse-engineers" a high-fidelity EnergyPlus IDF. It extracts building physics and calibration multipliers to save them in the archetype format. This allows us to "clone" complex models.

### Path B: Discovering from Boptest (Bottom-Up)
- **Tool**: `boptest_to_idf_params.py`
- **Logic**: It scans the Boptest filesystem (e.g., `kpis.json`, `config.json`) to see how many zones a Modelica model has. It synthesizes a matching archetype so we can build a "Mirror IDF" for a Modelica test case.

## 4. Geometry vs. Physics (The "Shoebox" Assumption)
You are right to be suspicious! A model with only area and U-values is a **LOD1 (Level of Detail 1)** model, often called a **"Shoebox" model**.

### What it captures:
- **Thermal Inertia**: The total mass (Concrete/Insulation) required to heat/cool the building.
- **Envelope Flux**: The total heat lost through walls based on the Surface-to-Volume ratio.
- **System Scale**: The peak capacity needed for HVAC sizing.

### What it misses (The "Geometric Gap"):
- **Orientation**: A shoebox doesn't know if your big window faces North or South.
- **Shading**: Self-shading from building wings or external shading from neighbors.
- **Inter-zonal Heat Transfer**: Internal walls between specific rooms.

## 5. Why use a "Naive" Geometry for Research?
In the context of **MPC and System Identification**, we often prioritize **Physics over Geometry**:
1. **Calibration as a Filter**: When we run SysID (Phase 20), the algorithm doesn't "see" the walls. It only sees `T_in`, `T_out`, and `Q`. If the geometry is a bit wrong (e.g., a window is on the wrong side), the SysID will identify an **"Effective Solar Gain"** that compensates for the geometric error.
2. **Computational Speed**: Complex geometry slows down the optimization solver. A "Thermal Zone" archetype is 100x faster to solve for MPC.

## 6. How to get more "Detail"?
If the Shoebox isn't enough, our pipeline has two "Upgrade" paths:
- **Path A (Detailed Ingestion)**: If you provide an existing IDF (like your Thesis model), our `parse_archetype.py` extracts the **Exact Geometric Vertices**.
- **Path B (GIS/Urban Scaling - Phase 22)**: We can ingest **GeoJSON** footprints. Instead of a square, the generator will build the exact polygon of the building from OpenStreetMap.

### Path C: BIM & GIS Ingestion (Future Sources)
The archetype format is designed to ingest data from design-phase tools:
- **gbXML / IFC**: Extracting geometry directly from Revit or ArchiCAD.
- **GeoJSON / CityGML**: Using OpenStreetMap footprints to define zone bounds and building height for urban-scale models.
- **Sensor Data (Digital Twin)**: Ingesting BMS (Building Management System) metadata to define real occupancy schedules and setpoints.

## 2b. Is there already a Library?
Yes! You don't always have to "create" an archetype from scratch. There are several gold-standard libraries you can leverage:

1. **TABULA / EPISCOPE (Europe)**: The definitive database for European building typologies. It categorizes buildings by age, type (Single-family, Office), and country. We can map TABULA "National Building Archetype" parameters directly into our `archetype_params.json`.
2. **DOE / PNNL Prototype Buildings (US)**: A library of 16 commercial building types representing 80% of US commercial floor area. 
3. **NREL ResStock / ComStock**: Large-scale libraries used for high-granularity national energy studies.
4. **Archetypal (Python Library)**: A powerful open-source library specifically designed to handle building archetypes. It can simplify EnergyPlus models into the thermal-zone format used in our pipeline.

## 3. How are they Used? (Model Synthesis)
Once we have an `archetype_params.json`, the **Generator Engine** (`generate_model.py`) takes over:
1. **Template Selection**: It picks a Jinja2-based EnergyPlus template (e.g., a multi-zone office template).
2. **Topology Injection**: It loops through the archetype's zones and dynamically writes the EnergyPlus `Zone`, `BuildingSurface:Detailed`, and `ZoneControl:Thermostat` objects.
3. **Instrumentation**: The synthesis output is then passed to `idf_instrumenter.py` to add the "co-simulation wires" for Boptest connection.

## 4. Future Applications & Scalability

- **Phase 21: HVAC Synthesis**: We will extend archetypes to include detailed HVAC layouts. Instead of manually drawing a radiant floor in EnergyPlus, you simply set `"hvac_type": "radiant"` in the archetype, and the generator builds the pipe network automatically.
- **Phase 22: Urban Modeling**: Imagine a CityGML or GeoJSON file representing 100 buildings. We can convert each building into an archetype and batch-generate 100 unique EnergyPlus models in minutes for neighborhood-level energy studies.
- **Automated Digital Twins**: By combining the **Archetype Generator** with the **Phase 20 SysID Calibration**, the pipeline can automatically discover a real building's zones, build the EnergyPlus model, and calibrate its R/C parameters without any human intervention.

## 5. Advanced Visionary Applications

Beyond current project scope, archetypes enable powerful long-term workflows:

- **Grid-Interactive Efficient Buildings (GEB)**: Archetypes allow for simulating "fleets" of buildings. We can model how 500 identical archetypes (with slight parameter variations) respond collectively to a demand response signal, providing high-fidelity virtual batteries for grid stabilization.
- **Generative Design & Sensitivity Optimization**: Instead of a "fixed" model, an archetype is a "fluid" model. We can run 1,000 simulations by sweeping archetype parameters (e.g., window-to-wall ratio, insulation thickness) to find the mathematically optimal design for a specific climate *before* any architectural drawing starts.
- **Synthetic Data for AI**: High-performance Machine Learning (ML) models for buildings require millions of data points. We can use the archetype engine to generate "Synthetic Building Universes"—millions of realistic building-performance labels used to train faster, lighter surrogate models.
- **Policy Impact & Code Analysis**: Carbon-neutrality policies can be tested on archetypes first. Policy makers can ask: *"What if all 1970s-era offices in Denver upgraded their $U$-value to 0.2?"* The archetype pipeline provides the answer in minutes.
- **Operational Performance Tracking**: By running a building's "Archetype Baseline" in parallel with its real meters, facility managers can detect **Performance Drift**. If the real building uses 20% more energy than its archetype twin, it flags a likely equipment fault or commissioning error.

---
> [!TIP]
> This "Parameter-First" approach is what makes the pipeline robust; we don't fixate on individual files, but on the underlying building data.
