from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import ensure_defaults
from .reliability import build_reliability_summary


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "indicator_validity_v1"

CASE_SOURCES = {
    "poisson": RESULTS_DIR / "matrices" / "coarse_v1" / "analysis" / "matrix_analysis.json",
    "stokes_poiseuille": RESULTS_DIR / "matrices" / "refine_stokes_v1" / "analysis" / "matrix_analysis.json",
    "burgers": RESULTS_DIR / "matrices" / "refine_burgers_v1" / "analysis" / "matrix_analysis.json",
    "fisher_kpp": RESULTS_DIR / "matrices" / "coarse_fisher_kpp_v1" / "analysis" / "matrix_analysis.json",
}

CASE_TITLES = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "burgers": "Burgers",
    "fisher_kpp": "Fisher-KPP",
}


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_case_dataframe(case_name: str, analysis_path: Path) -> pd.DataFrame:
    analysis = load_json(analysis_path)[case_name]
    rows = pd.DataFrame(analysis["all_rows"])
    thresholds = ensure_defaults({})["reliability"]["thresholds"]

    dim_rows: List[Dict[str, float]] = []
    for _, row in rows.iterrows():
        scalar_metrics = {
            "physics_rms": float(row["physics_rms"]),
            "boundary_rms": float(row["boundary_rms"]),
            "rel_l2": float(row["rel_l2"]),
            "structure_error": float(row["structure_error"]),
            "loss_std": float(row["loss_std"]),
            "loss_ratio": float(row["loss_ratio"]),
        }
        reliability = build_reliability_summary(scalar_metrics, thresholds)
        dim_rows.append(
            {
                "physics_consistency": float(reliability["dimension_scores"]["physics_consistency"]),
                "training_stability": float(reliability["dimension_scores"]["training_stability"]),
                "numerical_accuracy": float(reliability["dimension_scores"]["numerical_accuracy"]),
                "structural_stability": float(reliability["dimension_scores"]["structural_stability"]),
            }
        )
    dim_df = pd.DataFrame(dim_rows)
    merged = pd.concat([rows.reset_index(drop=True), dim_df], axis=1)
    merged["threshold_rel_l2"] = float(analysis["threshold_rel_l2"])
    return merged


def save_corr_heatmaps(case_frames: Dict[str, pd.DataFrame], output_path: Path) -> Dict[str, Dict]:
    metrics = [
        "rel_l2",
        "reliability_raw",
        "physics_rms",
        "structure_error",
        "loss_std",
        "physics_consistency",
        "training_stability",
        "numerical_accuracy",
        "structural_stability",
    ]
    order = list(case_frames.keys())
    n_case = len(order)
    ncols = 2 if n_case > 3 else n_case
    nrows = int(np.ceil(n_case / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.0 * ncols, 4.2 * nrows), constrained_layout=True)
    axes = np.atleast_1d(axes).ravel()
    summary: Dict[str, Dict] = {}
    for ax, case_name in zip(axes, order):
        df = case_frames[case_name]
        corr = df[metrics].corr(method="spearman")
        im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
        ax.set_title(CASE_TITLES[case_name])
        ax.set_xticks(range(len(metrics)))
        ax.set_xticklabels(metrics, rotation=55, ha="right", fontsize=8)
        ax.set_yticks(range(len(metrics)))
        ax.set_yticklabels(metrics, fontsize=8)
        summary[case_name] = {
            "corr_rel_l2_reliability_raw": float(corr.loc["rel_l2", "reliability_raw"]),
            "corr_rel_l2_physics_rms": float(corr.loc["rel_l2", "physics_rms"]),
            "corr_rel_l2_structure_error": float(corr.loc["rel_l2", "structure_error"]),
            "corr_rel_l2_training_stability": float(corr.loc["rel_l2", "training_stability"]),
        }
    for ax in axes[n_case:]:
        ax.axis("off")
    fig.colorbar(im, ax=axes[:n_case], shrink=0.9, label="Spearman correlation")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return summary


def save_failure_mode_plot(case_frames: Dict[str, pd.DataFrame], output_path: Path) -> Dict[str, Dict]:
    dim_cols = [
        "physics_consistency",
        "training_stability",
        "numerical_accuracy",
        "structural_stability",
    ]
    summary: Dict[str, Dict] = {}
    order = list(case_frames.keys())
    n_case = len(order)
    ncols = 2 if n_case > 3 else n_case
    nrows = int(np.ceil(n_case / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.4 * ncols, 4.0 * nrows), constrained_layout=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, case_name in zip(axes, order):
        df = case_frames[case_name]
        threshold = float(df["threshold_rel_l2"].iloc[0])
        selected = df[df["rel_l2"] >= threshold].copy()
        rule = "threshold_rel_l2"
        if selected.empty:
            cutoff = float(df["rel_l2"].quantile(0.75))
            selected = df[df["rel_l2"] >= cutoff].copy()
            rule = "top_quartile_rel_l2"
        counts = Counter(selected[dim_cols].idxmin(axis=1).tolist())
        values = [counts.get(col, 0) for col in dim_cols]
        ax.bar(range(len(dim_cols)), values, color=["#1f4e79", "#7a7a7a", "#b64040", "#2c7a5a"])
        ax.set_title(CASE_TITLES[case_name])
        ax.set_xticks(range(len(dim_cols)))
        ax.set_xticklabels(
            ["physics", "training", "numerical", "structural"],
            rotation=20,
            ha="right",
        )
        ax.set_ylabel("Count")
        summary[case_name] = {
            "selection_rule": rule,
            "n_selected": int(len(selected)),
            "dominant_dimension_counts": {col: int(counts.get(col, 0)) for col in dim_cols},
        }
    for ax in axes[n_case:]:
        ax.axis("off")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return summary


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    case_frames = {
        case_name: build_case_dataframe(case_name, analysis_path)
        for case_name, analysis_path in CASE_SOURCES.items()
    }

    case_frames["poisson"].to_csv(OUTPUT_DIR / "poisson_indicator_table.csv", index=False)
    case_frames["burgers"].to_csv(OUTPUT_DIR / "burgers_indicator_table.csv", index=False)
    case_frames["stokes_poiseuille"].to_csv(OUTPUT_DIR / "stokes_indicator_table.csv", index=False)
    case_frames["fisher_kpp"].to_csv(OUTPUT_DIR / "fisher_kpp_indicator_table.csv", index=False)

    corr_summary = save_corr_heatmaps(
        case_frames,
        OUTPUT_DIR / "figure_06_indicator_correlations.png",
    )
    failure_summary = save_failure_mode_plot(
        case_frames,
        OUTPUT_DIR / "figure_07_failure_mode_counts.png",
    )

    summary = {
        "correlation_summary": corr_summary,
        "failure_mode_summary": failure_summary,
    }
    with (OUTPUT_DIR / "indicator_validity_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
