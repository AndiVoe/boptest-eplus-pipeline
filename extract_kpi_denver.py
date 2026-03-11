import re

with open('/boptest/lib/kpis/kpi_calculator.py', 'r') as f:
    content = f.read()

match = re.search(r'def get_energy\(self\):.*?(?=def |\Z)', content, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Method get_energy not found")
