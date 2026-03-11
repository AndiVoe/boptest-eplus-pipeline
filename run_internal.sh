#!/bin/bash
# MS4.3: Direct Injection Runner (run_internal.sh)
# Synchronizes code into the BopTest worker and executes the simulation loop internally.

CONTAINER="project1-boptest-worker-1"
WORKER_DIR="/worker/jobs"

echo "=== PHASE 4: INTERNAL INJECTION ==="

# 1. Create necessary directories inside container
docker exec $CONTAINER mkdir -p $WORKER_DIR/src/mpc $WORKER_DIR/src/boptest $WORKER_DIR/data/models

# 2. Copy source code and calibrated weights
docker cp src/mpc/controller.py $CONTAINER:$WORKER_DIR/src/mpc/
docker cp src/mpc/closed_loop_runner.py $CONTAINER:$WORKER_DIR/src/mpc/
docker cp data/models/rc_3r1c_template.json $CONTAINER:$WORKER_DIR/data/models/

# 3. Create dummy __init__.py for module resolution
docker exec $CONTAINER touch $WORKER_DIR/src/__init__.py
docker exec $CONTAINER touch $WORKER_DIR/src/mpc/__init__.py

# 4. Launch the simulation inside the worker (using the worker's python/pyfmi environment)
echo "Launching 48-hour MPC benchmark inside container..."
docker exec -e PYTHONPATH=$WORKER_DIR $CONTAINER . miniconda/bin/activate && conda activate pyfmi3 && python -u $WORKER_DIR/src/mpc/closed_loop_runner.py --direct --testid "benchmark_winter"
