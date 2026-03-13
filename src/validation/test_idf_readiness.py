import sys
import os
import re
from pathlib import Path

# Ensure stdout handles UTF-8 for printing special characters in IDFs
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class IDFReadinessAudit:
    def __init__(self, idf_path):
        self.idf_path = Path(idf_path)
        self.content = self.idf_path.read_text(encoding='utf-8', errors='ignore')
        self.clean_content = re.sub(r'![^\n]*', '', self.content)
        self.objects = [o.strip() for o in self.clean_content.split(';') if o.strip()]
        self.report = []
        self.errors = 0

    def log(self, msg, level="INFO"):
        prefix = {"INFO": "ℹ️ ", "ERROR": "❌", "SUCCESS": "✅", "WARNING": "⚠️ "}.get(level, "")
        if level == "ERROR": self.errors += 1
        self.report.append(f"{prefix} {msg}")

    def get_object_by_class(self, class_name):
        # Handle cases like 'Zone ,' or 'Zone\n,'
        pattern = re.compile(rf"^{re.escape(class_name)}\s*,", re.IGNORECASE)
        return [obj for obj in self.objects if pattern.match(obj)]

    def run_audit(self):
        print(f"\n🚀 Running Readiness Audit for: {self.idf_path.name}")
        
        # 1. Version Check
        versions = self.get_object_by_class("Version")
        if versions:
            v_num = versions[0].split(',')[1].strip()
            self.log(f"EnergyPlus Version: {v_num}", "SUCCESS")
        else:
            self.log("No Version object found.", "ERROR")

        # 2. Material/Construction Integrity
        materials = set()
        for m_class in ["Material", "Material:NoMass", "WindowMaterial:SimpleGlazingSystem"]:
            for obj in self.get_object_by_class(m_class):
                materials.add(obj.split(',')[1].strip())
        
        constructions = self.get_object_by_class("Construction")
        for const in constructions:
            fields = [f.strip() for f in const.split(',')]
            c_name = fields[1]
            layers = fields[2:]
            for layer in layers:
                if layer and layer not in materials:
                    self.log(f"Construction '{c_name}' references missing material '{layer}'", "ERROR")
        
        if constructions:
            self.log(f"Verified {len(constructions)} constructions and {len(materials)} materials.", "SUCCESS")

        # 3. Zone and Surface Checks
        zones = [obj.split(',')[1].strip() for obj in self.get_object_by_class("Zone")]
        surfaces = self.get_object_by_class("BuildingSurface:Detailed")
        
        for surf in surfaces:
            fields = [f.strip() for f in surf.split(',')]
            s_name = fields[1]
            z_ref = fields[4]
            if z_ref not in zones:
                self.log(f"Surface '{s_name}' references missing zone '{z_ref}'", "ERROR")
        
        if zones:
             self.log(f"Verified {len(zones)} zones and {len(surfaces)} surfaces.", "SUCCESS")

        # 4. Thermal Control (Thermostats)
        t_controls = self.get_object_by_class("ZoneControl:Thermostat")
        t_zones = [obj.split(',')[2].strip() for obj in t_controls]
        for z in zones:
            if z not in t_zones:
                self.log(f"Zone '{z}' has no ZoneControl:Thermostat associated.", "WARNING")
        
        if t_controls:
            self.log(f"Verified {len(t_controls)} thermostat associations.", "SUCCESS")

        # 5. Co-Simulation Readiness (ExternalInterface)
        ei = self.get_object_by_class("ExternalInterface")
        if ei:
            self.log("ExternalInterface found. Building is configured for co-simulation.", "SUCCESS")
            vars = self.get_object_by_class("ExternalInterface:Variable")
            acts = self.get_object_by_class("ExternalInterface:Actuator")
            schs = self.get_object_by_class("ExternalInterface:Schedule")
            self.log(f"Found {len(vars)} sensor hooks, {len(acts)} actuator hooks, and {len(schs)} schedule overrides.", "INFO")
        else:
            self.log("No ExternalInterface found. Building is isolated (not Boptest-ready).", "WARNING")

    def print_report(self):
        for line in self.report:
            print(line)
        if self.errors == 0:
            print(f"\n✨ SUMMARY: Model is Simulation-Ready!")
        else:
            print(f"\n🛑 SUMMARY: Found {self.errors} errors. Fixing required before running EnergyPlus.")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/results/multizone_office_naive_instrumented.idf"
    audit = IDFReadinessAudit(path)
    audit.run_audit()
    audit.print_report()
