
import re
from pathlib import Path

def validate_idf(path):
    print(f"Checking {path}...")
    content = Path(path).read_text()
    
    # 1. Basic Syntax: Check for dangling commas before semicolons or end of objects
    # This is a bit complex for a regex, but we can check if all non-comment objects end in semicolon.
    # We'll split by bang signs and then look for semicolons.
    clean_content = re.sub(r'![^\n]*', '', content)
    objects = [obj.strip() for obj in clean_content.split(';') if obj.strip()]
    
    print(f"  - Total objects found: {len(objects)}")
    
    # 2. Check for required classes
    required_classes = [
        'Version', 'SimulationControl', 'Building', 'Timestep', 'RunPeriod',
        'GlobalGeometryRules', 'Zone', 'BuildingSurface:Detailed',
        'Material', 'Construction'
    ]
    
    found_classes = set()
    for obj in objects:
        first_word = obj.split(',')[0].strip()
        found_classes.add(first_word)
        
    missing = [c for c in required_classes if c not in found_classes]
    if missing:
        print(f"  - ❌ Missing classes: {missing}")
    else:
        print(f"  - ✅ All required core classes present.")

    # 3. Check for specific multizone zones
    zones = [obj for obj in objects if obj.startswith('Zone,')]
    print(f"  - Zones found: {len(zones)}")
    
    # 4. Check for ExternalInterface (if instrumented)
    if "ExternalInterface," in content:
        print("  - ✅ ExternalInterface found.")
        if "ExternalInterface:Schedule" in content:
            print("  - ✅ ExternalInterface:Schedule found.")
        else:
             print("  - ⚠️  ExternalInterface found but no Schedule overrides.")
    else:
        print("  - ℹ️  ExternalInterface not found (expected for raw naive model).")

    # 5. Peak check for malformed lines
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if '{{' in line or '}}' in line:
            print(f"  - ❌ RED ALERT: Unrendered Jinja template tag found at line {i+1}: {line.strip()}")
            return False
            
    print("  - ✅ No unrendered template tags found.")
    return True

if __name__ == "__main__":
    validate_idf("data/results/multizone_office_naive.idf")
    print("-" * 40)
    validate_idf("data/results/multizone_office_naive_instrumented.idf")
