"""
Information Density Uniformity Analysis
========================================
Quantifies how uniformly information is distributed across the solution domain.

Theory:
- Information density: I(x) = |gradu(x)| or I(x) = u^2 + |gradu|^2
- Coefficient of variation: CV = σ(I) / μ(I)
- Hypothesis: Higher CV → more irregular degradation boundary

This connects the physics of the PDE to the observed degradation patterns.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from scipy import stats as sp_stats
from torch import nn

from .cases import build_case
from .config import ensure_defaults, load_config
from .cases.base import gradients

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "information_density_v1"

# All cases with their properties
CASES = {
    "poisson": {
        "display": "Poisson",
        "input_dim": 2,
        "output_dim": 1,
        "boundary_width": 1.33,
        "boundary_irregularity": 0.133,  # jump_rate from clustering
    },
    "stokes_poiseuille": {
        "display": "Stokes-Poiseuille",
        "input_dim": 2,
        "output_dim": 3,
        "boundary_width": 3.67,
        "boundary_irregularity": 0.367,
    },
    "fisher_kpp": {
        "display": "Fisher-KPP",
        "input_dim": 2,
        "output_dim": 1,
        "boundary_width": 5.13,
        "boundary_irregularity": 0.300,
    },
    "burgers": {
        "display": "Burgers",
        "input_dim": 2,
        "output_dim": 1,
        "boundary_width": 4.77,
        "boundary_irregularity": 0.500,
    },
    "heat_equation": {
        "display": "Heat Equation",
        "input_dim": 2,
        "output_dim": 1,
        "boundary_width": None,
        "boundary_irregularity": None,
    },
    "allen_cahn": {
        "display": "Allen-Cahn",
        "input_dim": 2,
        "output_dim": 1,
        "boundary_width": None,
        "boundary_irregularity": None,
    },
}


# ═══════════════════════════════════════════════════════════
#  Information Density Computation
# ═══════════════════════════════════════════════════════════

def compute_information_density(
    case_name: str,
    n_eval: int = 101,
    device: torch.device = torch.device("cpu"),
) -> Dict[str, Any]:
    """
    Compute information density I(x) for the true solution of a PDE case.

    Returns:
        I_grad: |gradu(x)| - gradient-based information density
        I_full: u^2 + |gradu|^2 - full information density
        stats: CV and other statistics
    """
    case = build_case(case_name)
    x_eval = case.sample_eval(num_eval=n_eval, device=device)

    # Need gradients for gradient-based density
    x_req = x_eval.detach().clone().requires_grad_(True)
    u = case.truth(x_req)

    # Compute gradient
    if case.output_dim == 1:
        # Single output: u
        grad_u = gradients(u, x_req)
        grad_norm = torch.sqrt(torch.sum(grad_u ** 2, dim=1))

        # I(x) = |gradu|
        I_grad = grad_norm.detach().cpu().numpy()

        # I(x) = u^2 + |gradu|^2
        u_np = u.detach().cpu().numpy().flatten()
        I_full = (u_np ** 2 + grad_norm.detach().cpu().numpy() ** 2)
    else:
        # Multi-output (e.g., Stokes): sum over outputs
        grad_norms = []
        u_squares = []
        for i in range(case.output_dim):
            grad_i = gradients(u[:, i:i+1], x_req)
            grad_norm_i = torch.sqrt(torch.sum(grad_i ** 2, dim=1))
            grad_norms.append(grad_norm_i)
            u_squares.append(u[:, i:i+1].detach().cpu().numpy().flatten() ** 2)

        # Sum over outputs
        I_grad = sum(gn.detach().cpu().numpy() for gn in grad_norms)
        I_full = sum(u_squares) + sum(gn.detach().cpu().numpy() ** 2 for gn in grad_norms)

    # Compute statistics
    stats = {
        "I_grad": {
            "mean": float(np.mean(I_grad)),
            "std": float(np.std(I_grad)),
            "cv": float(np.std(I_grad) / max(np.mean(I_grad), 1e-10)),
            "median": float(np.median(I_grad)),
            "min": float(np.min(I_grad)),
            "max": float(np.max(I_grad)),
            "q25": float(np.percentile(I_grad, 25)),
            "q75": float(np.percentile(I_grad, 75)),
        },
        "I_full": {
            "mean": float(np.mean(I_full)),
            "std": float(np.std(I_full)),
            "cv": float(np.std(I_full) / max(np.mean(I_full), 1e-10)),
            "median": float(np.median(I_full)),
            "min": float(np.min(I_full)),
            "max": float(np.max(I_full)),
            "q25": float(np.percentile(I_full, 25)),
            "q75": float(np.percentile(I_full, 75)),
        },
    }

    return {
        "case": case_name,
        "I_grad": I_grad,
        "I_full": I_full,
        "x_eval": x_eval.detach().cpu().numpy(),
        "stats": stats,
        "n_points": len(I_grad),
    }


def compute_spatial_information_density(
    case_name: str,
    n_eval: int = 101,
    device: torch.device = torch.device("cpu"),
) -> Dict[str, Any]:
    """
    Compute spatially resolved information density for visualization.
    Returns 2D arrays for plotting.
    """
    case = build_case(case_name)
    x_eval = case.sample_eval(num_eval=n_eval, device=device)

    x_req = x_eval.detach().clone().requires_grad_(True)
    u = case.truth(x_req)

    if case.output_dim == 1:
        grad_u = gradients(u, x_req)
        grad_norm = torch.sqrt(torch.sum(grad_u ** 2, dim=1))

        I_grad = grad_norm.detach().cpu().numpy().reshape(n_eval, n_eval)
        u_field = u.detach().cpu().numpy().reshape(n_eval, n_eval)
        I_full = (u_field ** 2 + I_grad ** 2)
    else:
        # For multi-output, use first output (u velocity for Stokes)
        grad_u = gradients(u[:, 0:1], x_req)
        grad_norm = torch.sqrt(torch.sum(grad_u ** 2, dim=1))

        I_grad = grad_norm.detach().cpu().numpy().reshape(n_eval, n_eval)
        u_field = u[:, 0:1].detach().cpu().numpy().reshape(n_eval, n_eval)
        I_full = (u_field ** 2 + I_grad ** 2)

    # Get grid coordinates
    if case_name == "poisson":
        x_grid = np.linspace(0, 1, n_eval)
        y_grid = np.linspace(0, 1, n_eval)
    elif case_name == "stokes_poiseuille":
        x_grid = np.linspace(0, 1, n_eval)
        y_grid = np.linspace(-1, 1, n_eval)
    elif case_name in ["burgers", "fisher_kpp", "heat_equation", "allen_cahn"]:
        x_grid = np.linspace(-1, 1, n_eval)
        y_grid = np.linspace(0, 1, n_eval)
    else:
        x_grid = np.linspace(0, 1, n_eval)
        y_grid = np.linspace(0, 1, n_eval)

    return {
        "case": case_name,
        "I_grad": I_grad,
        "I_full": I_full,
        "u_field": u_field,
        "x_grid": x_grid,
        "y_grid": y_grid,
    }


# ═══════════════════════════════════════════════════════════
#  Analysis Pipeline
# ═══════════════════════════════════════════════════════════

def run_analysis() -> Dict[str, Any]:
    """Run information density analysis for all PDE cases."""
    results = {}
    spatial_results = {}

    for case_name in CASES:
        print(f"  Analyzing {CASES[case_name]['display']}...")

        # Point-wise statistics
        result = compute_information_density(case_name)
        results[case_name] = result

        # Spatial distribution
        spatial = compute_spatial_information_density(case_name)
        spatial_results[case_name] = spatial

        cv_grad = result["stats"]["I_grad"]["cv"]
        cv_full = result["stats"]["I_full"]["cv"]
        print(f"    CV(grad) = {cv_grad:.4f}, CV(full) = {cv_full:.4f}")

    # Compute correlations with boundary properties
    cases_with_boundary = [c for c in CASES if CASES[c]["boundary_width"] is not None]

    correlations = {}
    if len(cases_with_boundary) >= 3:
        widths = [CASES[c]["boundary_width"] for c in cases_with_boundary]
        irregularities = [CASES[c]["boundary_irregularity"] for c in cases_with_boundary]

        for metric in ["I_grad", "I_full"]:
            cvs = [results[c]["stats"][metric]["cv"] for c in cases_with_boundary]

            corr_width, p_width = sp_stats.spearmanr(cvs, widths)
            corr_irr, p_irr = sp_stats.spearmanr(cvs, irregularities)

            correlations[metric] = {
                "vs_boundary_width": {"correlation": float(corr_width), "p_value": float(p_width)},
                "vs_boundary_irregularity": {"correlation": float(corr_irr), "p_value": float(p_irr)},
            }

    return {
        "results": results,
        "spatial_results": spatial_results,
        "correlations": correlations,
    }


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_information_density_heatmaps(
    spatial_results: Dict[str, Any],
    output_dir: Path,
):
    """Plot heatmaps of information density for each case."""
    cases = list(spatial_results.keys())
    n_cases = len(cases)

    fig, axes = plt.subplots(n_cases, 3, figsize=(15, 4 * n_cases))

    for i, case_name in enumerate(cases):
        spatial = spatial_results[case_name]
        display = CASES[case_name]["display"]
        x_grid = spatial["x_grid"]
        y_grid = spatial["y_grid"]

        # u field
        ax = axes[i, 0] if n_cases > 1 else axes[0]
        im = ax.pcolormesh(x_grid, y_grid, spatial["u_field"].T, cmap="RdBu_r", shading="auto")
        ax.set_title(f"{display}: u(x)", fontsize=11)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, shrink=0.8)

        # I_grad = |gradu|
        ax = axes[i, 1] if n_cases > 1 else axes[1]
        im = ax.pcolormesh(x_grid, y_grid, spatial["I_grad"].T, cmap="viridis", shading="auto")
        ax.set_title(f"{display}: |gradu|", fontsize=11)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, shrink=0.8)

        # I_full = u^2 + |gradu|^2
        ax = axes[i, 2] if n_cases > 1 else axes[2]
        im = ax.pcolormesh(x_grid, y_grid, spatial["I_full"].T, cmap="viridis", shading="auto")
        ax.set_title(f"{display}: u^2 + |gradu|^2", fontsize=11)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle("Information Density Fields Across PDE Systems", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_information_density_heatmaps.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_information_density_heatmaps.png")


def plot_cv_comparison(
    results: Dict[str, Any],
    output_dir: Path,
):
    """Compare CV across PDE systems."""
    cases = list(results.keys())
    displays = [CASES[c]["display"] for c in cases]
    cv_grad = [results[c]["stats"]["I_grad"]["cv"] for c in cases]
    cv_full = [results[c]["stats"]["I_full"]["cv"] for c in cases]

    fig, ax = plt.subplots(figsize=(10, 6))

    x = range(len(cases))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], cv_grad, width, label="CV(|gradu|)",
                   color="#1f4e79", alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], cv_full, width, label="CV(u^2 + |gradu|^2)",
                   color="#b64040", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(displays, fontsize=11)
    ax.set_ylabel("Coefficient of Variation (CV)", fontsize=12)
    ax.set_title("Information Density Uniformity Across PDE Systems", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

    # Add value labels
    for bar, val in zip(bars1, cv_grad):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{val:.2f}", ha="center", fontsize=9)
    for bar, val in zip(bars2, cv_full):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{val:.2f}", ha="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(output_dir / "fig_cv_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_cv_comparison.png")


def plot_cv_vs_boundary(
    results: Dict[str, Any],
    correlations: Dict[str, Any],
    output_dir: Path,
):
    """Plot CV vs boundary width and irregularity."""
    cases_with_boundary = [c for c in CASES if CASES[c]["boundary_width"] is not None]
    displays = [CASES[c]["display"] for c in cases_with_boundary]
    widths = [CASES[c]["boundary_width"] for c in cases_with_boundary]
    irregularities = [CASES[c]["boundary_irregularity"] for c in cases_with_boundary]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513"]

    # CV vs boundary width
    ax = axes[0]
    for i, (case, display) in enumerate(zip(cases_with_boundary, displays)):
        cv = results[case]["stats"]["I_grad"]["cv"]
        w = CASES[case]["boundary_width"]
        ax.scatter(w, cv, c=colors[i % len(colors)], s=150, alpha=0.8,
                   edgecolors="white", linewidth=1.5, label=display, zorder=5)

    # Fit line
    cvs = [results[c]["stats"]["I_grad"]["cv"] for c in cases_with_boundary]
    if len(widths) > 2:
        z = np.polyfit(widths, cvs, 1)
        p_line = np.poly1d(z)
        x_line = np.linspace(min(widths), max(widths), 100)
        ax.plot(x_line, p_line(x_line), "--", color="gray", alpha=0.5)

    corr_info = correlations.get("I_grad", {}).get("vs_boundary_width", {})
    if corr_info:
        ax.text(0.05, 0.95, f"r = {corr_info['correlation']:.3f}\np = {corr_info['p_value']:.3f}",
                transform=ax.transAxes, fontsize=10, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    ax.set_xlabel("Boundary Width", fontsize=12)
    ax.set_ylabel("CV(|gradu|)", fontsize=12)
    ax.set_title("Information Density CV vs Boundary Width", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # CV vs boundary irregularity
    ax = axes[1]
    for i, (case, display) in enumerate(zip(cases_with_boundary, displays)):
        cv = results[case]["stats"]["I_grad"]["cv"]
        irr = CASES[case]["boundary_irregularity"]
        ax.scatter(irr, cv, c=colors[i % len(colors)], s=150, alpha=0.8,
                   edgecolors="white", linewidth=1.5, label=display, zorder=5)

    if len(irregularities) > 2:
        z = np.polyfit(irregularities, cvs, 1)
        p_line = np.poly1d(z)
        x_line = np.linspace(min(irregularities), max(irregularities), 100)
        ax.plot(x_line, p_line(x_line), "--", color="gray", alpha=0.5)

    corr_info = correlations.get("I_grad", {}).get("vs_boundary_irregularity", {})
    if corr_info:
        ax.text(0.05, 0.95, f"r = {corr_info['correlation']:.3f}\np = {corr_info['p_value']:.3f}",
                transform=ax.transAxes, fontsize=10, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    ax.set_xlabel("Boundary Irregularity (Jump Rate)", fontsize=12)
    ax.set_ylabel("CV(|gradu|)", fontsize=12)
    ax.set_title("Information Density CV vs Boundary Irregularity", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / "fig_cv_vs_boundary.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_cv_vs_boundary.png")


def plot_distribution_comparison(
    results: Dict[str, Any],
    output_dir: Path,
):
    """Compare distribution of information density across cases."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    colors = {"poisson": "#1f4e79", "stokes_poiseuille": "#2c7a5a",
              "fisher_kpp": "#b64040", "burgers": "#8B4513",
              "heat_equation": "#6A5ACD", "allen_cahn": "#FF6347"}

    # Distribution of |gradu|
    ax = axes[0]
    for case_name, result in results.items():
        display = CASES[case_name]["display"]
        I_grad = result["I_grad"]
        # Normalize for comparison
        I_norm = I_grad / max(np.mean(I_grad), 1e-10)
        ax.hist(I_norm, bins=50, alpha=0.5, density=True,
                color=colors.get(case_name, "#666"), label=display)

    ax.set_xlabel("Normalized |gradu|", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title("Distribution of Gradient Magnitude", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # Distribution of u^2 + |gradu|^2
    ax = axes[1]
    for case_name, result in results.items():
        display = CASES[case_name]["display"]
        I_full = result["I_full"]
        I_norm = I_full / max(np.mean(I_full), 1e-10)
        ax.hist(I_norm, bins=50, alpha=0.5, density=True,
                color=colors.get(case_name, "#666"), label=display)

    ax.set_xlabel("Normalized (u^2 + |gradu|^2)", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title("Distribution of Full Information Density", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / "fig_distribution_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_distribution_comparison.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    results: Dict[str, Any],
    correlations: Dict[str, Any],
) -> str:
    lines = [
        "# 信息密度均匀性分析",
        "",
        "## 概述",
        "",
        "本分析量化了各 PDE 系统解的信息密度分布均匀性，并检验其与退化边界特性的关系。",
        "",
        "**信息密度定义:**",
        "- I_grad(x) = |gradu(x)| — 梯度幅值",
        "- I_full(x) = u^2 + |gradu|^2 — 完整信息密度",
        "",
        "**均匀性度量:**",
        "- CV = σ(I) / μ(I) — 变异系数",
        "- CV 越大表示信息分布越不均匀",
        "",
        "---",
        "",
        "## 结果汇总",
        "",
        "| PDE 系统 | CV(|gradu|) | CV(u^2+|gradu|^2) | 均值(|gradu|) | 标准差(|gradu|) | 边界宽度 |",
        "|----------|----------|-------------|-----------|-------------|----------|",
    ]

    for case_name, result in results.items():
        display = CASES[case_name]["display"]
        stats = result["stats"]
        width = CASES[case_name]["boundary_width"]

        lines.append(
            f"| {display} | {stats['I_grad']['cv']:.4f} | {stats['I_full']['cv']:.4f} | "
            f"{stats['I_grad']['mean']:.4f} | {stats['I_grad']['std']:.4f} | "
            f"{width if width else '—'} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 相关性分析",
        "",
        "### CV 与边界宽度",
        "",
        "| 信息密度类型 | Spearman r | p 值 | 显著性 |",
        "|-------------|-----------|------|--------|",
    ])

    for metric, corr_data in correlations.items():
        for target, vals in corr_data.items():
            sig = "***" if vals["p_value"] < 0.001 else "**" if vals["p_value"] < 0.01 else "*" if vals["p_value"] < 0.05 else "ns"
            target_name = "边界宽度" if "width" in target else "边界不规则性"
            lines.append(
                f"| {metric} vs {target_name} | {vals['correlation']:.3f} | "
                f"{vals['p_value']:.3f} | {sig} |"
            )

    lines.extend([
        "",
        "---",
        "",
        "## 详细统计",
        "",
    ])

    for case_name, result in results.items():
        display = CASES[case_name]["display"]
        stats = result["stats"]

        lines.extend([
            f"### {display}",
            "",
            "**梯度信息密度 |gradu|:**",
            f"- 均值: {stats['I_grad']['mean']:.6f}",
            f"- 标准差: {stats['I_grad']['std']:.6f}",
            f"- CV: {stats['I_grad']['cv']:.6f}",
            f"- 中位数: {stats['I_grad']['median']:.6f}",
            f"- 范围: [{stats['I_grad']['min']:.6f}, {stats['I_grad']['max']:.6f}]",
            f"- IQR: [{stats['I_grad']['q25']:.6f}, {stats['I_grad']['q75']:.6f}]",
            "",
            "**完整信息密度 u^2 + |gradu|^2:**",
            f"- 均值: {stats['I_full']['mean']:.6f}",
            f"- 标准差: {stats['I_full']['std']:.6f}",
            f"- CV: {stats['I_full']['cv']:.6f}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 理论解释",
        "",
        "### 信息密度与退化模式",
        "",
        "1. **低 CV (信息均匀分布):**",
        "   - Poisson: 解平滑，梯度变化小",
        "   - 退化边界尖锐、规则",
        "",
        "2. **高 CV (信息集中分布):**",
        "   - Heat/Allen-Cahn: 存在边界层或前沿",
        "   - 退化边界可能更不规则",
        "",
        "### 物理直觉",
        "",
        "- **梯度大的区域**: 信息丰富，PINN 容易学习",
        "- **梯度小的区域**: 信息稀疏，PINN 可能失效",
        "- **CV 大**: 信息分布不均匀，导致学习不均衡",
        "",
        "### 与退化原型的联系",
        "",
        "- **尖锐边界 (Stokes)**: CV 低，信息均匀，边界清晰",
        "- **概率边界 (Burgers)**: CV 中等，信息分布导致不确定性",
        "- **前沿系统 (Heat/Allen-Cahn)**: CV 高，边界层导致信息集中",
        "",
        "### 局限性",
        "",
        "- 当前仅分析了真解的信息密度，未考虑训练后模型的预测",
        "- 信息密度是静态的，未考虑训练过程中的动态变化",
        "- 需要更多实验验证信息密度与退化模式的因果关系",
        "",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Information Density Uniformity Analysis")
    print("=" * 70)

    # Run analysis
    print("\n[1/3] Computing information density...")
    analysis_results = run_analysis()

    results = analysis_results["results"]
    spatial_results = analysis_results["spatial_results"]
    correlations = analysis_results["correlations"]

    # Generate figures
    print("\n[2/3] Generating figures...")
    plot_information_density_heatmaps(spatial_results, OUTPUT_DIR)
    plot_cv_comparison(results, OUTPUT_DIR)
    plot_cv_vs_boundary(results, correlations, OUTPUT_DIR)
    plot_distribution_comparison(results, OUTPUT_DIR)

    # Save results
    print("\n[3/3] Saving results...")
    json_results = {}
    for case_name, result in results.items():
        json_results[case_name] = {
            "case": case_name,
            "stats": result["stats"],
        }

    with open(OUTPUT_DIR / "information_density_results.json", "w", encoding="utf-8") as f:
        json.dump({"results": json_results, "correlations": correlations}, f, indent=2)
    print(f"  Saved: information_density_results.json")

    summary = generate_summary(results, correlations)
    (OUTPUT_DIR / "information_density_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: information_density_summary.md")

    print(f"\n{'=' * 70}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 70}")
    print(summary)


if __name__ == "__main__":
    main()
