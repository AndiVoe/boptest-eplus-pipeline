"""
Model Generator — Micro-Step 4 Deliverable
============================================
Generates an EnergyPlus IDF model from archetype parameters.  Uses a
minimal single-zone IdealLoadsAirSystem template as the starting point,
then injects envelope, HVAC, schedule, and sizing parameters from
archetype_params.json.

The approach:
  1. Start with a minimal, hand-crafted template IDF (template.idf)
     that has IdealLoadsAirSystem HVAC topology hard-coded
  2. Inject archetype parameters (U-values, schedules, capacities)
     into the template via eppy for structured objects
  3. Fall back to jinja2 text substitution for complex HVAC topology
     that eppy handles poorly

The generated model is a "naive" baseline — its purpose is to be
compared against the real calibrated IDF to quantify the calibration
gap.

Usage:
  python src/archetype/generate_model.py
  python src/archetype/generate_model.py --params data/results/archetype_params.json
  python src/archetype/generate_model.py --params data/results/archetype_params.json -o data/results/output_model.idf
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

try:
    from eppy.modeleditor import IDF
except ImportError:
    print("ERROR: eppy not installed. Run: pip install eppy")
    sys.exit(1)

from jinja2 import Template


# ======================================================================
# Paths
# ======================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "data" / "templates"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"

# IDD — update to match your EnergyPlus installation
DEFAULT_IDD_PATHS = [
    r"C:\EnergyPlusV23-2-0\Energy+.idd",
    r"C:\EnergyPlusV23-1-0\Energy+.idd",
    r"C:\EnergyPlusV22-2-0\Energy+.idd",
    "/usr/local/EnergyPlus-23-2-0/Energy+.idd",
    "/usr/local/EnergyPlus-23-1-0/Energy+.idd",
]


def find_idd() -> str:
    """Locate an EnergyPlus IDD file on the system."""
    for p in DEFAULT_IDD_PATHS:
        if Path(p).exists():
            return p
    raise FileNotFoundError(
        "Cannot find Energy+.idd. Set the path in DEFAULT_IDD_PATHS "
        "or pass --idd on the command line."
    )


# ======================================================================
# Template IDF (Jinja2-based)
# ======================================================================
# This is the minimal IDF template for one zone with IdealLoadsAirSystem.
# Complex HVAC topology is kept static; only envelope/sizing is injected.

TEMPLATE_IDF = """\
!-Generator Python generate_model.py
!-Option SortedOrder

Version,
    23.2;                    !- Version Identifier

SimulationControl,
    No,                      !- Do Zone Sizing Calculation
    No,                      !- Do System Sizing Calculation
    No,                      !- Do Plant Sizing Calculation
    No,                      !- Run Simulation for Sizing Periods
    Yes,                     !- Run Simulation for Weather File Run Periods
    No,                      !- Do HVAC Sizing Simulation for Sizing Periods
    ;                        !- Maximum Number of HVAC Sizing Simulation Passes

Building,
    {{ building_name }},     !- Name
    0,                       !- North Axis {deg}
    City,                    !- Terrain
    0.001,                   !- Loads Convergence Tolerance Value {W}
    0.01,                    !- Temperature Convergence Tolerance Value {deltaC}
    FullExterior,            !- Solar Distribution
    100,                     !- Maximum Number of Warmup Days
    6;                       !- Minimum Number of Warmup Days

Timestep,
    {{ timestep }};          !- Number of Timesteps per Hour

RunPeriod,
    AnnualRun,               !- Name
    {{ run_begin_month }},   !- Begin Month
    {{ run_begin_day }},     !- Begin Day of Month
    {{ run_begin_year }},    !- Begin Year
    {{ run_end_month }},     !- End Month
    {{ run_end_day }},       !- End Day of Month
    {{ run_end_year }},      !- End Year
    Monday,                  !- Day of Week for Start Day
    No,                      !- Use Weather File Holidays and Special Days
    No,                      !- Use Weather File Daylight Saving Period
    No,                      !- Apply Weekend Holiday Rule
    Yes,                     !- Use Weather File Rain Indicators
    Yes,                     !- Use Weather File Snow Indicators
    No,                      !- Treat Weather as Actual
    Hour24;                  !- First Hour Interpolation Starting Values

SurfaceConvectionAlgorithm:Inside,
    TARP;                    !- Algorithm

SurfaceConvectionAlgorithm:Outside,
    DOE-2;                   !- Algorithm

HeatBalanceAlgorithm,
    ConductionTransferFunction,  !- Algorithm
    200;                     !- Surface Temperature Upper Limit {C}

ScheduleTypeLimits,
    Fractional,              !- Name
    0,                       !- Lower Limit Value
    1,                       !- Upper Limit Value
    Continuous,              !- Numeric Type
    dimensionless;           !- Unit Type

ScheduleTypeLimits,
    AnyNumber,               !- Name
    ,                        !- Lower Limit Value
    ,                        !- Upper Limit Value
    Continuous,              !- Numeric Type
    Dimensionless;           !- Unit Type

ScheduleTypeLimits,
    Temperature,             !- Name
    -273.15,                 !- Lower Limit Value
    ,                        !- Upper Limit Value
    Continuous,              !- Numeric Type
    Temperature;             !- Unit Type

! --- Global Geometry Rules ---
GlobalGeometryRules,
    UpperLeftCorner,         !- Starting Vertex Position
    Counterclockwise,        !- Vertex Entry Direction
    Relative;                !- Coordinate System

! --- Schedules ---

Schedule:Compact,
    Always On,               !- Name
    Fractional,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 1;         !- Field 3-4

Schedule:Compact,
    Always Off,              !- Name
    Fractional,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 0;         !- Field 3-4

Schedule:Compact,
    HVACTemplate-Always 4,   !- Name
    AnyNumber,               !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 4;         !- Field 3-4

Schedule:Compact,
    Heating Setpoint Schedule,  !- Name
    Temperature,             !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 7:00, {{ heating_setback_c }},  !- Field 3-4
    Until: 20:00, {{ heating_setpoint_c }},  !- Field 5-6
    Until: 24:00, {{ heating_setback_c }},  !- Field 7-8
    For: AllOtherDays,       !- Field 9
    Until: 24:00, {{ heating_setback_c }};  !- Field 10-11

Schedule:Compact,
    Cooling Setpoint Schedule,  !- Name
    Temperature,             !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 7:00, {{ cooling_setback_c }},  !- Field 3-4
    Until: 20:00, {{ cooling_setpoint_c }},  !- Field 5-6
    Until: 24:00, {{ cooling_setback_c }},  !- Field 7-8
    For: AllOtherDays,       !- Field 9
    Until: 24:00, {{ cooling_setback_c }};  !- Field 10-11

Schedule:Compact,
    Office Occupancy,        !- Name
    Fractional,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: Weekdays,           !- Field 2
    Until: 7:00, 0,          !- Field 3-4
    Until: 8:00, 0.1,        !- Field 5-6
    Until: 9:00, 0.9,        !- Field 7-8
    Until: 17:00, 1.0,       !- Field 9-10
    Until: 18:00, 0.8,       !- Field 11-12
    Until: 20:00, 0.3,       !- Field 13-14
    Until: 21:00, 0.1,       !- Field 15-16
    Until: 24:00, 0,         !- Field 17-18
    For: AllOtherDays,       !- Field 19
    Until: 24:00, 0;         !- Field 20-21

{% for zone in zones %}
! ================================================================
! ZONE: {{ zone.name }}
! ================================================================

Zone,
    {{ zone.name }},         !- Name
    0,                       !- Direction of Relative North {deg}
    {{ zone.x_origin }},     !- X Origin {m}
    {{ zone.y_origin }},     !- Y Origin {m}
    0,                       !- Z Origin {m}
    1,                       !- Type
    1,                       !- Multiplier
    autocalculate,           !- Ceiling Height {m}
    {{ zone.volume }};       !- Volume {m3}

! --- Envelope surfaces ---

BuildingSurface:Detailed,
    {{ zone.name }}_Floor,   !- Name
    Floor,                   !- Surface Type
    {{ floor_construction }},  !- Construction Name
    {{ zone.name }},         !- Zone Name
    ,                        !- Space Name
    Ground,                  !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    NoSun,                   !- Sun Exposure
    NoWind,                  !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, 0, 0,
    0, {{ zone.depth }}, 0,
    {{ zone.width }}, {{ zone.depth }}, 0,
    {{ zone.width }}, 0, 0;

BuildingSurface:Detailed,
    {{ zone.name }}_Ceiling, !- Name
    Ceiling,                 !- Surface Type
    {{ ceiling_construction }},  !- Construction Name
    {{ zone.name }},         !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    {{ zone.width }}, 0, {{ zone.height }},
    {{ zone.width }}, {{ zone.depth }}, {{ zone.height }},
    0, {{ zone.depth }}, {{ zone.height }},
    0, 0, {{ zone.height }};

BuildingSurface:Detailed,
    {{ zone.name }}_Wall_South,  !- Name
    Wall,                    !- Surface Type
    {{ wall_construction }}, !- Construction Name
    {{ zone.name }},         !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, 0, {{ zone.height }},
    0, 0, 0,
    {{ zone.width }}, 0, 0,
    {{ zone.width }}, 0, {{ zone.height }};

BuildingSurface:Detailed,
    {{ zone.name }}_Wall_North,  !- Name
    Wall,                    !- Surface Type
    {{ wall_construction }}, !- Construction Name
    {{ zone.name }},         !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    {{ zone.width }}, {{ zone.depth }}, {{ zone.height }},
    {{ zone.width }}, {{ zone.depth }}, 0,
    0, {{ zone.depth }}, 0,
    0, {{ zone.depth }}, {{ zone.height }};

BuildingSurface:Detailed,
    {{ zone.name }}_Wall_East,  !- Name
    Wall,                    !- Surface Type
    {{ wall_construction }}, !- Construction Name
    {{ zone.name }},         !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    {{ zone.width }}, 0, {{ zone.height }},
    {{ zone.width }}, 0, 0,
    {{ zone.width }}, {{ zone.depth }}, 0,
    {{ zone.width }}, {{ zone.depth }}, {{ zone.height }};

BuildingSurface:Detailed,
    {{ zone.name }}_Wall_West,  !- Name
    Wall,                    !- Surface Type
    {{ wall_construction }}, !- Construction Name
    {{ zone.name }},         !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, {{ zone.depth }}, {{ zone.height }},
    0, {{ zone.depth }}, 0,
    0, 0, 0,
    0, 0, {{ zone.height }};

FenestrationSurface:Detailed,
    {{ zone.name }}_Window_South,  !- Name
    Window,                  !- Surface Type
    {{ window_construction }},  !- Construction Name
    {{ zone.name }}_Wall_South,  !- Building Surface Name
    ,                        !- Outside Boundary Condition Object
    autocalculate,           !- View Factor to Ground
    ,                        !- Frame and Divider Name
    1,                       !- Multiplier
    4,                       !- Number of Vertices
    {{ zone.width * 0.1 }}, 0, {{ zone.height * 0.8 }},
    {{ zone.width * 0.1 }}, 0, {{ zone.height * 0.2 }},
    {{ zone.width * 0.9 }}, 0, {{ zone.height * 0.2 }},
    {{ zone.width * 0.9 }}, 0, {{ zone.height * 0.8 }};

! --- Internal gains ---

People,
    {{ zone.name }}_People,  !- Name
    {{ zone.name }},         !- Zone or ZoneList or Space or SpaceList Name
    Office Occupancy,        !- Number of People Schedule Name
    People/Area,             !- Number of People Calculation Method
    ,                        !- Number of People
    {{ zone.people_density }},  !- People per Zone Floor Area {person/m2}
    ,                        !- Zone Floor Area per Person {m2/person}
    0.3,                     !- Fraction Radiant
    autocalculate,           !- Sensible Heat Fraction
    Activity Level Schedule; !- Activity Level Schedule Name

Lights,
    {{ zone.name }}_Lights,  !- Name
    {{ zone.name }},         !- Zone or ZoneList or Space or SpaceList Name
    Office Occupancy,        !- Schedule Name
    Watts/Area,              !- Design Level Calculation Method
    ,                        !- Lighting Level {W}
    {{ zone.lighting_density }},  !- Watts per Floor Area {W/m2}
    ,                        !- Watts per Person {W/person}
    0,                       !- Return Air Fraction
    0.72,                    !- Fraction Radiant
    0.18,                    !- Fraction Visible
    1;                       !- Fraction Replaceable

ElectricEquipment,
    {{ zone.name }}_Equipment,  !- Name
    {{ zone.name }},         !- Zone or ZoneList or Space or SpaceList Name
    Office Occupancy,        !- Schedule Name
    Watts/Area,              !- Design Level Calculation Method
    ,                        !- Design Level {W}
    {{ zone.equipment_density }},  !- Watts per Floor Area {W/m2}
    ,                        !- Watts per Person {W/person}
    0,                       !- Fraction Latent
    0.5,                     !- Fraction Radiant
    0;                       !- Fraction Lost

ZoneInfiltration:DesignFlowRate,
    {{ zone.name }}_Infiltration,  !- Name
    {{ zone.name }},         !- Zone or ZoneList or Space or SpaceList Name
    {{ zone.infiltration_ach }};  !- Air Changes per Hour {1/hr}

! --- HVAC: {{ hvac_type }} System ---

ZoneControl:Thermostat,
    {{ zone.name }} Thermostat,  !- Name
    {{ zone.name }},         !- Zone or ZoneList Name
    HVACTemplate-Always 4,   !- Control Type Schedule Name
    ThermostatSetpoint:DualSetpoint,  !- Control Object Type
    {{ zone.name }} Dual SP; !- Control Name

ThermostatSetpoint:DualSetpoint,
    {{ zone.name }} Dual SP, !- Name
    Heating Setpoint Schedule,  !- Heating Setpoint Temperature Schedule Name
    Cooling Setpoint Schedule;  !- Cooling Setpoint Temperature Schedule Name

ZoneHVAC:EquipmentConnections,
    {{ zone.name }},         !- Zone Name
    {{ zone.name }} Equipment,  !- Zone Conditioning Equipment List Name
    {{ zone.name }} Supply Inlet,  !- Zone Air Inlet Node or NodeList Name
    ,                        !- Zone Air Exhaust Node or NodeList Name
    {{ zone.name }} Air Node,  !- Zone Air Node Name
    {{ zone.name }} Return;  !- Zone Return Air Node Name

ZoneHVAC:EquipmentList,
    {{ zone.name }} Equipment,  !- Name
    SequentialLoad,          !- Load Distribution Scheme
    {% if hvac_type == 'Radiant' %}
    ZoneHVAC:LowTemperatureRadiant:VariableFlow, !- Zone Equipment Object Type
    {{ zone.name }} Radiant, !- Zone Equipment Name
    {% elif hvac_type == 'VAV' %}
    ZoneHVAC:UnitarySystem,  !- Zone Equipment Object Type
    {{ zone.name }} VAV,     !- Zone Equipment Name
    {% else %}
    ZoneHVAC:IdealLoadsAirSystem,  !- Zone Equipment Object Type
    {{ zone.name }} Ideal Loads,  !- Zone Equipment Name
    {% endif %}
    1,                       !- Zone Equipment Cooling Sequence
    1,                       !- Zone Equipment Heating or No-Load Sequence
    ,                        !- Zone Equipment Sequential Cooling Fraction
    ;                        !- Zone Equipment Sequential Heating Fraction

{% if hvac_type == 'Radiant' %}
ZoneHVAC:LowTemperatureRadiant:VariableFlow,
    {{ zone.name }} Radiant, !- Name
    Always On,               !- Availability Schedule Name
    {{ zone.name }},         !- Zone Name
    HeatedFloor,             !- Surface Name or Radiant Surface Group Name
    autocalculate,           !- Hydronic Tubing Inside Diameter {m}
    autocalculate,           !- Hydronic Tubing Length {m}
    MeanAirTemperature,      !- Temperature Control Type
    {{ zone.max_heating_w }},!- Maximum Hot Water Flow {m3/s}
    {{ zone.name }} Radiant Inlet, !- Heating Water Inlet Node Name
    {{ zone.name }} Radiant Outlet, !- Heating Water Outlet Node Name
    2.0,                     !- Heating Control Throttling Range {deltaC}
    Heating Setpoint Schedule, !- Heating Control Temperature Schedule Name
    {{ zone.max_cooling_w }},!- Maximum Cold Water Flow {m3/s}
    {{ zone.name }} Radiant Cooling Inlet, !- Cooling Water Inlet Node Name
    {{ zone.name }} Radiant Cooling Outlet, !- Cooling Water Outlet Node Name
    2.0,                     !- Cooling Control Throttling Range {deltaC}
    Cooling Setpoint Schedule, !- Cooling Control Temperature Schedule Name
    ,                        !- Condensation Control Type
    ,                        !- Condensation Control Dewpoint Connection
    ;                        !- Number of Circuits

{% elif hvac_type == 'VAV' %}
ZoneHVAC:UnitarySystem,
    {{ zone.name }} VAV,     !- Name
    Always On,               !- Availability Schedule Name
    {{ zone.name }} Supply Inlet,  !- Air Inlet Node Name
    {{ zone.name }} Air Node, !- Air Outlet Node Name
    ,                        !- Control Port Node Name
    Fan:VariableVolume,      !- Supply Fan Object Type
    {{ zone.name }} Fan,     !- Supply Fan Name
    ,                        !- Fan Placement
    ,                        !- Supply Air Fan Operating Mode Schedule Name
    Coil:Heating:Electric,   !- Heating Coil Object Type
    {{ zone.name }} HeatCoil, !- Heating Coil Name
    ,                        !- DX Heating Coil Quarterly Outage Fraction
    ,                        !- DX Heating Coil Quarterly Outage Period
    Coil:Cooling:DX:SingleSpeed, !- Cooling Coil Object Type
    {{ zone.name }} CoolCoil, !- Cooling Coil Name
    ;                        !- Dehumidification Control Type

Fan:VariableVolume,
    {{ zone.name }} Fan,     !- Name
    Always On,               !- Availability Schedule Name
    0.7,                     !- Fan Total Efficiency
    600,                     !- Pressure Rise {Pa}
    {{ zone.max_heating_w / 1000.0 }}, !- Maximum Flow Rate {m3/s}
    FixedQuarterly,          !- Fan Power Coefficient Array Name
    0.2,                     !- Minimum Flow Fraction
    {{ zone.name }} Supply Inlet,  !- Air Inlet Node Name
    {{ zone.name }} HeatNode;  !- Air Outlet Node Name

Coil:Heating:Electric,
    {{ zone.name }} HeatCoil, !- Name
    Always On,               !- Availability Schedule Name
    1.0,                     !- Efficiency
    {{ zone.max_heating_w }}, !- Nominal Capacity {W}
    {{ zone.name }} HeatNode, !- Air Inlet Node Name
    {{ zone.name }} CoolNode; !- Air Outlet Node Name

Coil:Cooling:DX:SingleSpeed,
    {{ zone.name }} CoolCoil, !- Name
    Always On,               !- Availability Schedule Name
    {{ zone.max_cooling_w }}, !- Gross Rated Total Cooling Capacity {W}
    0.75,                    !- Gross Rated Sensible Heat Ratio
    3.0,                     !- Gross Rated COP {W/W}
    {{ zone.max_cooling_w / 2000.0 }}, !- Rated Air Flow Rate {m3/s}
    {{ zone.name }} CoolNode, !- Air Inlet Node Name
    {{ zone.name }} Air Node; !- Air Outlet Node Name

{% else %}
ZoneHVAC:IdealLoadsAirSystem,
    {{ zone.name }} Ideal Loads,  !- Name
    Always On,               !- Availability Schedule Name
    {{ zone.name }} Supply Inlet,  !- Zone Supply Air Node Name
    ,                        !- Zone Exhaust Air Node Name
    ,                        !- System Inlet Air Node Name
    50,                      !- Maximum Heating Supply Air Temperature [C]
    13,                      !- Minimum Cooling Supply Air Temperature [C]
    0.0156,                  !- Maximum Heating Supply Air Humidity Ratio
    0.0077,                  !- Minimum Cooling Supply Air Humidity Ratio
    LimitCapacity,           !- Heating Limit
    ,                        !- Maximum Heating Air Flow Rate {m3/s}
    {{ zone.max_heating_w }},  !- Maximum Sensible Heating Capacity {W}
    LimitCapacity,           !- Cooling Limit
    ,                        !- Maximum Cooling Air Flow Rate {m3/s}
    {{ zone.max_cooling_w }},  !- Maximum Total Cooling Capacity {W}
    ,                        !- Heating Availability Schedule Name
    ,                        !- Cooling Availability Schedule Name
    ConstantSensibleHeatRatio,  !- Dehumidification Control Type
    0.7,                     !- Cooling Sensible Heat Ratio
    None,                    !- Humidification Control Type
    ,                        !- Design Specification Outdoor Air Object Name
    ,                        !- Outdoor Air Inlet Node Name
    None,                    !- Demand Controlled Ventilation Type
    NoEconomizer,            !- Outdoor Air Economizer Type
    None,                    !- Heat Recovery Type
    0.7,                     !- Sensible Heat Recovery Effectiveness
    0.65;                    !- Latent Heat Recovery Effectiveness
{% endif %}

{% endfor %}

! --- Shared schedules ---

Schedule:Compact,
    Activity Level Schedule, !- Name
    AnyNumber,               !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 120;       !- Field 3-4 (120 W/person seated)

! --- Materials and Constructions ---

Material,
    Concrete_200mm,          !- Name
    MediumRough,             !- Roughness
    0.2,                     !- Thickness {m}
    1.4,                     !- Conductivity {W/m-K}
    2100,                    !- Density {kg/m3}
    840,                     !- Specific Heat {J/kg-K}
    0.9,                     !- Thermal Absorptance
    0.7,                     !- Solar Absorptance
    0.7;                     !- Visible Absorptance

Material,
    Insulation_EPS,          !- Name
    MediumSmooth,            !- Roughness
    {{ insulation_thickness }},  !- Thickness {m}
    {{ insulation_conductivity }}, !- Conductivity {W/m-K}
    {{ insulation_density }}, !- Density {kg/m3}
    1400,                    !- Specific Heat {J/kg-K}
    0.9,                     !- Thermal Absorptance
    0.7,                     !- Solar Absorptance
    0.7;                     !- Visible Absorptance

Material,
    Plaster_15mm,            !- Name
    Smooth,                  !- Roughness
    0.015,                   !- Thickness {m}
    0.7,                     !- Conductivity {W/m-K}
    1400,                    !- Density {kg/m3}
    840,                     !- Specific Heat {J/kg-K}
    0.9,                     !- Thermal Absorptance
    0.5,                     !- Solar Absorptance
    0.5;                     !- Visible Absorptance

Construction,
    Ext_Wall,                !- Name
    Plaster_15mm,            !- Outside Layer
    Insulation_EPS,          !- Layer 2
    Concrete_200mm,          !- Layer 3
    Plaster_15mm;            !- Layer 4

Construction,
    Int_Floor,               !- Name
    Concrete_200mm;          !- Outside Layer

Construction,
    Ext_Roof,                !- Name
    Plaster_15mm,            !- Outside Layer
    Insulation_EPS,          !- Layer 2
    Concrete_200mm;          !- Layer 3

WindowMaterial:SimpleGlazingSystem,
    Simple_Window,           !- Name
    {{ window_u_value }},    !- U-Factor {W/m2-K}
    {{ window_shgc }},       !- Solar Heat Gain Coefficient
    ;                        !- Visible Transmittance

Construction,
    Simple_Window_Const,     !- Name
    Simple_Window;           !- Outside Layer

! --- Output Variables ---

Output:Variable,*,Zone Mean Air Temperature,Timestep;
Output:Variable,*,Zone Ideal Loads Zone Total Heating Energy,Timestep;
Output:Variable,*,Zone Ideal Loads Zone Total Cooling Energy,Timestep;

OutputControl:Table:Style,
    HTML;                    !- Column Separator

Output:Table:SummaryReports,
    AllSummary;              !- Report 1

"""


# ======================================================================
# Default archetype parameters (DOE Medium Office, CZ4A approximation)
# ======================================================================

DEFAULT_PARAMS = {
    "building_name": "Archetype_Office",
    "timestep": 6,
    "run_begin_month": 1,
    "run_begin_day": 1,
    "run_begin_year": 2024,
    "run_end_month": 3,
    "run_end_day": 1,
    "run_end_year": 2024,
    "hvac_type": "IdealLoads", # Options: IdealLoads, VAV, Radiant
    "insulation_conductivity": 0.04,
    "insulation_density": 25,

    # Envelope
    "insulation_thickness": 0.08,       # m (gives approx U=0.4 W/m2K wall)
    "window_u_value": 2.0,              # W/m2K
    "window_shgc": 0.4,

    # Constructions (point to names in template)
    "wall_construction": "Ext_Wall",
    "ceiling_construction": "Ext_Roof",
    "floor_construction": "Int_Floor",
    "window_construction": "Simple_Window_Const",

    # Setpoints (°C)
    "heating_setpoint_c": 23,
    "heating_setback_c": 18,
    "cooling_setpoint_c": 25,
    "cooling_setback_c": 30,

    # Zones — list of zone dicts
    "zones": [
        {
            "name": "Office_Zone_1",
            "x_origin": 0, "y_origin": 0,
            "width": 5.0, "depth": 4.5, "height": 3.0,
            "volume": 67.5,
            "people_density": 0.05,        # person/m2
            "lighting_density": 10,        # W/m2
            "equipment_density": 12,       # W/m2
            "infiltration_ach": 0.5,       # 1/hr
            "max_heating_w": 2000,
            "max_cooling_w": 2000,
        },
    ],
}


def generate_model(params: dict, output_path: str) -> Path:
    """
    Render the Jinja2 IDF template with the given parameters.

    Args:
        params: Dict of archetype parameters (see DEFAULT_PARAMS).
        output_path: Where to write the generated .idf.
    Returns:
        Path to the generated IDF.
    """
    template = Template(TEMPLATE_IDF)
    rendered = template.render(**params)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    return out


def load_params(params_path: Optional[str] = None) -> dict:
    """Load params from JSON, merging with defaults and adapting format."""
    import math
    params = dict(DEFAULT_PARAMS)
    
    if params_path:
        with open(params_path) as f:
            overrides = json.load(f)
            
        # The JSON provides `zones` as {"name", "ceiling_height_m", "volume_m3"}
        # The template expects a lot more per zone. We adapt them here:
        if "zones" in overrides:
            adapted_zones = []
            for z in overrides["zones"]:
                # Default to 3m height if missing
                h = z.get("ceiling_height_m") or 3.0
                vol = z.get("volume_m3") or (10.0 * 10.0 * h)
                
                # Assume a square room for the naive geometry
                area = vol / h
                side = math.sqrt(area)
                
                adapted_zones.append({
                    "name": z["name"],
                    "x_origin": 0, "y_origin": 0,
                    "width": side, "depth": side, "height": h,
                    "volume": vol,
                    # Provide defaults for loads since they aren't parsed from text yet
                    "people_density": 0.05,
                    "lighting_density": 10,
                    "equipment_density": 12,
                    "infiltration_ach": 0.5,
                    "max_heating_w": 3000,
                    "max_cooling_w": 3000,
                })
            # Replace the raw JSON zones with our adapted ones
            overrides["zones"] = adapted_zones
            
        # --- Parameter Injection (SysID calibration) ---
        if "target_r_env" in overrides and "total_area_m2" in overrides:
            R = overrides["target_r_env"]
            L = params["insulation_thickness"]
            # k = L / R
            params["insulation_conductivity"] = L / R
            print(f"[calib] Injected k={params['insulation_conductivity']:.4f} (R={R:.2f})")

        if "target_c_air" in overrides and "total_area_m2" in overrides:
            # This is a simplification: mapping global C to the insulation layer
            # In real EnergyPlus, mass is distributed.
            C = overrides["target_c_air"]
            L = params["insulation_thickness"]
            A = overrides["total_area_m2"]
            Cp = 1400 # specific heat from template
            # rho = C / (L * A * Cp)
            params["insulation_density"] = C / (L * A * Cp)
            print(f"[calib] Injected rho={params['insulation_density']:.2f} (C={C:.1e})")

        params.update(overrides)
        
    return params


# ======================================================================
# Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a naive EnergyPlus IDF from archetype parameters. "
            "The generated model uses IdealLoadsAirSystem and can be "
            "compared against the calibrated thesis model."
        )
    )
    parser.add_argument(
        "--params", default=None,
        help="Path to archetype_params.json (optional, uses defaults)",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output IDF path (default: data/results/output_model.idf)",
    )
    parser.add_argument(
        "--idd", default=None, help="Path to Energy+.idd (unused for template approach)",
    )
    args = parser.parse_args()

    output = args.output or str(RESULTS_DIR / "output_model.idf")
    params = load_params(args.params)

    print(f"[generate_model] Building: {params['building_name']}")
    print(f"[generate_model] Zones:    {len(params['zones'])}")
    print(f"[generate_model] Period:   {params['run_begin_month']}/{params['run_begin_day']}/{params['run_begin_year']}"
          f" → {params['run_end_month']}/{params['run_end_day']}/{params['run_end_year']}")

    out = generate_model(params, output)
    print(f"[generate_model] Output IDF → {out}")
    print(f"\n✅ generate_model.py completed successfully!")
    print(f"\nTo run the simulation:")
    print(f"  energyplus -w <weather.epw> {out}")


if __name__ == "__main__":
    main()
