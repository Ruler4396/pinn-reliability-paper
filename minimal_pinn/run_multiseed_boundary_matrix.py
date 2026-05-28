from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .matrix_specs import build_run_config, load_matrix_spec
from .reliability import build_reliability_summary
from .trainer import run_training


def make_tag(num_observation: int, noise_std: float, seed: int) -> str:
    noise_pct = int(round(noise_std * 1000))
    return f"obs{num_observation}_noise{noise_pct:03d}_seed{seed}"


def load_case_thresholds(path: str | Path, case_name: str) -> Dict[str, Dict[str, float | str]]:
    with Path(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data[case_name]["thresholds"]


def plot_heatmap(
    df: pd.DataFrame,
    value_col: str,
    title: str,
    output_path: Path,
    cmap: str = "viridis",
    fmt: str = ".3f",
) -> None:
    pivot = (
        df.pivot(index="noise_std", columns="num_observation", values=value_col)
        .sort_index(ascending=False)
        .sort_index(axis=1, ascending=True)
    )
    fig, ax = plt.subplots(figsize=(6.2, 4.6), constrained_layout=True)
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xlabel("Observation count")
    ax.set_ylabel("Noise std")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(int(v)) for v in pivot.columns])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{v:.3f}" for v in pivot.index])
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, format(float(pivot.values[i, j]), fmt), ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a multi-seed local boundary matrix.")
    parser.add_argument("--spec", required=True, help="Path to a boundary-matrix JSON spec.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to minimal_pinn/results/probability_matrices/<matrix_name>.",
    )
    args = parser.parse_args()

    spec = load_matrix_spec(args.spec)
    base_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else base_dir / "results" / "probability_matrices" / str(spec["matrix_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    case_name = str(spec["case"])
    observation_counts = [int(v) for v in spec["observation_counts"]]
    noise_levels = [float(v) for v in spec["noise_levels"]]
    seeds = [int(v) for v in spec["seeds"]]
    overrides = spec.get("overrides", {})
    threshold_rel_l2 = float(spec["threshold_rel_l2"])
    recalibration_path = spec["recalibration_path"]
    thresholds = load_case_thresholds(recalibration_path, case_name)

    rows: List[Dict[str, Any]] = []
    grouped: Dict[tuple[int, float], List[Dict[str, Any]]] = defaultdict(list)

    for noise_std in noise_levels:
        for num_observation in observation_counts:
            for seed in seeds:
                config = build_run_config(
                    case_name=case_name,
                    num_observation=num_observation,
                    noise_std=noise_std,
                    overrides=overrides,
                )
                config["seed"] = seed
                run_name = f"{case_name}_{spec['matrix_name']}_{make_tag(num_observation, noise_std, seed)}"
                config["run_name"] = run_name

                print(
                    f"[run] matrix={spec['matrix_name']} case={case_name} obs={num_observation} noise={noise_std} seed={seed}",
                    flush=True,
                )
                metrics = run_training(config=config, output_dir=runs_dir / run_name)
                scalar = metrics["scalar_metrics"]
                recal = build_reliability_summary(scalar, thresholds)

                row = {
                    "matrix_name": spec["matrix_name"],
                    "case": case_name,
                    "num_observation": num_observation,
                    "noise_std": noise_std,
                    "seed": seed,
                    "run_name": run_name,
                    "rel_l2": scalar["rel_l2"],
                    "physics_rms": scalar["physics_rms"],
                    "boundary_rms": scalar["boundary_rms"],
                    "structure_error": scalar["structure_error"],
                    "loss_std": scalar["loss_std"],
                    "loss_ratio": scalar["loss_ratio"],
                    "reliability_raw": metrics["reliability"]["reliability_raw"],
                    "reliability_raw_recal": recal["reliability_raw"],
                    "physics_consistency_recal": recal["dimension_scores"]["physics_consistency"],
                    "training_stability_recal": recal["dimension_scores"]["training_stability"],
                    "numerical_accuracy_recal": recal["dimension_scores"]["numerical_accuracy"],
                    "structural_stability_recal": recal["dimension_scores"]["structural_stability"],
                    "threshold_rel_l2": threshold_rel_l2,
                    "crosses_threshold": int(scalar["rel_l2"] >= threshold_rel_l2),
                }
                rows.append(row)
                grouped[(num_observation, noise_std)].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for noise_std in noise_levels:
        for num_observation in observation_counts:
            point_rows = grouped[(num_observation, noise_std)]
            rel_values = [r["rel_l2"] for r in point_rows]
            recal_values = [r["reliability_raw_recal"] for r in point_rows]
            summary_rows.append(
                {
                    "matrix_name": spec["matrix_name"],
                    "case": case_name,
                    "num_observation": num_observation,
                    "noise_std": noise_std,
                    "n_seed": len(point_rows),
                    "rel_l2_mean": statistics.mean(rel_values),
                    "rel_l2_std": statistics.pstdev(rel_values),
                    "reliability_raw_recal_mean": statistics.mean(recal_values),
                    "reliability_raw_recal_std": statistics.pstdev(recal_values),
                    "crosses_threshold_count": sum(r["crosses_threshold"] for r in point_rows),
                    "crosses_threshold_rate": sum(r["crosses_threshold"] for r in point_rows) / max(len(point_rows), 1),
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "matrix_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    with (output_dir / "multiseed_runs.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "multiseed_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    summary_df = pd.DataFrame(summary_rows)
    plot_heatmap(
        summary_df,
        "crosses_threshold_rate",
        f"{case_name} threshold-cross rate",
        output_dir / "figure_14_cross_rate_heatmap.png",
        cmap="magma",
        fmt=".2f",
    )
    plot_heatmap(
        summary_df,
        "rel_l2_std",
        f"{case_name} rel_l2 std",
        output_dir / "figure_15_rel_l2_std_heatmap.png",
        cmap="viridis",
        fmt=".3f",
    )
    plot_heatmap(
        summary_df,
        "reliability_raw_recal_mean",
        f"{case_name} mean recalibrated R",
        output_dir / "figure_16_recalibrated_R_heatmap.png",
        cmap="cividis",
        fmt=".3f",
    )

    summary_json = {
        "matrix_name": spec["matrix_name"],
        "case": case_name,
        "threshold_rel_l2": threshold_rel_l2,
        "seeds": seeds,
        "summary_rows": summary_rows,
    }
    with (output_dir / "multiseed_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={output_dir}")
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
