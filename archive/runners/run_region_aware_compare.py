from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List

from .matrix_specs import build_run_config, load_matrix_spec, merge_dict
from .reliability import build_reliability_summary
from .trainer import run_training


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare baseline and region-aware training on critical runs.")
    parser.add_argument("--spec", required=True, help="Path to the region-aware comparison spec.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to minimal_pinn/results/region_aware/<compare_name>.",
    )
    args = parser.parse_args()

    spec = load_matrix_spec(args.spec)
    root = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else root / "results" / "region_aware" / str(spec["compare_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    recal_summary = load_json(root / "results" / "analysis" / "recalibrated_dimensions_v1" / "recalibrated_summary.json")

    rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for experiment in spec["experiments"]:
        case_name = str(experiment["case"])
        label = str(experiment["label"])
        num_observation = int(experiment["num_observation"])
        noise_std = float(experiment["noise_std"])
        seeds = [int(seed) for seed in experiment["seeds"]]
        base_overrides = experiment.get("overrides", {})
        strategy_overrides = experiment["strategies"]
        recal_thresholds = recal_summary[case_name]["thresholds"]

        for strategy_name, strategy_cfg in strategy_overrides.items():
            strategy_rows: List[Dict[str, Any]] = []
            for seed in seeds:
                run_config = build_run_config(
                    case_name=case_name,
                    num_observation=num_observation,
                    noise_std=noise_std,
                    overrides=base_overrides,
                )
                merge_dict(run_config, strategy_cfg)
                run_config["seed"] = seed
                run_name = f"{case_name}_{spec['compare_name']}_{label}_{strategy_name}_seed{seed}"
                run_config["run_name"] = run_name

                print(
                    f"[run] compare={spec['compare_name']} case={case_name} label={label} "
                    f"strategy={strategy_name} seed={seed}",
                    flush=True,
                )
                metrics = run_training(run_config, runs_dir / run_name)
                scalar = metrics["scalar_metrics"]
                recal = build_reliability_summary(scalar, recal_thresholds)
                row = {
                    "compare_name": spec["compare_name"],
                    "case": case_name,
                    "label": label,
                    "strategy": strategy_name,
                    "seed": seed,
                    "num_observation": num_observation,
                    "noise_std": noise_std,
                    "run_name": run_name,
                    "rel_l2": float(scalar["rel_l2"]),
                    "reliability_raw_recal": float(recal["reliability_raw"]),
                    "physics_consistency_recal": float(recal["dimension_scores"]["physics_consistency"]),
                    "training_stability_recal": float(recal["dimension_scores"]["training_stability"]),
                    "numerical_accuracy_recal": float(recal["dimension_scores"]["numerical_accuracy"]),
                    "structural_stability_recal": float(recal["dimension_scores"]["structural_stability"]),
                    "physics_rms": float(scalar["physics_rms"]),
                    "boundary_rms": float(scalar["boundary_rms"]),
                    "structure_error": float(scalar["structure_error"]),
                    "loss_std": float(scalar["loss_std"]),
                    "loss_ratio": float(scalar["loss_ratio"]),
                }
                rows.append(row)
                strategy_rows.append(row)

            summary_rows.append(
                {
                    "case": case_name,
                    "label": label,
                    "strategy": strategy_name,
                    "n_seed": len(strategy_rows),
                    "rel_l2_mean": statistics.mean(row["rel_l2"] for row in strategy_rows),
                    "rel_l2_std": statistics.pstdev(row["rel_l2"] for row in strategy_rows),
                    "reliability_raw_recal_mean": statistics.mean(row["reliability_raw_recal"] for row in strategy_rows),
                    "reliability_raw_recal_std": statistics.pstdev(row["reliability_raw_recal"] for row in strategy_rows),
                    "physics_consistency_recal_mean": statistics.mean(row["physics_consistency_recal"] for row in strategy_rows),
                    "training_stability_recal_mean": statistics.mean(row["training_stability_recal"] for row in strategy_rows),
                    "numerical_accuracy_recal_mean": statistics.mean(row["numerical_accuracy_recal"] for row in strategy_rows),
                    "structural_stability_recal_mean": statistics.mean(row["structural_stability_recal"] for row in strategy_rows),
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "comparison_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    with (output_dir / "run_metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "compare_name",
                "case",
                "label",
                "strategy",
                "seed",
                "num_observation",
                "noise_std",
                "run_name",
                "rel_l2",
                "reliability_raw_recal",
                "physics_consistency_recal",
                "training_stability_recal",
                "numerical_accuracy_recal",
                "structural_stability_recal",
                "physics_rms",
                "boundary_rms",
                "structure_error",
                "loss_std",
                "loss_ratio",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "strategy_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "case",
                "label",
                "strategy",
                "n_seed",
                "rel_l2_mean",
                "rel_l2_std",
                "reliability_raw_recal_mean",
                "reliability_raw_recal_std",
                "physics_consistency_recal_mean",
                "training_stability_recal_mean",
                "numerical_accuracy_recal_mean",
                "structural_stability_recal_mean",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    by_case_label: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in summary_rows:
        key = f"{row['case']}::{row['label']}"
        by_case_label.setdefault(key, {})[row["strategy"]] = row

    comparisons: Dict[str, Any] = {}
    for key, strategies in by_case_label.items():
        if "baseline" not in strategies:
            continue
        base = strategies["baseline"]
        comparisons[key] = {"baseline": base}
        for strategy_name, strategy_summary in strategies.items():
            if strategy_name == "baseline":
                continue
            comparisons[key][strategy_name] = strategy_summary
            comparisons[key][f"{strategy_name}_delta"] = {
                "delta_rel_l2_mean": float(strategy_summary["rel_l2_mean"] - base["rel_l2_mean"]),
                "delta_reliability_raw_recal_mean": float(
                    strategy_summary["reliability_raw_recal_mean"] - base["reliability_raw_recal_mean"]
                ),
                "delta_physics_consistency_recal_mean": float(
                    strategy_summary["physics_consistency_recal_mean"] - base["physics_consistency_recal_mean"]
                ),
                "delta_training_stability_recal_mean": float(
                    strategy_summary["training_stability_recal_mean"] - base["training_stability_recal_mean"]
                ),
                "delta_numerical_accuracy_recal_mean": float(
                    strategy_summary["numerical_accuracy_recal_mean"] - base["numerical_accuracy_recal_mean"]
                ),
                "delta_structural_stability_recal_mean": float(
                    strategy_summary["structural_stability_recal_mean"] - base["structural_stability_recal_mean"]
                ),
            }

    with (output_dir / "comparison_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(comparisons, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")
    print(json.dumps(comparisons, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
