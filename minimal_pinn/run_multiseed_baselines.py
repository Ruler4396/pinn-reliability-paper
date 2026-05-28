from __future__ import annotations

import argparse
import csv
import json
import statistics
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from .config import ensure_defaults, load_config
from .trainer import run_training


SCALAR_KEYS = [
    "rel_l2",
    "physics_rms",
    "boundary_rms",
    "structure_error",
    "loss_std",
    "loss_ratio",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run clean baseline configs across multiple random seeds.")
    parser.add_argument("--configs", nargs="+", required=True, help="Baseline config JSON files.")
    parser.add_argument("--seeds", nargs="+", type=int, required=True, help="Random seeds to run.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to minimal_pinn/results/baseline_multiseed_v1.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else base_dir / "results" / "baseline_multiseed_v1"
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for config_path in args.configs:
        cfg = ensure_defaults(load_config(config_path))
        case_name = str(cfg["case"]["name"])
        base_run_name = str(cfg["run_name"])
        case_runs: List[Dict[str, Any]] = []
        for seed in args.seeds:
            run_cfg = deepcopy(cfg)
            run_cfg["seed"] = int(seed)
            run_cfg["run_name"] = f"{base_run_name}_seed{seed}"
            run_output_dir = runs_dir / run_cfg["run_name"]
            print(f"[run] case={case_name} seed={seed}", flush=True)
            metrics = run_training(config=run_cfg, output_dir=run_output_dir)
            scalar = metrics["scalar_metrics"]
            row: Dict[str, Any] = {
                "case": case_name,
                "config_path": str(Path(config_path).resolve()),
                "seed": int(seed),
                "run_name": run_cfg["run_name"],
                "reliability_raw": metrics["reliability"]["reliability_raw"],
            }
            for key in SCALAR_KEYS:
                row[key] = float(scalar[key])
            run_rows.append(row)
            case_runs.append(row)

        n = len(case_runs)
        summary: Dict[str, Any] = {
            "case": case_name,
            "config_path": str(Path(config_path).resolve()),
            "n_seed": n,
        }
        for key in SCALAR_KEYS + ["reliability_raw"]:
            values = [float(r[key]) for r in case_runs]
            summary[f"{key}_mean"] = statistics.mean(values)
            summary[f"{key}_std"] = statistics.stdev(values) if n > 1 else 0.0
            summary[f"{key}_min"] = min(values)
            summary[f"{key}_max"] = max(values)
        summary_rows.append(summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "run_rows.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(run_rows[0].keys()))
        writer.writeheader()
        writer.writerows(run_rows)

    with (output_dir / "summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    summary_json = {
        "seeds": [int(v) for v in args.seeds],
        "configs": [str(Path(v).resolve()) for v in args.configs],
        "summary_rows": summary_rows,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
