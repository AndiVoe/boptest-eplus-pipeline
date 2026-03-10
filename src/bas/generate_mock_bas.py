import pandas as pd
from pathlib import Path

def generate_mock_bas_point_list(output_path: Path):
    """
    Generates a realistic BAS point list for a commercial building.
    This list maps data points (sensors, setpoints, commands) to equipment (AHUs, VAVs, Chiller, Boiler).
    """
    points = []
    
    # 1. Air Handling Unit (AHU-1)
    ahu_points = [
        ("AHU1.DAT", "AHU-1", "Discharge Air Temperature", "Sensor", "degC", "Analog Input"),
        ("AHU1.RAT", "AHU-1", "Return Air Temperature", "Sensor", "degC", "Analog Input"),
        ("AHU1.OAT", "AHU-1", "Outside Air Temperature", "Sensor", "degC", "Analog Input"),
        ("AHU1.SAF.SPD", "AHU-1", "Supply Air Fan Speed", "Command", "percent", "Analog Output"),
        ("AHU1.SAF.STS", "AHU-1", "Supply Air Fan Status", "Status", "On/Off", "Binary Input"),
        ("AHU1.HC.VLV", "AHU-1", "Heating Coil Valve Position", "Command", "percent", "Analog Output"),
        ("AHU1.CC.VLV", "AHU-1", "Cooling Coil Valve Position", "Command", "percent", "Analog Output"),
        ("AHU1.OAD", "AHU-1", "Outside Air Damper Position", "Command", "percent", "Analog Output"),
    ]
    points.extend(ahu_points)

    # 2. VAV Boxes (VAV-101 to VAV-105)
    for i in range(101, 106):
        vav_id = f"VAV-{i}"
        vav_points = [
            (f"{vav_id}.ZNT", vav_id, "Zone Temperature", "Sensor", "degC", "Analog Input"),
            (f"{vav_id}.ZNT_SP", vav_id, "Zone Temperature Setpoint", "Setpoint", "degC", "Analog Value"),
            (f"{vav_id}.DMP", vav_id, "Damper Position", "Command", "percent", "Analog Output"),
            (f"{vav_id}.FLO", vav_id, "Discharge Airflow", "Sensor", "L/s", "Analog Input"),
            (f"{vav_id}.FLO_SP", vav_id, "Airflow Setpoint", "Setpoint", "L/s", "Analog Value"),
            (f"{vav_id}.RHC", vav_id, "Reheat Valve Position", "Command", "percent", "Analog Output"),
        ]
        points.extend(vav_points)

    # 3. Chilled Water Plant
    chw_points = [
        ("CHW.S.T", "CHW_Plant", "Chilled Water Supply Temp", "Sensor", "degC", "Analog Input"),
        ("CHW.R.T", "CHW_Plant", "Chilled Water Return Temp", "Sensor", "degC", "Analog Input"),
        ("CHIL1.STS", "Chiller-1", "Chiller Status", "Status", "On/Off", "Binary Input"),
        ("CHWP1.STS", "CHW_Pump-1", "Chilled Water Pump Status", "Status", "On/Off", "Binary Input"),
    ]
    points.extend(chw_points)

    # 4. Hot Water Plant
    hw_points = [
        ("HW.S.T", "HW_Plant", "Hot Water Supply Temp", "Sensor", "degC", "Analog Input"),
        ("HW.R.T", "HW_Plant", "Hot Water Return Temp", "Sensor", "degC", "Analog Input"),
        ("BOIL1.STS", "Boiler-1", "Boiler Status", "Status", "On/Off", "Binary Input"),
        ("HWP1.STS", "HW_Pump-1", "Hot Water Pump Status", "Status", "On/Off", "Binary Input"),
    ]
    points.extend(hw_points)
    
    # 5. Electric Meters
    meter_points = [
        ("BLDG.ELEC.KW", "Building", "Total Electric Power", "Sensor", "kW", "Analog Input"),
        ("HVAC.ELEC.KW", "Building", "HVAC Electric Power", "Sensor", "kW", "Analog Input"),
    ]
    points.extend(meter_points)

    # Create DataFrame
    df = pd.DataFrame(points, columns=[
        "Point_Name", "Equipment_ID", "Description", "Point_Class", "Unit", "BACnet_Type"
    ])
    
    # Save to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated mock BAS point list with {len(df)} points at {output_path}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    out_path = project_root / "data" / "bas" / "mock_point_list.csv"
    generate_mock_bas_point_list(out_path)
