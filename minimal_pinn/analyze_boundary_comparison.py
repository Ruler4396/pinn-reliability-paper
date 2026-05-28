"""
Three-system probability boundary quantitative comparison.
Computes boundary metrics for Stokes, Fisher-KPP, and Burgers from
their multi-seed probability boundary matrices.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBABILITY_DIR = RESULTS_DIR / "probability_matrices"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "boundary_comparison_v1"

SYSTEMS = [
    {
        "name": "stokes_poiseuille",
        "display": "Stokes-Poiseuille",
        "matrix": "stokes_probability_boundary_v1",
        "threshold": 0.015379,
    },
    {
        "name": "fisher_kpp",
        "display": "Fisher-KPP",
        "matrix": "fisher_kpp_probability_boundary_v1",
        "threshold": 0.018861,
    },
    {
        "name": "burgers",
        "display": "Burgers",
        "matrix": "burgers_probability_boundary_v2_5seed",
        "threshold": 0.026688,
    },
]

COLORS = {
    "Stokes-Poiseuille": "#2c7a5a",
    "Fisher-KPP": "#b64040",
    "Burgers": "#1f4e79",
}


def load_probability_data(matrix_name: str) -> pd.DataFrame:
    csv_path = PROBABILITY_DIR / matrix_name / "multiseed_summary.csv"
    if not csv_path.exists():
        csv_path = PROBABILITY_DIR / matrix_name / "multiseed_runs.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No CSV found for {matrix_name}")
    return pd.read_csv(csv_path)


def compute_boundary_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute quantitative boundary metrics from summary DataFrame."""
    cells = []
    for _, row in df.iterrows():
        cells.append({
            "num_observation": float(row["num_observation"]),
            "noise_std": float(row["noise_std"]),
            "n_seeds": float(row.get("n_seed", 0)),
            "rel_l2_mean": float(row.get("rel_l2_mean", 0)),
            "rel_l2_std": float(row.get("rel_l2_std", 0)),
            "cross_rate": float(row.get("crosses_threshold_rate", 0)),
        })

    cells.sort(key=lambda c: (c["num_observation"], -c["noise_std"]))

    # Safest cell: highest obs, lowest noise
    safest = max(cells, key=lambda c: (c["num_observation"], -c["noise_std"]))

    # Seed std
    std_values = [c["rel_l2_std"] for c in cells]
    mean_seed_std = np.mean(std_values) if std_values else 0

    # Cell distribution
    cross_rates = [c["cross_rate"] for c in cells]
    n_total = len(cross_rates)
    n_safe = sum(1 for cr in cross_rates if cr <= 0.20)
    n_transition = sum(1 for cr in cross_rates if 0.20 < cr < 0.80)
    n_failure = sum(1 for cr in cross_rates if cr >= 0.80)

    # Transition steepness: for each obs level, find the noise jump from 0% to 100%
    obs_levels = sorted(set(c["num_observation"] for c in cells))
    noise_levels = sorted(set(c["noise_std"] for c in cells))
    
    # Build cross_rate matrix
    cr_matrix = {}
    for c in cells:
        cr_matrix[(c["num_observation"], c["noise_std"])] = c["cross_rate"]
    
    # For each obs level, measure the noise span covering 0-100% transition
    transition_gaps = []
    for obs in obs_levels:
        first_above_0 = None
        reached_100 = None
        for noise in sorted(noise_levels):
            cr = cr_matrix.get((obs, noise), 1.0)
            if cr > 0.0 and first_above_0 is None:
                first_above_0 = noise
            if cr >= 1.0 and reached_100 is None and first_above_0 is not None:
                reached_100 = noise
        if first_above_0 is not None and reached_100 is not None:
            transition_gaps.append(reached_100 - first_above_0)

    avg_transition_gap = np.mean(transition_gaps) if transition_gaps else None

    # Cross-rate entropy proxy: sum of intermediate rates
    avg_cross_rate = np.mean(cross_rates)

    return {
        "safest_cell": {
            "num_observation": safest["num_observation"],
            "noise_std": safest["noise_std"],
            "rel_l2_mean": safest["rel_l2_mean"],
            "rel_l2_std": safest["rel_l2_std"],
            "cross_rate": safest["cross_rate"],
        },
        "baseline_instability": safest["cross_rate"],
        "mean_seed_std": mean_seed_std,
        "n_cells_total": n_total,
        "n_safe_cells": n_safe,
        "n_transition_cells": n_transition,
        "n_failure_cells": n_failure,
        "transition_ratio": n_transition / max(n_total, 1),
        "avg_transition_gap": avg_transition_gap,
        "transition_gaps": transition_gaps,
        "avg_cross_rate": avg_cross_rate,
        "cell_metrics": cells,
    }


def plot_combined_boundaries(all_metrics: Dict[str, Dict], output_path: Path) -> None:
    """Create a combined heatmap-style comparison of three systems."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), constrained_layout=True)

    for ax, sys_info in zip(axes, SYSTEMS):
        display = sys_info["display"]
        metrics = all_metrics.get(sys_info["name"], {})
        if not metrics or "cell_metrics" not in metrics:
            ax.set_title(f"{display}\n(no data)")
            continue
        
        cells = metrics["cell_metrics"]
        obs_levels = sorted(set(c["num_observation"] for c in cells), reverse=True)
        noise_levels = sorted(set(c["noise_std"] for c in cells))
        
        data = np.zeros((len(obs_levels), len(noise_levels)))
        for c in cells:
            i = obs_levels.index(c["num_observation"])
            j = noise_levels.index(c["noise_std"])
            data[i, j] = c["cross_rate"]
        
        im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=0, vmax=1)
        ax.set_title(display, fontsize=13, fontweight="bold")
        ax.set_xlabel("Noise std")
        ax.set_ylabel("Observations")
        ax.set_xticks(range(len(noise_levels)))
        ax.set_xticklabels([f"{n:.3f}" for n in noise_levels], rotation=45, fontsize=7)
        ax.set_yticks(range(len(obs_levels)))
        ax.set_yticklabels([str(int(o)) for o in obs_levels], fontsize=8)
        
        for i in range(len(obs_levels)):
            for j in range(len(noise_levels)):
                val = data[i, j]
                color = "white" if val > 0.5 else "black"
                ax.text(j, i, f"{val:.0%}", ha="center", va="center", color=color, fontsize=7)

        # Add metrics text
        ax.text(0.02, -0.18,
                f"Safe: {metrics['n_safe_cells']} | Trans: {metrics['n_transition_cells']} | Fail: {metrics['n_failure_cells']}\n"
                f"Baseline instability: {metrics['baseline_instability']:.0%} | Mean seed std: {metrics['mean_seed_std']:.4f}",
                transform=ax.transAxes, fontsize=7, color="#444444")

    fig.suptitle("Three-System Probability Boundary Comparison", fontsize=14, fontweight="bold")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_transition_profile(all_metrics: Dict[str, Dict], output_path: Path) -> None:
    """Plot cross-rate vs noise for each observation level, one subplot per system."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)

    for ax, sys_info in zip(axes, SYSTEMS):
        display = sys_info["display"]
        metrics = all_metrics.get(sys_info["name"], {})
        if not metrics or "cell_metrics" not in metrics:
            continue
        
        cells = metrics["cell_metrics"]
        obs_levels = sorted(set(c["num_observation"] for c in cells))
        
        for obs in obs_levels:
            obs_cells = sorted([c for c in cells if c["num_observation"] == obs], key=lambda c: c["noise_std"])
            noise_vals = [c["noise_std"] for c in obs_cells]
            cross_vals = [c["cross_rate"] for c in obs_cells]
            ax.plot(noise_vals, cross_vals, "o-", markersize=5, linewidth=1.5, label=f"obs={obs}")

        # Threshold line
        threshold = sys_info["threshold"]
        ax.set_title(display, fontsize=12, fontweight="bold")
        ax.set_xlabel("Noise std")
        ax.set_ylabel("Cross rate")
        ax.set_ylim(-0.05, 1.05)
        ax.axhline(y=0.2, color="green", linestyle="--", alpha=0.4, linewidth=1)
        ax.axhline(y=0.8, color="red", linestyle="--", alpha=0.4, linewidth=1)
        ax.legend(fontsize=7, loc="lower right")

    fig.suptitle("Transition Profiles: Cross Rate vs Noise by Observation Level", fontsize=13)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_summary_table(all_metrics: Dict[str, Dict]) -> str:
    lines = [
        "# Three-System Probability Boundary Quantitative Comparison",
        "",
        "| Metric | Stokes-Poiseuille | Fisher-KPP | Burgers |",
        "|--------|:-:|:-:|:-:|",
    ]

    def get(name, key, fmt=".3f"):
        m = all_metrics.get(name, {})
        val = m.get(key)
        if val is None:
            return "—"
        if isinstance(val, float):
            if fmt == "d":
                return str(int(val))
            return format(val, fmt)
        return str(val)

    metrics_rows = [
        ("Safest cell cross rate", "baseline_instability", ".0%"),
        ("Mean seed rel_l2 std", "mean_seed_std", ".4f"),
        ("Safe cells (rate<=20%)", "n_safe_cells", "d"),
        ("Transition cells (20-80%)", "n_transition_cells", "d"),
        ("Failure cells (rate>=80%)", "n_failure_cells", "d"),
        ("Transition ratio", "transition_ratio", ".0%"),
        ("Avg transition gap", "avg_transition_gap", ".3f"),
        ("Avg cross rate", "avg_cross_rate", ".2%"),
    ]

    for label, key, fmt in metrics_rows:
        stokes_val = get("stokes_poiseuille", key, fmt)
        fisher_val = get("fisher_kpp", key, fmt)
        burgers_val = get("burgers", key, fmt)
        lines.append(f"| {label} | {stokes_val} | {fisher_val} | {burgers_val} |")

    lines.extend([
        "",
        "## Interpretation",
        "",
        "The three systems form a clear gradient across multiple quantitative metrics:",
        "",
        "| Dimension | Stokes-Poiseuille | Fisher-KPP | Burgers |",
        "|-----------|:-:|:-:|:-:|",
        f"| Baseline instability | {get('stokes_poiseuille','baseline_instability','.0%')} | {get('fisher_kpp','baseline_instability','.0%')} | {get('burgers','baseline_instability','.0%')} |",
        f"| Mean seed std | {get('stokes_poiseuille','mean_seed_std','.4f')} | {get('fisher_kpp','mean_seed_std','.4f')} | {get('burgers','mean_seed_std','.4f')} |",
        f"| Avg cross rate | {get('stokes_poiseuille','avg_cross_rate','.1%')} | {get('fisher_kpp','avg_cross_rate','.1%')} | {get('burgers','avg_cross_rate','.1%')} |",
        "",
        "### Key observations:",
        "",
        "- **Stokes**: Sharp, regular boundary. Safest cell shows 0% failure. Low seed variance (0.0058). Drops quickly into failure with added noise.",
        "- **Fisher-KPP**: Intermediate. Safest cell 0% failure, but seed variance is 2x Stokes (0.0107). Boundaries are moderately sharp — more seed-dependent than Stokes but less than Burgers.",
        "- **Burgers**: Wide, probabilistic boundary. Safest cell already shows 40% failure. Highest seed variance (0.0137). No 'safe' cells by strict definition. Boundary is a probability distribution, not a line.",
        "",
        "### Note on transition metrics:",
        "Transition cell counts and gap metrics depend on grid resolution. Stokes and Fisher-KPP use 4x7 grids (different obs ranges), Burgers uses 5x5. Direct comparison of these specific metrics should be done with caution. The most reliable cross-system metrics are baseline instability, mean seed std, and avg cross rate.",
        "",
    ])

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_metrics = {}
    
    for sys_info in SYSTEMS:
        name = sys_info["name"]
        display = sys_info["display"]
        matrix_name = sys_info["matrix"]
        
        print(f"\nProcessing {display} ({matrix_name})...")
        
        df = load_probability_data(matrix_name)
        print(f"  Loaded {len(df)} summary rows")
        
        metrics = compute_boundary_metrics(df)
        all_metrics[name] = metrics
        
        print(f"  Safest cell: obs={metrics['safest_cell']['num_observation']}, "
              f"noise={metrics['safest_cell']['noise_std']:.3f}, "
              f"cross_rate={metrics['safest_cell']['cross_rate']:.0%}")
        print(f"  Cells: {metrics['n_safe_cells']} safe / {metrics['n_transition_cells']} transition / "
              f"{metrics['n_failure_cells']} failure")
        print(f"  Mean seed std: {metrics['mean_seed_std']:.4f}")
        if metrics['avg_transition_gap'] is not None:
            print(f"  Avg transition gap: {metrics['avg_transition_gap']:.3f}")

    # Save summary
    summary = {
        name: {k: v for k, v in metrics.items() if k != "cell_metrics"}
        for name, metrics in all_metrics.items()
    }
    with (OUTPUT_DIR / "boundary_comparison.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2, default=str)

    # Write markdown summary
    md = build_summary_table(all_metrics)
    (OUTPUT_DIR / "boundary_comparison.md").write_text(md, encoding="utf-8")

    # Generate plots
    plot_combined_boundaries(all_metrics, OUTPUT_DIR / "figure_boundary_comparison_heatmaps.png")
    plot_transition_profile(all_metrics, OUTPUT_DIR / "figure_boundary_transition_profiles.png")

    print(f"\nResults written to: {OUTPUT_DIR}")
    print(md)


if __name__ == "__main__":
    main()
