"""
Complexity Score, PCA Projection, and 2-Variable Clustering
============================================================
Task A: Complexity Score = z(d_null) + z(hessian_entropy)
Task B: PC1-PC2 projection of 10 PDEs
Task C: Clustering with Complexity Score + lambda_max
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats as sp_stats
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import pdist

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "complexity_score_v1"


# ═══════════════════════════════════════════════════════════
#  Data
# ═══════════════════════════════════════════════════════════

CASES = {
    "poisson": {"display": "Poisson", "display_zh": "Poisson方程", "prototype": "Non-Degrading"},
    "stokes_poiseuille": {"display": "Stokes-Poiseuille", "display_zh": "斯托克斯-泊肃叶流", "prototype": "Sharp Boundary"},
    "allen_cahn": {"display": "Allen-Cahn", "display_zh": "Allen-Cahn方程", "prototype": "Broad Band"},
    "fisher_kpp": {"display": "Fisher-KPP", "display_zh": "Fisher-KPP方程", "prototype": "Intermediate"},
    "burgers": {"display": "Burgers", "display_zh": "Burgers方程", "prototype": "Broad Band"},
    "heat_equation": {"display": "Heat Equation", "display_zh": "热方程", "prototype": "Broad Band"},
    "kdv_soliton": {"display": "KdV Soliton", "display_zh": "KdV孤子", "prototype": "Broad Band"},
    "nls_soliton": {"display": "NLS Soliton", "display_zh": "NLS孤子", "prototype": "Broad Band"},
    "wave_equation": {"display": "Wave Equation", "display_zh": "波动方程", "prototype": "Broad Band"},
    "kdv_double_soliton": {"display": "KdV Double", "display_zh": "KdV双孤子", "prototype": "Broad Band"},
}


def load_metrics() -> Dict[str, Dict[str, float]]:
    """Load all metrics for all 10 PDE cases."""
    
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
    
    basin_count = {
        "poisson": 4, "stokes_poiseuille": 2, "allen_cahn": 2,
        "fisher_kpp": 3, "burgers": 2, "heat_equation": 2,
        "kdv_soliton": 2, "nls_soliton": 2, "wave_equation": 2,
        "kdv_double_soliton": 2,
    }
    
    info_cv = {
        "poisson": 0.3035, "stokes_poiseuille": 0.1938, "allen_cahn": 1.1782,
        "fisher_kpp": 0.8504, "burgers": 0.4512, "heat_equation": 0.4506,
        "kdv_soliton": 1.6765, "nls_soliton": 1.6215, "wave_equation": 0.3033,
        "kdv_double_soliton": 2.0035,
    }
    
    # Boundary width from probe data
    boundary_width = {
        "poisson": 1.33, "stokes_poiseuille": 3.67, "allen_cahn": 2.37,
        "fisher_kpp": 5.13, "burgers": 4.77, "heat_equation": 3.03,
        "kdv_soliton": 5.50, "nls_soliton": 6.80, "wave_equation": 7.60,
        "kdv_double_soliton": 8.00,
    }
    
    data = {}
    for case in d_null.keys():
        data[case] = {
            "display": CASES[case]["display"],
            "prototype": CASES[case]["prototype"],
            "d_null": d_null[case],
            "lambda_max": lambda_max[case],
            "hessian_entropy": hessian_entropy[case],
            "basin_count": basin_count[case],
            "info_cv": info_cv[case],
            "boundary_width": boundary_width.get(case, None),
        }
    
    return data


# ═══════════════════════════════════════════════════════════
#  Task A: Complexity Score
# ═══════════════════════════════════════════════════════════

def task_a_complexity_score(data: Dict[str, Dict]) -> Dict[str, Any]:
    """Task A: Compute Complexity Score = z(d_null) + z(hessian_entropy)"""
    
    print("\n" + "=" * 60)
    print("TASK A: Complexity Score")
    print("=" * 60)
    
    cases = list(data.keys())
    
    # Extract d_null and hessian_entropy
    d_null_values = np.array([data[c]["d_null"] for c in cases])
    entropy_values = np.array([data[c]["hessian_entropy"] for c in cases])
    
    # Standardize (z-score)
    z_d_null = (d_null_values - d_null_values.mean()) / d_null_values.std()
    z_entropy = (entropy_values - entropy_values.mean()) / entropy_values.std()
    
    # Note: entropy is negative indicator (lower entropy = more complex)
    # So we use -z_entropy
    complexity_score = z_d_null + (-z_entropy)
    
    # Add to data
    for i, case in enumerate(cases):
        data[case]["z_d_null"] = float(z_d_null[i])
        data[case]["z_entropy"] = float(z_entropy[i])
        data[case]["complexity_score"] = float(complexity_score[i])
    
    # Sort by complexity score
    sorted_cases = sorted(cases, key=lambda c: data[c]["complexity_score"])
    
    print("\n  Complexity Score Ranking:")
    print(f"  {'Rank':<5} {'PDE':<20} {'d_null':>8} {'z(d_null)':>10} {'entropy':>10} {'z(-entropy)':>12} {'Score':>8} {'Prototype':<20}")
    print(f"  {'-' * 95}")
    
    for rank, case in enumerate(sorted_cases, 1):
        d = data[case]
        print(f"  {rank:<5} {d['display']:<20} {d['d_null']:>8} {d['z_d_null']:>10.3f} "
              f"{d['hessian_entropy']:>10.4f} {-d['z_entropy']:>12.3f} "
              f"{d['complexity_score']:>8.3f} {d['prototype']:<20}")
    
    # Compute correlation with boundary_width
    cases_with_bw = [c for c in cases if data[c]["boundary_width"] is not None]
    if len(cases_with_bw) >= 3:
        scores = [data[c]["complexity_score"] for c in cases_with_bw]
        bw = [data[c]["boundary_width"] for c in cases_with_bw]
        corr, p = sp_stats.spearmanr(scores, bw)
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        print(f"\n  Complexity Score vs boundary_width: r={corr:.3f}, p={p:.3f} {sig}")
    
    return {
        "ranking": [(rank, case, data[case]["complexity_score"]) for rank, case in enumerate(sorted_cases, 1)],
        "complexity_scores": {case: data[case]["complexity_score"] for case in cases},
    }


# ═══════════════════════════════════════════════════════════
#  Task B: PCA Projection
# ═══════════════════════════════════════════════════════════

def task_b_pca_projection(data: Dict[str, Dict]) -> Dict[str, Any]:
    """Task B: Project 10 PDEs onto PC1-PC2 space."""
    
    print("\n" + "=" * 60)
    print("TASK B: PCA Projection")
    print("=" * 60)
    
    cases = list(data.keys())
    metrics = ["d_null", "lambda_max", "hessian_entropy", "basin_count", "info_cv"]
    
    # Build data matrix
    X = np.array([[data[c][m] for m in metrics] for c in cases])
    
    # Standardize
    X_std = (X - X.mean(axis=0)) / X.std(axis=0)
    
    # PCA
    cov = np.cov(X_std.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    
    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Project
    projected = X_std @ eigenvectors[:, :2]
    explained_ratio = eigenvalues[:2] / eigenvalues.sum()
    
    print(f"\n  PC1 explains {explained_ratio[0]:.1%} variance")
    print(f"  PC2 explains {explained_ratio[1]:.1%} variance")
    print(f"  Total: {sum(explained_ratio):.1%}")
    
    # Loading matrix
    print("\n  Loading Matrix:")
    for i, m in enumerate(metrics):
        print(f"    {m}: PC1={eigenvectors[i, 0]:.3f}, PC2={eigenvectors[i, 1]:.3f}")
    
    # Add to data
    for i, case in enumerate(cases):
        data[case]["PC1"] = float(projected[i, 0])
        data[case]["PC2"] = float(projected[i, 1])
    
    return {
        "eigenvalues": eigenvalues.tolist(),
        "explained_ratio": explained_ratio.tolist(),
        "eigenvectors": eigenvectors.tolist(),
        "projected": projected.tolist(),
        "cases": cases,
    }


# ═══════════════════════════════════════════════════════════
#  Task C: 2-Variable Clustering
# ═══════════════════════════════════════════════════════════

def task_c_clustering(data: Dict[str, Dict]) -> Dict[str, Any]:
    """Task C: Cluster using Complexity Score + lambda_max."""
    
    print("\n" + "=" * 60)
    print("TASK C: Clustering with Complexity Score + lambda_max")
    print("=" * 60)
    
    cases = list(data.keys())
    
    # Build feature matrix
    X = np.array([[data[c]["complexity_score"], data[c]["lambda_max"]] for c in cases])
    
    # Standardize
    X_std = (X - X.mean(axis=0)) / X.std(axis=0)
    
    # Hierarchical clustering
    Z = linkage(X_std, method="ward")
    
    # Try k=2,3,4
    results = {}
    for k in range(2, 5):
        labels = fcluster(Z, t=k, criterion="maxclust") - 1
        
        # Compute silhouette-like score
        dist_matrix = np.zeros((len(X_std), len(X_std)))
        for i in range(len(X_std)):
            for j in range(len(X_std)):
                dist_matrix[i, j] = np.sqrt(np.sum((X_std[i] - X_std[j]) ** 2))
        
        sil_scores = []
        for i in range(len(X_std)):
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
        
        results[k] = {
            "labels": labels.tolist(),
            "silhouette": float(mean_sil),
        }
        
        print(f"\n  k={k}: Silhouette={mean_sil:.3f}")
        for cluster_id in range(k):
            cluster_cases = [cases[i] for i in range(len(cases)) if labels[i] == cluster_id]
            cluster_displays = [data[c]["display"] for c in cluster_cases]
            cluster_prototypes = [data[c]["prototype"] for c in cluster_cases]
            print(f"    Cluster {cluster_id}: {', '.join(cluster_displays)}")
            print(f"      Prototypes: {', '.join(set(cluster_prototypes))}")
    
    return results


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_all(
    data: Dict[str, Dict],
    task_a_results: Dict,
    task_b_results: Dict,
    task_c_results: Dict,
    output_dir: Path,
):
    """Generate all figures."""
    
    cases = list(data.keys())
    displays = [data[c]["display"] for c in cases]
    prototypes = [data[c]["prototype"] for c in cases]
    
    prototype_colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    colors = [prototype_colors.get(p, "#666") for p in prototypes]
    
    # Figure 1: Complexity Score ranking
    fig, ax = plt.subplots(figsize=(12, 6))
    
    sorted_cases = sorted(cases, key=lambda c: data[c]["complexity_score"])
    sorted_scores = [data[c]["complexity_score"] for c in sorted_cases]
    sorted_displays = [data[c]["display"] for c in sorted_cases]
    sorted_colors = [prototype_colors.get(data[c]["prototype"], "#666") for c in sorted_cases]
    
    bars = ax.barh(range(len(sorted_cases)), sorted_scores, color=sorted_colors, alpha=0.8)
    ax.set_yticks(range(len(sorted_cases)))
    ax.set_yticklabels(sorted_displays, fontsize=10)
    ax.set_xlabel("Complexity Score = z(d_null) + z(-entropy)", fontsize=12)
    ax.set_title("Task A: Complexity Score Ranking", fontsize=14)
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="x")
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=p) for p, c in prototype_colors.items()]
    ax.legend(handles=legend_elements, fontsize=9, loc="lower right")
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig1_complexity_score_ranking.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig1_complexity_score_ranking.png")
    
    # Figure 2: PC1-PC2 projection
    fig, ax = plt.subplots(figsize=(10, 8))
    
    for i, case in enumerate(cases):
        ax.scatter(data[case]["PC1"], data[case]["PC2"],
                  c=colors[i], s=150, alpha=0.8,
                  edgecolors="white", linewidth=1.5, zorder=5)
        ax.annotate(data[case]["display"], (data[case]["PC1"], data[case]["PC2"]),
                   fontsize=9, ha="center", va="bottom",
                   xytext=(0, 8), textcoords="offset points")
    
    ax.set_xlabel(f"PC1 ({task_b_results['explained_ratio'][0]:.1%} var)", fontsize=12)
    ax.set_ylabel(f"PC2 ({task_b_results['explained_ratio'][1]:.1%} var)", fontsize=12)
    ax.set_title("Task B: PC1-PC2 Projection of 10 PDE Systems", fontsize=14)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
    ax.axvline(x=0, color="gray", linestyle="--", alpha=0.3)
    ax.grid(True, alpha=0.3)
    
    legend_elements = [Patch(facecolor=c, label=p) for p, c in prototype_colors.items()]
    ax.legend(handles=legend_elements, fontsize=10)
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig2_pca_projection.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig2_pca_projection.png")
    
    # Figure 3: Clustering results
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, k in enumerate([2, 3, 4]):
        ax = axes[idx]
        labels = task_c_results[k]["labels"]
        sil = task_c_results[k]["silhouette"]
        
        cluster_colors = ["#1f4e79", "#b64040", "#2c7a5a", "#8B4513"]
        
        for i, case in enumerate(cases):
            ax.scatter(data[case]["complexity_score"], data[case]["lambda_max"],
                      c=cluster_colors[labels[i]], s=120, alpha=0.8,
                      edgecolors="white", linewidth=1.5, zorder=5)
            ax.annotate(data[case]["display"], (data[case]["complexity_score"], data[case]["lambda_max"]),
                       fontsize=8, ha="center", va="bottom",
                       xytext=(0, 5), textcoords="offset points")
        
        ax.set_xlabel("Complexity Score", fontsize=11)
        ax.set_ylabel("lambda_max", fontsize=11)
        ax.set_title(f"k={k} (Silhouette={sil:.3f})", fontsize=12)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle("Task C: Clustering with Complexity Score + lambda_max", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig3_clustering.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig3_clustering.png")
    
    # Figure 4: Dendrogram
    fig, ax = plt.subplots(figsize=(12, 6))
    
    X = np.array([[data[c]["complexity_score"], data[c]["lambda_max"]] for c in cases])
    X_std = (X - X.mean(axis=0)) / X.std(axis=0)
    Z = linkage(X_std, method="ward")
    
    dendrogram(Z, labels=displays, ax=ax, leaf_rotation=45, leaf_font_size=10)
    ax.set_title("Hierarchical Clustering Dendrogram", fontsize=14)
    ax.set_ylabel("Distance", fontsize=12)
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig4_dendrogram.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig4_dendrogram.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    data: Dict[str, Dict],
    task_a_results: Dict,
    task_b_results: Dict,
    task_c_results: Dict,
) -> str:
    """Generate summary report."""
    
    lines = [
        "# Complexity Score、PCA投影与聚类分析",
        "",
        "## Task A: Complexity Score",
        "",
        "### 定义",
        "",
        "```",
        "Complexity Score = z(d_null) + z(-hessian_entropy)",
        "```",
        "",
        "其中 z() 是标准化函数，-hessian_entropy 表示熵越低越复杂。",
        "",
        "### 排名",
        "",
        "| Rank | PDE | d_null | z(d_null) | entropy | z(-entropy) | Score | 原型 |",
        "|------|-----|--------|-----------|---------|-------------|-------|------|",
    ]
    
    for rank, case, score in task_a_results["ranking"]:
        d = data[case]
        lines.append(
            f"| {rank} | {d['display']} | {d['d_null']} | {d['z_d_null']:.3f} | "
            f"{d['hessian_entropy']:.4f} | {-d['z_entropy']:.3f} | "
            f"{d['complexity_score']:.3f} | {d['prototype']} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Task B: PCA投影",
        "",
        "### 方差解释率",
        "",
        "| PC | 解释率 | 累积 |",
        "|----|--------|------|",
    ])
    
    for i, ratio in enumerate(task_b_results["explained_ratio"]):
        cum = sum(task_b_results["explained_ratio"][:i+1])
        lines.append(f"| PC{i+1} | {ratio:.1%} | {cum:.1%} |")
    
    lines.extend([
        "",
        "### Loading Matrix",
        "",
        "| Factor | PC1 | PC2 |",
        "|--------|-----|-----|",
    ])
    
    metrics = ["d_null", "lambda_max", "hessian_entropy", "basin_count", "info_cv"]
    for i, m in enumerate(metrics):
        lines.append(f"| {m} | {task_b_results['eigenvectors'][i][0]:.3f} | {task_b_results['eigenvectors'][i][1]:.3f} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Task C: 聚类结果",
        "",
        "| k | Silhouette | Cluster 0 | Cluster 1 | Cluster 2 | Cluster 3 |",
        "|---|------------|-----------|-----------|-----------|-----------|",
    ])
    
    for k in [2, 3, 4]:
        labels = task_c_results[k]["labels"]
        sil = task_c_results[k]["silhouette"]
        
        clusters = {}
        for i, case in enumerate(data.keys()):
            cid = labels[i]
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append(data[case]["display"])
        
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
        "### Task A 结论",
        "",
        "Complexity Score 是否能区分不同退化原型？",
        "",
        "### Task B 结论",
        "",
        "PC1-PC2空间中，三种原型是否自然分离？",
        "",
        "### Task C 结论",
        "",
        "仅用Complexity Score + lambda_max，三类退化是否仍能出现？",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Complexity Score, PCA Projection, and Clustering")
    print("=" * 60)
    
    # Load data
    print("\n[0/3] Loading data...")
    data = load_metrics()
    print(f"  Loaded {len(data)} cases")
    
    # Task A
    task_a_results = task_a_complexity_score(data)
    
    # Task B
    task_b_results = task_b_pca_projection(data)
    
    # Task C
    task_c_results = task_c_clustering(data)
    
    # Generate figures
    print("\n[FIG] Generating figures...")
    plot_all(data, task_a_results, task_b_results, task_c_results, OUTPUT_DIR)
    
    # Save results
    print("\n[SAVE] Saving results...")
    
    all_results = {
        "task_a": task_a_results,
        "task_b": task_b_results,
        "task_c": {k: {"labels": v["labels"], "silhouette": v["silhouette"]} for k, v in task_c_results.items()},
        "data": {c: {k: v for k, v in d.items() if k != "display" and k != "prototype"} for c, d in data.items()},
    }
    
    with open(OUTPUT_DIR / "complexity_score_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Saved: complexity_score_results.json")
    
    summary = generate_summary(data, task_a_results, task_b_results, task_c_results)
    (OUTPUT_DIR / "complexity_score_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: complexity_score_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
