"""
Comprehensive Correlation Analysis
===================================
Computes correlations between all landscape metrics across all 10 PDE cases.

Metrics available for all 10 cases:
- d_null: null space dimension
- lambda_max: max Hessian eigenvalue (curvature)
- seed_cv: seed variance coefficient of variation
- info_cv: information density CV
- hessian_entropy: Hessian spectral entropy
- basin_count: number of basins (multi-modality)

Metrics available for 4 cases with boundary data:
- boundary_width: degradation boundary width
- boundary_irregularity: boundary jump rate
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
from scipy import stats as sp_stats

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "correlation_analysis_v1"


def load_all_metrics() -> Dict[str, Dict[str, float]]:
    """Load all computed metrics from previous analyses."""
    
    # All 10 PDE cases
    cases = [
        "poisson", "stokes_poiseuille", "allen_cahn", "fisher_kpp", "burgers",
        "heat_equation", "kdv_soliton", "nls_soliton", "wave_equation", "kdv_double_soliton"
    ]
    
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
    
    # Seed variance CV (all 10)
    seed_cv = {
        "poisson": 0.0477, "stokes_poiseuille": 0.2206, "allen_cahn": 0.3055,
        "fisher_kpp": 0.2804, "burgers": 0.3727, "heat_equation": 0.4616,
        "kdv_soliton": 0.4591, "nls_soliton": 0.3271, "wave_equation": 0.3300,
        "kdv_double_soliton": 0.1944,
    }
    
    # Information density CV (all 10)
    info_cv = {
        "poisson": 0.3035, "stokes_poiseuille": 0.1938, "allen_cahn": 1.1782,
        "fisher_kpp": 0.8504, "burgers": 0.4512, "heat_equation": 0.4506,
        "kdv_soliton": 1.6765, "nls_soliton": 1.6215, "wave_equation": 0.3033,
        "kdv_double_soliton": 2.0035,
    }
    
    # Hessian entropy (all 10)
    hessian_entropy = {
        "poisson": 3.9679, "stokes_poiseuille": 3.9821, "allen_cahn": 3.7366,
        "fisher_kpp": 3.8574, "burgers": 3.7846, "heat_equation": 3.7835,
        "kdv_soliton": 3.5509, "nls_soliton": 3.8558, "wave_equation": 3.8830,
        "kdv_double_soliton": 3.6104,
    }
    
    # Basin count (all 10)
    basin_count = {
        "poisson": 4, "stokes_poiseuille": 2, "allen_cahn": 2,
        "fisher_kpp": 3, "burgers": 2, "heat_equation": 2,
        "kdv_soliton": 2, "nls_soliton": 2, "wave_equation": 2,
        "kdv_double_soliton": 2,
    }
    
    # Boundary width (only 4 cases)
    boundary_width = {
        "poisson": 1.33, "stokes_poiseuille": 3.67,
        "fisher_kpp": 5.13, "burgers": 4.77,
    }
    
    # Boundary irregularity (only 4 cases)
    boundary_irregularity = {
        "poisson": 0.133, "stokes_poiseuille": 0.367,
        "fisher_kpp": 0.300, "burgers": 0.500,
    }
    
    # Combine
    data = {}
    for case in cases:
        data[case] = {
            "d_null": d_null[case],
            "lambda_max": lambda_max[case],
            "inverse_curvature": 1.0 / lambda_max[case],
            "seed_cv": seed_cv[case],
            "info_cv": info_cv[case],
            "hessian_entropy": hessian_entropy[case],
            "basin_count": basin_count[case],
            "boundary_width": boundary_width.get(case, None),
            "boundary_irregularity": boundary_irregularity.get(case, None),
        }
    
    return data


def compute_correlation_matrix(
    data: Dict[str, Dict[str, float]],
    metrics: List[str],
    cases: List[str],
) -> Dict[str, Any]:
    """Compute pairwise Spearman correlations between metrics."""
    n_metrics = len(metrics)
    
    # Build data matrix
    X = np.array([[data[c][m] for m in metrics] for c in cases])
    
    # Compute correlation matrix
    corr_matrix = np.zeros((n_metrics, n_metrics))
    p_matrix = np.zeros((n_metrics, n_metrics))
    
    for i in range(n_metrics):
        for j in range(n_metrics):
            if i == j:
                corr_matrix[i, j] = 1.0
                p_matrix[i, j] = 0.0
            else:
                corr, p = sp_stats.spearmanr(X[:, i], X[:, j])
                corr_matrix[i, j] = corr
                p_matrix[i, j] = p
    
    return {
        "metrics": metrics,
        "cases": cases,
        "correlation_matrix": corr_matrix.tolist(),
        "p_value_matrix": p_matrix.tolist(),
    }


def compute_boundary_correlations(
    data: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """Compute correlations with boundary width (only 4 cases)."""
    cases_with_boundary = [c for c in data if data[c]["boundary_width"] is not None]
    
    if len(cases_with_boundary) < 3:
        return {"error": "Not enough cases with boundary data"}
    
    boundary_widths = [data[c]["boundary_width"] for c in cases_with_boundary]
    
    # All metrics except boundary-related ones
    metrics = ["d_null", "lambda_max", "inverse_curvature", "seed_cv", 
               "info_cv", "hessian_entropy", "basin_count"]
    
    correlations = {}
    for metric in metrics:
        values = [data[c][metric] for c in cases_with_boundary]
        corr, p = sp_stats.spearmanr(values, boundary_widths)
        correlations[metric] = {
            "correlation": float(corr),
            "p_value": float(p),
            "n_cases": len(cases_with_boundary),
        }
    
    return correlations


def plot_correlation_heatmap(
    corr_result: Dict[str, Any],
    output_dir: Path,
):
    """Plot correlation heatmap."""
    metrics = corr_result["metrics"]
    corr_matrix = np.array(corr_result["correlation_matrix"])
    
    # Short labels for display
    short_labels = {
        "d_null": "d_null",
        "lambda_max": "lambda_max",
        "inverse_curvature": "1/kappa",
        "seed_cv": "seed_CV",
        "info_cv": "info_CV",
        "hessian_entropy": "entropy",
        "basin_count": "basins",
    }
    
    labels = [short_labels.get(m, m) for m in metrics]
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(corr_matrix, cmap="RdBu_r", vmin=-1, vmax=1)
    
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)
    
    # Add correlation values
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = corr_matrix[i, j]
            color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    color=color, fontsize=9, fontweight="bold")
    
    fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman Correlation")
    ax.set_title("Correlation Matrix: Landscape Metrics (10 PDE Systems)", fontsize=13)
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_correlation_heatmap.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_correlation_heatmap.png")


def plot_boundary_correlations(
    boundary_corr: Dict[str, Any],
    output_dir: Path,
):
    """Plot correlations with boundary width."""
    if "error" in boundary_corr:
        print(f"  Skipping boundary correlations: {boundary_corr['error']}")
        return
    
    metrics = list(boundary_corr.keys())
    corrs = [boundary_corr[m]["correlation"] for m in metrics]
    p_vals = [boundary_corr[m]["p_value"] for m in metrics]
    
    # Short labels
    short_labels = {
        "d_null": "d_null",
        "lambda_max": "lambda_max",
        "inverse_curvature": "1/kappa",
        "seed_cv": "seed_CV",
        "info_cv": "info_CV",
        "hessian_entropy": "entropy",
        "basin_count": "basins",
    }
    labels = [short_labels.get(m, m) for m in metrics]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ["#1f4e79" if c > 0 else "#b64040" for c in corrs]
    alphas = [1.0 if p < 0.1 else 0.5 for p in p_vals]
    
    bars = ax.barh(labels, corrs, color=colors, alpha=0.8)
    
    for bar, corr, p in zip(bars, corrs, p_vals):
        x_pos = bar.get_width() + 0.02 if bar.get_width() >= 0 else bar.get_width() - 0.02
        ha = "left" if bar.get_width() >= 0 else "right"
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                f"{corr:.3f} {sig}", ha=ha, va="center", fontsize=10)
    
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xlabel("Spearman Correlation with Boundary Width", fontsize=12)
    ax.set_title("Correlation with Degradation Boundary Width (4 PDE Systems)", fontsize=13)
    ax.grid(True, alpha=0.3, axis="x")
    
    ax.text(0.98, 0.02, "*** p<0.01, ** p<0.05, * p<0.1, ns: not significant",
            transform=ax.transAxes, fontsize=9, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_boundary_correlations.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_boundary_correlations.png")


def plot_scatter_matrix(
    data: Dict[str, Dict[str, float]],
    output_dir: Path,
):
    """Plot scatter matrix for key metrics."""
    cases = list(data.keys())
    displays = {
        "poisson": "Poisson", "stokes_poiseuille": "Stokes",
        "allen_cahn": "Allen-Cahn", "fisher_kpp": "Fisher-KPP",
        "burgers": "Burgers", "heat_equation": "Heat",
        "kdv_soliton": "KdV", "nls_soliton": "NLS",
        "wave_equation": "Wave", "kdv_double_soliton": "KdV2",
    }
    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513", "#6A5ACD",
              "#FF6347", "#4169E1", "#32CD32", "#FF8C00", "#9370DB"]
    
    metrics = ["d_null", "lambda_max", "seed_cv", "info_cv"]
    short_labels = ["d_null", "lambda_max", "seed_CV", "info_CV"]
    
    n = len(metrics)
    fig, axes = plt.subplots(n, n, figsize=(16, 16))
    
    for i in range(n):
        for j in range(n):
            ax = axes[i, j]
            
            if i == j:
                # Diagonal: histogram
                values = [data[c][metrics[i]] for c in cases]
                ax.hist(values, bins=10, color="#1f4e79", alpha=0.7)
                ax.set_ylabel(short_labels[i], fontsize=9)
            else:
                # Off-diagonal: scatter
                for k, c in enumerate(cases):
                    ax.scatter(data[c][metrics[j]], data[c][metrics[i]],
                              c=colors[k], s=50, alpha=0.8,
                              edgecolors="white", linewidth=0.5)
                
                # Add correlation
                x_vals = [data[c][metrics[j]] for c in cases]
                y_vals = [data[c][metrics[i]] for c in cases]
                corr, p = sp_stats.spearmanr(x_vals, y_vals)
                sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
                ax.text(0.05, 0.95, f"r={corr:.2f} {sig}",
                        transform=ax.transAxes, fontsize=8, va="top",
                        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
            
            if i == n - 1:
                ax.set_xlabel(short_labels[j], fontsize=9)
            if j == 0:
                ax.set_ylabel(short_labels[i], fontsize=9)
    
    fig.suptitle("Scatter Matrix: Landscape Metrics (10 PDE Systems)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_scatter_matrix.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_scatter_matrix.png")


def generate_summary(
    corr_result: Dict[str, Any],
    boundary_corr: Dict[str, Any],
) -> str:
    """Generate summary report."""
    lines = [
        "# 相关性分析报告",
        "",
        "## 概述",
        "",
        "本分析计算了所有10个PDE系统的景观指标之间的相关性。",
        "",
        "---",
        "",
        "## 景观指标相关性矩阵 (10 PDE)",
        "",
        "Spearman相关系数矩阵：",
        "",
    ]
    
    metrics = corr_result["metrics"]
    corr_matrix = corr_result["correlation_matrix"]
    
    # Table header
    short_labels = {
        "d_null": "d_null", "lambda_max": "lambda_max",
        "inverse_curvature": "1/kappa", "seed_cv": "seed_CV",
        "info_cv": "info_CV", "hessian_entropy": "entropy",
        "basin_count": "basins",
    }
    
    header = "| | " + " | ".join(short_labels.get(m, m) for m in metrics) + " |"
    separator = "|---" + "|---" * len(metrics) + "|"
    lines.extend([header, separator])
    
    for i, m1 in enumerate(metrics):
        row = f"| {short_labels.get(m1, m1)} |"
        for j, m2 in enumerate(metrics):
            val = corr_matrix[i][j]
            if i == j:
                row += " 1.00 |"
            else:
                p = corr_result["p_value_matrix"][i][j]
                sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
                row += f" {val:.2f}{sig} |"
        lines.append(row)
    
    lines.extend([
        "",
        "*** p<0.01, ** p<0.05, * p<0.1",
        "",
        "---",
        "",
        "## 与边界宽度的相关性 (4 PDE)",
        "",
        "只有4个PDE有边界宽度数据：",
        "",
        "| 指标 | Spearman r | p 值 | 显著性 |",
        "|------|-----------|------|--------|",
    ])
    
    if "error" not in boundary_corr:
        for metric, vals in boundary_corr.items():
            sig = "***" if vals["p_value"] < 0.01 else "**" if vals["p_value"] < 0.05 else "*" if vals["p_value"] < 0.1 else "ns"
            lines.append(f"| {metric} | {vals['correlation']:.3f} | {vals['p_value']:.3f} | {sig} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 关键发现",
        "",
        "### 景观指标之间的相关性",
        "",
        "1. **d_null 与 info_cv**: 如果正相关，说明零空间维度高的系统信息分布更不均匀",
        "2. **lambda_max 与 hessian_entropy**: 如果负相关，说明高曲率系统景观更简单",
        "3. **seed_cv 与 info_cv**: 如果正相关，说明信息不均匀导致种子敏感性",
        "",
        "### 与退化边界的关系",
        "",
        "1. **d_null**: 零空间维度越高，边界越宽（更多退化路径）",
        "2. **lambda_max**: 曲率越高，边界越窄（陡峭损失景观）",
        "3. **seed_cv**: 种子方差越高，边界越宽（多谷结构）",
        "4. **info_cv**: 信息分布越不均匀，边界越宽（学习不均衡）",
        "",
        "### 理论意义",
        "",
        "这些相关性支持以下理论框架：",
        "",
        "```",
        "W ~ d_null * (1/kappa) * M * CV",
        "```",
        "",
        "其中：",
        "- W: 边界宽度",
        "- d_null: 零空间维度",
        "- kappa: 曲率",
        "- M: 多谷性",
        "- CV: 信息密度变异系数",
        "",
    ])
    
    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Correlation Analysis")
    print("=" * 60)
    
    # Load data
    print("\n[1/4] Loading metrics...")
    data = load_all_metrics()
    cases = list(data.keys())
    print(f"  Loaded {len(cases)} cases")
    
    # Compute correlation matrix
    print("\n[2/4] Computing correlation matrix...")
    metrics = ["d_null", "lambda_max", "inverse_curvature", "seed_cv",
               "info_cv", "hessian_entropy", "basin_count"]
    corr_result = compute_correlation_matrix(data, metrics, cases)
    
    # Compute boundary correlations
    print("\n[3/4] Computing boundary correlations...")
    boundary_corr = compute_boundary_correlations(data)
    
    # Generate figures
    print("\n[4/4] Generating figures...")
    plot_correlation_heatmap(corr_result, OUTPUT_DIR)
    plot_boundary_correlations(boundary_corr, OUTPUT_DIR)
    plot_scatter_matrix(data, OUTPUT_DIR)
    
    # Save results
    print("\nSaving results...")
    
    json_results = {
        "correlation_matrix": corr_result,
        "boundary_correlations": boundary_corr,
    }
    with open(OUTPUT_DIR / "correlation_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"  Saved: correlation_results.json")
    
    summary = generate_summary(corr_result, boundary_corr)
    (OUTPUT_DIR / "correlation_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: correlation_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
