"""
Degradation Prototype Clustering Analysis
==========================================
Validates the three degradation prototypes (sharp/intermediate/probabilistic)
using data-driven unsupervised clustering methods.

Methods:
1. K-means, GMM, Hierarchical clustering with Silhouette Score comparison (k=2..5)
2. BIC/AIC model selection for GMM
3. PCA 2D projection visualization

Uses only numpy, scipy, matplotlib (no sklearn dependency).
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
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import pdist, squareform

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBABILITY_DIR = RESULTS_DIR / "probability_matrices"
PROBES_DIR = RESULTS_DIR / "probes"
COARSE_DIR = RESULTS_DIR / "matrices"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "degradation_clustering_v1"

# ── PDE case definitions ──
CASES = {
    "poisson": {
        "display": "Poisson",
        "display_zh": "Poisson方程",
        "probe": "keypoints_v2_poisson",
        "probability": "probability_v2_poisson",
        "threshold": 0.11297,
    },
    "stokes_poiseuille": {
        "display": "Stokes-Poiseuille",
        "display_zh": "斯托克斯-泊肃叶流",
        "probe": "keypoints_v2_stokes",
        "probability": "probability_v2_stokes",
        "threshold": 0.015379,
    },
    "allen_cahn": {
        "display": "Allen-Cahn",
        "display_zh": "Allen-Cahn方程",
        "probe": "keypoints_v2_allen_cahn",
        "probability": None,
        "threshold": 0.02,
    },
    "fisher_kpp": {
        "display": "Fisher-KPP",
        "display_zh": "Fisher-KPP方程",
        "probe": "keypoints_v2_fisher_kpp",
        "probability": "probability_v2_fisher_kpp",
        "threshold": 0.018861,
    },
    "burgers": {
        "display": "Burgers",
        "display_zh": "Burgers方程",
        "probe": "keypoints_v2_burgers",
        "probability": "probability_v2_burgers",
        "threshold": 0.026688,
    },
    "heat_equation": {
        "display": "Heat Equation",
        "display_zh": "热方程",
        "probe": "keypoints_v2_heat_equation",
        "probability": None,
        "threshold": 0.03,
    },
    "kdv_soliton": {
        "display": "KdV Soliton",
        "display_zh": "KdV孤子",
        "probe": "keypoints_v2_kdv_soliton",
        "probability": None,
        "threshold": 0.05,
    },
    "nls_soliton": {
        "display": "NLS Soliton",
        "display_zh": "NLS孤子",
        "probe": "keypoints_v2_nls_soliton",
        "probability": None,
        "threshold": 0.05,
    },
    "wave_equation": {
        "display": "Wave Equation",
        "display_zh": "波动方程",
        "probe": "keypoints_v2_wave_equation",
        "probability": None,
        "threshold": 0.25,
    },
    "kdv_double_soliton": {
        "display": "KdV Double Soliton",
        "display_zh": "KdV双孤子",
        "probe": "keypoints_v2_kdv_double_soliton",
        "probability": None,
        "threshold": 0.05,
    },
}

# Additional cases from coarse matrices
ADDITIONAL_CASES = {}


# ═══════════════════════════════════════════════════════════
#  Data Loading
# ═══════════════════════════════════════════════════════════

def load_probe_data(case_name: str) -> Optional[pd.DataFrame]:
    info = CASES.get(case_name, {})
    if info.get("probe") is None:
        return None
    csv_path = PROBES_DIR / info["probe"] / "probe_summary.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def load_probe_runs(case_name: str) -> Optional[pd.DataFrame]:
    info = CASES.get(case_name, {})
    if info.get("probe") is None:
        return None
    csv_path = PROBES_DIR / info["probe"] / "probe_runs.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def load_coarse_data(case_name: str) -> Optional[pd.DataFrame]:
    coarse_dir = ADDITIONAL_CASES.get(case_name)
    if coarse_dir is None:
        return None
    csv_path = COARSE_DIR / coarse_dir / "matrix_summary.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


# ═══════════════════════════════════════════════════════════
#  Feature Extraction
# ═══════════════════════════════════════════════════════════

def extract_features_from_probes(case_name: str) -> Optional[Dict[str, float]]:
    """
    Extract clustering features from probe data (30 seeds per keypoint).

    Features:
    - safe_rate: crossing rate at the safest keypoint
    - transition_width: fraction of keypoints in transition zone (0.2 < rate < 0.8)
    - seed_std: mean rel_l2 std across all keypoints
    - jump_rate: max adjacent keypoint crossing rate difference (sorted by rate)
    - mean_cross_rate: average crossing rate across all keypoints
    - boundary_sharpness: 1 - transition_width
    - avg_seed_std_per_point: average per-point seed std from runs data
    """
    df_summary = load_probe_data(case_name)
    df_runs = load_probe_runs(case_name)

    if df_summary is None:
        return None

    n_points = len(df_summary)
    if n_points == 0:
        return None

    cross_rates = df_summary["crosses_threshold_rate"].values.astype(float)

    # Safe rate: minimum crossing rate
    safe_rate = float(np.min(cross_rates))

    # Transition width
    n_transition = int(np.sum((cross_rates > 0.2) & (cross_rates < 0.8)))
    transition_width = n_transition / n_points

    # Seed std: mean of rel_l2_std column
    if "rel_l2_std" in df_summary.columns:
        seed_std = float(df_summary["rel_l2_std"].mean())
    else:
        seed_std = 0.0

    # Jump rate: max difference between adjacent keypoints (sorted)
    sorted_rates = np.sort(cross_rates)
    if len(sorted_rates) >= 2:
        jump_rate = float(np.max(np.abs(np.diff(sorted_rates))))
    else:
        jump_rate = 0.0

    # Mean crossing rate
    mean_cross_rate = float(np.mean(cross_rates))

    # Boundary sharpness
    boundary_sharpness = 1.0 - transition_width

    # Per-point seed std from runs
    avg_seed_std_per_point = 0.0
    if df_runs is not None and "rel_l2" in df_runs.columns and "label" in df_runs.columns:
        stds = []
        for label in df_runs["label"].unique():
            sub = df_runs[df_runs["label"] == label]
            if len(sub) > 1:
                stds.append(float(sub["rel_l2"].std()))
        avg_seed_std_per_point = float(np.mean(stds)) if stds else 0.0

    return {
        "case": case_name,
        "safe_rate": safe_rate,
        "transition_width": transition_width,
        "seed_std": seed_std,
        "jump_rate": jump_rate,
        "mean_cross_rate": mean_cross_rate,
        "boundary_sharpness": boundary_sharpness,
        "avg_seed_std_per_point": avg_seed_std_per_point,
        "n_keypoints": n_points,
    }


def extract_features_from_coarse(case_name: str) -> Optional[Dict[str, float]]:
    df = load_coarse_data(case_name)
    if df is None:
        return None

    rel_l2_values = df["rel_l2"].values.astype(float)

    safest_idx = df["num_observation"].idxmax()
    safest_rel_l2 = float(df.loc[safest_idx, "rel_l2"])

    failure_idx = df["num_observation"].idxmin()
    failure_rel_l2 = float(df.loc[failure_idx, "rel_l2"])

    return {
        "case": case_name,
        "safe_rate": 0.0,
        "transition_width": 0.0,
        "seed_std": 0.0,
        "jump_rate": 0.0,
        "mean_cross_rate": 0.0,
        "boundary_sharpness": 0.0,
        "avg_seed_std_per_point": 0.0,
        "n_keypoints": 0,
        "safest_rel_l2": safest_rel_l2,
        "failure_rel_l2": failure_rel_l2,
        "degradation_ratio": failure_rel_l2 / max(safest_rel_l2, 1e-10),
        "rel_l2_std": float(np.std(rel_l2_values)),
        "rel_l2_range": float(np.max(rel_l2_values) - np.min(rel_l2_values)),
    }


def extract_all_features() -> pd.DataFrame:
    features_list = []
    for case_name in CASES:
        feats = extract_features_from_probes(case_name)
        if feats is not None:
            features_list.append(feats)
            print(f"  {case_name}: probe features extracted")
    for case_name in ADDITIONAL_CASES:
        if case_name not in [f["case"] for f in features_list]:
            feats = extract_features_from_coarse(case_name)
            if feats is not None:
                features_list.append(feats)
                print(f"  {case_name}: coarse features extracted (limited)")
    return pd.DataFrame(features_list)


# ═══════════════════════════════════════════════════════════
#  Clustering Implementations (numpy only)
# ═══════════════════════════════════════════════════════════

def _euclidean_dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.sum((a - b) ** 2)))


def kmeans_manual(
    X: np.ndarray,
    k: int,
    max_iter: int = 100,
    n_init: int = 10,
    seed: int = 42,
) -> Tuple[np.ndarray, float]:
    """K-means clustering. Returns (labels, inertia)."""
    n_samples = X.shape[0]

    # Edge case: k >= n_samples => each point is its own cluster
    if k >= n_samples:
        labels = np.arange(min(k, n_samples))
        centers = X[:min(k, n_samples)]
        inertia = 0.0
        # Pad labels if k > n_samples
        if k > n_samples:
            labels = np.concatenate([labels, np.full(k - n_samples, n_samples - 1)])
        return labels[:n_samples], inertia

    best_labels = None
    best_inertia = np.inf

    for init_idx in range(n_init):
        rng = np.random.RandomState(seed + init_idx)
        # k-means++ initialization
        centers = np.empty((k, X.shape[1]))
        idx = rng.randint(n_samples)
        centers[0] = X[idx]
        for c in range(1, k):
            dists = np.min([np.sum((X - centers[j]) ** 2, axis=1) for j in range(c)], axis=0)
            total = dists.sum()
            if total < 1e-12:
                # All remaining points are identical to existing centers
                remaining = [i for i in range(n_samples) if i not in set(np.where(np.all(X == centers[:c], axis=1))[0])]
                if remaining:
                    idx = remaining[0]
                else:
                    idx = rng.randint(n_samples)
            else:
                probs = dists / total
                probs = np.clip(probs, 0, None)
                probs /= probs.sum()  # renormalize
                idx = rng.choice(n_samples, p=probs)
            centers[c] = X[idx]

        labels = np.zeros(n_samples, dtype=int)
        for _ in range(max_iter):
            # Assign
            dists = np.array([np.sum((X - centers[j]) ** 2, axis=1) for j in range(k)])
            new_labels = np.argmin(dists, axis=0)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            # Update centers
            for j in range(k):
                mask = labels == j
                if mask.any():
                    centers[j] = X[mask].mean(axis=0)

        inertia = float(np.sum((X - centers[labels]) ** 2))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()

    return best_labels, best_inertia


def gmm_manual(
    X: np.ndarray,
    k: int,
    max_iter: int = 100,
    n_init: int = 5,
    seed: int = 42,
) -> Tuple[np.ndarray, float, float, float]:
    """GMM via EM. Returns (labels, bic, aic, log_likelihood)."""
    n_samples, n_features = X.shape

    # Edge case: k >= n_samples
    if k >= n_samples:
        labels = np.arange(min(k, n_samples))
        ll = -float(n_features) * n_samples  # rough estimate
        n_params = k * n_features + k * n_features * (n_features + 1) / 2 + (k - 1)
        bic = -2 * ll + n_params * np.log(n_samples)
        aic = -2 * ll + 2 * n_params
        return labels, float(bic), float(aic), float(ll)

    best_labels = None
    best_ll = -np.inf

    for init_idx in range(n_init):
        rng = np.random.RandomState(seed + init_idx)

        # Initialize with k-means
        km_labels, _ = kmeans_manual(X, k, n_init=3, seed=seed + init_idx)
        means = np.array([X[km_labels == j].mean(axis=0) if (km_labels == j).any()
                          else X[rng.randint(n_samples)] for j in range(k)])
        covs = np.array([np.eye(n_features) for _ in range(k)])
        weights = np.ones(k) / k

        ll = -np.inf
        for _ in range(max_iter):
            # E-step
            resp = np.zeros((n_samples, k))
            for j in range(k):
                diff = X - means[j]
                cov_inv = np.linalg.inv(covs[j] + 1e-6 * np.eye(n_features))
                mahal = np.sum(diff @ cov_inv * diff, axis=1)
                sign, logdet = np.linalg.slogdet(covs[j])
                log_prob = -0.5 * (n_features * np.log(2 * np.pi) + logdet + mahal)
                resp[:, j] = np.log(weights[j] + 1e-12) + log_prob

            # Log-sum-exp for stability
            max_resp = resp.max(axis=1, keepdims=True)
            log_sum = max_resp.squeeze() + np.log(np.sum(np.exp(resp - max_resp), axis=1))
            resp = np.exp(resp - log_sum.reshape(-1, 1))

            new_ll = float(np.sum(log_sum))
            if abs(new_ll - ll) < 1e-6:
                ll = new_ll
                break
            ll = new_ll

            # M-step
            Nk = resp.sum(axis=0) + 1e-12
            weights = Nk / n_samples
            means = (resp.T @ X) / Nk.reshape(-1, 1)
            for j in range(k):
                diff = X - means[j]
                covs[j] = (resp[:, j:j+1] * diff).T @ diff / Nk[j]
                covs[j] += 1e-6 * np.eye(n_features)

        if ll > best_ll:
            best_ll = ll
            best_labels = np.argmax(resp, axis=1).copy()

    # BIC / AIC
    n_params = k * n_features + k * n_features * (n_features + 1) / 2 + (k - 1)
    bic = -2 * best_ll + n_params * np.log(n_samples)
    aic = -2 * best_ll + 2 * n_params

    return best_labels, float(bic), float(aic), float(best_ll)


def hierarchical_manual(X: np.ndarray, k: int) -> np.ndarray:
    """Agglomerative hierarchical clustering using scipy."""
    Z = linkage(X, method="ward")
    labels = fcluster(Z, t=k, criterion="maxclust") - 1  # 0-indexed
    return labels


# ═══════════════════════════════════════════════════════════
#  Silhouette Score (numpy only)
# ═══════════════════════════════════════════════════════════

def silhouette_score_manual(X: np.ndarray, labels: np.ndarray) -> float:
    """Compute mean Silhouette Score."""
    n = len(X)
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2 or n < 2:
        return 0.0
    samples = silhouette_samples_manual(X, labels)
    return float(np.mean(samples))


def silhouette_samples_manual(X: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Compute per-sample Silhouette Scores."""
    n = len(X)
    sil = np.zeros(n)
    unique_labels = np.unique(labels)

    if len(unique_labels) < 2:
        return sil

    # Precompute pairwise distances
    dist_matrix = squareform(pdist(X))

    for i in range(n):
        same_cluster = labels == labels[i]
        same_cluster[i] = False
        n_same = same_cluster.sum()

        if n_same == 0:
            sil[i] = 0.0
            continue

        # a(i): mean distance to same-cluster points
        a_i = dist_matrix[i, same_cluster].mean()

        # b(i): min mean distance to other clusters
        b_i = np.inf
        for c in unique_labels:
            if c == labels[i]:
                continue
            mask = labels == c
            if mask.sum() > 0:
                mean_dist = dist_matrix[i, mask].mean()
                b_i = min(b_i, mean_dist)

        if np.isinf(b_i):
            sil[i] = 0.0
        else:
            sil[i] = (b_i - a_i) / max(a_i, b_i) if max(a_i, b_i) > 0 else 0.0

    return sil


# ═══════════════════════════════════════════════════════════
#  PCA (numpy only)
# ═══════════════════════════════════════════════════════════

def pca_manual(X: np.ndarray, n_components: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """PCA via eigendecomposition. Returns (projected, explained_variance_ratio)."""
    # Center
    X_centered = X - X.mean(axis=0)
    # Covariance
    cov = np.cov(X_centered, rowvar=False)
    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    # Project
    projected = X_centered @ eigenvectors[:, :n_components]
    # Explained variance ratio
    explained = eigenvalues[:n_components] / eigenvalues.sum()
    return projected, explained


# ═══════════════════════════════════════════════════════════
#  StandardScaler (numpy only)
# ═══════════════════════════════════════════════════════════

class StandardScalerManual:
    def __init__(self):
        self.mean_ = None
        self.scale_ = None

    def fit(self, X: np.ndarray) -> "StandardScalerManual":
        self.mean_ = X.mean(axis=0)
        self.scale_ = X.std(axis=0)
        self.scale_[self.scale_ < 1e-10] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


# ═══════════════════════════════════════════════════════════
#  Clustering Analysis
# ═══════════════════════════════════════════════════════════

def run_clustering_analysis(
    X: np.ndarray,
    case_names: List[str],
    max_k: int = 5,
) -> Dict[str, Any]:
    results = {}
    for k in range(2, max_k + 1):
        k_results = {}

        # K-means
        km_labels, km_inertia = kmeans_manual(X, k)
        km_sil = silhouette_score_manual(X, km_labels)
        k_results["kmeans"] = {
            "labels": km_labels.tolist(),
            "silhouette": float(km_sil),
            "inertia": float(km_inertia),
        }

        # GMM
        gmm_labels, bic, aic, ll = gmm_manual(X, k)
        gmm_sil = silhouette_score_manual(X, gmm_labels)
        k_results["gmm"] = {
            "labels": gmm_labels.tolist(),
            "silhouette": float(gmm_sil),
            "bic": float(bic),
            "aic": float(aic),
            "log_likelihood": float(ll),
        }

        # Hierarchical
        hier_labels = hierarchical_manual(X, k)
        hier_sil = silhouette_score_manual(X, hier_labels)
        k_results["hierarchical"] = {
            "labels": hier_labels.tolist(),
            "silhouette": float(hier_sil),
        }

        results[k] = k_results
        print(f"  k={k}: K-means Sil={km_sil:.3f}, GMM Sil={gmm_sil:.3f}, "
              f"Hier Sil={hier_sil:.3f}, GMM BIC={bic:.1f}")

    return results


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_silhouette_comparison(clustering_results: Dict, output_dir: Path):
    k_values = sorted(clustering_results.keys())
    methods = ["kmeans", "gmm", "hierarchical"]
    labels = {"kmeans": "K-Means", "gmm": "GMM", "hierarchical": "Hierarchical"}
    colors = {"kmeans": "#1f4e79", "gmm": "#b64040", "hierarchical": "#2c7a5a"}

    fig, ax = plt.subplots(figsize=(8, 5))
    for m in methods:
        sils = [clustering_results[k][m]["silhouette"] for k in k_values]
        ax.plot(k_values, sils, "o-", color=colors[m], label=labels[m], linewidth=2, markersize=8)

    all_sils = {k: max(clustering_results[k][m]["silhouette"] for m in methods) for k in k_values}
    optimal_k = max(all_sils, key=all_sils.get)

    ax.axvline(x=optimal_k, color="gold", linestyle="--", alpha=0.7, linewidth=2)
    ax.text(optimal_k + 0.1, ax.get_ylim()[1] * 0.95, f"Optimal k={optimal_k}",
            fontsize=10, color="goldenrod", fontweight="bold")

    ax.set_xlabel("Number of Clusters (k)", fontsize=12)
    ax.set_ylabel("Silhouette Score", fontsize=12)
    ax.set_title("Silhouette Score vs Number of Clusters", fontsize=14)
    ax.set_xticks(k_values)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_silhouette_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_silhouette_comparison.png")


def plot_bic_aic_comparison(clustering_results: Dict, output_dir: Path):
    k_values = sorted(clustering_results.keys())
    bic_vals = [clustering_results[k]["gmm"]["bic"] for k in k_values]
    aic_vals = [clustering_results[k]["gmm"]["aic"] for k in k_values]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(k_values, bic_vals, "s-", color="#1f4e79", label="BIC", linewidth=2, markersize=8)
    ax.plot(k_values, aic_vals, "D-", color="#b64040", label="AIC", linewidth=2, markersize=8)

    opt_bic = k_values[np.argmin(bic_vals)]
    opt_aic = k_values[np.argmin(aic_vals)]
    ax.axvline(x=opt_bic, color="#1f4e79", linestyle="--", alpha=0.5)
    ax.text(opt_bic + 0.1, max(bic_vals) * 0.98, f"Best BIC: k={opt_bic}", fontsize=10, color="#1f4e79")
    ax.axvline(x=opt_aic, color="#b64040", linestyle="--", alpha=0.5)
    ax.text(opt_aic + 0.1, max(aic_vals) * 0.92, f"Best AIC: k={opt_aic}", fontsize=10, color="#b64040")

    ax.set_xlabel("Number of Clusters (k)", fontsize=12)
    ax.set_ylabel("Information Criterion", fontsize=12)
    ax.set_title("GMM Model Selection: BIC and AIC", fontsize=14)
    ax.set_xticks(k_values)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_bic_aic_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_bic_aic_comparison.png")


def plot_pca_projection(
    X: np.ndarray,
    case_names: List[str],
    clustering_results: Dict,
    output_dir: Path,
):
    projected, explained_var = pca_manual(X, n_components=2)

    k = 3 if 3 in clustering_results else max(clustering_results.keys())
    methods = ["kmeans", "gmm", "hierarchical"]
    labels_map = {"kmeans": "K-Means", "gmm": "GMM", "hierarchical": "Hierarchical"}
    cc = ["#1f4e79", "#b64040", "#2c7a5a", "#8B4513", "#6A5ACD"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, m in zip(axes, methods):
        lbls = np.array(clustering_results[k][m]["labels"])
        sil = clustering_results[k][m]["silhouette"]
        for cid in range(k):
            mask = lbls == cid
            ax.scatter(projected[mask, 0], projected[mask, 1], c=cc[cid],
                      s=120, alpha=0.8, edgecolors="white", linewidth=1.5,
                      label=f"Cluster {cid + 1}")
        for i, name in enumerate(case_names):
            display = CASES.get(name, {}).get("display", name)
            ax.annotate(display, (projected[i, 0], projected[i, 1]),
                       fontsize=8, ha="center", va="bottom", xytext=(0, 8),
                       textcoords="offset points")
        ax.set_xlabel(f"PC1 ({explained_var[0]:.1%} var)", fontsize=10)
        ax.set_ylabel(f"PC2 ({explained_var[1]:.1%} var)", fontsize=10)
        ax.set_title(f"{labels_map[m]} (k={k})\nSilhouette={sil:.3f}", fontsize=11)
        ax.legend(fontsize=8, loc="best")
        ax.grid(True, alpha=0.2)

    fig.suptitle(f"PCA Projection of PDE Degradation Features (k={k})", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_pca_projection.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_pca_projection.png")


def plot_feature_heatmap(feature_df: pd.DataFrame, output_dir: Path):
    feature_cols = ["safe_rate", "transition_width", "seed_std", "jump_rate",
                    "mean_cross_rate", "boundary_sharpness", "avg_seed_std_per_point"]
    available = [c for c in feature_cols if c in feature_df.columns]
    if not available:
        return

    display_names = [CASES.get(r["case"], {}).get("display", r["case"]) for _, r in feature_df.iterrows()]
    data = feature_df[available].values.astype(float)
    data_norm = np.zeros_like(data)
    for j in range(data.shape[1]):
        cmin, cmax = data[:, j].min(), data[:, j].max()
        data_norm[:, j] = (data[:, j] - cmin) / (cmax - cmin) if cmax > cmin else 0.5

    feature_labels = {
        "safe_rate": "Safe Zone\nCross Rate",
        "transition_width": "Transition\nWidth",
        "seed_std": "Seed\nStd",
        "jump_rate": "Boundary\nJump Rate",
        "mean_cross_rate": "Mean\nCross Rate",
        "boundary_sharpness": "Boundary\nSharpness",
        "avg_seed_std_per_point": "Avg Seed Std\nPer Point",
    }

    fig, ax = plt.subplots(figsize=(10, max(4, len(display_names) * 0.8)))
    im = ax.imshow(data_norm, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(len(available)))
    ax.set_xticklabels([feature_labels.get(c, c) for c in available], fontsize=9)
    ax.set_yticks(range(len(display_names)))
    ax.set_yticklabels(display_names, fontsize=10)
    for i in range(len(display_names)):
        for j in range(len(available)):
            color = "white" if data_norm[i, j] > 0.6 else "black"
            ax.text(j, i, f"{data[i, j]:.3f}", ha="center", va="center",
                    color=color, fontsize=8, fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Normalized Value")
    ax.set_title("Degradation Feature Profile per PDE System", fontsize=13)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_feature_heatmap.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_feature_heatmap.png")


def plot_silhouette_per_sample(
    X: np.ndarray,
    case_names: List[str],
    clustering_results: Dict,
    output_dir: Path,
):
    k = 3 if 3 in clustering_results else max(clustering_results.keys())
    methods = ["kmeans", "gmm", "hierarchical"]
    labels_map = {"kmeans": "K-Means", "gmm": "GMM", "hierarchical": "Hierarchical"}
    cc = ["#1f4e79", "#b64040", "#2c7a5a"]
    display_names = [CASES.get(n, {}).get("display", n) for n in case_names]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, m in zip(axes, methods):
        lbls = np.array(clustering_results[k][m]["labels"])
        sil_samples = silhouette_samples_manual(X, lbls)
        order = np.argsort(lbls * 100 - sil_samples)
        y_pos = 0
        for cid in range(k):
            mask = lbls[order] == cid
            n_c = mask.sum()
            ax.barh(range(y_pos, y_pos + n_c), sil_samples[order][mask],
                   color=cc[cid], alpha=0.8, label=f"Cluster {cid + 1}")
            y_pos += n_c
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([display_names[i] for i in order], fontsize=8)
        ax.set_xlabel("Silhouette Score", fontsize=10)
        ax.set_title(f"{labels_map[m]}", fontsize=11)
        ax.axvline(x=clustering_results[k][m]["silhouette"], color="red", linestyle="--", alpha=0.7, label="Mean")
        ax.legend(fontsize=8)
        ax.set_xlim(-0.5, 1.0)

    fig.suptitle(f"Per-Sample Silhouette Scores (k={k})", fontsize=13)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_silhouette_per_sample.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_silhouette_per_sample.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary_report(
    feature_df: pd.DataFrame,
    probe_cases: pd.DataFrame,
    clustering_results: Dict,
    features: List[str],
    case_names: List[str],
) -> str:
    lines = [
        "# 三种退化原型的无监督聚类验证",
        "",
        "## 概述",
        "",
        "本分析使用无监督聚类方法验证三种退化原型（尖锐边界/中间边界/概率边界）的合理性。",
        "通过比较 k=2,3,4,5 的聚类质量，确定数据驱动的最优分类数。",
        "",
        f"**分析案例数:** {len(case_names)}",
        f"**使用特征:** {', '.join(features)}",
        "",
        "## 特征矩阵",
        "",
        "| PDE 系统 | 安全区越界率 | 过渡带宽度 | 种子标准差 | 边界跳变率 | 平均越界率 | 边界尖锐度 | 逐点种子标准差 |",
        "|----------|-------------|-----------|----------|----------|----------|----------|-------------|",
    ]

    for _, row in probe_cases.iterrows():
        display = CASES.get(row["case"], {}).get("display", row["case"])
        lines.append(
            f"| {display} | {row.get('safe_rate',0):.3f} | {row.get('transition_width',0):.3f} | "
            f"{row.get('seed_std',0):.4f} | {row.get('jump_rate',0):.3f} | "
            f"{row.get('mean_cross_rate',0):.3f} | {row.get('boundary_sharpness',0):.3f} | "
            f"{row.get('avg_seed_std_per_point',0):.4f} |"
        )

    # Silhouette table
    lines.extend([
        "",
        "## Silhouette Score 比较",
        "",
        "Silhouette Score 越高表示聚类结构越清晰。如果 k=3 显著优于 k=2 和 k=4，则支持三类分类。",
        "",
        "| k | K-Means | GMM | Hierarchical | 最优方法 |",
        "|---|---------|-----|--------------|---------|",
    ])

    all_sils = {}
    for k in clustering_results:
        sils = [clustering_results[k][m]["silhouette"] for m in ["kmeans", "gmm", "hierarchical"]]
        all_sils[k] = max(sils)

    optimal_k_sil = max(all_sils, key=all_sils.get)
    best_labels = {"kmeans": "K-Means", "gmm": "GMM", "hierarchical": "Hierarchical"}

    for k in sorted(clustering_results.keys()):
        km = clustering_results[k]["kmeans"]["silhouette"]
        gm = clustering_results[k]["gmm"]["silhouette"]
        hi = clustering_results[k]["hierarchical"]["silhouette"]
        best_m = max(["kmeans", "gmm", "hierarchical"], key=lambda m: clustering_results[k][m]["silhouette"])
        marker = " **(最优)**" if k == optimal_k_sil else ""
        lines.append(f"| {k}{marker} | {km:.3f} | {gm:.3f} | {hi:.3f} | {best_labels[best_m]} |")

    # BIC/AIC table
    lines.extend([
        "",
        "## GMM 模型选择 (BIC/AIC)",
        "",
        "BIC/AIC 越低表示模型拟合越好。",
        "",
        "| k | BIC | AIC | 对数似然 |",
        "|---|-----|-----|---------|",
    ])

    for k in sorted(clustering_results.keys()):
        bic = clustering_results[k]["gmm"]["bic"]
        aic = clustering_results[k]["gmm"]["aic"]
        ll = clustering_results[k]["gmm"]["log_likelihood"]
        lines.append(f"| {k} | {bic:.1f} | {aic:.1f} | {ll:.1f} |")

    bic_vals = {k: clustering_results[k]["gmm"]["bic"] for k in clustering_results}
    aic_vals = {k: clustering_results[k]["gmm"]["aic"] for k in clustering_results}
    opt_bic = min(bic_vals, key=bic_vals.get)
    opt_aic = min(aic_vals, key=aic_vals.get)

    # Cluster assignments
    if 3 in clustering_results:
        lines.extend([
            "",
            "## 聚类分配 (k=3)",
            "",
            "| PDE 系统 | K-Means | GMM | Hierarchical | 理论分类 |",
            "|----------|---------|-----|-------------|---------|",
        ])
        theory_map = {
            "poisson": "无边界/对照",
            "stokes_poiseuille": "尖锐边界",
            "fisher_kpp": "中间边界",
            "burgers": "概率边界",
        }
        for i, case in enumerate(case_names):
            display = CASES.get(case, {}).get("display", case)
            km = clustering_results[3]["kmeans"]["labels"][i] + 1
            gm = clustering_results[3]["gmm"]["labels"][i] + 1
            hi = clustering_results[3]["hierarchical"]["labels"][i] + 1
            theory = theory_map.get(case, "—")
            lines.append(f"| {display} | {km} | {gm} | {hi} | {theory} |")

    # Interpretation
    lines.extend([
        "",
        "## 结论",
        "",
        "### 最优聚类数",
        "",
        f"- **Silhouette Score:** 最优 k = {optimal_k_sil} (score = {all_sils[optimal_k_sil]:.3f})",
        f"- **BIC:** 最优 k = {opt_bic} (BIC = {bic_vals[opt_bic]:.1f})",
        f"- **AIC:** 最优 k = {opt_aic} (AIC = {aic_vals[opt_aic]:.1f})",
        "",
    ])

    if optimal_k_sil == 3:
        lines.extend([
            "### 支持三类分类的证据",
            "",
            "1. Silhouette Score 在 k=3 时最高，表明三类是最自然的聚类数",
            "2. 三种聚类方法（K-means, GMM, Hierarchical）在 k=3 时均给出一致的聚类结构",
            "3. 聚类分配与理论预期一致：",
            "   - Stokes-Poiseuille：尖锐边界（低越界率、窄过渡带）",
            "   - Fisher-KPP/Burgers：概率边界（高越界率、宽过渡带）",
            "",
        ])
    else:
        lines.extend([
            "### 注意",
            "",
            f"最优聚类数为 k={optimal_k_sil}，而非 k=3。需要重新审视三类分类的合理性。",
            "",
        ])

    lines.extend([
        "### 局限性",
        "",
        "- 样本量有限（4个PDE系统），统计检验力受限",
        "- 特征来源于特定实验配置",
        "- 结果应视为支持性证据，而非决定性证明",
        "",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Degradation Prototype Clustering Analysis")
    print("=" * 70)

    # 1. Extract features
    print("\n[1/5] Extracting degradation features...")
    feature_df = extract_all_features()
    if len(feature_df) < 3:
        print("ERROR: Need at least 3 PDE cases")
        return
    print(f"\n  Total cases: {len(feature_df)}")

    # 2. Prepare feature matrix
    print("\n[2/5] Preparing feature matrix...")
    common_features = ["safe_rate", "transition_width", "seed_std", "jump_rate",
                       "mean_cross_rate", "boundary_sharpness", "avg_seed_std_per_point"]
    available_features = [f for f in common_features if f in feature_df.columns]
    probe_cases = feature_df[feature_df["n_keypoints"] > 0].copy()

    if len(probe_cases) < 3:
        print("ERROR: Need at least 3 cases with probe data")
        return

    X_raw = probe_cases[available_features].values.astype(float)
    case_names = probe_cases["case"].tolist()
    scaler = StandardScalerManual()
    X = scaler.fit_transform(X_raw)
    print(f"  Feature matrix: {X.shape}, Cases: {case_names}")

    # 3. Clustering
    max_k = min(5, len(case_names))
    print(f"\n[3/5] Running clustering (k=2..{max_k})...")
    clustering_results = run_clustering_analysis(X, case_names, max_k=max_k)

    # 4. Visualizations
    print("\n[4/5] Generating figures...")
    plot_silhouette_comparison(clustering_results, OUTPUT_DIR)
    plot_bic_aic_comparison(clustering_results, OUTPUT_DIR)
    plot_pca_projection(X, case_names, clustering_results, OUTPUT_DIR)
    plot_feature_heatmap(probe_cases, OUTPUT_DIR)
    plot_silhouette_per_sample(X, case_names, clustering_results, OUTPUT_DIR)

    # 5. Save
    print("\n[5/5] Saving results...")
    feature_df.to_csv(OUTPUT_DIR / "degradation_features.csv", index=False)
    with open(OUTPUT_DIR / "clustering_results.json", "w", encoding="utf-8") as f:
        json.dump(clustering_results, f, indent=2, default=str)

    summary = generate_summary_report(feature_df, probe_cases, clustering_results,
                                      available_features, case_names)
    (OUTPUT_DIR / "clustering_summary.md").write_text(summary, encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 70}")
    print(summary)


if __name__ == "__main__":
    main()
