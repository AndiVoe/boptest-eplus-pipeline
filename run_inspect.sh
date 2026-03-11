#!/bin/bash
. /miniconda/bin/activate
conda activate pyfmi3
export PYTHONPATH=/worker/jobs:/:/boptest:/boptest/lib
python /worker/jobs/extract_kpi.py
