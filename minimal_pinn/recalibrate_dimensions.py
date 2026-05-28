from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .reliability import build_reliability_summary


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "results" / "analysis" / "indicator_validity_v1"
OUTPUT_DIR = ROOT / "results" / "analysis" / "recalibrated_dimensions_v1"

CASE_TABLES = {
    "poisson": INPUT_DIR / "poisson_indicator_table.csv",
    "burgers": INPUT_DIR / "burgers_indicator_table.csv",
    "stokes_poiseuille": INPUT_DIR / "stokes_indicator_table.csv",
    "fisher_kpp": INPUT_DIR / "fisher_kpp_indicator_table.csv",
}

METRICS = [
    "physics_rms",
    "boundary_rms",
    "rel_l2",
    "structure_error",
    "loss_std",
    "loss_ratio",
]

DIM_COLS = [
    "physics_consistency",
    "training_stability",
    "numerical_accuracy",
    "structural_stability",
]

CASE_TITLES = {
    "poisson": "Poisson",
    "burgers": "Burgers",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "fisher_kpp": "Fisher-KPP",
}


def quantile_thresholds(df: pd.DataFrame, low_q: float = 0.15, high_q: float = 0.85) -> Dict[str, Dict[str, float | str]]:
    thresholds: Dict[str, Dict[str, float | str]] = {}
    for metric in METRICS:
        good = float(df[metric].quantile(low_q))
        fail = float(df[metric].quantile(high_q))
        if math.isclose(good, fail):
            span = max(abs(good) * 0.1, 1e-8)
            good = good - span
            fail = fail + span
        thresholds[metric] = {
            "good": good,
            "fail": fail,
            "mode": "smaller_better",
        }
    return thresholds


def recalibrate_case(
    case_name: str,
    df: pd.DataFrame,
    low_q: float = 0.15,
    high_q: float = 0.85,
) -> Dict:
    thresholds = quantile_thresholds(df, low_q=low_q, high_q=high_q)
    rows = []
    for _, row in df.iterrows():
        scalar_metrics = {metric: float(row[metric]) for metric in METRICS}
        reliability = build_reliability_summary(scalar_metrics, thresholds)
        rows.append(
            {
                **row.to_dict(),
                "physics_consistency_recal": float(reliability["dimension_scores"]["physics_consistency"]),
                "training_stability_recal": float(reliability["dimension_scores"]["training_stability"]),
                "numerical_accuracy_recal": float(reliability["dimension_scores"]["numerical_accuracy"]),
                "structural_stability_recal": float(reliability["dimension_scores"]["structural_stability"]),
                "reliability_raw_recal": float(reliability["reliability_raw"]),
            }
        )
    recal_df = pd.DataFrame(rows)

    corr = recal_df[
        [
            "rel_l2",
            "reliability_raw_recal",
            "physics_consistency_recal",
            "training_stability_recal",
            "numerical_accuracy_recal",
            "structural_stability_recal",
        ]
    ].corr(method="spearman")

    threshold_rel_l2 = float(df["threshold_rel_l2"].iloc[0])
    selected = recal_df[recal_df["rel_l2"] >= threshold_rel_l2].copy()
    selection_rule = "threshold_rel_l2"
    if selected.empty:
        selected = recal_df[recal_df["rel_l2"] >= float(recal_df["rel_l2"].quantile(0.75))].copy()
        selection_rule = "top_quartile_rel_l2"
    counts = Counter(selected[[f"{col}_recal" for col in DIM_COLS]].idxmin(axis=1).tolist())
    counts = {key.replace("_recal", ""): int(value) for key, value in counts.items()}

    return {
        "thresholds": thresholds,
        "table": recal_df,
        "summary": {
            "low_q": low_q,
            "high_q": high_q,
            "selection_rule": selection_rule,
            "n_selected": int(len(selected)),
            "spearman_rel_l2_vs_reliability_raw_recal": float(corr.loc["rel_l2", "reliability_raw_recal"]),
            "spearman_rel_l2_vs_physics_consistency_recal": float(corr.loc["rel_l2", "physics_consistency_recal"]),
            "spearman_rel_l2_vs_training_stability_recal": float(corr.loc["rel_l2", "training_stability_recal"]),
            "spearman_rel_l2_vs_numerical_accuracy_recal": float(corr.loc["rel_l2", "numerical_accuracy_recal"]),
            "spearman_rel_l2_vs_structural_stability_recal": float(corr.loc["rel_l2", "structural_stability_recal"]),
            "dominant_dimension_counts_recal": {
                "physics_consistency": counts.get("physics_consistency", 0),
                "training_stability": counts.get("training_stability", 0),
                "numerical_accuracy": counts.get("numerical_accuracy", 0),
                "structural_stability": counts.get("structural_stability", 0),
            },
        },
    }


def plot_dimension_spreads(case_results: Dict[str, Dict], output_path: Path) -> None:
    order = list(case_results.keys())
    n_case = len(order)
    ncols = 2 if n_case > 3 else n_case
    nrows = int(math.ceil(n_case / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.4 * ncols, 4.2 * nrows), constrained_layout=True)
    axes = pd.Series(axes.ravel() if hasattr(axes, "ravel") else [axes])
    for ax, case_name in zip(axes.iloc[:n_case], order):
        result = case_results[case_name]
        df = result["table"]
        box_data = [df[f"{col}_recal"].values for col in DIM_COLS]
        ax.boxplot(
            box_data,
            tick_labels=["physics", "training", "numerical", "structural"],
            patch_artist=True,
        )
        ax.set_ylim(0.0, 1.0)
        ax.set_title(CASE_TITLES[case_name])
        ax.set_ylabel("Recalibrated dimension score")
        ax.tick_params(axis="x", rotation=20)
    for ax in axes.iloc[n_case:]:
        ax.axis("off")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_failure_mode_counts(case_results: Dict[str, Dict], output_path: Path) -> None:
    colors = ["#1f4e79", "#7a7a7a", "#b64040", "#2c7a5a"]
    order = list(case_results.keys())
    n_case = len(order)
    ncols = 2 if n_case > 3 else n_case
    nrows = int(math.ceil(n_case / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.4 * ncols, 4.2 * nrows), constrained_layout=True)
    axes = pd.Series(axes.ravel() if hasattr(axes, "ravel") else [axes])
    for ax, case_name in zip(axes.iloc[:n_case], order):
        result = case_results[case_name]
        counts = result["summary"]["dominant_dimension_counts_recal"]
        labels = ["physics_consistency", "training_stability", "numerical_accuracy", "structural_stability"]
        values = [counts[label] for label in labels]
        ax.bar(range(len(labels)), values, color=colors)
        ax.set_title(CASE_TITLES[case_name])
        ax.set_ylabel("Count")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(["physics", "training", "numerical", "structural"], rotation=20, ha="right")
    for ax in axes.iloc[n_case:]:
        ax.axis("off")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    case_results: Dict[str, Dict] = {}
    summary = {}
    for case_name, path in CASE_TABLES.items():
        df = pd.read_csv(path)
        result = recalibrate_case(case_name, df)
        case_results[case_name] = result
        result["table"].to_csv(OUTPUT_DIR / f"{case_name}_recalibrated_table.csv", index=False)
        summary[case_name] = {
            "thresholds": result["thresholds"],
            **result["summary"],
        }

    plot_dimension_spreads(case_results, OUTPUT_DIR / "figure_08_recalibrated_dimension_spreads.png")
    plot_failure_mode_counts(case_results, OUTPUT_DIR / "figure_09_recalibrated_failure_mode_counts.png")

    with (OUTPUT_DIR / "recalibrated_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
