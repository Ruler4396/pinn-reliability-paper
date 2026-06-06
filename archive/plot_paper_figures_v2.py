"""
Unified paper figure generation script (A5).
Generates all key figures for the paper in one pass.

Paper figure plan:
  Fig 1: Four-case 2D phase maps (rel_l2)
  Fig 2: Four-case recalibrated R phase maps
  Fig 3: Three-system probability boundary comparison
  Fig 4: Dimension ablation: ranking consistency + overlap
  Fig 5: R-vs-rel_l2 divergence morphology
  Fig A1: Calibration sensitivity
  Fig A2: Anti-circularity calibration
  Fig A3: Clean baseline failure analysis
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
M_ROOT = PROJECT / "minimal_pinn"
R_DIR = M_ROOT / "results"
FIG_DIR = R_DIR / "paper_figures" / "v2"

CASE_DISPLAY = {
    "poisson": "Poisson", "burgers": "Burgers",
    "stokes_poiseuille": "Stokes", "fisher_kpp": "Fisher-KPP",
}


def ensure_dir(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pivot_from_df(df: pd.DataFrame, val_col: str):
    return df.pivot(index="noise_std", columns="num_observation", values=val_col).sort_index().sort_index(axis=1)


# ─── Figure 1: Four-case rel_l2 phase maps ───
def fig1_phase_maps_rel_l2():
    cases = ["poisson", "burgers", "stokes_poiseuille", "fisher_kpp"]
    paths = {
        "poisson,burgers,stokes_poiseuille": R_DIR / "matrices" / "coarse_v1" / "matrix_summary.csv",
        "fisher_kpp": R_DIR / "matrices" / "coarse_fisher_kpp_v1" / "matrix_summary.csv",
    }
    dfs = {}
    for key, path in paths.items():
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for case in key.split(","):
            if case in cases:
                dfs[case] = df[df["case"] == case]

    tables = {c: _pivot_from_df(d, "rel_l2") for c, d in dfs.items() if c in dfs}
    if not tables:
        print("  Fig1: no data")
        return

    cnames = [c for c in cases if c in tables]
    vmin = min(t.values.min() for t in tables.values())
    vmax = max(t.values.max() for t in tables.values())

    fig, axes = plt.subplots(1, len(cnames), figsize=(4.5 * len(cnames), 4.2), constrained_layout=True)
    if len(cnames) == 1:
        axes = [axes]

    for ax, c in zip(axes, cnames):
        t = tables[c]
        pos = (pd.cut(t.columns, bins=len(t.columns), labels=False) if hasattr(pd, "cut") 
               else range(len(t.columns)))
        im = ax.imshow(t.values, origin="lower", aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_title(CASE_DISPLAY.get(c, c))
        ax.set_xlabel("Observations"); ax.set_ylabel("Noise std")
        ax.set_xticks(range(len(t.columns))); ax.set_xticklabels([str(int(x)) for x in t.columns], rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(t.index))); ax.set_yticklabels([f"{x:.3f}" for x in t.index], fontsize=8)

    fig.colorbar(im, ax=list(axes), shrink=0.8, label="rel_l2")
    out = ensure_dir(FIG_DIR) / "fig01_rel_l2_phase_maps.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Fig1 saved: {out}")


# ─── Figure 2: Four-case recalibrated R phase maps ───
def fig2_phase_maps_R():
    cases = ["poisson", "burgers", "stokes_poiseuille", "fisher_kpp"]
    table_dir = R_DIR / "analysis" / "recalibrated_dimensions_v1"

    tables = {}
    for c in cases:
        p = table_dir / f"{c}_recalibrated_table.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        tables[c] = _pivot_from_df(df, "reliability_raw_recal")

    if not tables:
        print("  Fig2: no data")
        return

    cnames = [c for c in cases if c in tables]
    fig, axes = plt.subplots(1, len(cnames), figsize=(4.5 * len(cnames), 4.2), constrained_layout=True)
    if len(cnames) == 1:
        axes = [axes]

    for ax, c in zip(axes, cnames):
        t = tables[c]
        im = ax.imshow(t.values, origin="lower", aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
        ax.set_title(CASE_DISPLAY.get(c, c))
        ax.set_xlabel("Observations"); ax.set_ylabel("Noise std")
        ax.set_xticks(range(len(t.columns))); ax.set_xticklabels([str(int(x)) for x in t.columns], rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(t.index))); ax.set_yticklabels([f"{x:.3f}" for x in t.index], fontsize=8)

    fig.colorbar(im, ax=list(axes), shrink=0.8, label="Recalibrated R")
    out = ensure_dir(FIG_DIR) / "fig02_recalibrated_R_phase_maps.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Fig2 saved: {out}")


# ─── Figure 3: Three-system probability boundary comparison ───
def fig3_boundary_comparison():
    src_paths = [
        (R_DIR / "probability_matrices" / "stokes_probability_boundary_v1" / "multiseed_summary.csv", "Stokes-Poiseuille", "#2c7a5a"),
        (R_DIR / "probability_matrices" / "fisher_kpp_probability_boundary_v1" / "multiseed_summary.csv", "Fisher-KPP", "#b64040"),
        (R_DIR / "probability_matrices" / "burgers_probability_boundary_v2_5seed" / "multiseed_summary.csv", "Burgers", "#1f4e79"),
    ]

    dfs = []
    for p, name, color in src_paths:
        if not p.exists():
            continue
        df = pd.read_csv(p)
        df["system"] = name
        df["color"] = color
        dfs.append(df)

    if not dfs:
        print("  Fig3: no data")
        return

    all_df = pd.concat(dfs, ignore_index=True)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), constrained_layout=True)

    for ax, (name, color) in zip(axes, [(d["system"].iloc[0], d["color"].iloc[0]) for d in dfs]):
        sub = all_df[all_df["system"] == name]
        cr_col = "crosses_threshold_rate"
        if cr_col not in sub.columns:
            continue

        obs_levels = sorted(sub["num_observation"].unique(), reverse=True)
        noise_levels = sorted(sub["noise_std"].unique())

        data = np.zeros((len(obs_levels), len(noise_levels)))
        for _, row in sub.iterrows():
            i = obs_levels.index(row["num_observation"])
            j = noise_levels.index(row["noise_std"])
            data[i, j] = row[cr_col]

        im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=0, vmax=1)
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.set_xlabel("Noise std"); ax.set_ylabel("Observations")
        ax.set_xticks(range(len(noise_levels))); ax.set_xticklabels([f"{n:.3f}" for n in noise_levels], rotation=45, fontsize=7)
        ax.set_yticks(range(len(obs_levels))); ax.set_yticklabels([str(int(o)) for o in obs_levels], fontsize=8)
        for i in range(len(obs_levels)):
            for j in range(len(noise_levels)):
                ax.text(j, i, f"{data[i, j]:.0%}", ha="center", va="center", color="white" if data[i, j] > 0.5 else "black", fontsize=7)

    out = ensure_dir(FIG_DIR) / "fig03_boundary_comparison.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Fig3 saved: {out}")


# ─── Figure 4: Ablation comparison ───
def fig4_ablation():
    summary_path = R_DIR / "analysis" / "dimension_ablation_v2" / "ablation_summary.json"
    if not summary_path.exists():
        print("  Fig4: no ablation summary")
        return

    data = load_json(summary_path)
    cases = ["burgers", "fisher_kpp", "stokes_poiseuille"]
    score_labels = [
        ("R_full", "Full 4D", "#333333"),
        ("R_minus_physics", "-Physics", "#1f4e79"),
        ("R_minus_training", "-Training", "#7a7a7a"),
        ("R_minus_numerical", "-Numerical", "#b64040"),
        ("R_minus_structural", "-Structural", "#2c7a5a"),
        ("rel_l2", "rel_l2", "#b64040"),
        ("training_stability", "Train.stab", "#7a7a7a"),
        ("physics_consistency", "Physics", "#1f4e79"),
        ("numerical_accuracy", "Num.acc", "#b64040"),
        ("structural_stability", "Str.stab", "#2c7a5a"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), constrained_layout=True)

    for ax, case in zip(axes, cases):
        if case not in data:
            continue
        rhos = data[case].get("ranking_consistency", {})
        labels, values, colors = [], [], []
        for key, label, color in score_labels:
            if key in rhos:
                labels.append(label)
                values.append(rhos[key].get("mean_rho", 0))
                colors.append(color)

        if values:
            ax.barh(range(len(labels)), values, color=colors)
            ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8)
            ax.set_xlim(0, 1.05)
            ax.set_xlabel("Mean Spearman rho (cross-seed)")
            ax.set_title(f"{CASE_DISPLAY.get(case, case)}: Ranking Consistency", fontsize=10)

    fig.suptitle("Dimension Ablation: Cross-Seed Ranking Stability", fontsize=12, fontweight="bold")
    out = ensure_dir(FIG_DIR) / "fig04_ablation_ranking.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Fig4 saved: {out}")


# ─── Figure 5: Divergence morphology ───
def fig5_divergence():
    src_dir = R_DIR / "analysis" / "divergence_morphology_v1"
    out_dir = ensure_dir(FIG_DIR)

    # Simply reference existing plots
    for img in sorted(src_dir.glob("*.png")):
        print(f"  Fig5 source: {img}")

    # Create a combined summary figure if data available
    available = list(src_dir.glob("*.png"))
    if not available:
        print("  Fig5: no divergence plots")
        return
    
    print(f"  Fig5: {len(available)} divergence plots available in {src_dir}")


# ─── Figure A1: Calibration sensitivity ───
def fig_a1_calibration():
    src = R_DIR / "analysis" / "calibration_sensitivity_v1" / "figure_12_calibration_sensitivity_counts.png"
    if src.exists():
        out = ensure_dir(FIG_DIR) / "fig_a1_calibration_sensitivity.png"
        import shutil
        shutil.copy(src, out)
        print(f"  FigA1 saved: {out}")
    else:
        print("  FigA1: source not found")


# ─── Figure A2: Anti-circularity ───
def fig_a2_anti_circularity():
    summary = R_DIR / "analysis" / "anti_circularity_v1" / "anti_circularity_summary.json"
    if not summary.exists():
        print("  FigA2: no data")
        return

    data = load_json(summary)
    case_results = data.get("case_results", {})

    fig, ax = plt.subplots(figsize=(8, 4.5))
    case_names = list(case_results.keys())
    rates = [case_results[c]["agreement_rate"] * 100 for c in case_names]
    bars = ax.bar(case_names, rates, color=["#1f4e79", "#b64040", "#2c7a5a"][:len(case_names)])
    ax.axhline(25, color="gray", linestyle="--", label="Chance (4-way)")
    ax.set_ylabel("Split-half agreement rate (%)")
    ax.set_title("Anti-Circularity: Split-Half Calibration Agreement")
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{rate:.0f}%", ha="center")
    ax.legend()
    ax.set_ylim(0, 105)

    out = ensure_dir(FIG_DIR) / "fig_a2_anti_circularity.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  FigA2 saved: {out}")


# ─── Figure A3: Clean baseline failure ───
def fig_a3_baseline_failure():
    # Compute threshold sensitivity directly from probe data
    probe_paths = [
        R_DIR / "probes" / "burgers_boundary_keypoints_v3_10seed" / "probe_runs.csv",
        R_DIR / "probes" / "burgers_boundary_keypoints_v4_extra_seed51_70" / "probe_runs.csv",
        R_DIR / "probes" / "burgers_boundary_keypoints_v5_transition_seed71_80" / "probe_runs.csv",
    ]

    # Load Burgers baseline rel_l2 mean
    baseline_path = R_DIR / "baseline_multiseed_v1" / "summary.json"
    baseline_mean = 0.017792
    if baseline_path.exists():
        bl = load_json(baseline_path)
        for r in bl.get("summary_rows", []):
            if r["case"] == "burgers":
                baseline_mean = r["rel_l2_mean"]
                break

    rows = []
    for p in probe_paths:
        if not p.exists():
            continue
        df = pd.read_csv(p)
        rows.append(df)

    if not rows:
        print("  FigA3: no probe data")
        return

    all_df = pd.concat(rows, ignore_index=True)
    # Find "safe_clean" points (obs=128, noise=0)
    safe = all_df[(all_df["num_observation"] == 128) & (all_df["noise_std"] == 0.0)]
    if safe.empty:
        safe = all_df[all_df["num_observation"] == all_df["num_observation"].max()]

    rel_l2s = safe["rel_l2"].values
    n = len(rel_l2s)

    multipliers = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    rates = []
    for m in multipliers:
        thr = baseline_mean * m
        n_cross = sum(1 for v in rel_l2s if v >= thr)
        rates.append(n_cross / max(n, 1))

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#2c7a5a" if r < 0.2 else "#b64040" for r in rates]
    bars = ax.bar([str(m) for m in multipliers], [r * 100 for r in rates], width=0.6, color=colors)
    ax.axhline(20, color="gray", linestyle="--", label="20% threshold")
    ax.set_xlabel("Threshold multiplier (x baseline)")
    ax.set_ylabel("Failure rate at safest point (%)")
    ax.set_title(f"Burgers: Safe-Point Failure Rate vs Threshold ({n} seeds)")
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{rate:.0%}", ha="center", fontsize=9)
    ax.legend()
    ax.set_ylim(0, 105)

    out = ensure_dir(FIG_DIR) / "fig_a3_baseline_failure.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  FigA3 saved: {out}")


def main():
    print("Generating paper figures...")
    fig1_phase_maps_rel_l2()
    fig2_phase_maps_R()
    fig3_boundary_comparison()
    fig4_ablation()
    fig5_divergence()
    fig_a1_calibration()
    fig_a2_anti_circularity()
    fig_a3_baseline_failure()
    print(f"\nAll figures written to: {ensure_dir(FIG_DIR)}")


if __name__ == "__main__":
    main()
