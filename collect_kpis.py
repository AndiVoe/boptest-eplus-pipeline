# collect_kpis.py
import sys
import logging
# Suppress boptest logs
logging.getLogger().setLevel(logging.CRITICAL)

sys.path.append('/worker/jobs')
import argparse
from src.mpc.closed_loop_runner import run_closed_loop

# We will patch sys.argv to run multiple times
scenarios = ['typical_heat_day', 'typical_cool_day', 'mix_day']

# To avoid prints from run_closed_loop cluttering, we could redirect stdout,
# but it's fine, we'll just grep the final summary or rely on clean output.
import contextlib
import io

results = {}

for s in scenarios:
    print(f"\n--- RUNNING SCENARIO: {s} ---")
    sys.argv = ['closed_loop_runner.py', '--direct', '--scenario', s]
    
    # Capture stdout to avoid spam
    f = io.StringIO()
    try:
        with contextlib.redirect_stdout(f):
            run_closed_loop()
        output = f.getvalue()
        # Find the KPI block
        if "Evaluating KPIs..." in output:
            lines = output.split("Evaluating KPIs...")[1].strip().split('\n')
            for line in lines[:10]:
                print(line)
        else:
            print("Failed to find KPIs in output.")
            print(output[-500:])
    except Exception as e:
        print(f"Error running {s}: {e}")
