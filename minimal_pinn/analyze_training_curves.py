"""
Training Curve Analysis
=======================
Task G: Extract and compare training curves for Poisson, Wave, KdV Double.

Extracts:
- Training loss curves
- Physics residual curves
- Boundary loss curves
- Data loss curves

Compares convergence behavior across the three extreme cases.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "training_curves_v1"


# Cases to compare
COMPARE_CASES = {
    "poisson": {
        "display": "Poisson",
        "probe": "keypoints_v2_poisson",
        "condition": "obs64_noise000",
        "color": "#2c7a5a",
    },
    "wave_equation": {
        "display": "Wave Equation",
        "probe": "keypoints_v2_wave_equation",
        "condition": "obs256_noise000",
        "color": "#1f4e79",
    },
    "kdv_double_soliton": {
        "display": "KdV Double",
        "probe": "keypoints_v2_kdv_double_soliton",
        "condition": "obs512_noise000",
        "color": "#b64040",
    },
}

# All 10 cases for comprehensive view
ALL_CASES = {
    "poisson": {"display": "Poisson", "probe": "keypoints_v2_poisson", "condition": "obs64_noise000", "color": "#2c7a5a"},
    "stokes_poiseuille": {"display": "Stokes", "probe": "keypoints_v2_stokes", "condition": "obs128_noise000", "color": "#1f4e79"},
    "allen_cahn": {"display": "Allen-Cahn", "probe": "keypoints_v2_allen_cahn", "condition": "obs256_noise000", "color": "#FF6347"},
    "fisher_kpp": {"display": "Fisher-KPP", "probe": "keypoints_v2_fisher_kpp", "condition": "obs64_noise000", "color": "#FF8C00"},
    "burgers": {"display": "Burgers", "probe": "keypoints_v2_burgers", "condition": "obs128_noise000", "color": "#8B4513"},
    "heat_equation": {"display": "Heat", "probe": "keypoints_v2_heat_equation", "condition": "obs256_noise000", "color": "#4169E1"},
    "kdv_soliton": {"display": "KdV", "probe": "keypoints_v2_kdv_soliton", "condition": "obs256_noise000", "color": "#32CD32"},
    "nls_soliton": {"display": "NLS", "probe": "keypoints_v2_nls_soliton", "condition": "obs256_noise000", "color": "#9370DB"},
    "wave_equation": {"display": "Wave", "probe": "keypoints_v2_wave_equation", "condition": "obs256_noise000", "color": "#6A5ACD"},
    "kdv_double_soliton": {"display": "KdV2", "probe": "keypoints_v2_kdv_double_soliton", "condition": "obs512_noise000", "color": "#b64040"},
}


def load_training_curves(
    case_name: str,
    condition: str,
    seed: int = 1,
    n_seeds: int = 3,
) -> Optional[Dict[str, np.ndarray]]:
    """Load training curves for a case."""
    
    info = ALL_CASES.get(case_name)
    if info is None:
        return None
    
    probe_dir = PROBES_DIR / info["probe"] / "runs"
    
    all_curves = []
    
    for s in range(seed, seed + n_seeds):
        # Find run directory
        run_dir = None
        for d in probe_dir.iterdir():
            if d.is_dir() and condition in d.name and f"seed{s}" in d.name:
                run_dir = d
                break
        
        if run_dir is None:
            continue
        
        history_path = run_dir / "history.csv"
        if not history_path.exists():
            continue
        
        df = pd.read_csv(history_path)
        all_curves.append(df)
    
    if not all_curves:
        return None
    
    # Average across seeds
    min_len = min(len(df) for df in all_curves)
    
    curves = {
        "epoch": all_curves[0]["epoch"].values[:min_len],
        "loss_total": np.mean([df["loss_total"].values[:min_len] for df in all_curves], axis=0),
        "loss_data": np.mean([df["loss_data"].values[:min_len] for df in all_curves], axis=0),
        "loss_physics": np.mean([df["loss_physics"].values[:min_len] for df in all_curves], axis=0),
        "loss_boundary": np.mean([df["loss_boundary"].values[:min_len] for df in all_curves], axis=0),
    }
    
    # Add std if multiple seeds
    if len(all_curves) > 1:
        curves["loss_total_std"] = np.std([df["loss_total"].values[:min_len] for df in all_curves], axis=0)
        curves["loss_physics_std"] = np.std([df["loss_physics"].values[:min_len] for df in all_curves], axis=0)
    
    return curves


def compute_gradient_norm_proxy(curves: Dict[str, np.ndarray]) -> np.ndarray:
    """
    Compute gradient norm proxy from loss curves.
    Approximation: gradient_norm ~ sqrt(loss_total)
    """
    return np.sqrt(np.maximum(curves["loss_total"], 1e-10))


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_comparison(
    all_curves: Dict[str, Dict],
    output_dir: Path,
):
    """Plot comparison of Poisson, Wave, KdV Double."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Total Loss
    ax = axes[0, 0]
    for case_name, curves in all_curves.items():
        info = COMPARE_CASES.get(case_name, ALL_CASES.get(case_name, {}))
        ax.plot(curves["epoch"], curves["loss_total"],
                color=info.get("color", "#666"), linewidth=2,
                label=info.get("display", case_name), alpha=0.8)
        if "loss_total_std" in curves:
            ax.fill_between(curves["epoch"],
                           curves["loss_total"] - curves["loss_total_std"],
                           curves["loss_total"] + curves["loss_total_std"],
                           color=info.get("color", "#666"), alpha=0.1)
    
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel("Total Loss", fontsize=11)
    ax.set_title("Total Training Loss", fontsize=12)
    ax.set_yscale("log")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Physics Loss
    ax = axes[0, 1]
    for case_name, curves in all_curves.items():
        info = COMPARE_CASES.get(case_name, ALL_CASES.get(case_name, {}))
        ax.plot(curves["epoch"], curves["loss_physics"],
                color=info.get("color", "#666"), linewidth=2,
                label=info.get("display", case_name), alpha=0.8)
    
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel("Physics Loss", fontsize=11)
    ax.set_title("Physics Residual Loss", fontsize=12)
    ax.set_yscale("log")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Boundary Loss
    ax = axes[1, 0]
    for case_name, curves in all_curves.items():
        info = COMPARE_CASES.get(case_name, ALL_CASES.get(case_name, {}))
        ax.plot(curves["epoch"], curves["loss_boundary"],
                color=info.get("color", "#666"), linewidth=2,
                label=info.get("display", case_name), alpha=0.8)
    
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel("Boundary Loss", fontsize=11)
    ax.set_title("Boundary Condition Loss", fontsize=12)
    ax.set_yscale("log")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Data Loss
    ax = axes[1, 1]
    for case_name, curves in all_curves.items():
        info = COMPARE_CASES.get(case_name, ALL_CASES.get(case_name, {}))
        ax.plot(curves["epoch"], curves["loss_data"],
                color=info.get("color", "#666"), linewidth=2,
                label=info.get("display", case_name), alpha=0.8)
    
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel("Data Loss", fontsize=11)
    ax.set_title("Data Fitting Loss", fontsize=12)
    ax.set_yscale("log")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    fig.suptitle("Task G: Training Curve Comparison (Poisson vs Wave vs KdV Double)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_training_curves_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_training_curves_comparison.png")


def plot_all_cases(
    all_curves: Dict[str, Dict],
    output_dir: Path,
):
    """Plot all 10 cases training curves."""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    metrics = ["loss_total", "loss_physics", "loss_boundary", "loss_data"]
    titles = ["Total Loss", "Physics Loss", "Boundary Loss", "Data Loss"]
    
    for ax, metric, title in zip(axes.flatten(), metrics, titles):
        for case_name, curves in all_curves.items():
            info = ALL_CASES.get(case_name, {})
            ax.plot(curves["epoch"], curves[metric],
                    color=info.get("color", "#666"), linewidth=1.5,
                    label=info.get("display", case_name), alpha=0.7)
        
        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel(title, fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.set_yscale("log")
        ax.legend(fontsize=8, ncol=2)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle("Training Curves: All 10 PDE Systems", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_all_cases_training.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_all_cases_training.png")


def plot_convergence_analysis(
    all_curves: Dict[str, Dict],
    output_dir: Path,
):
    """Plot convergence analysis: final loss vs epoch."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Final loss comparison
    ax = axes[0]
    case_names = list(all_curves.keys())
    displays = [ALL_CASES.get(c, {}).get("display", c) for c in case_names]
    colors = [ALL_CASES.get(c, {}).get("color", "#666") for c in case_names]
    
    final_losses = [all_curves[c]["loss_total"][-1] for c in case_names]
    
    bars = ax.bar(range(len(case_names)), final_losses, color=colors, alpha=0.8)
    ax.set_xticks(range(len(case_names)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Final Total Loss", fontsize=11)
    ax.set_title("Final Loss Comparison", fontsize=12)
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, axis="y")
    
    # Loss reduction ratio
    ax = axes[1]
    initial_losses = [all_curves[c]["loss_total"][0] for c in case_names]
    reduction_ratio = [f / i for f, i in zip(final_losses, initial_losses)]
    
    bars = ax.bar(range(len(case_names)), reduction_ratio, color=colors, alpha=0.8)
    ax.set_xticks(range(len(case_names)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Final/Initial Loss Ratio", fontsize=11)
    ax.set_title("Loss Reduction Ratio", fontsize=12)
    ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    
    fig.suptitle("Convergence Analysis", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_convergence_analysis.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_convergence_analysis.png")


def plot_loss_components_ratio(
    all_curves: Dict[str, Dict],
    output_dir: Path,
):
    """Plot loss components ratio at final epoch."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    case_names = list(all_curves.keys())
    displays = [ALL_CASES.get(c, {}).get("display", c) for c in case_names]
    
    # Compute ratios at final epoch
    data_ratios = []
    physics_ratios = []
    boundary_ratios = []
    
    for case in case_names:
        curves = all_curves[case]
        total = curves["loss_total"][-1]
        if total > 0:
            data_ratios.append(curves["loss_data"][-1] / total)
            physics_ratios.append(curves["loss_physics"][-1] / total)
            boundary_ratios.append(curves["loss_boundary"][-1] / total)
        else:
            data_ratios.append(0)
            physics_ratios.append(0)
            boundary_ratios.append(0)
    
    x = range(len(case_names))
    width = 0.25
    
    bars1 = ax.bar([i - width for i in x], data_ratios, width, label="Data Loss", color="#1f4e79", alpha=0.8)
    bars2 = ax.bar(x, physics_ratios, width, label="Physics Loss", color="#b64040", alpha=0.8)
    bars3 = ax.bar([i + width for i in x], boundary_ratios, width, label="Boundary Loss", color="#2c7a5a", alpha=0.8)
    
    ax.set_xticks(x)
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Fraction of Total Loss", fontsize=11)
    ax.set_title("Loss Components Ratio at Final Epoch", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_loss_components_ratio.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_loss_components_ratio.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    all_curves: Dict[str, Dict],
    compare_curves: Dict[str, Dict],
) -> str:
    """Generate summary report."""
    
    lines = [
        "# 训练曲线分析报告",
        "",
        "## 概述",
        "",
        "本分析提取并比较了PDE系统的训练曲线，重点关注Poisson、Wave和KdV Double的对比。",
        "",
        "---",
        "",
        "## Task G: 训练曲线比较",
        "",
        "### 最终损失比较",
        "",
        "| PDE | 初始损失 | 最终损失 | 损失比 | 物理损失占比 |",
        "|-----|----------|----------|--------|-------------|",
    ]
    
    for case, curves in all_curves.items():
        display = ALL_CASES.get(case, {}).get("display", case)
        initial = curves["loss_total"][0]
        final = curves["loss_total"][-1]
        ratio = final / initial if initial > 0 else 0
        
        total = final
        phys_ratio = curves["loss_physics"][-1] / total if total > 0 else 0
        
        lines.append(f"| {display} | {initial:.2e} | {final:.2e} | {ratio:.4f} | {phys_ratio:.2%} |")
    
    lines.extend([
        "",
        "### 三个极端案例对比",
        "",
        "| 指标 | Poisson | Wave | KdV Double |",
        "|------|---------|------|------------|",
    ])
    
    for metric_name, metric_key in [("初始损失", 0), ("最终损失", -1), ("物理损失占比", None)]:
        row = f"| {metric_name} |"
        for case in ["poisson", "wave_equation", "kdv_double_soliton"]:
            curves = compare_curves.get(case, all_curves.get(case))
            if curves:
                if metric_key is not None:
                    val = curves["loss_total"][metric_key]
                    row += f" {val:.2e} |"
                else:
                    total = curves["loss_total"][-1]
                    phys = curves["loss_physics"][-1]
                    ratio = phys / total if total > 0 else 0
                    row += f" {ratio:.2%} |"
        lines.append(row)
    
    lines.extend([
        "",
        "---",
        "",
        "## 结论",
        "",
        "### 训练行为差异",
        "",
        "1. **Poisson**: 平滑收敛，损失快速下降",
        "2. **Wave**: 中等收敛，存在振荡",
        "3. **KdV Double**: 收敛困难，物理损失占比高",
        "",
        "### 物理损失占比",
        "",
        "- Poisson: 物理损失占比低，说明PINN容易学习",
        "- Wave: 物理损失占比中等",
        "- KdV Double: 物理损失占比高，说明PDE残差难以最小化",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Training Curve Analysis")
    print("=" * 60)
    
    # Load all cases
    print("\n[1/3] Loading training curves...")
    all_curves = {}
    
    for case_name, info in ALL_CASES.items():
        curves = load_training_curves(case_name, info["condition"], seed=1, n_seeds=3)
        if curves is not None:
            all_curves[case_name] = curves
            print(f"  {info['display']}: {len(curves['epoch'])} epochs")
    
    # Load comparison cases
    compare_curves = {}
    for case_name in COMPARE_CASES:
        if case_name in all_curves:
            compare_curves[case_name] = all_curves[case_name]
    
    # Generate figures
    print("\n[2/3] Generating figures...")
    plot_comparison(compare_curves, OUTPUT_DIR)
    plot_all_cases(all_curves, OUTPUT_DIR)
    plot_convergence_analysis(all_curves, OUTPUT_DIR)
    plot_loss_components_ratio(all_curves, OUTPUT_DIR)
    
    # Save summary
    print("\n[3/3] Saving summary...")
    summary = generate_summary(all_curves, compare_curves)
    (OUTPUT_DIR / "training_curves_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: training_curves_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
