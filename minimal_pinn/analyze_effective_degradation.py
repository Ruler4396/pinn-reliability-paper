"""
Effective Degradation Metrics, Factor-Behavior Mapping, and PCA Clustering
==========================================================================
Task D: Build effective degradation metrics
Task E: Factor-behavior mapping with new metrics
Task F: Clustering and PCA validation
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
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "effective_degradation_v1"


# ═══════════════════════════════════════════════════════════
#  Data
# ═══════════════════════════════════════════════════════════

CASES = {
    "poisson": {"display": "Poisson", "display_zh": "Poisson方程", "prototype": "Non-Degrading", "threshold": 0.11297},
    "stokes_poiseuille": {"display": "Stokes-Poiseuille", "display_zh": "斯托克斯-泊肃叶流", "prototype": "Sharp Boundary", "threshold": 0.015379},
    "allen_cahn": {"display": "Allen-Cahn", "display_zh": "Allen-Cahn方程", "prototype": "Broad Band", "threshold": 0.05},
    "fisher_kpp": {"display": "Fisher-KPP", "display_zh": "Fisher-KPP方程", "prototype": "Intermediate", "threshold": 0.018861},
    "burgers": {"display": "Burgers", "display_zh": "Burgers方程", "prototype": "Broad Band", "threshold": 0.026688},
    "heat_equation": {"display": "Heat Equation", "display_zh": "热方程", "prototype": "Broad Band", "threshold": 0.05},
    "kdv_soliton": {"display": "KdV Soliton", "display_zh": "KdV孤子", "prototype": "Broad Band", "threshold": 0.05},
    "nls_soliton": {"display": "NLS Soliton", "display_zh": "NLS孤子", "prototype": "Broad Band", "threshold": 0.05},
    "wave_equation": {"display": "Wave Equation", "display_zh": "波动方程", "prototype": "Broad Band", "threshold": 0.05},
    "kdv_double_soliton": {"display": "KdV Double", "display_zh": "KdV双孤子", "prototype": "Broad Band", "threshold": 0.05},
}


# ═══════════════════════════════════════════════════════════
#  Task D: Build Effective Degradation Metrics
# ═══════════════════════════════════════════════════════════

def compute_effective_degradation() -> Dict[str, Dict[str, float]]:
    """
    Compute effective degradation metrics for all PDE cases.
    
    Metrics:
    - probability_band_area: fraction of keypoints with 0.2 <= cross_rate <= 0.8
    - mean_failure_entropy: mean entropy of failure probability distribution
    - irregularity: max jump in crossing rates
    - seed_variability: mean std of rel_l2 across seeds per keypoint
    """
    
    results = {}
    
    for case_name, info in CASES.items():
        probe_dir = PROBES_DIR / f"keypoints_v2_{case_name}"
        runs_csv = probe_dir / "probe_runs.csv"
        
        if not runs_csv.exists():
            continue
        
        df = pd.read_csv(runs_csv)
        threshold = info["threshold"]
        
        # Compute crossing rates per keypoint
        cross_rates = []
        seed_stds = []
        
        for label in df["label"].unique():
            label_data = df[df["label"] == label]
            
            # Crossing rate
            rate = (label_data["rel_l2"] > threshold).mean()
            cross_rates.append(rate)
            
            # Seed std
            if len(label_data) > 1:
                seed_stds.append(label_data["rel_l2"].std())
        
        cross_rates = np.array(cross_rates)
        
        # Probability band area: fraction of keypoints in transition zone
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
        
        # Irregularity: max jump in crossing rates
        sorted_rates = np.sort(cross_rates)
        if len(sorted_rates) >= 2:
            jumps = np.abs(np.diff(sorted_rates))
            irregularity = float(np.max(jumps))
        else:
            irregularity = 0
        
        # Seed variability
        seed_variability = np.mean(seed_stds) if seed_stds else 0
        
        results[case_name] = {
            "display": info["display"],
            "prototype": info["prototype"],
            "probability_band_area": float(prob_band_area),
            "mean_failure_entropy": float(mean_failure_entropy),
            "irregularity": float(irregularity),
            "seed_variability": float(seed_variability),
            "cross_rates": cross_rates.tolist(),
        }
        
        print(f"  {info['display']:<20} PBA={prob_band_area:.3f}  MFE={mean_failure_entropy:.4f}  "
              f"IRR={irregularity:.3f}  SV={seed_variability:.4f}")
    
    return results


def load_landscape_metrics() -> Dict[str, Dict[str, float]]:
    """Load landscape metrics from previous analyses."""
    
    d_null = {
        "poisson": 18, "stokes_poiseuille": 19, "allen_cahn": 29,
        "fisher_kpp": 34, "burgers": 27, "heat_equation": 26,
        "kdv_soliton": 38, "nls_soliton": 23, "wave_equation": 17,
        "kdv_double_soliton": 32,
    }
    
    lambda_max = {
        "poisson": 2540.0, "stokes_poiseuille": 446.0, "allen_cahn": 555.0,
        "fisher_kpp": 269.0, "burgers": 1300.0, "heat_equation": 903.0,
        "kdv_soliton": 906.0, "nls_soliton": 473.0, "wave_equation": 1111.0,
        "kdv_double_soliton": 2890.0,
    }
    
    hessian_entropy = {
        "poisson": 3.9679, "stokes_poiseuille": 3.9821, "allen_cahn": 3.7366,
        "fisher_kpp": 3.8574, "burgers": 3.7846, "heat_equation": 3.7835,
        "kdv_soliton": 3.5509, "nls_soliton": 3.8558, "wave_equation": 3.8830,
        "kdv_double_soliton": 3.6104,
    }
    
    info_cv = {
        "poisson": 0.3035, "stokes_poiseuille": 0.1938, "allen_cahn": 1.1782,
        "fisher_kpp": 0.8504, "burgers": 0.4512, "heat_equation": 0.4506,
        "kdv_soliton": 1.6765, "nls_soliton": 1.6215, "wave_equation": 0.3033,
        "kdv_double_soliton": 2.0035,
    }
    
    data = {}
    for case in d_null.keys():
        data[case] = {
            "d_null": d_null[case],
            "lambda_max": lambda_max[case],
            "hessian_entropy": hessian_entropy[case],
            "info_cv": info_cv[case],
        }
    
    return data


# ═══════════════════════════════════════════════════════════
#  Task E: Factor-Behavior Mapping
# ═══════════════════════════════════════════════════════════

def task_e_factor_behavior(
    landscape: Dict[str, Dict],
    degradation: Dict[str, Dict],
) -> Dict[str, Any]:
    """Task E: Compute factor-behavior correlations with new metrics."""
    
    print("\n" + "=" * 60)
    print("TASK E: Factor-Behavior Mapping")
    print("=" * 60)
    
    common_cases = [c for c in landscape if c in degradation]
    
    # Define correlations
    correlations = [
        ("d_null", "probability_band_area", "d_null <-> PBA"),
        ("lambda_max", "mean_failure_entropy", "lambda <-> MFE"),
        ("hessian_entropy", "seed_variability", "entropy <-> seed_var"),
        ("info_cv", "irregularity", "infoCV <-> IRR"),
        ("d_null", "seed_variability", "d_null <-> seed_var"),
        ("lambda_max", "irregularity", "lambda <-> IRR"),
        ("hessian_entropy", "probability_band_area", "entropy <-> PBA"),
        ("info_cv", "mean_failure_entropy", "infoCV <-> MFE"),
    ]
    
    results = {}
    
    print(f"\n  {'Correlation':<35} {'Spearman':>10} {'Pearson':>10} {'95% CI':>20} {'p':>8} {'Sig':>5}")
    print(f"  {'-' * 95}")
    
    for x_metric, y_metric, label in correlations:
        x_vals = []
        y_vals = []
        
        for case in common_cases:
            if x_metric in landscape[case] and y_metric in degradation[case]:
                x_vals.append(landscape[case][x_metric])
                y_vals.append(degradation[case][y_metric])
        
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
            
            sig = "***" if spearman_p < 0.01 else "**" if spearman_p < 0.05 else "*" if spearman_p < 0.1 else "ns"
            
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
            }
            
            print(f"  {label:<35} {spearman_r:>10.3f} {pearson_r:>10.3f} "
                  f"[{ci_lower:.3f}, {ci_upper:.3f}] {spearman_p:>8.3f} {sig:>5}")
    
    return results


# ═══════════════════════════════════════════════════════════
#  Task F: Clustering and PCA Validation
# ═══════════════════════════════════════════════════════════

def task_f_clustering_pca(
    degradation: Dict[str, Dict],
    landscape: Dict[str, Dict],
) -> Dict[str, Any]:
    """Task F: Clustering and PCA with new degradation metrics."""
    
    print("\n" + "=" * 60)
    print("TASK F: Clustering and PCA Validation")
    print("=" * 60)
    
    common_cases = [c for c in degradation if c in landscape]
    
    # Build feature matrix with degradation metrics
    degradation_metrics = ["probability_band_area", "mean_failure_entropy", "irregularity", "seed_variability"]
    
    X_deg = np.array([[degradation[c][m] for m in degradation_metrics] for c in common_cases])
    
    # Standardize
    X_deg_std = (X_deg - X_deg.mean(axis=0)) / X_deg.std(axis=0)
    
    # PCA on degradation metrics
    cov_deg = np.cov(X_deg_std.T)
    eigenvalues_deg, eigenvectors_deg = np.linalg.eigh(cov_deg)
    
    # Sort descending
    idx = np.argsort(eigenvalues_deg)[::-1]
    eigenvalues_deg = eigenvalues_deg[idx]
    eigenvectors_deg = eigenvectors_deg[:, idx]
    
    explained_ratio_deg = eigenvalues_deg / eigenvalues_deg.sum()
    cumulative_deg = np.cumsum(explained_ratio_deg)
    
    print("\n  PCA on Degradation Metrics:")
    for i, m in enumerate(degradation_metrics):
        print(f"    {m}: PC1={eigenvectors_deg[i, 0]:.3f}, PC2={eigenvectors_deg[i, 1]:.3f}")
    print(f"\n  Explained variance: PC1={explained_ratio_deg[0]:.1%}, PC2={explained_ratio_deg[1]:.1%}")
    
    # Project onto PC1-PC2
    projected_deg = X_deg_std @ eigenvectors_deg[:, :2]
    
    # Combine with landscape PCA (from previous analysis)
    landscape_metrics = ["d_null", "lambda_max", "hessian_entropy", "info_cv"]
    X_land = np.array([[landscape[c][m] for m in landscape_metrics] for c in common_cases])
    X_land_std = (X_land - X_land.mean(axis=0)) / X_land.std(axis=0)
    
    cov_land = np.cov(X_land_std.T)
    eigenvalues_land, eigenvectors_land = np.linalg.eigh(cov_land)
    idx = np.argsort(eigenvalues_land)[::-1]
    eigenvalues_land = eigenvalues_land[idx]
    eigenvectors_land = eigenvectors_land[:, idx]
    
    explained_ratio_land = eigenvalues_land / eigenvalues_land.sum()
    projected_land = X_land_std @ eigenvectors_land[:, :2]
    
    # Clustering with combined features
    # Combine degradation PC1-PC2 with landscape PC1-PC2
    X_combined = np.column_stack([projected_deg, projected_land])
    X_combined_std = (X_combined - X_combined.mean(axis=0)) / X_combined.std(axis=0)
    
    # Hierarchical clustering
    Z = linkage(X_combined_std, method="ward")
    
    # Try k=2,3,4
    clustering_results = {}
    
    print("\n  Clustering Results (Degradation PC + Landscape PC):")
    
    for k in range(2, 5):
        labels = fcluster(Z, t=k, criterion="maxclust") - 1
        
        # Compute silhouette
        dist_matrix = squareform(pdist(X_combined_std))
        sil_scores = []
        
        for i in range(len(X_combined_std)):
            same_cluster = labels == labels[i]
            same_cluster[i] = False
            n_same = same_cluster.sum()
            
            if n_same == 0:
                continue
            
            a_i = dist_matrix[i, same_cluster].mean()
            b_i = np.inf
            for c in range(k):
                if c == labels[i]:
                    continue
                mask = labels == c
                if mask.sum() > 0:
                    mean_dist = dist_matrix[i, mask].mean()
                    b_i = min(b_i, mean_dist)
            
            if np.isinf(b_i):
                continue
            
            sil = (b_i - a_i) / max(a_i, b_i) if max(a_i, b_i) > 0 else 0
            sil_scores.append(sil)
        
        mean_sil = np.mean(sil_scores) if sil_scores else 0
        
        clustering_results[k] = {
            "labels": labels.tolist(),
            "silhouette": float(mean_sil),
        }
        
        print(f"\n    k={k}: Silhouette={mean_sil:.3f}")
        for cluster_id in range(k):
            cluster_cases = [common_cases[i] for i in range(len(common_cases)) if labels[i] == cluster_id]
            cluster_displays = [degradation[c]["display"] for c in cluster_cases]
            cluster_prototypes = [degradation[c]["prototype"] for c in cluster_cases]
            print(f"      Cluster {cluster_id}: {', '.join(cluster_displays)}")
            print(f"        Prototypes: {', '.join(set(cluster_prototypes))}")
    
    return {
        "degradation_metrics": degradation_metrics,
        "landscape_metrics": landscape_metrics,
        "eigenvalues_deg": eigenvalues_deg.tolist(),
        "explained_ratio_deg": explained_ratio_deg.tolist(),
        "eigenvectors_deg": eigenvectors_deg.tolist(),
        "projected_deg": projected_deg.tolist(),
        "eigenvalues_land": eigenvalues_land.tolist(),
        "explained_ratio_land": explained_ratio_land.tolist(),
        "projected_land": projected_land.tolist(),
        "clustering": clustering_results,
        "cases": common_cases,
    }


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_all(
    degradation: Dict[str, Dict],
    landscape: Dict[str, Dict],
    task_e_results: Dict,
    task_f_results: Dict,
    output_dir: Path,
):
    """Generate all figures."""
    
    cases = list(degradation.keys())
    displays = [degradation[c]["display"] for c in cases]
    prototypes = [degradation[c]["prototype"] for c in cases]
    
    prototype_colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    colors = [prototype_colors.get(p, "#666") for p in prototypes]
    
    # Figure 1: Degradation metrics by prototype
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    metrics = ["probability_band_area", "mean_failure_entropy", "irregularity", "seed_variability"]
    titles = ["Probability Band Area", "Mean Failure Entropy", "Irregularity", "Seed Variability"]
    
    for ax, metric, title in zip(axes.flatten(), metrics, titles):
        proto_data = {}
        for case, data in degradation.items():
            proto = data["prototype"]
            if proto not in proto_data:
                proto_data[proto] = []
            proto_data[proto].append(data[metric])
        
        proto_names = list(proto_data.keys())
        proto_values = [proto_data[p] for p in proto_names]
        proto_colors = [prototype_colors.get(p, "#666") for p in proto_names]
        
        bp = ax.boxplot(proto_values, labels=proto_names, patch_artist=True)
        for patch, color in zip(bp["boxes"], proto_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(metric, fontsize=10)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis="y")
    
    fig.suptitle("Task D: Effective Degradation Metrics by Prototype", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig1_degradation_metrics.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig1_degradation_metrics.png")
    
    # Figure 2: Factor-behavior correlations
    n_corr = len(task_e_results)
    if n_corr > 0:
        n_cols = min(4, n_corr)
        n_rows = (n_corr + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
        if n_corr == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for idx, (label, result) in enumerate(task_e_results.items()):
            ax = axes[idx]
            
            x_vals = []
            y_vals = []
            for case in result.get("cases", degradation.keys()):
                x_metric = result["x_metric"]
                y_metric = result["y_metric"]
                if case in landscape and case in degradation:
                    if x_metric in landscape[case] and y_metric in degradation[case]:
                        x_vals.append(landscape[case][x_metric])
                        y_vals.append(degradation[case][y_metric])
            
            for i, (x, y) in enumerate(zip(x_vals, y_vals)):
                case = list(degradation.keys())[i] if i < len(degradation) else None
                if case:
                    proto = degradation[case]["prototype"]
                    ax.scatter(x, y, c=prototype_colors.get(proto, "#666"), s=100, alpha=0.8,
                              edgecolors="white", linewidth=1)
                    ax.annotate(degradation[case]["display"], (x, y), fontsize=7, ha="center", va="bottom",
                               xytext=(0, 5), textcoords="offset points")
            
            sig = "***" if result["spearman_p"] < 0.01 else "**" if result["spearman_p"] < 0.05 else "*" if result["spearman_p"] < 0.1 else "ns"
            ax.text(0.05, 0.95, f"r={result['spearman_r']:.3f} {sig}\n"
                    f"95% CI [{result['ci_lower']:.3f}, {result['ci_upper']:.3f}]",
                    transform=ax.transAxes, fontsize=9, va="top",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
            
            ax.set_xlabel(result["x_metric"], fontsize=10)
            ax.set_ylabel(result["y_metric"], fontsize=10)
            ax.set_title(label, fontsize=10)
            ax.grid(True, alpha=0.3)
        
        for idx in range(n_corr, len(axes)):
            axes[idx].set_visible(False)
        
        fig.suptitle("Task E: Factor-Behavior Correlations", fontsize=14)
        fig.tight_layout()
        fig.savefig(output_dir / "fig2_factor_behavior.png", dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: fig2_factor_behavior.png")
    
    # Figure 3: PCA projections
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Degradation PCA
    ax = axes[0]
    projected_deg = np.array(task_f_results["projected_deg"])
    for i, case in enumerate(task_f_results["cases"]):
        proto = degradation[case]["prototype"]
        ax.scatter(projected_deg[i, 0], projected_deg[i, 1],
                  c=prototype_colors.get(proto, "#666"), s=120, alpha=0.8,
                  edgecolors="white", linewidth=1.5, zorder=5)
        ax.annotate(degradation[case]["display"], (projected_deg[i, 0], projected_deg[i, 1]),
                   fontsize=9, ha="center", va="bottom",
                   xytext=(0, 8), textcoords="offset points")
    
    ax.set_xlabel(f"Deg PC1 ({task_f_results['explained_ratio_deg'][0]:.1%} var)", fontsize=11)
    ax.set_ylabel(f"Deg PC2 ({task_f_results['explained_ratio_deg'][1]:.1%} var)", fontsize=11)
    ax.set_title("Degradation Metrics PCA", fontsize=12)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
    ax.axvline(x=0, color="gray", linestyle="--", alpha=0.3)
    ax.grid(True, alpha=0.3)
    
    # Landscape PCA
    ax = axes[1]
    projected_land = np.array(task_f_results["projected_land"])
    for i, case in enumerate(task_f_results["cases"]):
        proto = degradation[case]["prototype"]
        ax.scatter(projected_land[i, 0], projected_land[i, 1],
                  c=prototype_colors.get(proto, "#666"), s=120, alpha=0.8,
                  edgecolors="white", linewidth=1.5, zorder=5)
        ax.annotate(degradation[case]["display"], (projected_land[i, 0], projected_land[i, 1]),
                   fontsize=9, ha="center", va="bottom",
                   xytext=(0, 8), textcoords="offset points")
    
    ax.set_xlabel(f"Land PC1 ({task_f_results['explained_ratio_land'][0]:.1%} var)", fontsize=11)
    ax.set_ylabel(f"Land PC2 ({task_f_results['explained_ratio_land'][1]:.1%} var)", fontsize=11)
    ax.set_title("Landscape Metrics PCA", fontsize=12)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
    ax.axvline(x=0, color="gray", linestyle="--", alpha=0.3)
    ax.grid(True, alpha=0.3)
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=p) for p, c in prototype_colors.items()]
    axes[1].legend(handles=legend_elements, fontsize=9)
    
    fig.suptitle("Task F: PCA Projections", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig3_pca_projections.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig3_pca_projections.png")
    
    # Figure 4: Clustering comparison
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, k in enumerate([2, 3, 4]):
        ax = axes[idx]
        labels = task_f_results["clustering"][k]["labels"]
        sil = task_f_results["clustering"][k]["silhouette"]
        
        cluster_colors = ["#1f4e79", "#b64040", "#2c7a5a", "#8B4513"]
        
        # Use degradation PC1-PC2 for plotting
        for i, case in enumerate(task_f_results["cases"]):
            ax.scatter(projected_deg[i, 0], projected_deg[i, 1],
                      c=cluster_colors[labels[i]], s=120, alpha=0.8,
                      edgecolors="white", linewidth=1.5, zorder=5)
            ax.annotate(degradation[case]["display"], (projected_deg[i, 0], projected_deg[i, 1]),
                       fontsize=8, ha="center", va="bottom",
                       xytext=(0, 5), textcoords="offset points")
        
        ax.set_xlabel("Deg PC1", fontsize=11)
        ax.set_ylabel("Deg PC2", fontsize=11)
        ax.set_title(f"k={k} (Silhouette={sil:.3f})", fontsize=12)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle("Task F: Clustering on Degradation PCA Space", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig4_clustering.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig4_clustering.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    degradation: Dict[str, Dict],
    task_e_results: Dict,
    task_f_results: Dict,
) -> str:
    """Generate summary report."""
    
    lines = [
        "# 有效退化指标、因素映射与聚类验证",
        "",
        "## Task D: 有效退化指标",
        "",
        "| PDE | 原型 | PBA | MFE | IRR | seed_var |",
        "|-----|------|-----|-----|-----|----------|",
    ]
    
    for case, data in degradation.items():
        lines.append(
            f"| {data['display']} | {data['prototype']} | "
            f"{data['probability_band_area']:.3f} | {data['mean_failure_entropy']:.4f} | "
            f"{data['irregularity']:.3f} | {data['seed_variability']:.4f} |"
        )
    
    lines.extend([
        "",
        "**指标定义:**",
        "- PBA: probability_band_area (0.2 <= cross_rate <= 0.8 的比例)",
        "- MFE: mean_failure_entropy (失效概率分布的平均熵)",
        "- IRR: irregularity (越界率最大跳变)",
        "- seed_var: seed_variability (跨种子rel_l2标准差均值)",
        "",
        "---",
        "",
        "## Task E: 因素→行为映射",
        "",
        "| 相关性 | Spearman r | 95% CI | p | 显著性 |",
        "|--------|-----------|--------|---|--------|",
    ])
    
    for label, result in task_e_results.items():
        sig = "***" if result["spearman_p"] < 0.01 else "**" if result["spearman_p"] < 0.05 else "*" if result["spearman_p"] < 0.1 else "ns"
        lines.append(
            f"| {label} | {result['spearman_r']:.3f} | "
            f"[{result['ci_lower']:.3f}, {result['ci_upper']:.3f}] | "
            f"{result['spearman_p']:.3f} | {sig} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Task F: 聚类与PCA验证",
        "",
        "### PCA结果",
        "",
        "**退化指标PCA:**",
        f"- PC1解释率: {task_f_results['explained_ratio_deg'][0]:.1%}",
        f"- PC2解释率: {task_f_results['explained_ratio_deg'][1]:.1%}",
        "",
        "**景观指标PCA:**",
        f"- PC1解释率: {task_f_results['explained_ratio_land'][0]:.1%}",
        f"- PC2解释率: {task_f_results['explained_ratio_land'][1]:.1%}",
        "",
        "### 聚类结果",
        "",
        "| k | Silhouette | Cluster 0 | Cluster 1 | Cluster 2 | Cluster 3 |",
        "|---|------------|-----------|-----------|-----------|-----------|",
    ])
    
    for k in [2, 3, 4]:
        labels = task_f_results["clustering"][k]["labels"]
        sil = task_f_results["clustering"][k]["silhouette"]
        
        clusters = {}
        for i, case in enumerate(task_f_results["cases"]):
            cid = labels[i]
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append(degradation[case]["display"])
        
        row = f"| {k} | {sil:.3f} |"
        for cid in range(k):
            if cid in clusters:
                row += f" {', '.join(clusters[cid])} |"
            else:
                row += " — |"
        lines.append(row)
    
    lines.extend([
        "",
        "---",
        "",
        "## 结论",
        "",
        "### Task D 结论",
        "",
        "新退化指标是否能区分三种原型？",
        "",
        "### Task E 结论",
        "",
        "哪些因素→行为相关性最强？",
        "",
        "### Task F 结论",
        "",
        "原型是否在PCA空间中自然分离？",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Effective Degradation Metrics Analysis")
    print("=" * 60)
    
    # Task D
    print("\n[Task D] Computing effective degradation metrics...")
    degradation = compute_effective_degradation()
    
    # Load landscape metrics
    print("\n[Loading] Landscape metrics...")
    landscape = load_landscape_metrics()
    
    # Task E
    task_e_results = task_e_factor_behavior(landscape, degradation)
    
    # Task F
    task_f_results = task_f_clustering_pca(degradation, landscape)
    
    # Generate figures
    print("\n[FIG] Generating figures...")
    plot_all(degradation, landscape, task_e_results, task_f_results, OUTPUT_DIR)
    
    # Save results
    print("\n[SAVE] Saving results...")
    
    all_results = {
        "degradation_metrics": {c: {k: v for k, v in d.items() if k != "display" and k != "prototype" and k != "cross_rates"} 
                                for c, d in degradation.items()},
        "factor_behavior": task_e_results,
        "clustering_pca": task_f_results,
    }
    
    with open(OUTPUT_DIR / "effective_degradation_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Saved: effective_degradation_results.json")
    
    summary = generate_summary(degradation, task_e_results, task_f_results)
    (OUTPUT_DIR / "effective_degradation_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: effective_degradation_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
