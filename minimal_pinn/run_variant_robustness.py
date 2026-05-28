from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from .matrix_specs import build_run_config, load_matrix_spec, merge_dict
from .reliability import build_reliability_summary
from .trainer import run_training


def load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_case_thresholds(path: str | Path, case_name: str) -> Dict[str, Dict[str, float | str]]:
    data = load_json(path)
    return data[case_name]["thresholds"]


def case_threshold_rel_l2(path: str | Path, case_name: str) -> float:
    table_path = Path(path)
    import pandas as pd

    df = pd.read_csv(table_path)
    return float(df["threshold_rel_l2"].iloc[0])


def run_one(
    suite_name: str,
    runs_dir: Path,
    case_name: str,
    label: str,
    variant_name: str,
    variant_overrides: Dict[str, Any],
    seed: int,
    num_observation: int,
    noise_std: float,
    base_overrides: Dict[str, Any],
    recal_thresholds: Dict[str, Dict[str, float | str]],
    threshold_rel_l2: float,
    strategy_name: str | None = None,
    strategy_overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    config = build_run_config(
        case_name=case_name,
        num_observation=num_observation,
        noise_std=noise_std,
        overrides=base_overrides,
    )
    merge_dict(config, variant_overrides)
    if strategy_overrides:
        merge_dict(config, strategy_overrides)
    config["seed"] = seed

    tag_parts = [case_name, suite_name, label, variant_name]
    if strategy_name is not None:
        tag_parts.append(strategy_name)
    tag_parts.append(f"seed{seed}")
    run_name = "_".join(tag_parts)
    config["run_name"] = run_name

    print(
        f"[run] suite={suite_name} case={case_name} label={label} variant={variant_name}"
        + (f" strategy={strategy_name}" if strategy_name is not None else "")
        + f" seed={seed}",
        flush=True,
    )
    metrics = run_training(config=config, output_dir=runs_dir / run_name)
    scalar = metrics["scalar_metrics"]
    recal = build_reliability_summary(scalar, recal_thresholds)

    row = {
        "suite_name": suite_name,
        "case": case_name,
        "label": label,
        "variant": variant_name,
        "strategy": strategy_name or "baseline",
        "seed": seed,
        "num_observation": num_observation,
        "noise_std": noise_std,
        "run_name": run_name,
        "rel_l2": float(scalar["rel_l2"]),
        "threshold_rel_l2": float(threshold_rel_l2),
        "crosses_threshold": int(float(scalar["rel_l2"]) >= float(threshold_rel_l2)),
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
    return row


def summarize(rows: List[Dict[str, Any]], group_keys: List[str]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row[k] for k in group_keys)
        groups[key].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for key, items in groups.items():
        out = {k: v for k, v in zip(group_keys, key)}
        out["n_seed"] = len(items)
        out["rel_l2_mean"] = statistics.mean(x["rel_l2"] for x in items)
        out["rel_l2_std"] = statistics.pstdev(x["rel_l2"] for x in items)
        out["cross_rate"] = statistics.mean(x["crosses_threshold"] for x in items)
        out["reliability_raw_recal_mean"] = statistics.mean(x["reliability_raw_recal"] for x in items)
        out["reliability_raw_recal_std"] = statistics.pstdev(x["reliability_raw_recal"] for x in items)
        out["physics_consistency_recal_mean"] = statistics.mean(x["physics_consistency_recal"] for x in items)
        out["training_stability_recal_mean"] = statistics.mean(x["training_stability_recal"] for x in items)
        out["numerical_accuracy_recal_mean"] = statistics.mean(x["numerical_accuracy_recal"] for x in items)
        out["structural_stability_recal_mean"] = statistics.mean(x["structural_stability_recal"] for x in items)
        summary_rows.append(out)
    return summary_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cross-PINN variant robustness experiments.")
    parser.add_argument("--spec", required=True, help="Path to robustness spec JSON.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Defaults to minimal_pinn/results/variant_robustness/<suite_name>.",
    )
    args = parser.parse_args()

    spec = load_matrix_spec(args.spec)
    root = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else root / "results" / "variant_robustness" / str(spec["suite_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    variants = spec["variants"]
    thresholds_tables = spec["threshold_tables"]
    recalibration_path = spec["recalibration_path"]

    point_rows: List[Dict[str, Any]] = []
    for experiment in spec["point_experiments"]:
        case_name = str(experiment["case"])
        label = str(experiment["label"])
        seeds = [int(s) for s in experiment["seeds"]]
        num_observation = int(experiment["num_observation"])
        noise_std = float(experiment["noise_std"])
        base_overrides = experiment.get("overrides", {})
        recal_thresholds = load_case_thresholds(recalibration_path, case_name)
        threshold_rel_l2 = case_threshold_rel_l2(thresholds_tables[case_name], case_name)

        for variant_name, variant_overrides in variants.items():
            for seed in seeds:
                row = run_one(
                    suite_name=str(spec["suite_name"]),
                    runs_dir=runs_dir,
                    case_name=case_name,
                    label=label,
                    variant_name=variant_name,
                    variant_overrides=variant_overrides,
                    seed=seed,
                    num_observation=num_observation,
                    noise_std=noise_std,
                    base_overrides=base_overrides,
                    recal_thresholds=recal_thresholds,
                    threshold_rel_l2=threshold_rel_l2,
                )
                point_rows.append(row)

    strategy_rows: List[Dict[str, Any]] = []
    for experiment in spec.get("strategy_experiments", []):
        case_name = str(experiment["case"])
        label = str(experiment["label"])
        seeds = [int(s) for s in experiment["seeds"]]
        num_observation = int(experiment["num_observation"])
        noise_std = float(experiment["noise_std"])
        base_overrides = experiment.get("overrides", {})
        recal_thresholds = load_case_thresholds(recalibration_path, case_name)
        threshold_rel_l2 = case_threshold_rel_l2(thresholds_tables[case_name], case_name)

        selected_variants = experiment.get("variants", list(variants.keys()))
        strategies = experiment["strategies"]
        for variant_name in selected_variants:
            variant_overrides = variants[variant_name]
            for strategy_name, strategy_overrides in strategies.items():
                for seed in seeds:
                    row = run_one(
                        suite_name=str(spec["suite_name"]),
                        runs_dir=runs_dir,
                        case_name=case_name,
                        label=label,
                        variant_name=variant_name,
                        variant_overrides=variant_overrides,
                        seed=seed,
                        num_observation=num_observation,
                        noise_std=noise_std,
                        base_overrides=base_overrides,
                        recal_thresholds=recal_thresholds,
                        threshold_rel_l2=threshold_rel_l2,
                        strategy_name=strategy_name,
                        strategy_overrides=strategy_overrides,
                    )
                    strategy_rows.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "suite_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    if point_rows:
        with (output_dir / "point_runs.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(point_rows[0].keys()))
            writer.writeheader()
            writer.writerows(point_rows)
        point_summary = summarize(point_rows, ["case", "label", "variant"])
        with (output_dir / "point_summary.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(point_summary[0].keys()))
            writer.writeheader()
            writer.writerows(point_summary)
    else:
        point_summary = []

    if strategy_rows:
        with (output_dir / "strategy_runs.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(strategy_rows[0].keys()))
            writer.writeheader()
            writer.writerows(strategy_rows)
        strategy_summary = summarize(strategy_rows, ["case", "label", "variant", "strategy"])
        with (output_dir / "strategy_summary.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(strategy_summary[0].keys()))
            writer.writeheader()
            writer.writerows(strategy_summary)
    else:
        strategy_summary = []

    summary_json = {
        "suite_name": spec["suite_name"],
        "n_point_runs": len(point_rows),
        "n_strategy_runs": len(strategy_rows),
        "point_summary": point_summary,
        "strategy_summary": strategy_summary,
    }
    with (output_dir / "robustness_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
