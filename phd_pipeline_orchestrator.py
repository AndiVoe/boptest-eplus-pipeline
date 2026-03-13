"""
PHD Pipeline Orchestrator
-------------------------
Automates the full chain:
1. Parse Archetype IDF -> JSON
2. Generate Naive Baseline IDF
3. Calibrate Model (SysID)
4. Run MPC Benchmark
5. Extract & Plot KPIs
"""

import argparse
import subprocess
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def run_cmd(cmd, cwd=None, env=None):
    print(f"\n{'='*60}")
    print(f">> RUNNING PHASE STEP: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    # Merge current env with provided env
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
        
    result = subprocess.run(cmd, cwd=cwd, env=full_env, capture_output=False) # stream to console
    if result.returncode != 0:
        print(f"\n❌ STEP FAILED with return code {result.returncode}")
        return False
    return True

def detect_boptest_port():
    """Tries to find which port BopTest is running on (typically 8000 or 5000)."""
    import socket
    for port in [8000, 5000]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) == 0:
                print(f"[Orchestrator] Detected BopTest on port {port}")
                return port
    print("[Orchestrator] Warning: Could not detect BopTest locally. Defaulting to 8000.")
    return 8000

def main():
    parser = argparse.ArgumentParser(description="PhD Energy Modeling & MPC Master Orchestrator")
    parser.add_argument("--idf", default="data/archetypes/Model_Thesis_MPC_Optimized.idf", help="Input archetype IDF")
    parser.add_argument("--model", default="multizone_office_simple_air", help="BopTest model name")
    parser.add_argument("--scenario", default="typical_heat_day", help="Simulation scenario")
    parser.add_argument("--skip-id", action="store_true", help="Skip System Identification phase")
    parser.add_argument("--preflight", action="store_true", help="Run Pre-Flight Sanity Check")
    args = parser.parse_args()

    port = detect_boptest_port()
    base_url = f"http://localhost:{port}"

    # Set PYTHONPATH so scripts can find src/
    env = {"PYTHONPATH": str(Path.cwd())}

    print("\n🚀 STARTING PHD PIPELINE ORCHESTRATOR")
    start_time = time.time()

    # --- PHASE 0: Diagnostics ---
    print("\n--- PHASE 0: DIAGNOSTICS & AUTO-MAPPING ---")
    if not os.path.exists("data/archetypes/mapping_template.json"):
        if not run_cmd(["python", "src/archetype/auto_mapper.py", args.idf], env=env):
            print("Warning: Auto-mapping failed. Proceeding with manual config.")
    
    if args.preflight:
        print("\n--- PHASE 0.1: PRE-FLIGHT SANITY CHECK ---")
        run_cmd(["python", "src/validation/preflight_checker.py"], env=env)

    # --- PHASE 1: MODEL EXTRACTION ---
    print("\n--- PHASE 1: MODEL EXTRACTION ---")
    
    # If a Boptest model is specified but no IDF exists, or for Category B logic:
    if args.model and (not os.path.exists(args.idf) or "multizone" in args.model):
        print(f"[Orchestrator] Using Boptest discovery for {args.model}")
        if not run_cmd(["python", "src/archetype/boptest_to_idf_params.py", args.model, "--offline"], env=env):
            return
    else:
        if not run_cmd(["python", "src/archetype/parse_archetype.py", args.idf], env=env):
            return

    if not run_cmd(["python", "src/archetype/generate_model.py"], env=env):
        return

    # --- PHASE 2: System Identification (SysID) ---
    if not args.skip_id:
        print("\n--- PHASE 2: SYSTEM CALIBRATION ---")
        # Ensure we have data for SysID if needed (simplified for now)
        if not run_cmd(["python", "system_id_multizone.py"], env=env):
            print("Warning: SysID failed or skipped. Using default parameters.")

    # --- PHASE 3: MPC Execution ---
    print(f"\n--- PHASE 3: MPC BENCHMARK ({args.model}) ---")
    if not run_cmd(["python", "-m", "src.mpc.closed_loop_runner", "--model", args.model, "--scenario", args.scenario], env=env):
        return

    # --- PHASE 4: Baseline Extraction ---
    print("\n--- PHASE 4: BASELINE COMPARISON ---")
    if not run_cmd(["python", "src/boptest/extract_baseline_kpis.py", "--url", base_url, "--hours", "48"], env=env):
        print("Warning: Baseline extraction failed. Proceeding to plotting.")

    # --- PHASE 5: Analytics & Plotting ---
    print("\n--- PHASE 5: ANALYTICS & VISUALIZATION ---")
    if not run_cmd(["python", "src/calculate_final_kpis_v2.py"], env=env):
        return
    
    plot_script = "plot_multizone.py" if "multizone" in args.model else "plot_copenhagen.py"
    run_cmd(["python", plot_script], env=env)

    total = (time.time() - start_time) / 60
    print(f"\n✨ PIPELINE COMPLETE in {total:.1f} minutes!")
    print(f"Check 'data/results/' and 'plots/' for outputs.")

if __name__ == "__main__":
    main()
