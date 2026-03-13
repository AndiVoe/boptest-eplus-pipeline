import time

def simple_vav_controller(sensors, step_size=3600):
    """
    Standard Rule-Based Control (RBC) for a VAV system.
    Logic:
    - If temp > 24C, set cooling setpoint to 22C.
    - If temp < 20C, set heating setpoint to 21C.
    - Otherwise, maintain deadband.
    """
    control = {}
    
    # Generic mapping logic (to be customized per building)
    for key, val in sensors.items():
        if 'TRooAir' in key or 'TZon' in key:
            # Heating setpoint
            hea_key = key.replace('rea', 'ove').replace('TRooAir', 'TSetHea').replace('TZon', 'TSetHea')
            if val < 293.15: # 20C
                control[hea_key] = 294.15 # 21C
            else:
                control[hea_key] = 288.15 # 15C (setback)
            
            # Cooling setpoint
            coo_key = key.replace('rea', 'ove').replace('TRooAir', 'TSetCoo').replace('TZon', 'TSetCoo')
            if val > 297.15: # 24C
                control[coo_key] = 295.15 # 22C
            else:
                control[coo_key] = 303.15 # 30C (setback)
                
            # Generic activation (BopTest style)
            control[hea_key + "_activate"] = 1
            control[coo_key + "_activate"] = 1
            
    return control
