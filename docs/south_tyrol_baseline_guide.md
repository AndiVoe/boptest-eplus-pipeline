# Manual Guide: Generating a South Tyrol Baseline Model

This guide walks you through the manual steps to create a region-specific EnergyPlus model for South Tyrol (Italy) using the built-in TABULA bridge.

## Step 1: Define the TABULA Archetype
Find the appropriate TABULA code for your building. For South Tyrol, we use Italian (IT) typologies. For a relatively modern apartment block, we use `IT.N.MFH.08.Gen`.

Create a file `data/archetypes/south_tyrol_my_building.json`:
```json
{
    "code": "IT.N.MFH.08.Gen",
    "country": "Italy (South Tyrol)",
    "type": "Multi Family House",
    "year_range": "1991-2005",
    "geometry": {
        "floor_area_m2": 450.0,
        "surface_area_envelope_m2": 850.0,
        "window_area_m2": 65.0
    },
    "envelope_u_values": {
        "wall": 0.38,
        "roof": 0.35,
        "floor": 0.45,
        "window": 1.70
    },
    "thermal_mass": "Heavy",
    "hvac": {
        "heating_system": "Gas Boiler",
        "cooling_system": "None"
    }
}
```

## Step 2: Run the TABULA Bridge
Convert the TABULA specification into a standardized archetype parameter file.

**Command:**
```powershell
.venv\Scripts\python.exe src/archetype/tabula_bridge.py `
    --json data/archetypes/south_tyrol_my_building.json `
    --out data/results/south_tyrol_params.json
```
*This extracts the U-values and geometry and prepares them for EnergyPlus.*

## Step 3: Generate the EnergyPlus IDF
Synthesize the actual EnergyPlus model from the parameter file.

**Command:**
```powershell
.venv\Scripts\python.exe src/archetype/generate_model.py `
    --params data/results/south_tyrol_params.json `
    -o data/results/south_tyrol_baseline.idf
```
*This creates the `.idf` file containing the building topology and materials.*

## Step 4: Verify the Model
Check the generated IDF to ensure it has the correct thermal properties.

**Command:**
```powershell
# Check for the correct U-values or materials
Get-Content data/results/south_tyrol_baseline.idf | Select-String "Material" -Context 2
```

## Step 5: (Optional) Static Validation
Run the readiness tester to ensure the IDF is structurally sound for co-simulation.

**Command:**
```powershell
.venv\Scripts\python.exe src/validation/test_idf_readiness.py `
    data/results/south_tyrol_baseline.idf
```

---
> [!NOTE]
> You can find the TABULA database at [episcope.eu](https://episcope.eu/building-typology/webtool/) to look up more codes for different building ages and types in Italy.
