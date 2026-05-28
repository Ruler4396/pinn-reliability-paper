from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from .matrix_specs import build_run_config, load_matrix_spec
from .trainer import run_training


def make_tag(num_observation: int, noise_std: float, seed: int) -> str:
    noise_pct = int(round(noise_std * 1000))
    return f"obs{num_observation}_noise{noise_pct:03d}_seed{seed}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a multi-seed probe on selected grid points.")
    parser.add_argument("--spec", required=True, help="Path to a probe JSON spec.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to minimal_pinn/results/probes/<probe_name>.",
    )
    args = parser.parse_args()

    spec = load_matrix_spec(args.spec)
    base_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else base_dir / "results" / "probes" / str(spec["probe_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    case_name = str(spec["case"])
    seeds = [int(seed) for seed in spec["seeds"]]
    points = spec["points"]
    overrides = spec.get("overrides", {})
    threshold_rel_l2 = float(spec["threshold_rel_l2"])

    rows: List[Dict[str, Any]] = []
    grouped_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for point in points:
        label = str(point["label"])
        num_observation = int(point["num_observation"])
        noise_std = float(point["noise_std"])

        for seed in seeds:
            config = build_run_config(
                case_name=case_name,
                num_observation=num_observation,
                noise_std=noise_std,
                overrides=overrides,
            )
            config["seed"] = seed
            run_name = f"{case_name}_{spec['probe_name']}_{make_tag(num_observation, noise_std, seed)}"
            config["run_name"] = run_name

            print(
                f"[run] probe={spec['probe_name']} label={label} obs={num_observation} "
                f"noise={noise_std} seed={seed}",
                flush=True,
            )
            metrics = run_training(config=config, output_dir=runs_dir / run_name)
            scalar = metrics["scalar_metrics"]
            reliability = metrics["reliability"]
            row = {
                "probe_name": spec["probe_name"],
                "case": case_name,
                "label": label,
                "num_observation": num_observation,
                "noise_std": noise_std,
                "seed": seed,
                "run_name": run_name,
                "rel_l2": scalar["rel_l2"],
                "reliability_raw": reliability["reliability_raw"],
                "physics_rms": scalar["physics_rms"],
                "boundary_rms": scalar["boundary_rms"],
                "structure_error": scalar["structure_error"],
                "loss_std": scalar["loss_std"],
                "loss_ratio": scalar["loss_ratio"],
                "threshold_rel_l2": threshold_rel_l2,
                "crosses_threshold": int(scalar["rel_l2"] >= threshold_rel_l2),
            }
            rows.append(row)
            grouped_rows[label].append(row)

    summary_rows: List[Dict[str, Any]] = []
    summary_json: Dict[str, Any] = {
        "probe_name": spec["probe_name"],
        "case": case_name,
        "seeds": seeds,
        "threshold_rel_l2": threshold_rel_l2,
        "points": {},
    }
    for point in points:
        label = str(point["label"])
        point_rows = grouped_rows[label]
        rel_values = [row["rel_l2"] for row in point_rows]
        reliability_values = [row["reliability_raw"] for row in point_rows]
        structure_values = [row["structure_error"] for row in point_rows]
        summary = {
            "label": label,
            "num_observation": int(point["num_observation"]),
            "noise_std": float(point["noise_std"]),
            "n_seed": len(point_rows),
            "rel_l2_mean": statistics.mean(rel_values),
            "rel_l2_std": statistics.pstdev(rel_values),
            "rel_l2_min": min(rel_values),
            "rel_l2_max": max(rel_values),
            "reliability_raw_mean": statistics.mean(reliability_values),
            "reliability_raw_std": statistics.pstdev(reliability_values),
            "structure_error_mean": statistics.mean(structure_values),
            "structure_error_std": statistics.pstdev(structure_values),
            "crosses_threshold_count": sum(row["crosses_threshold"] for row in point_rows),
            "crosses_threshold_rate": (
                sum(row["crosses_threshold"] for row in point_rows) / max(len(point_rows), 1)
            ),
        }
        summary_rows.append(summary)
        summary_json["points"][label] = summary

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "probe_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    with (output_dir / "probe_runs.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "probe_name",
                "case",
                "label",
                "num_observation",
                "noise_std",
                "seed",
                "run_name",
                "rel_l2",
                "reliability_raw",
                "physics_rms",
                "boundary_rms",
                "structure_error",
                "loss_std",
                "loss_ratio",
                "threshold_rel_l2",
                "crosses_threshold",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "probe_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "label",
                "num_observation",
                "noise_std",
                "n_seed",
                "rel_l2_mean",
                "rel_l2_std",
                "rel_l2_min",
                "rel_l2_max",
                "reliability_raw_mean",
                "reliability_raw_std",
                "structure_error_mean",
                "structure_error_std",
                "crosses_threshold_count",
                "crosses_threshold_rate",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    with (output_dir / "probe_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
