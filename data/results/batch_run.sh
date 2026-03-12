#!/bin/bash
for s in typical_heat_day typical_cool_day mix_day
do
    echo "--- STARTING $s ---"
    /worker/jobs/launch_internal.sh --scenario $s | grep -A 5 "MPC Loop Finished"
done
