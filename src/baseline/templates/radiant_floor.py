def radiant_floor_controller(sensors, step_size=3600):
    """
    Standard Rule-Based Control (RBC) for a Radiant Floor system.
    Logic:
    - Heating focused (typical for radiant floors).
    - If indoor temp < 19C, set floor water temp to 35C.
    - If indoor temp > 21C, set floor water temp to 20C (off).
    """
    control = {}
    
    for key, val in sensors.items():
        if 'TRooAir' in key or 'TZon' in key:
            # Floor heating water setpoint
            # Mapping assumption: reaTRooAir_Room1 -> oveTSetFlo_Room1
            flo_key = key.replace('rea', 'ove').replace('TRooAir', 'TSetFlo').replace('TZon', 'TSetFlo')
            
            if val < 292.15: # 19C
                control[flo_key] = 308.15 # 35C
            elif val > 294.15: # 21C
                control[flo_key] = 293.15 # 20C
            else:
                pass # Maintain previous or default
            
            control[flo_key + "_activate"] = 1
            
    return control
