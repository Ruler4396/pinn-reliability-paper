#!/usr/bin/env bash
set -euo pipefail
cd "/root/dev/pinn-reliability-paper"
rm -f "/root/dev/pinn-reliability-paper/minimal_pinn/results/region_aware/region_aware_compare_v3_u3/background_run.done"
date -Is > "/root/dev/pinn-reliability-paper/minimal_pinn/results/region_aware/region_aware_compare_v3_u3/background_run.started_at.txt"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export PYTHONUNBUFFERED=1
if command -v ionice >/dev/null 2>&1; then
  ionice -c3 nice -n 10 python -u -m minimal_pinn.run_region_aware_compare --spec "/root/dev/pinn-reliability-paper/minimal_pinn/configs/region_aware_compare_v3_u3.json"
else
  nice -n 10 python -u -m minimal_pinn.run_region_aware_compare --spec "/root/dev/pinn-reliability-paper/minimal_pinn/configs/region_aware_compare_v3_u3.json"
fi
date -Is > "/root/dev/pinn-reliability-paper/minimal_pinn/results/region_aware/region_aware_compare_v3_u3/background_run.done"
