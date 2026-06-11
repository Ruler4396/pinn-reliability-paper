"""
Direct Degradation Metric Correlations
=======================================
Computes direct correlations between landscape metrics and degradation metrics.

Landscape Metrics (all 10 PDEs):
- d_null: null space dimension
- lambda_max: max Hessian eigenvalue (curvature)
- entropy: Hessian spectral entropy
- infoCV: information density CV

Degradation Metrics:
- boundary_width: number of failure keypoints per seed
- transition_width: width of transition zone
- seedCV: seed variance coefficient of variation
- irregularity: boundary irregularity (jump rate)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

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
OUTPUT_DIR = RESULTS_DIR / "analysis" / "degradation_correlation_v1"

# All 10 PDE cases
CASES = {
    "poisson": {"display": "Poisson", "display_zh": "Poisson方程"},
    "stokes_poiseuille": {"display": "Stokes-Poiseuille", "display_zh": "斯托克斯-泊肃叶流"},
    "allen_cahn": {"display": "Allen-Cahn", "display_zh": "Allen-Cahn方程"},
    "fisher_kpp": {"display": "Fisher-KPP", "display_zh": "Fisher-KPP方程"},
    "burgers": {"display": "Burgers", "display_zh": "Burgers方程"},
    "heat_equation": {"display": "Heat Equation", "display_zh": "热方程"},
    "kdv_soliton": {"display": "KdV Soliton", "display_zh": "KdV孤子"},
    "nls_soliton": {"display": "NLS Soliton", "display_zh": "NLS孤子"},
    "wave_equation": {"display": "Wave Equation", "display_zh": "波动方程"},
    "kdv_double_soliton": {"display": "KdV Double", "display_zh": "KdV双孤子"},
}

# Thresholds for each case
THRESHOLDS = {
    "poisson": 0.11297,
    "stokes_poiseuille": 0.015379,
    "allen_cahn": 0.05,
    "fisher_kpp": 0.018861,
    "burgers": 0.026688,
    "heat_equation": 0.05,
    "kdv_soliton": 0.05,
    "nls_soliton": 0.05,
    "wave_equation": 0.05,
    "kdv_double_soliton": 0.05,
}


# ═══════════════════════════════════════════════════════════
#  Landscape Metrics (from previous analyses)
# ═══════════════════════════════════════════════════════════

def load_landscape_metrics() -> Dict[str, Dict[str, float]]:
    """Load landscape metrics from previous analyses."""
    
    # Null space dimension (all 10)
    d_null = {
        "poisson": 18, "stokes_poiseuille": 19, "allen_cahn": 29,
        "fisher_kpp": 34, "burgers": 27, "heat_equation": 26,
        "kdv_soliton": 38, "nls_soliton": 23, "wave_equation": 17,
        "kdv_double_soliton": 32,
    }
    
    # Curvature - lambda_max (all 10)
    lambda_max = {
        "poisson": 2540.0, "stokes_poiseuille": 446.0, "allen_cahn": 555.0,
        "fisher_kpp": 269.0, "burgers": 1300.0, "heat_equation": 903.0,
        "kdv_soliton": 906.0, "nls_soliton": 473.0, "wave_equation": 1111.0,
        "kdv_double_soliton": 2890.0,
    }
    
    # Hessian entropy (all 10)
    entropy = {
        "poisson": 3.9679, "stokes_poiseuille": 3.9821, "allen_cahn": 3.7366,
        "fisher_kpp": 3.8574, "burgers": 3.7846, "heat_equation": 3.7835,
        "kdv_soliton": 3.5509, "nls_soliton": 3.8558, "wave_equation": 3.8830,
        "kdv_double_soliton": 3.6104,
    }
    
    # Information density CV (all 10)
    info_cv = {
        "poisson": 0.3035, "stokes_poiseuille": 0.1938, "allen_cahn": 1.1782,
        "fisher_kpp": 0.8504, "burgers": 0.4512, "heat_equation": 0.4506,
        "kdv_soliton": 1.6765, "nls_soliton": 1.6215, "wave_equation": 0.3033,
        "kdv_double_soliton": 2.0035,
    }
    
    cases = list(d_null.keys())
    data = {}
    for case in cases:
        data[case] = {
            "d_null": d_null[case],
            "lambda_max": lambda_max[case],
            "entropy": entropy[case],
            "info_cv": info_cv[case],
        }
    
    return data


# ═══════════════════════════════════════════════════════════
#  Degradation Metrics (computed from probe data)
# ═══════════════════════════════════════════════════════════

def compute_degradation_metrics() -> Dict[str, Dict[str, float]]:
    """Compute degradation metrics from probe data."""
    
    degradation = {}
    
    for case_name in CASES:
        probe_dir = PROBES_DIR / f"keypoints_v2_{case_name}"
        runs_csv = probe_dir / "probe_runs.csv"
        
        if not runs_csv.exists():
            continue
        
        df = pd.read_csv(runs_csv)
        threshold = THRESHOLDS.get(case_name, 0.05)
        
        # Boundary width: number of failure keypoints per seed
        boundary_widths = []
        for seed in df["seed"].unique():
            seed_data = df[df["seed"] == seed]
            n_fail = (seed_data["rel_l2"] > threshold).sum()
            boundary_widths.append(n_fail)
        
        # Transition width: number of keypoints with crossing rate between 0.2 and 0.8
        cross_rates = []
        for label in df["label"].unique():
            label_data = df[df["label"] == label]
            rate = (label_data["rel_l2"] > threshold).mean()
            cross_rates.append(rate)
        
        cross_rates = np.array(cross_rates)
        n_transition = np.sum((cross_rates > 0.2) & (cross_rates < 0.8))
        transition_width = n_transition / len(cross_rates) if len(cross_rates) > 0 else 0
        
        # Seed CV: coefficient of variation of rel_l2 across seeds
        seed_stds = []
        for label in df["label"].unique():
            label_data = df[df["label"] == label]
            if len(label_data) > 1:
                seed_stds.append(label_data["rel_l2"].std())
        
        seed_cv = np.mean(seed_stds) if seed_stds else 0
        
        # Irregularity: max jump in crossing rates
        sorted_rates = np.sort(cross_rates)
        if len(sorted_rates) >= 2:
            jumps = np.abs(np.diff(sorted_rates))
            irregularity = float(np.max(jumps))
        else:
            irregularity = 0
        
        degradation[case_name] = {
            "boundary_width": float(np.mean(boundary_widths)),
            "transition_width": float(transition_width),
            "seed_cv": float(seed_cv),
            "irregularity": float(irregularity),
        }
        
        display = CASES[case_name]["display"]
        print(f"  {display}: BW={degradation[case_name]['boundary_width']:.2f}, "
              f"TW={degradation[case_name]['transition_width']:.3f}, "
              f"seedCV={degradation[case_name]['seed_cv']:.4f}, "
              f"irr={degradation[case_name]['irregularity']:.3f}")
    
    return degradation


# ═══════════════════════════════════════════════════════════
#  Correlation Analysis
# ═══════════════════════════════════════════════════════════

def compute_direct_correlations(
    landscape: Dict[str, Dict[str, float]],
    degradation: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """Compute direct correlations between landscape and degradation metrics."""
    
    # Define the four specific correlations
    correlations = [
        ("d_null", "boundary_width", "d_null <-> boundary_width"),
        ("lambda_max", "transition_width", "lambda_max <-> transition_width"),
        ("entropy", "seed_cv", "entropy <-> seedCV"),
        ("info_cv", "irregularity", "infoCV <-> irregularity"),
    ]
    
    results = {}
    
    # Get common cases
    common_cases = [c for c in landscape if c in degradation]
    
    for landscape_metric, degradation_metric, label in correlations:
        x_vals = []
        y_vals = []
        case_names = []
        
        for case in common_cases:
            if landscape_metric in landscape[case] and degradation_metric in degradation[case]:
                x_vals.append(landscape[case][landscape_metric])
                y_vals.append(degradation[case][degradation_metric])
                case_names.append(case)
        
        if len(x_vals) >= 3:
            corr, p = sp_stats.spearmanr(x_vals, y_vals)
            results[label] = {
                "landscape_metric": landscape_metric,
                "degradation_metric": degradation_metric,
                "correlation": float(corr),
                "p_value": float(p),
                "n_cases": len(x_vals),
                "cases": case_names,
                "x_values": x_vals,
                "y_values": y_vals,
            }
            
            sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
            print(f"  {label}: r={corr:.3f}, p={p:.3f} {sig} (n={len(x_vals)})")
    
    return results


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_direct_correlations(
    corr_results: Dict[str, Any],
    landscape: Dict[str, Dict[str, float]],
    degradation: Dict[str, Dict[str, float]],
    output_dir: Path,
):
    """Plot the four direct correlations."""
    
    displays = {
        "poisson": "Poisson", "stokes_poiseuille": "Stokes",
        "allen_cahn": "Allen-Cahn", "fisher_kpp": "Fisher-KPP",
        "burgers": "Burgers", "heat_equation": "Heat",
        "kdv_soliton": "KdV", "nls_soliton": "NLS",
        "wave_equation": "Wave", "kdv_double_soliton": "KdV2",
    }
    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513", "#6A5ACD",
              "#FF6347", "#4169E1", "#32CD32", "#FF8C00", "#9370DB"]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    for idx, (label, result) in enumerate(corr_results.items()):
        ax = axes[idx // 2, idx % 2]
        
        x_vals = result["x_values"]
        y_vals = result["y_values"]
        case_names = result["cases"]
        corr = result["correlation"]
        p = result["p_value"]
        
        # Plot points
        for i, (x, y, case) in enumerate(zip(x_vals, y_vals, case_names)):
            color_idx = list(CASES.keys()).index(case)
            ax.scatter(x, y, c=colors[color_idx], s=120, alpha=0.8,
                      edgecolors="white", linewidth=1.5, zorder=5)
            ax.annotate(displays.get(case, case), (x, y),
                       fontsize=8, ha="center", va="bottom",
                       xytext=(0, 8), textcoords="offset points")
        
        # Fit line
        if len(x_vals) > 2:
            z = np.polyfit(x_vals, y_vals, 1)
            p_line = np.poly1d(z)
            x_line = np.linspace(min(x_vals), max(x_vals), 100)
            ax.plot(x_line, p_line(x_line), "--", color="gray", alpha=0.5)
        
        # Add correlation info
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        ax.text(0.05, 0.95, f"r = {corr:.3f} {sig}\np = {p:.3f}\nn = {len(x_vals)}",
                transform=ax.transAxes, fontsize=10, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
        
        ax.set_xlabel(result["landscape_metric"], fontsize=11)
        ax.set_ylabel(result["degradation_metric"], fontsize=11)
        ax.set_title(label, fontsize=12)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle("Direct Correlations: Landscape Metrics vs Degradation Metrics", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_direct_correlations.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_direct_correlations.png")


def plot_correlation_summary(
    corr_results: Dict[str, Any],
    output_dir: Path,
):
    """Plot correlation summary bar chart."""
    
    labels = list(corr_results.keys())
    corrs = [corr_results[l]["correlation"] for l in labels]
    p_vals = [corr_results[l]["p_value"] for l in labels]
    
    # Short labels for display
    short_labels = [
        "d_null\n<->\nboundary_width",
        "lambda_max\n<->\ntransition_width",
        "entropy\n<->\nseedCV",
        "infoCV\n<->\nirregularity",
    ]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ["#1f4e79" if c > 0 else "#b64040" for c in corrs]
    
    bars = ax.bar(short_labels, corrs, color=colors, alpha=0.8, width=0.5)
    
    for bar, corr, p in zip(bars, corrs, p_vals):
        y_pos = bar.get_height() + 0.02 if bar.get_height() >= 0 else bar.get_height() - 0.05
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                f"r={corr:.3f}\n{sig}", ha="center", va="bottom", fontsize=10)
    
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax.set_ylabel("Spearman Correlation", fontsize=12)
    ax.set_title("Direct Correlations: Landscape Metrics vs Degradation Metrics", fontsize=13)
    ax.set_ylim(-1.1, 1.1)
    ax.grid(True, alpha=0.3, axis="y")
    
    ax.text(0.98, 0.02, "*** p<0.01, ** p<0.05, * p<0.1, ns: not significant",
            transform=ax.transAxes, fontsize=9, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_correlation_summary.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_correlation_summary.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    landscape: Dict[str, Dict[str, float]],
    degradation: Dict[str, Dict[str, float]],
    corr_results: Dict[str, Any],
) -> str:
    """Generate summary report."""
    
    lines = [
        "# 直接相关性分析：景观指标 vs 退化指标",
        "",
        "## 概述",
        "",
        "本分析直接计算景观指标与退化指标之间的相关性。",
        "",
        "---",
        "",
        "## 数据表",
        "",
        "### 表1: 边界宽度 (boundary_width)",
        "",
        "| PDE | boundary_width |",
        "|-----|---------------|",
    ]
    
    for case in CASES:
        if case in degradation:
            display = CASES[case]["display"]
            bw = degradation[case]["boundary_width"]
            lines.append(f"| {display} | {bw:.2f} |")
    
    lines.extend([
        "",
        "### 表2: 过渡带宽度 (transition_width)",
        "",
        "| PDE | transition_width |",
        "|-----|-----------------|",
    ])
    
    for case in CASES:
        if case in degradation:
            display = CASES[case]["display"]
            tw = degradation[case]["transition_width"]
            lines.append(f"| {display} | {tw:.3f} |")
    
    lines.extend([
        "",
        "### 表3: 种子变异系数 (seedCV)",
        "",
        "| PDE | seedCV |",
        "|-----|--------|",
    ])
    
    for case in CASES:
        if case in degradation:
            display = CASES[case]["display"]
            scv = degradation[case]["seed_cv"]
            lines.append(f"| {display} | {scv:.4f} |")
    
    lines.extend([
        "",
        "### 表4: 边界不规则性 (irregularity)",
        "",
        "| PDE | irregularity |",
        "|-----|-------------|",
    ])
    
    for case in CASES:
        if case in degradation:
            display = CASES[case]["display"]
            irr = degradation[case]["irregularity"]
            lines.append(f"| {display} | {irr:.3f} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 相关性结果",
        "",
        "| 相关性 | Spearman r | p 值 | 显著性 | n |",
        "|--------|-----------|------|--------|---|",
    ])
    
    for label, result in corr_results.items():
        sig = "***" if result["p_value"] < 0.01 else "**" if result["p_value"] < 0.05 else "*" if result["p_value"] < 0.1 else "ns"
        lines.append(f"| {label} | {result['correlation']:.3f} | {result['p_value']:.3f} | {sig} | {result['n_cases']} |")
    
    lines.extend([
        "",
        "*** p<0.01, ** p<0.05, * p<0.1",
        "",
        "---",
        "",
        "## 解释",
        "",
        "### d_null <-> boundary_width",
        "",
        "- 零空间维度越高，边界越宽",
        "- 物理解释：更多近零方向 → 更多退化路径",
        "",
        "### lambda_max <-> transition_width",
        "",
        "- 曲率越高，过渡带越窄",
        "- 物理解释：高曲率 → 陡峭损失景观 → 尖锐边界",
        "",
        "### entropy <-> seedCV",
        "",
        "- 熵越高，种子方差越大",
        "- 物理解释：复杂景观 → 多个局部最优 → 种子敏感",
        "",
        "### infoCV <-> irregularity",
        "",
        "- 信息分布越不均匀，边界越不规则",
        "- 物理解释：信息集中 → 学习不均衡 → 不规则边界",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Direct Degradation Metric Correlations")
    print("=" * 60)
    
    # Load landscape metrics
    print("\n[1/4] Loading landscape metrics...")
    landscape = load_landscape_metrics()
    print(f"  Loaded {len(landscape)} cases")
    
    # Compute degradation metrics
    print("\n[2/4] Computing degradation metrics...")
    degradation = compute_degradation_metrics()
    
    # Compute correlations
    print("\n[3/4] Computing direct correlations...")
    corr_results = compute_direct_correlations(landscape, degradation)
    
    # Generate figures
    print("\n[4/4] Generating figures...")
    plot_direct_correlations(corr_results, landscape, degradation, OUTPUT_DIR)
    plot_correlation_summary(corr_results, OUTPUT_DIR)
    
    # Save results
    print("\nSaving results...")
    
    json_results = {
        "landscape_metrics": landscape,
        "degradation_metrics": degradation,
        "correlations": corr_results,
    }
    with open(OUTPUT_DIR / "degradation_correlation_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"  Saved: degradation_correlation_results.json")
    
    summary = generate_summary(landscape, degradation, corr_results)
    (OUTPUT_DIR / "degradation_correlation_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: degradation_correlation_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")
    print(summary)


if __name__ == "__main__":
    main()
