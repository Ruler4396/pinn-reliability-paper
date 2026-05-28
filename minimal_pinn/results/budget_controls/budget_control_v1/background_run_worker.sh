#!/usr/bin/env bash
set -euo pipefail
cd "/root/dev/pinn-reliability-paper"
rm -f "/root/dev/pinn-reliability-paper/minimal_pinn/results/budget_controls/budget_control_v1/background_run.done" "/root/dev/pinn-reliability-paper/minimal_pinn/results/budget_controls/budget_control_v1/background_run.failed"
date -Is > "/root/dev/pinn-reliability-paper/minimal_pinn/results/budget_controls/budget_control_v1/background_run.started_at.txt"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export PYTHONUNBUFFERED=1
if command -v ionice >/dev/null 2>&1; then
  ionice -c3 nice -n 10 python -u -m minimal_pinn.run_budget_control --spec "/root/dev/pinn-reliability-paper/minimal_pinn/configs/budget_control_v1.json"
else
  nice -n 10 python -u -m minimal_pinn.run_budget_control --spec "/root/dev/pinn-reliability-paper/minimal_pinn/configs/budget_control_v1.json"
fi
python -u -m minimal_pinn.analyze_budget_control --input-dir "/root/dev/pinn-reliability-paper/minimal_pinn/results/budget_controls/budget_control_v1"
date -Is > "/root/dev/pinn-reliability-paper/minimal_pinn/results/budget_controls/budget_control_v1/background_run.done"
