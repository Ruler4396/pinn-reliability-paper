from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ensure_defaults, load_config
from .trainer import run_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small protocol sweep.")
    parser.add_argument("--spec", required=True, help="Path to sweep spec JSON.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory.")
    args = parser.parse_args()

    spec = load_config(args.spec)
    base_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else base_dir / "results" / "protocol_sweeps" / str(spec["suite_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for exp in spec["experiments"]:
        label = str(exp["label"])
        config = ensure_defaults(exp["config"])
        config["run_name"] = str(config["run_name"])
        run_dir = runs_dir / config["run_name"]
        print(f"[run] sweep={spec['suite_name']} label={label}", flush=True)
        metrics = run_training(config, run_dir)
        rows.append(
            {
                "label": label,
                "run_name": config["run_name"],
                "case": config["case"]["name"],
                "activation": config["network"]["activation"],
                "hidden_layers": "-".join(str(x) for x in config["network"]["hidden_layers"]),
                "epochs": config["training"]["epochs"],
                "num_observation": config["data"]["num_observation"],
                "num_collocation": config["data"]["num_collocation"],
                "num_boundary": config["data"]["num_boundary"],
                "rel_l2": metrics["scalar_metrics"]["rel_l2"],
                "physics_rms": metrics["scalar_metrics"]["physics_rms"],
                "boundary_rms": metrics["scalar_metrics"]["boundary_rms"],
                "structure_error": metrics["scalar_metrics"]["structure_error"],
                "reliability_raw": metrics["reliability"]["reliability_raw"],
            }
        )

    with (output_dir / "sweep_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    with (output_dir / "sweep_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "label",
                "run_name",
                "case",
                "activation",
                "hidden_layers",
                "epochs",
                "num_observation",
                "num_collocation",
                "num_boundary",
                "rel_l2",
                "physics_rms",
                "boundary_rms",
                "structure_error",
                "reliability_raw",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] output_dir={output_dir}")


if __name__ == "__main__":
    main()
