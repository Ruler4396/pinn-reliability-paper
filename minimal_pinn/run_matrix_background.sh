#!/usr/bin/env bash
set -euo pipefail

SPEC_PATH="$1"
OUT_DIR="$2"

mkdir -p "$OUT_DIR"
LOG="$OUT_DIR/background_run.log"
PID_FILE="$OUT_DIR/background_run.pid"
DONE_FILE="$OUT_DIR/background_run.done"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

(
  cd /root/dev/pinn-reliability-paper
  if command -v ionice >/dev/null 2>&1; then
    ionice -c3 nice -n 10 python3 -u -m minimal_pinn.run_matrix --spec "$SPEC_PATH" --output-dir "$OUT_DIR" >>"$LOG" 2>&1
  else
    nice -n 10 python3 -u -m minimal_pinn.run_matrix --spec "$SPEC_PATH" --output-dir "$OUT_DIR" >>"$LOG" 2>&1
  fi
  python3 -u -m minimal_pinn.analyze_matrix --input-csv "$OUT_DIR/matrix_summary.csv" --output-dir "$OUT_DIR/analysis" >>"$LOG" 2>&1
  touch "$DONE_FILE"
) >/dev/null 2>&1 &

echo $! > "$PID_FILE"
echo "started pid=$(cat "$PID_FILE")"
