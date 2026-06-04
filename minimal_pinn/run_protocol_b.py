from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ensure_defaults
from .trainer import run_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Protocol B experiments.")
    parser.add_argument("--spec", required=True, help="Path to protocol spec JSON.")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    with Path(args.spec).open("r", encoding="utf-8") as fh:
        spec = json.load(fh)

    base_dir = Path(__file__).resolve().parent
    protocol_name = spec["protocol_name"]
    output_dir = Path(args.output_dir) if args.output_dir else base_dir / "results" / protocol_name
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    proto = spec["protocol"]
    seeds = [int(s) for s in spec["seeds"]]
    rows: List[Dict[str, Any]] = []

    for exp in spec["experiments"]:
        case_name = exp["case"]
        case_kwargs = exp.get("case_kwargs", {})
        num_obs = int(exp.get("num_observation", 256))
        noise = float(exp.get("noise_std", 0.0))
        num_eval = int(exp.get("num_eval", 51))

        for seed in seeds:
            config: Dict[str, Any] = {
                "case": {"name": case_name, **case_kwargs},
                "seed": seed,
                "network": {
                    "hidden_layers": list(proto["hidden_layers"]),
                    "activation": proto["activation"],
                },
                "training": {
                    "epochs": int(proto["epochs"]),
                    "lr": float(proto["lr"]),
                    "print_every": int(proto["print_every"]),
                    "weights": dict(proto["weights"]),
                },
                "data": {
                    "num_observation": num_obs,
                    "num_collocation": int(proto["num_collocation"]),
                    "num_boundary": 256,
                    "num_eval": num_eval,
                    "noise_std": noise,
                },
                "reliability": {},
            }
            if "lr_schedule" in proto:
                config["training"]["lr_schedule"] = dict(proto["lr_schedule"])
            config = ensure_defaults(config)
            config["run_name"] = f"{case_name}_{protocol_name}_seed{seed}"
            run_dir = runs_dir / config["run_name"]

            print(f"[run] case={case_name} seed={seed}", flush=True)
            metrics = run_training(config, run_dir)
            scalar = metrics["scalar_metrics"]
            rows.append({
                "protocol": protocol_name,
                "case": case_name,
                "seed": seed,
                "run_name": config["run_name"],
                "activation": proto["activation"],
                "hidden_layers": str(proto["hidden_layers"]),
                "epochs": int(proto["epochs"]),
                "num_collocation": int(proto["num_collocation"]),
                "rel_l2": scalar["rel_l2"],
                "physics_rms": scalar["physics_rms"],
                "boundary_rms": scalar["boundary_rms"],
                "structure_error": scalar["structure_error"],
                "loss_std": scalar["loss_std"],
                "loss_ratio": scalar["loss_ratio"],
                "reliability_raw": metrics["reliability"]["reliability_raw"],
            })

    if rows:
        fields = list(rows[0].keys())
        with (output_dir / "protocol_b_runs.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    with (output_dir / "protocol_b_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")


if __name__ == "__main__":
    main()
