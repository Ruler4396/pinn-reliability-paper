from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .matrix_specs import build_run_config, load_matrix_spec
from .trainer import run_training


def make_run_name(case_name: str, point_label: str, budget_name: str, seed: int) -> str:
    return f"{case_name}_{point_label}_{budget_name}_seed{seed}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run targeted protocol-budget control experiments.")
    parser.add_argument("--spec", required=True, help="Path to a budget-control JSON spec.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to minimal_pinn/results/budget_controls/<name>.",
    )
    args = parser.parse_args()

    spec = load_matrix_spec(args.spec)
    root = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else root / "results" / "budget_controls" / str(spec["experiment_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    seeds = [int(seed) for seed in spec["seeds"]]
    for case_spec in spec["cases"]:
        case_name = str(case_spec["case"])
        threshold_rel_l2 = float(case_spec["threshold_rel_l2"])
        for point in case_spec["points"]:
            label = str(point["label"])
            num_observation = int(point["num_observation"])
            noise_std = float(point["noise_std"])
            for budget in spec["budgets"]:
                budget_name = str(budget["name"])
                overrides = budget.get("overrides", {})
                for seed in seeds:
                    config = build_run_config(
                        case_name=case_name,
                        num_observation=num_observation,
                        noise_std=noise_std,
                        overrides=overrides,
                    )
                    config["seed"] = seed
                    run_name = make_run_name(case_name, label, budget_name, seed)
                    config["run_name"] = run_name
                    print(
                        f"[run] case={case_name} label={label} budget={budget_name} "
                        f"obs={num_observation} noise={noise_std} seed={seed}",
                        flush=True,
                    )
                    metrics = run_training(config=config, output_dir=runs_dir / run_name)
                    scalar = metrics["scalar_metrics"]
                    reliability = metrics["reliability"]
                    row = {
                        "experiment_name": spec["experiment_name"],
                        "case": case_name,
                        "label": label,
                        "budget_name": budget_name,
                        "num_observation": num_observation,
                        "noise_std": noise_std,
                        "seed": seed,
                        "run_name": run_name,
                        "epochs": int(config["training"]["epochs"]),
                        "num_collocation": int(config["data"]["num_collocation"]),
                        "num_boundary": int(config["data"]["num_boundary"]),
                        "rel_l2": float(scalar["rel_l2"]),
                        "reliability_raw": float(reliability["reliability_raw"]),
                        "physics_rms": float(scalar["physics_rms"]),
                        "boundary_rms": float(scalar["boundary_rms"]),
                        "structure_error": float(scalar["structure_error"]),
                        "loss_std": float(scalar["loss_std"]),
                        "loss_ratio": float(scalar["loss_ratio"]),
                        "physics_consistency": float(reliability["dimension_scores"]["physics_consistency"]),
                        "training_stability": float(reliability["dimension_scores"]["training_stability"]),
                        "numerical_accuracy": float(reliability["dimension_scores"]["numerical_accuracy"]),
                        "structural_stability": float(reliability["dimension_scores"]["structural_stability"]),
                        "threshold_rel_l2": threshold_rel_l2,
                        "crosses_threshold": int(float(scalar["rel_l2"]) >= threshold_rel_l2),
                    }
                    rows.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "experiment_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    fieldnames = [
        "experiment_name",
        "case",
        "label",
        "budget_name",
        "num_observation",
        "noise_std",
        "seed",
        "run_name",
        "epochs",
        "num_collocation",
        "num_boundary",
        "rel_l2",
        "reliability_raw",
        "physics_rms",
        "boundary_rms",
        "structure_error",
        "loss_std",
        "loss_ratio",
        "physics_consistency",
        "training_stability",
        "numerical_accuracy",
        "structural_stability",
        "threshold_rel_l2",
        "crosses_threshold",
    ]
    with (output_dir / "budget_control_runs.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] output_dir={output_dir}")


if __name__ == "__main__":
    main()
