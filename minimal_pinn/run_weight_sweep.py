from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .matrix_specs import build_run_config
from .trainer import run_training


def make_tag(obs: int, noise: float, seed: int) -> str:
    noise_pct = int(round(noise * 1000))
    return f"obs{obs}_noise{noise_pct:03d}_seed{seed}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weight sweep experiments.")
    parser.add_argument("--spec", required=True, help="Path to weight sweep spec JSON.")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    with Path(args.spec).open("r", encoding="utf-8") as fh:
        spec = json.load(fh)

    base_dir = Path(__file__).resolve().parent
    sweep_name = spec["sweep_name"]
    output_dir = Path(args.output_dir) if args.output_dir else base_dir / "results" / sweep_name
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    seeds = [int(s) for s in spec["seeds"]]
    epochs = int(spec["epochs"])
    weight_configs = spec["weight_configs"]

    rows: List[Dict[str, Any]] = []

    for case_spec in spec["cases"]:
        case_name = case_spec["case"]
        case_kwargs = case_spec.get("case_kwargs", {})
        for cond in case_spec["conditions"]:
            label = cond["label"]
            num_obs = int(cond["num_observation"])
            noise = float(cond["noise_std"])
            for w_name, w_vals in weight_configs.items():
                for seed in seeds:
                    overrides = {}
                    if case_kwargs:
                        overrides["case"] = case_kwargs
                    config = build_run_config(case_name, num_obs, noise, overrides=overrides)
                    config["training"]["epochs"] = epochs
                    config["training"]["weights"] = {
                        "data": float(w_vals["data"]),
                        "physics": float(w_vals["physics"]),
                        "boundary": float(w_vals["boundary"]),
                    }
                    config["seed"] = seed
                    run_name = f"{case_name}_{w_name}_{label}_{make_tag(num_obs, noise, seed)}"
                    config["run_name"] = run_name
                    run_dir = runs_dir / run_name

                    print(
                        f"[run] case={case_name} w={w_name} cond={label} "
                        f"obs={num_obs} noise={noise} seed={seed}",
                        flush=True,
                    )
                    metrics = run_training(config, run_dir)
                    scalar = metrics["scalar_metrics"]
                    rows.append({
                        "sweep_name": sweep_name,
                        "case": case_name,
                        "weight_config": w_name,
                        "label": label,
                        "num_observation": num_obs,
                        "noise_std": noise,
                        "seed": seed,
                        "run_name": run_name,
                        "data_w": float(w_vals["data"]),
                        "physics_w": float(w_vals["physics"]),
                        "boundary_w": float(w_vals["boundary"]),
                        "rel_l2": scalar["rel_l2"],
                        "physics_rms": scalar["physics_rms"],
                        "boundary_rms": scalar["boundary_rms"],
                        "structure_error": scalar["structure_error"],
                        "loss_std": scalar["loss_std"],
                        "loss_ratio": scalar["loss_ratio"],
                        "reliability_raw": metrics["reliability"]["reliability_raw"],
                    })

    fields = list(rows[0].keys())
    with (output_dir / "weight_sweep_runs.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "weight_sweep_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")


if __name__ == "__main__":
    main()
