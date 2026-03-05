#!/usr/bin/env python3
"""Generate a BESTEST Case 600-equivalent naive EnergyPlus IDF.

This model matches the bestest_air BopTest test case geometry:
  - Single zone: 8m x 6m x 2.7m (48 m², 129.6 m³)
  - Lightweight construction (Case 600)
  - South-facing window 12 m²  (2 × 3m × 2m)
  - Infiltration: 0.5 ACH
  - Heating setpoint: 21°C (occ) / 15°C (unocc)
  - Cooling setpoint: 24°C (occ) / 30°C (unocc)
  - Occupancy: 08:00–18:00 daily
  - Internal gains: 11.8W lighting + 5.4W equipment + 2×(73W sen + 45W lat)
"""
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parents[2] / "data" / "results"

IDF_CONTENT = """\
!-Generator bestest_naive.py
!-Option SortedOrder

Version,
    23.2;                    !- Version Identifier

Timestep,
    6;                       !- Number of Timesteps per Hour

SimulationControl,
    No,                      !- Do Zone Sizing Calculation
    No,                      !- Do System Sizing Calculation
    No,                      !- Do Plant Sizing Calculation
    Yes,                     !- Run Simulation for Sizing Periods
    Yes,                     !- Run Simulation for Weather File Run Periods
    No,                      !- Do HVAC Sizing Simulation for Sizing Periods
    1;                       !- Maximum Number of HVAC Sizing Simulation Passes

Building,
    BESTEST_Case600,         !- Name
    0,                       !- North Axis {deg}
    Suburbs,                 !- Terrain
    0.04,                    !- Loads Convergence Tolerance Value
    0.004,                   !- Temperature Convergence Tolerance Value {deltaC}
    FullExterior,            !- Solar Distribution
    25,                      !- Maximum Number of Warmup Days
    6;                       !- Minimum Number of Warmup Days

RunPeriod,
    Annual,                  !- Name
    1,                       !- Begin Month
    1,                       !- Begin Day of Month
    ,                        !- Begin Year
    3,                       !- End Month
    1,                       !- End Day of Month
    ,                        !- End Year
    ,                        !- Day of Week for Start Day
    Yes,                     !- Use Weather File Holidays and Special Days
    Yes,                     !- Use Weather File Daylight Saving Period
    No,                      !- Apply Weekend Holiday Rule
    Yes,                     !- Use Weather File Rain Indicators
    Yes;                     !- Use Weather File Snow Indicators

! --- Schedule Type Limits ---

ScheduleTypeLimits,
    Fractional,              !- Name
    0, 1,                    !- Lower/Upper Limit
    Continuous;              !- Numeric Type

ScheduleTypeLimits,
    Temperature,             !- Name
    -100, 100,               !- Lower/Upper Limit
    Continuous,              !- Numeric Type
    Temperature;             !- Unit Type

ScheduleTypeLimits,
    AnyNumber,               !- Name
    ,,,                      !- No limits
    Dimensionless;           !- Numeric Type

! --- Global Geometry Rules ---

GlobalGeometryRules,
    UpperLeftCorner,         !- Starting Vertex Position
    Counterclockwise,        !- Vertex Entry Direction
    Relative;                !- Coordinate System

! --- Schedules (matching BopTest thermostat: occ 08:00-18:00 daily) ---

Schedule:Compact,
    Always On,               !- Name
    Fractional,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 1;         !- Field 3-4

Schedule:Compact,
    Occupancy Schedule,      !- Name
    Fractional,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 8:00, 0,          !- Field 3-4
    Until: 18:00, 1,         !- Field 5-6
    Until: 24:00, 0;         !- Field 7-8

Schedule:Compact,
    Heating Setpoint Schedule,  !- Name
    Temperature,             !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 8:00, 15,         !- Field 3-4 (unoccupied)
    Until: 18:00, 21,        !- Field 5-6 (occupied)
    Until: 24:00, 15;        !- Field 7-8 (unoccupied)

Schedule:Compact,
    Cooling Setpoint Schedule,  !- Name
    Temperature,             !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 8:00, 30,         !- Field 3-4 (unoccupied)
    Until: 18:00, 24,        !- Field 5-6 (occupied)
    Until: 24:00, 30;        !- Field 7-8 (unoccupied)

Schedule:Compact,
    Activity Level Schedule, !- Name
    AnyNumber,               !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 120;       !- Field 3-4 (120 W/person)

Schedule:Compact,
    HVACTemplate-Always 4,   !- Name
    AnyNumber,               !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00, 4;         !- Field 3-4

! === ZONE ===

Zone,
    BESTEST_Zone,            !- Name
    0,                       !- Direction of Relative North {deg}
    0, 0, 0,                 !- Origin {m}
    1,                       !- Type
    1,                       !- Multiplier
    2.7,                     !- Ceiling Height {m}
    129.6;                   !- Volume {m3}

! --- Envelope: Lightweight walls (BESTEST Case 600) ---

! Exterior wall: 9mm wood + 66mm insulation + 12mm plasterboard
Material,
    Wood_Siding_9mm,         !- Name
    MediumSmooth,            !- Roughness
    0.009,                   !- Thickness {m}
    0.14,                    !- Conductivity {W/m-K}
    530,                     !- Density {kg/m3}
    900;                     !- Specific Heat {J/kg-K}

Material,
    Insulation_66mm,         !- Name
    MediumSmooth,            !- Roughness
    0.066,                   !- Thickness {m}
    0.04,                    !- Conductivity {W/m-K}
    12,                      !- Density {kg/m3}
    840;                     !- Specific Heat {J/kg-K}

Material,
    Plasterboard_12mm,       !- Name
    MediumSmooth,            !- Roughness
    0.012,                   !- Thickness {m}
    0.16,                    !- Conductivity {W/m-K}
    950,                     !- Density {kg/m3}
    840;                     !- Specific Heat {J/kg-K}

Construction,
    Lightweight_Wall,        !- Name
    Wood_Siding_9mm,         !- Outside Layer
    Insulation_66mm,         !- Layer 2
    Plasterboard_12mm;       !- Layer 3

! Roof: 19mm wood + 112mm insulation + 10mm plasterboard
Material,
    Wood_Siding_19mm,        !- Name
    MediumSmooth,            !- Roughness
    0.019,                   !- Thickness {m}
    0.14,                    !- Conductivity {W/m-K}
    530,                     !- Density {kg/m3}
    900;                     !- Specific Heat {J/kg-K}

Material,
    Insulation_112mm,        !- Name
    MediumSmooth,            !- Roughness
    0.1118,                  !- Thickness {m}
    0.04,                    !- Conductivity {W/m-K}
    12,                      !- Density {kg/m3}
    840;                     !- Specific Heat {J/kg-K}

Material,
    Plasterboard_10mm,       !- Name
    MediumSmooth,            !- Roughness
    0.010,                   !- Thickness {m}
    0.16,                    !- Conductivity {W/m-K}
    950,                     !- Density {kg/m3}
    840;                     !- Specific Heat {J/kg-K}

Construction,
    Lightweight_Roof,        !- Name
    Wood_Siding_19mm,        !- Outside Layer
    Insulation_112mm,        !- Layer 2
    Plasterboard_10mm;       !- Layer 3

! Floor: 25mm wood + 1003mm insulation (ground-coupled)
Material,
    Floor_Insulation,        !- Name
    MediumSmooth,            !- Roughness
    1.003,                   !- Thickness {m}
    0.04,                    !- Conductivity {W/m-K}
    1,                       !- Density {kg/m3}
    1000;                    !- Specific Heat {J/kg-K}

Material,
    Floor_Wood_25mm,         !- Name
    MediumSmooth,            !- Roughness
    0.025,                   !- Thickness {m}
    0.14,                    !- Conductivity {W/m-K}
    650,                     !- Density {kg/m3}
    1200;                    !- Specific Heat {J/kg-K}

Construction,
    BESTEST_Floor,           !- Name
    Floor_Insulation,        !- Outside Layer
    Floor_Wood_25mm;         !- Layer 2

! Window (south-facing, U~3 W/m2K, SHGC typical for double-pane)
WindowMaterial:SimpleGlazingSystem,
    BESTEST_Window,          !- Name
    3.0,                     !- U-Factor {W/m2-K}
    0.787,                   !- Solar Heat Gain Coefficient
    ;                        !- Visible Transmittance

Construction,
    BESTEST_Window_Const,    !- Name
    BESTEST_Window;          !- Outside Layer

! --- Surfaces ---

! Floor (8m x 6m)
BuildingSurface:Detailed,
    BESTEST_Floor_Srf,       !- Name
    Floor,                   !- Surface Type
    BESTEST_Floor,           !- Construction Name
    BESTEST_Zone,            !- Zone Name
    ,                        !- Space Name
    Ground,                  !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    NoSun,                   !- Sun Exposure
    NoWind,                  !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, 0, 0,
    0, 6, 0,
    8, 6, 0,
    8, 0, 0;

! Ceiling/Roof
BuildingSurface:Detailed,
    BESTEST_Roof_Srf,        !- Name
    Roof,                    !- Surface Type
    Lightweight_Roof,        !- Construction Name
    BESTEST_Zone,            !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, 6, 2.7,
    0, 0, 2.7,
    8, 0, 2.7,
    8, 6, 2.7;

! South Wall (8m wide, 2.7m high, contains window)
BuildingSurface:Detailed,
    BESTEST_South_Wall,      !- Name
    Wall,                    !- Surface Type
    Lightweight_Wall,        !- Construction Name
    BESTEST_Zone,            !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    8, 0, 2.7,
    8, 0, 0,
    0, 0, 0,
    0, 0, 2.7;

FenestrationSurface:Detailed,
    BESTEST_South_Window,    !- Name
    Window,                  !- Surface Type
    BESTEST_Window_Const,    !- Construction Name
    BESTEST_South_Wall,      !- Building Surface Name
    ,                        !- Outside Boundary Condition Object
    autocalculate,           !- View Factor to Ground
    ,                        !- Frame and Divider Name
    1,                       !- Multiplier
    4,                       !- Number of Vertices
    6, 0, 2.35,
    6, 0, 0.35,
    0, 0, 0.35,
    0, 0, 2.35;

! North Wall (8m wide)
BuildingSurface:Detailed,
    BESTEST_North_Wall,      !- Name
    Wall,                    !- Surface Type
    Lightweight_Wall,        !- Construction Name
    BESTEST_Zone,            !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, 6, 2.7,
    0, 6, 0,
    8, 6, 0,
    8, 6, 2.7;

! East Wall (6m wide)
BuildingSurface:Detailed,
    BESTEST_East_Wall,       !- Name
    Wall,                    !- Surface Type
    Lightweight_Wall,        !- Construction Name
    BESTEST_Zone,            !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    8, 6, 2.7,
    8, 6, 0,
    8, 0, 0,
    8, 0, 2.7;

! West Wall (6m wide)
BuildingSurface:Detailed,
    BESTEST_West_Wall,       !- Name
    Wall,                    !- Surface Type
    Lightweight_Wall,        !- Construction Name
    BESTEST_Zone,            !- Zone Name
    ,                        !- Space Name
    Outdoors,                !- Outside Boundary Condition
    ,                        !- Outside Boundary Condition Object
    SunExposed,              !- Sun Exposure
    WindExposed,             !- Wind Exposure
    autocalculate,           !- View Factor to Ground
    4,                       !- Number of Vertices
    0, 0, 2.7,
    0, 0, 0,
    0, 6, 0,
    0, 6, 2.7;

! --- Internal Gains ---

People,
    BESTEST_People,          !- Name
    BESTEST_Zone,            !- Zone
    Occupancy Schedule,      !- Number of People Schedule Name
    People,                  !- Number of People Calculation Method
    2,                       !- Number of People
    ,                        !- People per Floor Area
    ,                        !- Floor Area per Person
    0.6,                     !- Fraction Radiant
    autocalculate,           !- Sensible Heat Fraction
    Activity Level Schedule; !- Activity Level Schedule Name

Lights,
    BESTEST_Lights,          !- Name
    BESTEST_Zone,            !- Zone
    Occupancy Schedule,      !- Schedule Name
    LightingLevel,           !- Design Level Calculation Method
    11.8,                    !- Lighting Level {W}
    ,                        !- Watts per Floor Area
    ,                        !- Watts per Person
    0,                       !- Return Air Fraction
    0.5,                     !- Fraction Radiant
    0.5,                     !- Fraction Visible
    1;                       !- Fraction Replaceable

ElectricEquipment,
    BESTEST_Equipment,       !- Name
    BESTEST_Zone,            !- Zone
    Occupancy Schedule,      !- Schedule Name
    EquipmentLevel,          !- Design Level Calculation Method
    5.4,                     !- Design Level {W}
    ,                        !- Watts per Floor Area
    ,                        !- Watts per Person
    0,                       !- Fraction Latent
    0.7,                     !- Fraction Radiant
    0;                       !- Fraction Lost

! Infiltration: 0.5 ACH
ZoneInfiltration:DesignFlowRate,
    BESTEST_Infiltration,    !- Name
    BESTEST_Zone,            !- Zone
    Always On,               !- Schedule Name
    AirChanges/Hour,         !- Design Flow Rate Calculation Method
    ,                        !- Design Flow Rate {m3/s}
    ,                        !- Flow per Zone Floor Area
    ,                        !- Flow per Exterior Surface Area
    0.5;                     !- Air Changes per Hour

! --- HVAC: IdealLoadsAirSystem ---

ZoneControl:Thermostat,
    BESTEST_Thermostat,      !- Name
    BESTEST_Zone,            !- Zone
    HVACTemplate-Always 4,   !- Control Type Schedule Name
    ThermostatSetpoint:DualSetpoint,  !- Control Object Type
    BESTEST_DualSP;          !- Control Name

ThermostatSetpoint:DualSetpoint,
    BESTEST_DualSP,          !- Name
    Heating Setpoint Schedule,  !- Heating Setpoint Temperature Schedule Name
    Cooling Setpoint Schedule;  !- Cooling Setpoint Temperature Schedule Name

ZoneHVAC:EquipmentConnections,
    BESTEST_Zone,            !- Zone Name
    BESTEST_Equipment_List,  !- Zone Conditioning Equipment List Name
    BESTEST_Supply_Inlet,    !- Zone Air Inlet Node
    ,                        !- Zone Air Exhaust Node
    BESTEST_Air_Node,        !- Zone Air Node Name
    BESTEST_Return;          !- Zone Return Air Node

ZoneHVAC:EquipmentList,
    BESTEST_Equipment_List,  !- Name
    SequentialLoad,          !- Load Distribution Scheme
    ZoneHVAC:IdealLoadsAirSystem,  !- Zone Equipment Object Type
    BESTEST_IdealLoads,      !- Zone Equipment Name
    1,                       !- Cooling Sequence
    1,                       !- Heating Sequence
    ,                        !- Sequential Cooling Fraction
    ;                        !- Sequential Heating Fraction

ZoneHVAC:IdealLoadsAirSystem,
    BESTEST_IdealLoads,      !- Name
    Always On,               !- Availability Schedule Name
    BESTEST_Supply_Inlet,    !- Zone Supply Air Node Name
    ,                        !- Zone Exhaust Air Node Name
    ,                        !- System Inlet Air Node Name
    50,                      !- Maximum Heating Supply Air Temperature [C]
    13,                      !- Minimum Cooling Supply Air Temperature [C]
    0.0156,                  !- Maximum Heating Supply Air Humidity Ratio
    0.0077,                  !- Minimum Cooling Supply Air Humidity Ratio
    NoLimit,                 !- Heating Limit
    ,                        !- Maximum Heating Air Flow Rate
    ,                        !- Maximum Sensible Heating Capacity
    NoLimit,                 !- Cooling Limit
    ,                        !- Maximum Cooling Air Flow Rate
    ,                        !- Maximum Total Cooling Capacity
    ,                        !- Heating Availability Schedule
    ,                        !- Cooling Availability Schedule
    ConstantSensibleHeatRatio,  !- Dehumidification Control Type
    0.7,                     !- Cooling Sensible Heat Ratio
    None,                    !- Humidification Control Type
    ,                        !- Design Specification Outdoor Air
    ,                        !- Outdoor Air Inlet Node
    None,                    !- Demand Controlled Ventilation
    NoEconomizer,            !- Outdoor Air Economizer
    None,                    !- Heat Recovery Type
    0.7,                     !- Sensible Heat Recovery Effectiveness
    0.65;                    !- Latent Heat Recovery Effectiveness

! --- Output Variables ---

Output:Variable,*,Zone Mean Air Temperature,Timestep;
Output:Variable,*,Zone Ideal Loads Zone Total Heating Energy,Timestep;
Output:Variable,*,Zone Ideal Loads Zone Total Cooling Energy,Timestep;

OutputControl:Table:Style,
    Comma;                   !- Column Separator

Output:Table:SummaryReports,
    AllSummary;              !- Report 1

Output:SQLite,
    SimpleAndTabular;        !- Option Type
"""


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "bestest_naive.idf"
    out.write_text(IDF_CONTENT, encoding="utf-8")
    print(f"[bestest_naive] Generated -> {out}")
    print(f"[bestest_naive] Zone: 8m x 6m x 2.7m = 48 m2, 129.6 m3")
    print(f"[bestest_naive] Windows: 12 m2 south-facing")
    print(f"[bestest_naive] Setpoints: Heat 21/15C, Cool 24/30C")
    print(f"[bestest_naive] To simulate: docker run ... energyplus -w weather.epw bestest_naive.idf")


if __name__ == "__main__":
    main()
