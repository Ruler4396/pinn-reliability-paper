#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/dev/pinn-reliability-paper"
SPEC="${1:-$ROOT/minimal_pinn/configs/budget_control_v1.json}"

EXPERIMENT_NAME="$(python - <<'PY' "$SPEC"
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    spec = json.load(fh)
print(spec["experiment_name"])
PY
)"

OUT_DIR="$ROOT/minimal_pinn/results/budget_controls/$EXPERIMENT_NAME"
LOG_DIR="$OUT_DIR"
LOG_FILE="$LOG_DIR/background_run.log"
PID_FILE="$LOG_DIR/background_run.pid"
START_FILE="$LOG_DIR/background_run.started_at.txt"
DONE_FILE="$LOG_DIR/background_run.done"
FAIL_FILE="$LOG_DIR/background_run.failed"
WORKER_FILE="$LOG_DIR/background_run_worker.sh"

mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "already running: pid=$OLD_PID log=$LOG_FILE"
    exit 0
  fi
fi

cat > "$WORKER_FILE" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
rm -f "$DONE_FILE" "$FAIL_FILE"
date -Is > "$START_FILE"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export PYTHONUNBUFFERED=1
if command -v ionice >/dev/null 2>&1; then
  ionice -c3 nice -n 10 python -u -m minimal_pinn.run_budget_control --spec "$SPEC"
else
  nice -n 10 python -u -m minimal_pinn.run_budget_control --spec "$SPEC"
fi
python -u -m minimal_pinn.analyze_budget_control --input-dir "$OUT_DIR"
date -Is > "$DONE_FILE"
EOF

chmod +x "$WORKER_FILE"

if command -v setsid >/dev/null 2>&1; then
  setsid bash "$WORKER_FILE" </dev/null >> "$LOG_FILE" 2>&1 &
else
  nohup bash "$WORKER_FILE" </dev/null >> "$LOG_FILE" 2>&1 &
fi
BG_PID=$!
echo "$BG_PID" > "$PID_FILE"

echo "started"
echo "pid=$BG_PID"
echo "spec=$SPEC"
echo "out_dir=$OUT_DIR"
echo "log=$LOG_FILE"
