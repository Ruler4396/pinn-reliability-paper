"""
Failure Probability Landscape Analysis
=======================================
Task Z1: Compute P(failure|density,noise) as 16x16 matrix
Task Z2: Extract critical curves and compute geometric features
Task Z3: Compare sensitivity within each PDE
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
import pandas as pd
from scipy import stats as sp_stats
from scipy.ndimage import label as ndlabel
from scipy.interpolate import interp1d

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "failure_probability_v1"


# All 10 cases
CASES = {
    "poisson": {"display": "Poisson", "display_zh": "Poisson方程", "prototype": "Non-Degrading", "probe": "keypoints_v2_poisson", "threshold": 0.11297},
    "stokes_poiseuille": {"display": "Stokes-Poiseuille", "display_zh": "斯托克斯-泊肃叶流", "prototype": "Sharp Boundary", "probe": "keypoints_v2_stokes", "threshold": 0.015379},
    "allen_cahn": {"display": "Allen-Cahn", "display_zh": "Allen-Cahn方程", "prototype": "Broad Band", "probe": "keypoints_v2_allen_cahn", "threshold": 0.05},
    "fisher_kpp": {"display": "Fisher-KPP", "display_zh": "Fisher-KPP方程", "prototype": "Intermediate", "probe": "keypoints_v2_fisher_kpp", "threshold": 0.018861},
    "burgers": {"display": "Burgers", "display_zh": "Burgers方程", "prototype": "Broad Band", "probe": "keypoints_v2_burgers", "threshold": 0.026688},
    "heat_equation": {"display": "Heat Equation", "display_zh": "热方程", "prototype": "Broad Band", "probe": "keypoints_v2_heat_equation", "threshold": 0.05},
    "kdv_soliton": {"display": "KdV Soliton", "display_zh": "KdV孤子", "prototype": "Broad Band", "probe": "keypoints_v2_kdv_soliton", "threshold": 0.05},
    "nls_soliton": {"display": "NLS Soliton", "display_zh": "NLS孤子", "prototype": "Broad Band", "probe": "keypoints_v2_nls_soliton", "threshold": 0.05},
    "wave_equation": {"display": "Wave Equation", "display_zh": "波动方程", "prototype": "Broad Band", "probe": "keypoints_v2_wave_equation", "threshold": 0.05},
    "kdv_double_soliton": {"display": "KdV Double", "display_zh": "KdV双孤子", "prototype": "Broad Band", "probe": "keypoints_v2_kdv_double_soliton", "threshold": 0.05},
}


# ═══════════════════════════════════════════════════════════
#  Task Z1: Compute P(failure|density,noise) Matrix
# ═══════════════════════════════════════════════════════════

def compute_failure_matrix(case_name: str) -> Optional[Dict[str, Any]]:
    """
    Compute P(failure|density,noise) matrix for a PDE case.
    
    Returns a grid of failure probabilities indexed by (num_observation, noise_std).
    """
    
    info = CASES.get(case_name)
    if info is None:
        return None
    
    probe_dir = PROBES_DIR / info["probe"]
    runs_csv = probe_dir / "probe_runs.csv"
    
    if not runs_csv.exists():
        return None
    
    df = pd.read_csv(runs_csv)
    threshold = info["threshold"]
    
    # Get unique observation counts and noise levels
    obs_levels = sorted(df["num_observation"].unique())
    noise_levels = sorted(df["noise_std"].unique())
    
    # Create grid
    n_obs = len(obs_levels)
    n_noise = len(noise_levels)
    
    failure_matrix = np.zeros((n_obs, n_noise))
    count_matrix = np.zeros((n_obs, n_noise))
    
    for _, row in df.iterrows():
        obs_idx = obs_levels.index(row["num_observation"])
        noise_idx = noise_levels.index(row["noise_std"])
        
        if row["rel_l2"] > threshold:
            failure_matrix[obs_idx, noise_idx] += 1
        count_matrix[obs_idx, noise_idx] += 1
    
    # Normalize to get probability
    with np.errstate(divide='ignore', invalid='ignore'):
        failure_prob = np.where(count_matrix > 0, failure_matrix / count_matrix, 0)
    
    return {
        "case": case_name,
        "display": info["display"],
        "prototype": info["prototype"],
        "obs_levels": [float(x) for x in obs_levels],
        "noise_levels": [float(x) for x in noise_levels],
        "failure_prob": failure_prob.tolist(),
        "failure_matrix": failure_matrix.tolist(),
        "count_matrix": count_matrix.tolist(),
        "threshold": threshold,
    }


# ═══════════════════════════════════════════════════════════
#  Task Z2: Extract Critical Curves
# ═══════════════════════════════════════════════════════════

def extract_critical_curve(
    failure_prob: np.ndarray,
    obs_levels: List[float],
    noise_levels: List[float],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Extract the P(failure)=threshold contour and compute geometric features.
    """
    
    # Create interpolation for smoother contour
    n_interp = 100
    obs_interp = np.linspace(min(obs_levels), max(obs_levels), n_interp)
    noise_interp = np.linspace(min(noise_levels), max(noise_levels), n_interp)
    
    # Interpolate failure probability
    from scipy.interpolate import RectBivariateSpline
    
    try:
        # Create interpolator
        f_interp = RectBivariateSpline(
            obs_levels, noise_levels, failure_prob,
            kx=min(3, len(obs_levels)-1), ky=min(3, len(noise_levels)-1)
        )
        prob_interp = f_interp(obs_interp, noise_interp)
    except:
        # Fallback to nearest neighbor
        prob_interp = np.zeros((n_interp, n_interp))
        for i, obs in enumerate(obs_interp):
            for j, noise in enumerate(noise_interp):
                # Find nearest
                obs_idx = np.argmin(np.abs(np.array(obs_levels) - obs))
                noise_idx = np.argmin(np.abs(np.array(noise_levels) - noise))
                prob_interp[i, j] = failure_prob[obs_idx, noise_idx]
    
    # Find contour at threshold
    from matplotlib.pyplot import contour as plt_contour
    import io
    
    # Use matplotlib to extract contour
    fig, ax = plt.subplots()
    cs = ax.contour(obs_interp, noise_interp, prob_interp, levels=[threshold])
    plt.close(fig)
    
    # Extract contour path - robust method
    contour_paths = []
    
    # Try to get paths from the contour set
    try:
        # Try allsegs attribute (older matplotlib)
        if hasattr(cs, 'allsegs'):
            for seg_list in cs.allsegs:
                for seg in seg_list:
                    if len(seg) > 1:
                        contour_paths.append(np.array(seg))
        # Try collections attribute (newer matplotlib)
        elif hasattr(cs, 'collections'):
            for collection in cs.collections:
                for path in collection.get_paths():
                    vertices = path.vertices
                    if len(vertices) > 1:
                        contour_paths.append(vertices)
    except Exception:
        pass
    
    if not contour_paths:
        # Fallback: manually find the 0.5 contour
        # Find points where failure_prob crosses 0.5
        obs_array = np.array(obs_levels)
        noise_array = np.array(noise_levels)
        
        # For each noise level, find the obs where P crosses 0.5
        contour_points = []
        for j in range(len(noise_array)):
            for i in range(len(obs_array) - 1):
                if (failure_prob[i, j] < threshold and failure_prob[i+1, j] >= threshold) or \
                   (failure_prob[i, j] >= threshold and failure_prob[i+1, j] < threshold):
                    # Linear interpolation
                    t = (threshold - failure_prob[i, j]) / (failure_prob[i+1, j] - failure_prob[i, j] + 1e-10)
                    obs_cross = obs_array[i] + t * (obs_array[i+1] - obs_array[i])
                    contour_points.append([obs_cross, noise_array[j]])
        
        if len(contour_points) > 1:
            contour_paths = [np.array(contour_points)]
    
    if not contour_paths:
        return {
            "has_contour": False,
            "curve_length": 0,
            "curve_curvature": 0,
            "area_above": 0,
            "n_components": 0,
        }
    
    # Use the longest contour
    valid_paths = [p for p in contour_paths if len(p) > 1]
    if not valid_paths:
        return {
            "has_contour": False,
            "curve_length": 0,
            "curve_curvature": 0,
            "area_above": 0,
            "n_components": 0,
        }
    
    longest_path = max(valid_paths, key=lambda p: len(p))
    
    # Curve length
    dx = np.diff(longest_path[:, 0])
    dy = np.diff(longest_path[:, 1])
    curve_length = float(np.sum(np.sqrt(dx**2 + dy**2)))
    
    # Curve curvature (mean absolute curvature)
    if len(longest_path) > 2:
        # Compute curvature using finite differences
        x = longest_path[:, 0]
        y = longest_path[:, 1]
        
        dx = np.gradient(x)
        dy = np.gradient(y)
        ddx = np.gradient(dx)
        ddy = np.gradient(dy)
        
        curvature = np.abs(dx * ddy - dy * ddx) / (dx**2 + dy**2 + 1e-10)**1.5
        mean_curvature = float(np.mean(curvature))
    else:
        mean_curvature = 0
    
    # Area above threshold (where P(failure) > 0.5)
    area_above = float(np.sum(prob_interp > threshold) / prob_interp.size)
    
    # Connected components of failure region
    failure_mask = prob_interp > threshold
    labeled, n_components = ndlabel(failure_mask)
    
    return {
        "has_contour": True,
        "curve_length": curve_length,
        "curve_curvature": mean_curvature,
        "area_above": area_above,
        "n_components": int(n_components),
        "contour_x": longest_path[:, 0].tolist(),
        "contour_y": longest_path[:, 1].tolist(),
    }


# ═══════════════════════════════════════════════════════════
#  Task Z3: Sensitivity Analysis
# ═══════════════════════════════════════════════════════════

def compute_sensitivity(
    failure_prob: np.ndarray,
    obs_levels: List[float],
    noise_levels: List[float],
) -> Dict[str, Any]:
    """
    Compute sensitivity: how failure probability changes as density decreases.
    """
    
    obs_array = np.array(obs_levels)
    noise_array = np.array(noise_levels)
    
    # Sensitivity to density: dP/d(obs) at each noise level
    # Negative because decreasing obs increases failure
    density_sensitivity = []
    for j in range(len(noise_levels)):
        if len(obs_levels) > 1:
            # Compute gradient
            dp_dobs = np.gradient(failure_prob[:, j], obs_array)
            # Mean absolute sensitivity
            density_sensitivity.append(float(np.mean(np.abs(dp_dobs))))
        else:
            density_sensitivity.append(0)
    
    # Sensitivity to noise: dP/d(noise) at each obs level
    noise_sensitivity = []
    for i in range(len(obs_levels)):
        if len(noise_levels) > 1:
            dp_dnoise = np.gradient(failure_prob[i, :], noise_array)
            noise_sensitivity.append(float(np.mean(np.abs(dp_dnoise))))
        else:
            noise_sensitivity.append(0)
    
    # Overall sensitivity
    mean_density_sensitivity = float(np.mean(density_sensitivity))
    mean_noise_sensitivity = float(np.mean(noise_sensitivity))
    
    # Critical density: obs level where P(failure) first exceeds 0.5
    critical_densities = []
    for j in range(len(noise_levels)):
        above_threshold = np.where(failure_prob[:, j] > 0.5)[0]
        if len(above_threshold) > 0:
            critical_densities.append(float(obs_array[above_threshold[0]]))
        else:
            critical_densities.append(float(obs_array[0]))
    
    # Critical noise: noise level where P(failure) first exceeds 0.5
    critical_noises = []
    for i in range(len(obs_levels)):
        above_threshold = np.where(failure_prob[i, :] > 0.5)[0]
        if len(above_threshold) > 0:
            critical_noises.append(float(noise_array[above_threshold[0]]))
        else:
            critical_noises.append(float(noise_array[0]))
    
    return {
        "density_sensitivity_per_noise": density_sensitivity,
        "noise_sensitivity_per_obs": noise_sensitivity,
        "mean_density_sensitivity": mean_density_sensitivity,
        "mean_noise_sensitivity": mean_noise_sensitivity,
        "critical_densities": critical_densities,
        "critical_noises": critical_noises,
        "mean_critical_density": float(np.mean(critical_densities)),
        "mean_critical_noise": float(np.mean(critical_noises)),
    }


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_failure_matrices(
    all_results: Dict[str, Dict],
    output_dir: Path,
):
    """Plot failure probability matrices for all cases."""
    
    n_cases = len(all_results)
    n_cols = min(5, n_cases)
    n_rows = (n_cases + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
    if n_cases == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, (case_name, result) in enumerate(all_results.items()):
        ax = axes[idx]
        
        failure_prob = np.array(result["failure_prob"])
        obs_levels = result["obs_levels"]
        noise_levels = result["noise_levels"]
        
        im = ax.imshow(failure_prob, origin="lower", aspect="auto",
                       cmap="RdBu_r", vmin=0, vmax=1,
                       extent=[min(noise_levels), max(noise_levels),
                               min(obs_levels), max(obs_levels)])
        
        # Add contour at 0.5
        ax.contour(noise_levels, obs_levels, failure_prob,
                   levels=[0.5], colors="white", linewidths=2)
        
        ax.set_xlabel("Noise", fontsize=9)
        ax.set_ylabel("Observations", fontsize=9)
        ax.set_title(f"{result['display']}", fontsize=10)
        
        # Add colorbar
        plt.colorbar(im, ax=ax, shrink=0.8)
    
    # Hide unused axes
    for idx in range(n_cases, len(axes)):
        axes[idx].set_visible(False)
    
    fig.suptitle("Task Z1: P(failure|density,noise)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_failure_matrices.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_failure_matrices.png")


def plot_critical_curves(
    all_results: Dict[str, Dict],
    output_dir: Path,
):
    """Plot critical curves (P=0.5 contour) for all cases."""
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    
    for case_name, result in all_results.items():
        curve = result.get("critical_curve", {})
        if curve.get("has_contour", False):
            color = colors.get(result["prototype"], "#666")
            ax.plot(curve["contour_x"], curve["contour_y"],
                    color=color, linewidth=2, alpha=0.8,
                    label=f"{result['display']} (L={curve['curve_length']:.2f})")
    
    ax.set_xlabel("Observations", fontsize=12)
    ax.set_ylabel("Noise", fontsize=12)
    ax.set_title("Task Z2: Critical Curves (P(failure)=0.5)", fontsize=14)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_critical_curves.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_critical_curves.png")


def plot_sensitivity_comparison(
    all_results: Dict[str, Dict],
    output_dir: Path,
):
    """Plot sensitivity comparison across cases."""
    
    cases = list(all_results.keys())
    displays = [all_results[c]["display"] for c in cases]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Density sensitivity
    ax = axes[0, 0]
    values = [all_results[c]["sensitivity"]["mean_density_sensitivity"] for c in cases]
    colors = ["#1f4e79" if all_results[c]["prototype"] == "Non-Degrading" else
              "#2c7a5a" if all_results[c]["prototype"] == "Sharp Boundary" else
              "#FF8C00" if all_results[c]["prototype"] == "Intermediate" else
              "#b64040" for c in cases]
    
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Mean |dP/d(obs)|", fontsize=11)
    ax.set_title("Density Sensitivity", fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")
    
    # Noise sensitivity
    ax = axes[0, 1]
    values = [all_results[c]["sensitivity"]["mean_noise_sensitivity"] for c in cases]
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Mean |dP/d(noise)|", fontsize=11)
    ax.set_title("Noise Sensitivity", fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")
    
    # Critical density
    ax = axes[1, 0]
    values = [all_results[c]["sensitivity"]["mean_critical_density"] for c in cases]
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Critical Observations", fontsize=11)
    ax.set_title("Critical Density (where P>0.5)", fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")
    
    # Critical noise
    ax = axes[1, 1]
    values = [all_results[c]["sensitivity"]["mean_critical_noise"] for c in cases]
    bars = ax.bar(range(len(cases)), values, color=colors, alpha=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(displays, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Critical Noise", fontsize=11)
    ax.set_title("Critical Noise (where P>0.5)", fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")
    
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2c7a5a", label="Non-Degrading"),
        Patch(facecolor="#1f4e79", label="Sharp Boundary"),
        Patch(facecolor="#FF8C00", label="Intermediate"),
        Patch(facecolor="#b64040", label="Broad Band"),
    ]
    axes[0, 0].legend(handles=legend_elements, fontsize=8)
    
    fig.suptitle("Task Z3: Sensitivity Comparison", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_sensitivity.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_sensitivity.png")


def plot_sensitivity_curves(
    all_results: Dict[str, Dict],
    output_dir: Path,
):
    """Plot sensitivity curves: P(failure) vs density at different noise levels."""
    
    n_cases = len(all_results)
    n_cols = min(5, n_cases)
    n_rows = (n_cases + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
    if n_cases == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, (case_name, result) in enumerate(all_results.items()):
        ax = axes[idx]
        
        failure_prob = np.array(result["failure_prob"])
        obs_levels = result["obs_levels"]
        noise_levels = result["noise_levels"]
        
        # Plot P(failure) vs obs for each noise level
        for j, noise in enumerate(noise_levels):
            ax.plot(obs_levels, failure_prob[:, j], "o-",
                    label=f"noise={noise:.2f}", markersize=4, linewidth=1.5)
        
        ax.axhline(y=0.5, color="red", linestyle="--", alpha=0.5, label="P=0.5")
        ax.set_xlabel("Observations", fontsize=9)
        ax.set_ylabel("P(failure)", fontsize=9)
        ax.set_title(f"{result['display']}", fontsize=10)
        ax.legend(fontsize=6, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.05, 1.05)
    
    # Hide unused axes
    for idx in range(n_cases, len(axes)):
        axes[idx].set_visible(False)
    
    fig.suptitle("Task Z3: Failure Probability vs Density (per noise level)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_sensitivity_curves.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_sensitivity_curves.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(all_results: Dict[str, Dict]) -> str:
    """Generate summary report."""
    
    lines = [
        "# 失效概率景观分析报告",
        "",
        "## 概述",
        "",
        "本分析计算每个PDE的P(failure|density,noise)矩阵，提取临界曲线，并比较PDE内部敏感度。",
        "",
        "---",
        "",
        "## Task Z1: 失效概率矩阵",
        "",
        "对于每个PDE，计算P(failure|density,noise)的16x16矩阵。",
        "",
        "---",
        "",
        "## Task Z2: 临界曲线几何特征",
        "",
        "| PDE | 原型 | 曲线长度 | 曲率 | 失效面积 | 连通域数 |",
        "|-----|------|----------|------|----------|----------|",
    ]
    
    for case_name, result in all_results.items():
        curve = result.get("critical_curve", {})
        if curve.get("has_contour", False):
            lines.append(
                f"| {result['display']} | {result['prototype']} | "
                f"{curve['curve_length']:.3f} | {curve['curve_curvature']:.4f} | "
                f"{curve['area_above']:.3f} | {curve['n_components']} |"
            )
        else:
            lines.append(f"| {result['display']} | {result['prototype']} | — | — | — | — |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Task Z3: PDE内部敏感度",
        "",
        "| PDE | 原型 | 密度敏感度 | 噪声敏感度 | 临界密度 | 临界噪声 |",
        "|-----|------|-----------|-----------|----------|----------|",
    ])
    
    for case_name, result in all_results.items():
        sens = result.get("sensitivity", {})
        lines.append(
            f"| {result['display']} | {result['prototype']} | "
            f"{sens.get('mean_density_sensitivity', 0):.4f} | "
            f"{sens.get('mean_noise_sensitivity', 0):.4f} | "
            f"{sens.get('mean_critical_density', 0):.1f} | "
            f"{sens.get('mean_critical_noise', 0):.3f} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 结论",
        "",
        "### Task Z1 结论",
        "",
        "失效概率矩阵展示了每个PDE在不同观测密度和噪声水平下的失效概率分布。",
        "",
        "### Task Z2 结论",
        "",
        "临界曲线的几何特征（长度、曲率、面积、连通域数）可以量化退化边界的复杂性。",
        "",
        "### Task Z3 结论",
        "",
        "敏感度分析比较了每个PDE内部对密度和噪声变化的响应，而不是比较最终统计量。",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Failure Probability Landscape Analysis")
    print("=" * 60)
    
    all_results = {}
    
    # Task Z1: Compute failure matrices
    print("\n[Task Z1] Computing failure probability matrices...")
    for case_name in CASES:
        result = compute_failure_matrix(case_name)
        if result is not None:
            all_results[case_name] = result
            print(f"  {CASES[case_name]['display']}: {len(result['obs_levels'])}x{len(result['noise_levels'])} grid")
    
    # Task Z2: Extract critical curves
    print("\n[Task Z2] Extracting critical curves...")
    for case_name, result in all_results.items():
        failure_prob = np.array(result["failure_prob"])
        curve = extract_critical_curve(
            failure_prob, result["obs_levels"], result["noise_levels"]
        )
        result["critical_curve"] = curve
        
        if curve["has_contour"]:
            print(f"  {result['display']}: length={curve['curve_length']:.3f}, "
                  f"curvature={curve['curve_curvature']:.4f}, "
                  f"area={curve['area_above']:.3f}, "
                  f"components={curve['n_components']}")
        else:
            print(f"  {result['display']}: no contour found")
    
    # Task Z3: Compute sensitivity
    print("\n[Task Z3] Computing sensitivity...")
    for case_name, result in all_results.items():
        failure_prob = np.array(result["failure_prob"])
        sensitivity = compute_sensitivity(
            failure_prob, result["obs_levels"], result["noise_levels"]
        )
        result["sensitivity"] = sensitivity
        
        print(f"  {result['display']}: "
              f"density_sens={sensitivity['mean_density_sensitivity']:.4f}, "
              f"noise_sens={sensitivity['mean_noise_sensitivity']:.4f}, "
              f"critical_density={sensitivity['mean_critical_density']:.1f}")
    
    # Generate figures
    print("\n[FIG] Generating figures...")
    plot_failure_matrices(all_results, OUTPUT_DIR)
    plot_critical_curves(all_results, OUTPUT_DIR)
    plot_sensitivity_comparison(all_results, OUTPUT_DIR)
    plot_sensitivity_curves(all_results, OUTPUT_DIR)
    
    # Save results
    print("\n[SAVE] Saving results...")
    
    # Make JSON serializable
    json_results = {}
    for case_name, result in all_results.items():
        json_results[case_name] = {
            k: v for k, v in result.items()
            if k not in ["contour_x", "contour_y"]
        }
    
    with open(OUTPUT_DIR / "failure_probability_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"  Saved: failure_probability_results.json")
    
    summary = generate_summary(all_results)
    (OUTPUT_DIR / "failure_probability_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: failure_probability_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
