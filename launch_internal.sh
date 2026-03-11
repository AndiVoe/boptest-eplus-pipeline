#!/bin/bash
export PYTHONPATH=/worker/jobs:/:/boptest:/boptest/lib
cd /worker/jobs
/miniconda/bin/conda run -n pyfmi3 python -u /worker/jobs/src/mpc/closed_loop_runner.py --direct "$@"
