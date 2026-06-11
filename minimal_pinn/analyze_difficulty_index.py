"""
Difficulty Index Analysis
=========================
Task H: Construct Difficulty index and compute correlations.

Difficulty = z(log(FinalLoss)) + z(PhysicalLossRatio)

Then compute:
- Difficulty <-> boundary_width
- Difficulty <-> seed_variability
- Difficulty <-> probability_band_area
- Difficulty <-> mean_failure_entropy
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "difficulty_index_v1"


# All 10 cases
CASES = {
    "poisson": {"display": "Poisson", "display_zh": "Poisson方程", "prototype": "Non-Degrading", "probe": "keypoints_v2_poisson", "condition": "obs64_noise000", "threshold": 0.11297},
    "stokes_poiseuille": {"display": "Stokes-Poiseuille", "display_zh": "斯托克斯-泊肃叶流", "prototype": "Sharp Boundary", "probe": "keypoints_v2_stokes", "condition": "obs128_noise000", "threshold": 0.015379},
    "allen_cahn": {"display": "Allen-Cahn", "display_zh": "Allen-Cahn方程", "prototype": "Broad Band", "probe": "keypoints_v2_allen_cahn", "condition": "obs256_noise000", "threshold": 0.05},
    "fisher_kpp": {"display": "Fisher-KPP", "display_zh": "Fisher-KPP方程", "prototype": "Intermediate", "probe": "keypoints_v2_fisher_kpp", "condition": "obs64_noise000", "threshold": 0.018861},
    "burgers": {"display": "Burgers", "display_zh": "Burgers方程", "prototype": "Broad Band", "probe": "keypoints_v2_burgers", "condition": "obs128_noise000", "threshold": 0.026688},
    "heat_equation": {"display": "Heat Equation", "display_zh": "热方程", "prototype": "Broad Band", "probe": "keypoints_v2_heat_equation", "condition": "obs256_noise000", "threshold": 0.05},
    "kdv_soliton": {"display": "KdV Soliton", "display_zh": "KdV孤子", "prototype": "Broad Band", "probe": "keypoints_v2_kdv_soliton", "condition": "obs256_noise000", "threshold": 0.05},
    "nls_soliton": {"display": "NLS Soliton", "display_zh": "NLS孤子", "prototype": "Broad Band", "probe": "keypoints_v2_nls_soliton", "condition": "obs256_noise000", "threshold": 0.05},
    "wave_equation": {"display": "Wave Equation", "display_zh": "波动方程", "prototype": "Broad Band", "probe": "keypoints_v2_wave_equation", "condition": "obs256_noise000", "threshold": 0.05},
    "kdv_double_soliton": {"display": "KdV Double", "display_zh": "KdV双孤子", "prototype": "Broad Band", "probe": "keypoints_v2_kdv_double_soliton", "condition": "obs512_noise000", "threshold": 0.05},
}


# ═══════════════════════════════════════════════════════════
#  Data Loading
# ═══════════════════════════════════════════════════════════

def load_training_metrics() -> Dict[str, Dict[str, float]]:
    """Load final loss and physics loss ratio from training curves."""
    
    results = {}
    
    for case_name, info in CASES.items():
        probe_dir = PROBES_DIR / info["probe"] / "runs"
        
        # Find run directory
        run_dir = None
        for d in probe_dir.iterdir():
            if d.is_dir() and info["condition"] in d.name and "seed1" in d.name:
                run_dir = d
                break
        
        if run_dir is None:
            continue
        
        history_path = run_dir / "history.csv"
        if not history_path.exists():
            continue
        
        df = pd.read_csv(history_path)
        
        # Final loss (average of last 10 epochs)
        final_loss = float(df["loss_total"].iloc[-10:].mean())
        
        # Physics loss ratio at final epoch
        final_total = float(df["loss_total"].iloc[-1])
        final_physics = float(df["loss_physics"].iloc[-1])
        physics_ratio = final_physics / final_total if final_total > 0 else 0
        
        results[case_name] = {
            "display": info["display"],
            "prototype": info["prototype"],
            "final_loss": final_loss,
            "log_final_loss": float(np.log(final_loss + 1e-10)),
            "physics_loss_ratio": float(physics_ratio),
        }
    
    return results


def load_degradation_metrics() -> Dict[str, Dict[str, float]]:
    """Load degradation metrics from previous analyses."""
    
    # Load from effective_degradation results
    results_path = RESULTS_DIR / "analysis" / "effective_degradation_v1" / "effective_degradation_results.json"
    
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("degradation_metrics", {})
    
    # Fallback: compute from probe data
    results = {}
    
    for case_name, info in CASES.items():
        probe_dir = PROBES_DIR / info["probe"] / "runs"
        runs_csv = PROBES_DIR / info["probe"] / "probe_runs.csv"
        
        if not runs_csv.exists():
            continue
        
        df = pd.read_csv(runs_csv)
        threshold = info["threshold"]
        
        # Crossing rates per keypoint
        cross_rates = []
        seed_stds = []
        
        for label in df["label"].unique():
            label_data = df[df["label"] == label]
            rate = (label_data["rel_l2"] > threshold).mean()
            cross_rates.append(rate)
            if len(label_data) > 1:
                seed_stds.append(label_data["rel_l2"].std())
        
        cross_rates = np.array(cross_rates)
        
        # Probability band area
        n_transition = np.sum((cross_rates >= 0.2) & (cross_rates <= 0.8))
        prob_band_area = n_transition / len(cross_rates) if len(cross_rates) > 0 else 0
        
        # Mean failure entropy
        entropies = []
        for rate in cross_rates:
            if 0 < rate < 1:
                h = -rate * np.log(rate) - (1 - rate) * np.log(1 - rate)
                entropies.append(h)
            else:
                entropies.append(0)
        mean_failure_entropy = np.mean(entropies) if entropies else 0
        
        # Seed variability
        seed_variability = np.mean(seed_stds) if seed_stds else 0
        
        results[case_name] = {
            "probability_band_area": float(prob_band_area),
            "mean_failure_entropy": float(mean_failure_entropy),
            "seed_variability": float(seed_variability),
        }
    
    return results


def load_boundary_width() -> Dict[str, float]:
    """Load boundary width data."""
    
    boundary_width = {
        "poisson": 1.33, "stokes_poiseuille": 3.67, "allen_cahn": 2.37,
        "fisher_kpp": 5.13, "burgers": 4.77, "heat_equation": 3.03,
        "kdv_soliton": 5.50, "nls_soliton": 6.80, "wave_equation": 7.60,
        "kdv_double_soliton": 8.00,
    }
    
    return boundary_width


# ═══════════════════════════════════════════════════════════
#  Task H: Difficulty Index
# ═══════════════════════════════════════════════════════════

def compute_difficulty_index(
    training: Dict[str, Dict],
) -> Dict[str, Dict[str, float]]:
    """Compute Difficulty = z(log(FinalLoss)) + z(PhysicsLossRatio)"""
    
    cases = list(training.keys())
    
    # Extract values
    log_final_loss = np.array([training[c]["log_final_loss"] for c in cases])
    physics_ratio = np.array([training[c]["physics_loss_ratio"] for c in cases])
    
    # Standardize
    z_log_loss = (log_final_loss - log_final_loss.mean()) / log_final_loss.std()
    z_phys_ratio = (physics_ratio - physics_ratio.mean()) / physics_ratio.std()
    
    # Difficulty index
    difficulty = z_log_loss + z_phys_ratio
    
    # Add to results
    for i, case in enumerate(cases):
        training[case]["z_log_final_loss"] = float(z_log_loss[i])
        training[case]["z_physics_ratio"] = float(z_phys_ratio[i])
        training[case]["difficulty"] = float(difficulty[i])
    
    return training


def compute_correlations(
    training: Dict[str, Dict],
    degradation: Dict[str, Dict],
    boundary_width: Dict[str, float],
) -> Dict[str, Any]:
    """Compute correlations between Difficulty and degradation metrics."""
    
    common_cases = [c for c in training if c in degradation]
    
    # Define correlations
    correlations = [
        ("difficulty", "boundary_width", "Difficulty <-> boundary_width"),
        ("difficulty", "seed_variability", "Difficulty <-> seed_var"),
        ("difficulty", "probability_band_area", "Difficulty <-> PBA"),
        ("difficulty", "mean_failure_entropy", "Difficulty <-> MFE"),
    ]
    
    results = {}
    
    for x_metric, y_metric, label in correlations:
        x_vals = []
        y_vals = []
        case_names = []
        
        for case in common_cases:
            if x_metric in training[case]:
                x_val = training[case][x_metric]
                
                if y_metric == "boundary_width":
                    y_val = boundary_width.get(case)
                elif y_metric in degradation.get(case, {}):
                    y_val = degradation[case][y_metric]
                else:
                    continue
                
                if y_val is not None:
                    x_vals.append(x_val)
                    y_vals.append(y_val)
                    case_names.append(case)
        
        if len(x_vals) >= 3:
            spearman_r, spearman_p = sp_stats.spearmanr(x_vals, y_vals)
            pearson_r, pearson_p = sp_stats.pearsonr(x_vals, y_vals)
            
            # Bootstrap CI
            n_boot = 1000
            rng = np.random.RandomState(42)
            boot_corrs = []
            for _ in range(n_boot):
                idx = rng.choice(len(x_vals), size=len(x_vals), replace=True)
                boot_corr, _ = sp_stats.spearmanr(
                    [x_vals[i] for i in idx],
                    [y_vals[i] for i in idx]
                )
                if not np.isnan(boot_corr):
                    boot_corrs.append(boot_corr)
            
            ci_lower = float(np.percentile(boot_corrs, 2.5))
            ci_upper = float(np.percentile(boot_corrs, 97.5))
            
            results[label] = {
                "x_metric": x_metric,
                "y_metric": y_metric,
                "spearman_r": float(spearman_r),
                "spearman_p": float(spearman_p),
                "pearson_r": float(pearson_r),
                "pearson_p": float(pearson_p),
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "n_cases": len(x_vals),
                "cases": case_names,
                "x_values": x_vals,
                "y_values": y_vals,
            }
    
    return results


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_difficulty_ranking(
    training: Dict[str, Dict],
    output_dir: Path,
):
    """Plot Difficulty ranking."""
    
    cases = sorted(training.keys(), key=lambda c: training[c]["difficulty"])
    
    displays = [CASES[c]["display"] for c in cases]
    difficulties = [training[c]["difficulty"] for c in cases]
    
    prototype_colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    colors = [prototype_colors.get(training[c]["prototype"], "#666") for c in cases]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars = ax.barh(range(len(cases)), difficulties, color=colors, alpha=0.8)
    ax.set_yticks(range(len(cases)))
    ax.set_yticklabels(displays, fontsize=10)
    ax.set_xlabel("Difficulty = z(log(FinalLoss)) + z(PhysicsRatio)", fontsize=12)
    ax.set_title("Task H: Difficulty Index Ranking", fontsize=14)
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="x")
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=p) for p, c in prototype_colors.items()]
    ax.legend(handles=legend_elements, fontsize=9, loc="lower right")
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_difficulty_ranking.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_difficulty_ranking.png")


def plot_correlations(
    training: Dict[str, Dict],
    degradation: Dict[str, Dict],
    boundary_width: Dict[str, float],
    corr_results: Dict[str, Any],
    output_dir: Path,
):
    """Plot Difficulty vs degradation metrics."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    prototype_colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    
    for idx, (label, result) in enumerate(corr_results.items()):
        ax = axes[idx // 2, idx % 2]
        
        x_vals = result["x_values"]
        y_vals = result["y_values"]
        case_names = result["cases"]
        
        for i, (x, y, case) in enumerate(zip(x_vals, y_vals, case_names)):
            proto = training[case]["prototype"]
            ax.scatter(x, y, c=prototype_colors.get(proto, "#666"), s=120, alpha=0.8,
                      edgecolors="white", linewidth=1.5, zorder=5)
            ax.annotate(CASES[case]["display"], (x, y),
                       fontsize=8, ha="center", va="bottom",
                       xytext=(0, 8), textcoords="offset points")
        
        # Fit line
        if len(x_vals) > 2:
            z = np.polyfit(x_vals, y_vals, 1)
            p_line = np.poly1d(z)
            x_line = np.linspace(min(x_vals), max(x_vals), 100)
            ax.plot(x_line, p_line(x_line), "--", color="gray", alpha=0.5)
        
        sig = "***" if result["spearman_p"] < 0.01 else "**" if result["spearman_p"] < 0.05 else "*" if result["spearman_p"] < 0.1 else "ns"
        ax.text(0.05, 0.95, f"r={result['spearman_r']:.3f} {sig}\np={result['spearman_p']:.3f}\n"
                f"95% CI [{result['ci_lower']:.3f}, {result['ci_upper']:.3f}]",
                transform=ax.transAxes, fontsize=9, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
        
        ax.set_xlabel("Difficulty", fontsize=11)
        ax.set_ylabel(result["y_metric"], fontsize=11)
        ax.set_title(label, fontsize=11)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle("Task H: Difficulty vs Degradation Metrics", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_difficulty_correlations.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_difficulty_correlations.png")


def plot_components(
    training: Dict[str, Dict],
    output_dir: Path,
):
    """Plot Difficulty components."""
    
    cases = list(training.keys())
    displays = [CASES[c]["display"] for c in cases]
    
    prototype_colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    colors = [prototype_colors.get(training[c]["prototype"], "#666") for c in cases]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Component 1: z(log(FinalLoss))
    ax = axes[0]
    values = [training[c]["z_log_final_loss"] for c in cases]
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("z(log(FinalLoss))", fontsize=11)
    ax.set_title("Component 1: log(FinalLoss)", fontsize=12)
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    
    # Component 2: z(PhysicsRatio)
    ax = axes[1]
    values = [training[c]["z_physics_ratio"] for c in cases]
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("z(PhysicsLossRatio)", fontsize=11)
    ax.set_title("Component 2: PhysicsLossRatio", fontsize=12)
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    
    # Combined: Difficulty
    ax = axes[2]
    values = [training[c]["difficulty"] for c in cases]
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Difficulty", fontsize=11)
    ax.set_title("Combined: Difficulty Index", fontsize=12)
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=p) for p, c in prototype_colors.items()]
    axes[2].legend(handles=legend_elements, fontsize=8, loc="upper left")
    
    fig.suptitle("Task H: Difficulty Index Components", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_difficulty_components.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_difficulty_components.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    training: Dict[str, Dict],
    corr_results: Dict[str, Any],
) -> str:
    """Generate summary report."""
    
    lines = [
        "# Difficulty Index分析报告",
        "",
        "## 概述",
        "",
        "本分析构造Difficulty指标并计算与退化指标的相关性。",
        "",
        "### Difficulty定义",
        "",
        "```",
        "Difficulty = z(log(FinalLoss)) + z(PhysicsLossRatio)",
        "```",
        "",
        "---",
        "",
        "## Difficulty排名",
        "",
        "| Rank | PDE | 原型 | log(FinalLoss) | PhysicsRatio | Difficulty |",
        "|------|-----|------|---------------|--------------|------------|",
    ]
    
    sorted_cases = sorted(training.keys(), key=lambda c: training[c]["difficulty"])
    
    for rank, case in enumerate(sorted_cases, 1):
        d = training[case]
        lines.append(
            f"| {rank} | {CASES[case]['display']} | {d['prototype']} | "
            f"{d['log_final_loss']:.2f} | {d['physics_loss_ratio']:.4f} | "
            f"{d['difficulty']:.3f} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Difficulty与退化指标的相关性",
        "",
        "| 相关性 | Spearman r | 95% CI | p | 显著性 |",
        "|--------|-----------|--------|---|--------|",
    ])
    
    for label, result in corr_results.items():
        sig = "***" if result["spearman_p"] < 0.01 else "**" if result["spearman_p"] < 0.05 else "*" if result["spearman_p"] < 0.1 else "ns"
        lines.append(
            f"| {label} | {result['spearman_r']:.3f} | "
            f"[{result['ci_lower']:.3f}, {result['ci_upper']:.3f}] | "
            f"{result['spearman_p']:.3f} | {sig} |"
        )
    
    lines.extend([
        "",
        "*** p<0.01, ** p<0.05, * p<0.1",
        "",
        "---",
        "",
        "## 结论",
        "",
        "### Difficulty是否能预测退化行为？",
        "",
        "如果Difficulty与退化指标显著相关，则说明训练难度可以预测退化行为。",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Difficulty Index Analysis")
    print("=" * 60)
    
    # Load data
    print("\n[1/5] Loading training metrics...")
    training = load_training_metrics()
    print(f"  Loaded {len(training)} cases")
    
    # Compute Difficulty
    print("\n[2/5] Computing Difficulty index...")
    training = compute_difficulty_index(training)
    
    # Print ranking
    sorted_cases = sorted(training.keys(), key=lambda c: training[c]["difficulty"])
    print("\n  Difficulty Ranking:")
    for rank, case in enumerate(sorted_cases, 1):
        d = training[case]
        print(f"  {rank}. {CASES[case]['display']:<20} Difficulty={d['difficulty']:.3f} "
              f"(z_log={d['z_log_final_loss']:.3f}, z_phys={d['z_physics_ratio']:.3f})")
    
    # Load degradation metrics
    print("\n[3/5] Loading degradation metrics...")
    degradation = load_degradation_metrics()
    boundary_width = load_boundary_width()
    print(f"  Loaded {len(degradation)} cases with degradation metrics")
    
    # Compute correlations
    print("\n[4/5] Computing correlations...")
    corr_results = compute_correlations(training, degradation, boundary_width)
    
    print("\n  Difficulty Correlations:")
    for label, result in corr_results.items():
        sig = "***" if result["spearman_p"] < 0.01 else "**" if result["spearman_p"] < 0.05 else "*" if result["spearman_p"] < 0.1 else "ns"
        print(f"  {label}: r={result['spearman_r']:.3f} [{result['ci_lower']:.3f}, {result['ci_upper']:.3f}] {sig}")
    
    # Generate figures
    print("\n[5/5] Generating figures...")
    plot_difficulty_ranking(training, OUTPUT_DIR)
    plot_correlations(training, degradation, boundary_width, corr_results, OUTPUT_DIR)
    plot_components(training, OUTPUT_DIR)
    
    # Save results
    print("\nSaving results...")
    
    all_results = {
        "difficulty_index": {c: {k: v for k, v in d.items() if k not in ["display", "prototype"]} 
                            for c, d in training.items()},
        "correlations": corr_results,
    }
    
    with open(OUTPUT_DIR / "difficulty_index_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Saved: difficulty_index_results.json")
    
    summary = generate_summary(training, corr_results)
    (OUTPUT_DIR / "difficulty_index_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: difficulty_index_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
