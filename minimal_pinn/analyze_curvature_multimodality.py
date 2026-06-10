"""
Curvature and Multi-Modality Quantification
============================================
Extends the Hessian spectrum analysis with:

1. Curvature metrics:
   - Max eigenvalue (lambda_max)
   - Effective curvature (average of top-k eigenvalues)
   - Correlation with boundary width

2. Multi-modality metrics:
   - Seed variance of rel_l2
   - Basin diversity (output field clustering)
   - Hessian spectral entropy
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
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from torch import nn

from .cases import build_case
from .config import ensure_defaults, load_config
from .network import MLP

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "curvature_multimodality_v1"

CASES = {
    "poisson": {
        "display": "Poisson",
        "display_zh": "Poisson方程",
        "probe": "keypoints_v2_poisson",
        "safe_condition": "obs64_noise000",
        "boundary_width": 1.33,
    },
    "stokes_poiseuille": {
        "display": "Stokes-Poiseuille",
        "display_zh": "斯托克斯-泊肃叶流",
        "probe": "keypoints_v2_stokes",
        "safe_condition": "obs128_noise000",
        "boundary_width": 3.67,
    },
    "allen_cahn": {
        "display": "Allen-Cahn",
        "display_zh": "Allen-Cahn方程",
        "probe": "keypoints_v2_allen_cahn",
        "safe_condition": "obs256_noise000",
        "boundary_width": None,
    },
    "fisher_kpp": {
        "display": "Fisher-KPP",
        "display_zh": "Fisher-KPP方程",
        "probe": "keypoints_v2_fisher_kpp",
        "safe_condition": "obs64_noise000",
        "boundary_width": 5.13,
    },
    "burgers": {
        "display": "Burgers",
        "display_zh": "Burgers方程",
        "probe": "keypoints_v2_burgers",
        "safe_condition": "obs128_noise000",
        "boundary_width": 4.77,
    },
    "heat_equation": {
        "display": "Heat Equation",
        "display_zh": "热方程",
        "probe": "keypoints_v2_heat_equation",
        "safe_condition": "obs256_noise000",
        "boundary_width": None,
    },
    "kdv_soliton": {
        "display": "KdV Soliton",
        "display_zh": "KdV孤子",
        "probe": "keypoints_v2_kdv_soliton",
        "safe_condition": "obs256_noise000",
        "boundary_width": None,
    },
    "nls_soliton": {
        "display": "NLS Soliton",
        "display_zh": "NLS孤子",
        "probe": "keypoints_v2_nls_soliton",
        "safe_condition": "obs256_noise000",
        "boundary_width": None,
    },
    "wave_equation": {
        "display": "Wave Equation",
        "display_zh": "波动方程",
        "probe": "keypoints_v2_wave_equation",
        "safe_condition": "obs256_noise000",
        "boundary_width": None,
    },
    "kdv_double_soliton": {
        "display": "KdV Double Soliton",
        "display_zh": "KdV双孤子",
        "probe": "keypoints_v2_kdv_double_soliton",
        "safe_condition": "obs512_noise000",
        "boundary_width": None,
    },
}


# ═══════════════════════════════════════════════════════════
#  Model Loading (reusing from null_space_hessian)
# ═══════════════════════════════════════════════════════════

def load_trained_model(
    case_name: str,
    condition: str,
    seed: int = 1,
) -> Optional[Tuple[nn.Module, Dict[str, Any]]]:
    """Load a trained model checkpoint."""
    info = CASES.get(case_name)
    if info is None:
        return None

    probe_name = info["probe"]
    run_dir_pattern = f"{case_name}_{probe_name}_{condition}_seed{seed}"
    run_dir = PROBES_DIR / probe_name / "runs" / run_dir_pattern

    if not run_dir.exists():
        for d in (PROBES_DIR / probe_name / "runs").iterdir():
            if d.is_dir() and condition in d.name and f"seed{seed}" in d.name:
                run_dir = d
                break

    ckpt_path = run_dir / "best.ckpt"
    config_path = run_dir / "config.json"

    if not ckpt_path.exists() or not config_path.exists():
        return None

    config = ensure_defaults(load_config(config_path))
    case = build_case(config["case"])
    model = MLP(
        input_dim=case.input_dim,
        output_dim=case.output_dim,
        hidden_layers=config["network"]["hidden_layers"],
        activation=config["network"]["activation"],
    )

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    return model, config


# ═══════════════════════════════════════════════════════════
#  Curvature Metrics
# ═══════════════════════════════════════════════════════════

def compute_curvature_metrics(eigenvalues: np.ndarray) -> Dict[str, float]:
    """
    Compute curvature metrics from Hessian eigenvalues.

    Returns:
        lambda_max: Maximum eigenvalue
        lambda_min: Minimum eigenvalue
        effective_curvature_k5: Average of top 5 eigenvalues
        effective_curvature_k10: Average of top 10 eigenvalues
        curvature_ratio: lambda_max / lambda_min (condition number proxy)
        spectral_gap: lambda_1 - lambda_2
    """
    sorted_eigs = np.sort(np.abs(eigenvalues))[::-1]

    lambda_max = float(sorted_eigs[0])
    lambda_min = float(sorted_eigs[-1])

    # Effective curvature (average of top-k)
    k5 = min(5, len(sorted_eigs))
    k10 = min(10, len(sorted_eigs))
    effective_k5 = float(np.mean(sorted_eigs[:k5]))
    effective_k10 = float(np.mean(sorted_eigs[:k10]))

    # Condition number proxy
    curvature_ratio = lambda_max / max(lambda_min, 1e-10)

    # Spectral gap
    spectral_gap = float(sorted_eigs[0] - sorted_eigs[1]) if len(sorted_eigs) > 1 else 0.0

    return {
        "lambda_max": lambda_max,
        "lambda_min": lambda_min,
        "effective_curvature_k5": effective_k5,
        "effective_curvature_k10": effective_k10,
        "curvature_ratio": float(curvature_ratio),
        "spectral_gap": spectral_gap,
    }


# ═══════════════════════════════════════════════════════════
#  Multi-Modality Metrics
# ═══════════════════════════════════════════════════════════

def compute_seed_variance(
    case_name: str,
    condition: str,
    seeds: List[int] = list(range(1, 31)),
) -> Dict[str, Any]:
    """
    Compute seed variance of rel_l2 across multiple seeds.
    High variance suggests multiple basins.
    """
    rel_l2_values = []
    info = CASES.get(case_name)
    if info is None:
        return {}

    probe_name = info["probe"]
    for seed in seeds:
        run_dir_pattern = f"{case_name}_{probe_name}_{condition}_seed{seed}"
        run_dir = PROBES_DIR / probe_name / "runs" / run_dir_pattern

        metrics_path = run_dir / "metrics.json"
        if not run_dir.exists():
            for d in (PROBES_DIR / probe_name / "runs").iterdir():
                if d.is_dir() and condition in d.name and f"seed{seed}" in d.name:
                    metrics_path = d / "metrics.json"
                    break

        if metrics_path.exists():
            with open(metrics_path, "r") as f:
                metrics = json.load(f)
            rel_l2 = metrics.get("scalar_metrics", {}).get("rel_l2")
            if rel_l2 is not None:
                rel_l2_values.append(float(rel_l2))

    if len(rel_l2_values) < 2:
        return {"n_seeds": len(rel_l2_values), "variance": 0.0, "std": 0.0}

    return {
        "n_seeds": len(rel_l2_values),
        "mean": float(np.mean(rel_l2_values)),
        "std": float(np.std(rel_l2_values)),
        "variance": float(np.var(rel_l2_values)),
        "cv": float(np.std(rel_l2_values) / max(np.mean(rel_l2_values), 1e-10)),
        "values": rel_l2_values,
    }


def compute_basin_diversity(
    case_name: str,
    condition: str,
    seeds: List[int] = list(range(1, 21)),
    n_clusters_range: Tuple[int, int] = (2, 5),
) -> Dict[str, Any]:
    """
    Compute basin diversity by clustering model outputs.
    If multiple clusters appear, suggests multiple basins.

    Uses pairwise output field distance + hierarchical clustering.
    """
    info = CASES.get(case_name)
    if info is None:
        return {}

    probe_name = info["probe"]

    # Load models and compute outputs on a fixed evaluation grid
    models = []
    valid_seeds = []

    for seed in seeds:
        result = load_trained_model(case_name, condition, seed)
        if result is not None:
            model, config = result
            models.append(model)
            valid_seeds.append(seed)

    if len(models) < 3:
        return {"n_models": len(models), "n_clusters": 1}

    # Build case for evaluation
    config = ensure_defaults(load_config(
        PROBES_DIR / probe_name / "runs" /
        f"{case_name}_{probe_name}_{condition}_seed{valid_seeds[0]}" / "config.json"
    ))
    case = build_case(config["case"])

    # Fixed evaluation points
    x_eval = case.sample_eval(num_eval=21, device=torch.device("cpu"))

    # Compute output fields
    outputs = []
    with torch.no_grad():
        for model in models:
            pred = case.observable_prediction(x_eval, model(x_eval))
            outputs.append(pred.numpy().flatten())

    outputs = np.array(outputs)

    # Compute pairwise distances
    dist_matrix = squareform(pdist(outputs, metric="euclidean"))

    # Hierarchical clustering
    Z = linkage(outputs, method="ward")

    # Find optimal number of clusters using silhouette-like criterion
    best_k = 1
    best_score = -1

    for k in range(n_clusters_range[0], n_clusters_range[1] + 1):
        labels = fcluster(Z, t=k, criterion="maxclust") - 1

        # Compute silhouette-like score
        if len(np.unique(labels)) < 2:
            continue

        sil_scores = []
        for i in range(len(outputs)):
            same_cluster = labels == labels[i]
            same_cluster[i] = False
            n_same = same_cluster.sum()

            if n_same == 0:
                continue

            a_i = dist_matrix[i, same_cluster].mean()
            b_i = np.inf
            for c in np.unique(labels):
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

        if sil_scores:
            mean_sil = np.mean(sil_scores)
            if mean_sil > best_score:
                best_score = mean_sil
                best_k = k

    # Compute inter-cluster distances for best_k
    labels = fcluster(Z, t=best_k, criterion="maxclust") - 1
    cluster_centers = []
    for c in range(best_k):
        mask = labels == c
        if mask.any():
            cluster_centers.append(outputs[mask].mean(axis=0))

    inter_cluster_dist = 0
    if len(cluster_centers) > 1:
        inter_cluster_dist = float(np.mean(pdist(np.array(cluster_centers))))

    return {
        "n_models": len(models),
        "n_clusters": best_k,
        "silhouette_score": float(best_score),
        "inter_cluster_distance": inter_cluster_dist,
        "labels": labels.tolist(),
        "valid_seeds": valid_seeds,
    }


def compute_hessian_entropy(eigenvalues: np.ndarray) -> Dict[str, float]:
    """
    Compute Hessian spectral entropy.

    H = -sum(p_i * log(p_i)) where p_i = lambda_i / sum(lambda_i)

    Higher entropy indicates more complex loss landscape.
    """
    # Use absolute values
    eigs_abs = np.abs(eigenvalues)

    # Normalize to probability distribution
    total = eigs_abs.sum()
    if total < 1e-10:
        return {"entropy": 0.0, "normalized_entropy": 0.0, "n_eigenvalues": len(eigenvalues)}

    p = eigs_abs / total

    # Compute entropy (avoid log(0))
    mask = p > 1e-10
    entropy = -np.sum(p[mask] * np.log(p[mask]))

    # Normalized entropy (0 to 1)
    max_entropy = np.log(len(eigenvalues))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    return {
        "entropy": float(entropy),
        "normalized_entropy": float(normalized_entropy),
        "n_eigenvalues": len(eigenvalues),
    }


# ═══════════════════════════════════════════════════════════
#  Analysis Pipeline
# ═══════════════════════════════════════════════════════════

def analyze_single_case(case_name: str) -> Dict[str, Any]:
    """Run all analyses for a single PDE case."""
    info = CASES[case_name]
    safe_condition = info["safe_condition"]

    print(f"\n  Analyzing {info['display']}...")

    # 1. Load eigenvalues from previous Hessian analysis
    eigenvalues_full_path = RESULTS_DIR / "analysis" / "null_space_hessian_v1" / "eigenvalues_full.json"
    eigenvalues = None

    if eigenvalues_full_path.exists():
        with open(eigenvalues_full_path, "r") as f:
            eigenvalues_data = json.load(f)
        if case_name in eigenvalues_data:
            eigenvalues = np.array(eigenvalues_data[case_name])
            print(f"    Eigenvalues loaded from eigenvalues_full.json: {len(eigenvalues)} values")

    # If no eigenvalues found, skip curvature analysis
    curvature_metrics = {}
    entropy_metrics = {}
    if eigenvalues is not None:
        print(f"    Eigenvalues loaded: {len(eigenvalues)} values")
        curvature_metrics = compute_curvature_metrics(eigenvalues)
        entropy_metrics = compute_hessian_entropy(eigenvalues)
        print(f"    lambda_max = {curvature_metrics['lambda_max']:.2e}")
        print(f"    effective_curvature_k5 = {curvature_metrics['effective_curvature_k5']:.2e}")
        print(f"    Hessian entropy = {entropy_metrics['entropy']:.4f}")
    else:
        print(f"    [WARN] No eigenvalues found, skipping curvature analysis")

    # 2. Seed variance
    print(f"    Computing seed variance...")
    seed_var_metrics = compute_seed_variance(case_name, safe_condition)
    if "std" in seed_var_metrics:
        print(f"    Seed std = {seed_var_metrics['std']:.4f}, CV = {seed_var_metrics.get('cv', 0):.4f}")

    # 3. Basin diversity
    print(f"    Computing basin diversity...")
    basin_metrics = compute_basin_diversity(case_name, safe_condition)
    if "n_clusters" in basin_metrics:
        print(f"    Basin clusters = {basin_metrics['n_clusters']}, "
              f"silhouette = {basin_metrics.get('silhouette_score', 0):.3f}")

    return {
        "case": case_name,
        "display": info["display"],
        "boundary_width": info["boundary_width"],
        "curvature": curvature_metrics,
        "seed_variance": {k: v for k, v in seed_var_metrics.items() if k != "values"},
        "basin_diversity": {k: v for k, v in basin_metrics.items() if k != "labels"},
        "hessian_entropy": entropy_metrics,
    }


def run_full_analysis() -> Dict[str, Any]:
    """Run analysis for all PDE cases."""
    results = {}

    for case_name in CASES:
        result = analyze_single_case(case_name)
        results[case_name] = result

    # Compute correlations - only for cases with boundary_width
    case_names = list(results.keys())
    cases_with_width = [c for c in case_names if results[c]["boundary_width"] is not None]
    boundary_widths = [results[c]["boundary_width"] for c in cases_with_width]

    # Curvature correlations
    curvature_corr = {}
    if cases_with_width and results[cases_with_width[0]].get("curvature"):
        for metric in ["lambda_max", "effective_curvature_k5", "effective_curvature_k10"]:
            values = [results[c]["curvature"].get(metric, 0) for c in cases_with_width]
            if any(v > 0 for v in values) and len(values) >= 3:
                corr, p_val = sp_stats.spearmanr(boundary_widths, values)
                curvature_corr[metric] = {"correlation": float(corr), "p_value": float(p_val)}

    # Entropy correlations
    entropy_corr = {}
    if cases_with_width and results[cases_with_width[0]].get("hessian_entropy"):
        for metric in ["entropy", "normalized_entropy"]:
            values = [results[c]["hessian_entropy"].get(metric, 0) for c in cases_with_width]
            if any(v > 0 for v in values) and len(values) >= 3:
                corr, p_val = sp_stats.spearmanr(boundary_widths, values)
                entropy_corr[metric] = {"correlation": float(corr), "p_value": float(p_val)}

    # Seed variance correlations
    seed_var_corr = {}
    for metric in ["std", "variance", "cv"]:
        values = [results[c]["seed_variance"].get(metric, 0) for c in cases_with_width]
        if any(v > 0 for v in values) and len(values) >= 3:
            corr, p_val = sp_stats.spearmanr(boundary_widths, values)
            seed_var_corr[metric] = {"correlation": float(corr), "p_value": float(p_val)}

    return {
        "cases": results,
        "cases_with_boundary_width": cases_with_width,
        "correlations": {
            "curvature_vs_width": curvature_corr,
            "entropy_vs_width": entropy_corr,
            "seed_variance_vs_width": seed_var_corr,
        },
    }


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_curvature_vs_width(
    results: Dict[str, Any],
    output_dir: Path,
):
    """Plot curvature metrics vs boundary width."""
    cases = list(results["cases"].keys())
    displays = [results["cases"][c]["display"] for c in cases]
    widths = [results["cases"][c]["boundary_width"] for c in cases]

    # Filter to cases with boundary_width
    cases_with_width = [c for c in cases if results["cases"][c]["boundary_width"] is not None]
    displays_with_width = [results["cases"][c]["display"] for c in cases_with_width]
    widths_with_width = [results["cases"][c]["boundary_width"] for c in cases_with_width]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    metrics = [
        ("lambda_max", "Max Eigenvalue"),
        ("effective_curvature_k5", "Effective Curvature (k=5)"),
        ("effective_curvature_k10", "Effective Curvature (k=10)"),
    ]

    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513", "#6A5ACD",
              "#FF6347", "#4169E1", "#32CD32", "#FF8C00", "#9370DB"]

    for ax, (metric, label) in zip(axes, metrics):
        values = [results["cases"][c]["curvature"].get(metric, 0) for c in cases_with_width]

        ax.scatter(widths_with_width, values, c=colors[:len(cases_with_width)], s=120, alpha=0.8,
                   edgecolors="white", linewidth=1.5, zorder=5)

        # Add case labels
        for i, (w, v, d) in enumerate(zip(widths_with_width, values, displays_with_width)):
            ax.annotate(d, (w, v), fontsize=8, ha="center", va="bottom",
                       xytext=(0, 8), textcoords="offset points")

        # Add correlation info
        corr_info = results["correlations"]["curvature_vs_width"].get(metric, {})
        if corr_info:
            corr = corr_info["correlation"]
            p = corr_info["p_value"]
            ax.text(0.05, 0.95, f"r = {corr:.3f}\np = {p:.3f}",
                    transform=ax.transAxes, fontsize=9, va="top",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

        # Fit line
        if len(widths_with_width) > 2:
            z = np.polyfit(widths_with_width, values, 1)
            p_line = np.poly1d(z)
            x_line = np.linspace(min(widths_with_width), max(widths_with_width), 100)
            ax.plot(x_line, p_line(x_line), "--", color="gray", alpha=0.5)

        ax.set_xlabel("Boundary Width", fontsize=11)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(f"{label} vs Boundary Width", fontsize=12)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / "fig_curvature_vs_width.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_curvature_vs_width.png")


def plot_multimodality_metrics(
    results: Dict[str, Any],
    output_dir: Path,
):
    """Plot multi-modality metrics comparison."""
    cases = list(results["cases"].keys())
    displays = [results["cases"][c]["display"] for c in cases]
    widths = [results["cases"][c]["boundary_width"] for c in cases]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513"]

    # 1. Seed variance
    ax = axes[0, 0]
    stds = [results["cases"][c]["seed_variance"].get("std", 0) for c in cases]
    bars = ax.bar(displays, stds, color=colors[:len(cases)], alpha=0.8)
    ax.set_ylabel("Seed Std of rel_l2", fontsize=11)
    ax.set_title("Seed Variance (Higher = More Multi-Modal)", fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")

    # Add correlation info
    corr_info = results["correlations"]["seed_variance_vs_width"].get("std", {})
    if corr_info:
        ax.text(0.05, 0.95, f"r = {corr_info['correlation']:.3f}",
                transform=ax.transAxes, fontsize=9, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    # 2. Basin diversity
    ax = axes[0, 1]
    n_clusters = [results["cases"][c]["basin_diversity"].get("n_clusters", 1) for c in cases]
    sil_scores = [results["cases"][c]["basin_diversity"].get("silhouette_score", 0) for c in cases]

    x = range(len(cases))
    bars1 = ax.bar([i - 0.2 for i in x], n_clusters, 0.4, label="N Clusters",
                   color="#1f4e79", alpha=0.8)
    ax2 = ax.twinx()
    bars2 = ax2.bar([i + 0.2 for i in x], sil_scores, 0.4, label="Silhouette",
                    color="#b64040", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(displays, fontsize=9)
    ax.set_ylabel("Number of Clusters", fontsize=11, color="#1f4e79")
    ax2.set_ylabel("Silhouette Score", fontsize=11, color="#b64040")
    ax.set_title("Basin Diversity (More Clusters = More Basins)", fontsize=12)

    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")

    # 3. Hessian entropy
    ax = axes[1, 0]
    entropies = [results["cases"][c]["hessian_entropy"].get("entropy", 0) for c in cases]
    norm_entropies = [results["cases"][c]["hessian_entropy"].get("normalized_entropy", 0) for c in cases]

    x = range(len(cases))
    bars1 = ax.bar([i - 0.2 for i in x], entropies, 0.4, label="Entropy",
                   color="#1f4e79", alpha=0.8)
    ax2 = ax.twinx()
    bars2 = ax2.bar([i + 0.2 for i in x], norm_entropies, 0.4, label="Normalized",
                    color="#b64040", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(displays, fontsize=9)
    ax.set_ylabel("Spectral Entropy", fontsize=11, color="#1f4e79")
    ax2.set_ylabel("Normalized Entropy", fontsize=11, color="#b64040")
    ax.set_title("Hessian Entropy (Higher = More Complex)", fontsize=12)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")

    # 4. Summary scatter: seed_std vs entropy
    ax = axes[1, 1]
    for i, (c, d) in enumerate(zip(cases, displays)):
        sv = results["cases"][c]["seed_variance"].get("std", 0)
        he = results["cases"][c]["hessian_entropy"].get("normalized_entropy", 0)
        w = results["cases"][c]["boundary_width"]
        # Use default size if boundary_width is None
        size = w * 50 if w is not None else 100
        ax.scatter(sv, he, c=colors[i % len(colors)], s=size, alpha=0.8,
                   edgecolors="white", linewidth=1.5, label=d, zorder=5)

    ax.set_xlabel("Seed Std (Multi-Modality)", fontsize=11)
    ax.set_ylabel("Hessian Entropy (Complexity)", fontsize=11)
    ax.set_title("Multi-Modality vs Landscape Complexity", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.suptitle("Multi-Modality Metrics Across PDE Systems", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_multimodality_metrics.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_multimodality_metrics.png")


def plot_correlation_summary(
    results: Dict[str, Any],
    output_dir: Path,
):
    """Plot correlation summary between metrics and boundary width."""
    corr_data = results["correlations"]

    # Collect all correlations
    all_corrs = []
    for category, metrics in corr_data.items():
        for metric, vals in metrics.items():
            all_corrs.append({
                "metric": f"{category.split('_vs_')[0]}_{metric}",
                "correlation": vals["correlation"],
                "p_value": vals["p_value"],
            })

    if not all_corrs:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    metrics = [d["metric"] for d in all_corrs]
    corrs = [d["correlation"] for d in all_corrs]
    p_vals = [d["p_value"] for d in all_corrs]

    colors = ["#1f4e79" if c > 0 else "#b64040" for c in corrs]
    alphas = [1.0 if p < 0.05 else 0.5 for p in p_vals]

    bars = ax.barh(metrics, corrs, color=colors, alpha=0.8)

    # Add value labels
    for bar, corr, p in zip(bars, corrs, p_vals):
        x_pos = bar.get_width() + 0.02 if bar.get_width() >= 0 else bar.get_width() - 0.02
        ha = "left" if bar.get_width() >= 0 else "right"
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                f"{corr:.3f} {sig}", ha=ha, va="center", fontsize=9)

    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xlabel("Spearman Correlation with Boundary Width", fontsize=11)
    ax.set_title("Correlation Between Landscape Metrics and Boundary Width", fontsize=13)
    ax.grid(True, alpha=0.3, axis="x")

    # Add legend for significance
    ax.text(0.98, 0.02, "*** p<0.001, ** p<0.01, * p<0.05, ns: not significant",
            transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    fig.tight_layout()
    fig.savefig(output_dir / "fig_correlation_summary.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_correlation_summary.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(results: Dict[str, Any]) -> str:
    lines = [
        "# 曲率与多谷性量化分析",
        "",
        "## 概述",
        "",
        "本分析量化了损失景观的曲率和多谷性，并检验它们与退化边界宽度的关系。",
        "",
        "---",
        "",
        "## 曲率指标",
        "",
        "| PDE 系统 | 边界宽度 | lambda_max | 有效曲率(k=5) | 有效曲率(k=10) | 谱间隙 |",
        "|----------|----------|-----------|---------------|---------------|--------|",
    ]

    for case_name, result in results["cases"].items():
        display = result["display"]
        width = result["boundary_width"]
        curv = result.get("curvature", {})

        width_str = f"{width:.2f}" if width is not None else "N/A"
        lines.append(
            f"| {display} | {width_str} | "
            f"{curv.get('lambda_max', 0):.2e} | "
            f"{curv.get('effective_curvature_k5', 0):.2e} | "
            f"{curv.get('effective_curvature_k10', 0):.2e} | "
            f"{curv.get('spectral_gap', 0):.2e} |"
        )

    # Correlation table
    lines.extend([
        "",
        "### 曲率与边界宽度的相关性",
        "",
        "| 指标 | Spearman r | p 值 | 显著性 |",
        "|------|-----------|------|--------|",
    ])

    for metric, vals in results["correlations"]["curvature_vs_width"].items():
        sig = "***" if vals["p_value"] < 0.001 else "**" if vals["p_value"] < 0.01 else "*" if vals["p_value"] < 0.05 else "ns"
        lines.append(f"| {metric} | {vals['correlation']:.3f} | {vals['p_value']:.3f} | {sig} |")

    lines.extend([
        "",
        "**假说验证:** 如果曲率与边界宽度呈负相关 (r < 0)，则支持'高曲率→陡边界'的假说。",
        "",
        "---",
        "",
        "## 多谷性指标",
        "",
        "| PDE 系统 | 边界宽度 | 种子标准差 | CV | 谷数 | 轮廓系数 | Hessian 熵 | 归一化熵 |",
        "|----------|----------|----------|-----|------|---------|-----------|---------|",
    ])

    for case_name, result in results["cases"].items():
        display = result["display"]
        width = result["boundary_width"]
        sv = result.get("seed_variance", {})
        bd = result.get("basin_diversity", {})
        he = result.get("hessian_entropy", {})

        width_str = f"{width:.2f}" if width is not None else "N/A"
        lines.append(
            f"| {display} | {width_str} | "
            f"{sv.get('std', 0):.4f} | {sv.get('cv', 0):.4f} | "
            f"{bd.get('n_clusters', 1)} | {bd.get('silhouette_score', 0):.3f} | "
            f"{he.get('entropy', 0):.4f} | {he.get('normalized_entropy', 0):.4f} |"
        )

    # Seed variance correlation
    lines.extend([
        "",
        "### 种子方差与边界宽度的相关性",
        "",
        "| 指标 | Spearman r | p 值 | 显著性 |",
        "|------|-----------|------|--------|",
    ])

    for metric, vals in results["correlations"]["seed_variance_vs_width"].items():
        sig = "***" if vals["p_value"] < 0.001 else "**" if vals["p_value"] < 0.01 else "*" if vals["p_value"] < 0.05 else "ns"
        lines.append(f"| {metric} | {vals['correlation']:.3f} | {vals['p_value']:.3f} | {sig} |")

    # Entropy correlation
    lines.extend([
        "",
        "### Hessian 熵与边界宽度的相关性",
        "",
        "| 指标 | Spearman r | p 值 | 显著性 |",
        "|------|-----------|------|--------|",
    ])

    for metric, vals in results["correlations"]["entropy_vs_width"].items():
        sig = "***" if vals["p_value"] < 0.001 else "**" if vals["p_value"] < 0.01 else "*" if vals["p_value"] < 0.05 else "ns"
        lines.append(f"| {metric} | {vals['correlation']:.3f} | {vals['p_value']:.3f} | {sig} |")

    lines.extend([
        "",
        "---",
        "",
        "## 综合解释",
        "",
        "### 曲率与退化边界",
        "",
        "- **高曲率** (大 lambda_max): 损失景观陡峭，解对扰动敏感",
        "- **低曲率** (小 lambda_max): 损失景观平坦，解对扰动鲁棒",
        "- 如果曲率与边界宽度负相关，则'高曲率→窄边界'",
        "",
        "### 多谷性与退化边界",
        "",
        "- **高种子方差**: 不同种子收敛到不同解，说明存在多个吸引 basin",
        "- **多谷结构**: 输出场聚类出现多个 cluster，说明多个最优解",
        "- **高 Hessian 熵**: 特征值分布均匀，景观更复杂",
        "- 如果多谷性与边界宽度正相关，则'多谷→宽概率边界'",
        "",
        "### 理论意义",
        "",
        "1. **曲率** 可能是退化边界'尖锐性'的直接度量",
        "2. **多谷性** 可能是'概率边界'的根本原因",
        "3. 两者共同解释了为什么不同 PDE 系统有不同的退化原型",
        "",
        "### 局限性",
        "",
        "- Lanczos 算法只近似前 N 个特征值",
        "- Basin diversity 依赖于评估网格的选择",
        "- 需要更多实验验证跨模型的稳定性",
        "",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Curvature and Multi-Modality Quantification")
    print("=" * 70)

    # Run analysis
    results = run_full_analysis()

    # Generate figures
    print("\n" + "=" * 70)
    print("Generating Figures")
    print("=" * 70)

    plot_curvature_vs_width(results, OUTPUT_DIR)
    plot_multimodality_metrics(results, OUTPUT_DIR)
    plot_correlation_summary(results, OUTPUT_DIR)

    # Save results
    print("\n" + "=" * 70)
    print("Saving Results")
    print("=" * 70)

    # Prepare JSON-serializable data
    json_results = {
        "cases": {},
        "correlations": results["correlations"],
    }
    for case_name, result in results["cases"].items():
        json_results["cases"][case_name] = {
            k: v for k, v in result.items()
            if k != "basin_diversity" or "labels" not in v
        }

    with open(OUTPUT_DIR / "curvature_multimodality_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"  Saved: curvature_multimodality_results.json")

    summary = generate_summary(results)
    (OUTPUT_DIR / "curvature_multimodality_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: curvature_multimodality_summary.md")

    print(f"\n{'=' * 70}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 70}")
    print(summary)


if __name__ == "__main__":
    main()
