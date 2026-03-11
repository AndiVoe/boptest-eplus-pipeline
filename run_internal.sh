#!/bin/bash
# MS4.3: Direct Injection Runner (run_internal.sh)
# Synchronizes code into the BopTest worker and executes the simulation loop internally.

CONTAINER="project1-boptest-worker-1"
WORKER_DIR="/worker/jobs"
MODEL=${1:-"bestest_air"}
SCENARIO=$2

echo "=== PHASE 6: INTERNAL INJECTION [MODEL: $MODEL] ==="

# 1. Create necessary directories inside container
docker exec $CONTAINER mkdir -p $WORKER_DIR/src/mpc $WORKER_DIR/src/boptest $WORKER_DIR/data/models $WORKER_DIR/models

# 2. Copy source code and calibrated weights
docker cp src/mpc/controller.py $CONTAINER:$WORKER_DIR/src/mpc/
docker cp src/mpc/closed_loop_runner.py $CONTAINER:$WORKER_DIR/src/mpc/
docker cp data/models/rc_3r1c_template.json $CONTAINER:$WORKER_DIR/data/models/

# 3. Copy specialized FMUs if needed (Copenhagen)
if [ "$MODEL" == "singlezone_commercial_hydronic" ]; then
    echo "Copying Copenhagen FMU..."
    docker cp ../project1-boptest/testcases/singlezone_commercial_hydronic/models/wrapped.fmu $CONTAINER:$WORKER_DIR/models/singlezone_commercial_hydronic.fmu
fi

# 4. Create dummy __init__.py for module resolution
docker exec $CONTAINER touch $WORKER_DIR/src/__init__.py
docker exec $CONTAINER touch $WORKER_DIR/src/mpc/__init__.py

# 5. Launch the simulation inside the worker
echo "Launching MPC benchmark inside container..."
CMD="python -u $WORKER_DIR/src/mpc/closed_loop_runner.py --direct --model $MODEL"
if [ ! -z "$SCENARIO" ]; then
    CMD="$CMD --scenario $SCENARIO"
fi

docker exec -e PYTHONPATH=$WORKER_DIR $CONTAINER /miniconda/bin/conda run -n pyfmi3 $CMD
