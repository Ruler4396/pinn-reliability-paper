"""
Comprehensive Degradation Mechanism Analysis
=============================================
5-phase analysis to validate degradation prototypes and four-factor theory.

Phase 1: Prototype-metric consistency check
Phase 2: Probability band area and failure entropy
Phase 3: Factor-behavior correlation matrix
Phase 4: VIF and PCA collinearity analysis
Phase 5: Model A/B/C comparison
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

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
PROBABILITY_DIR = RESULTS_DIR / "probability_matrices"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "comprehensive_mechanism_v1"

# All 10 PDE cases with prototype labels
CASES = {
    "poisson": {
        "display": "Poisson",
        "prototype": "Non-Degrading",
        "probe": "keypoints_v2_poisson",
        "threshold": 0.11297,
    },
    "stokes_poiseuille": {
        "display": "Stokes-Poiseuille",
        "prototype": "Sharp Boundary",
        "probe": "keypoints_v2_stokes",
        "threshold": 0.015379,
    },
    "allen_cahn": {
        "display": "Allen-Cahn",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_allen_cahn",
        "threshold": 0.05,
    },
    "fisher_kpp": {
        "display": "Fisher-KPP",
        "prototype": "Intermediate",
        "probe": "keypoints_v2_fisher_kpp",
        "threshold": 0.018861,
    },
    "burgers": {
        "display": "Burgers",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_burgers",
        "threshold": 0.026688,
    },
    "heat_equation": {
        "display": "Heat Equation",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_heat_equation",
        "threshold": 0.05,
    },
    "kdv_soliton": {
        "display": "KdV Soliton",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_kdv_soliton",
        "threshold": 0.05,
    },
    "nls_soliton": {
        "display": "NLS Soliton",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_nls_soliton",
        "threshold": 0.05,
    },
    "wave_equation": {
        "display": "Wave Equation",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_wave_equation",
        "threshold": 0.05,
    },
    "kdv_double_soliton": {
        "display": "KdV Double",
        "prototype": "Broad Band",
        "probe": "keypoints_v2_kdv_double_soliton",
        "threshold": 0.05,
    },
}


# ═══════════════════════════════════════════════════════════
#  Data Loading
# ═══════════════════════════════════════════════════════════

def load_probe_data(case_name: str) -> Optional[pd.DataFrame]:
    """Load probe runs data."""
    info = CASES.get(case_name)
    if info is None:
        return None
    csv_path = PROBES_DIR / info["probe"] / "probe_runs.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    for col in ["rel_l2", "num_observation", "noise_std", "seed", "crosses_threshold"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ═══════════════════════════════════════════════════════════
#  Phase 1: Prototype-Metric Consistency
# ═══════════════════════════════════════════════════════════

def compute_degradation_metrics_all() -> Dict[str, Dict[str, float]]:
    """Compute all degradation metrics for all cases."""
    
    results = {}
    
    for case_name, info in CASES.items():
        df = load_probe_data(case_name)
        if df is None:
            continue
        
        threshold = info["threshold"]
        
        # Boundary width: mean number of failure keypoints per seed
        boundary_widths = []
        for seed in df["seed"].unique():
            seed_data = df[df["seed"] == seed]
            n_fail = (seed_data["rel_l2"] > threshold).sum()
            boundary_widths.append(n_fail)
        
        # Crossing rates per keypoint
        cross_rates = []
        for label in df["label"].unique():
            label_data = df[df["label"] == label]
            rate = (label_data["rel_l2"] > threshold).mean()
            cross_rates.append(rate)
        
        cross_rates = np.array(cross_rates)
        
        # Transition width: fraction of keypoints in transition zone (0.2 < rate < 0.8)
        n_transition = np.sum((cross_rates > 0.2) & (cross_rates < 0.8))
        transition_width = n_transition / len(cross_rates) if len(cross_rates) > 0 else 0
        
        # Seed CV
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
        
        # Phase 2 new metrics
        # Probability band area: fraction of keypoints with 0.2 <= rate <= 0.8
        prob_band_area = n_transition / len(cross_rates) if len(cross_rates) > 0 else 0
        
        # Failure entropy per keypoint
        entropies = []
        for rate in cross_rates:
            if 0 < rate < 1:
                h = -rate * np.log(rate) - (1 - rate) * np.log(1 - rate)
                entropies.append(h)
            else:
                entropies.append(0)
        
        mean_entropy = np.mean(entropies) if entropies else 0
        max_entropy = np.max(entropies) if entropies else 0
        entropy_area = np.sum(entropies) / len(cross_rates) if len(cross_rates) > 0 else 0
        
        results[case_name] = {
            "display": info["display"],
            "prototype": info["prototype"],
            "boundary_width": float(np.mean(boundary_widths)),
            "transition_width": float(transition_width),
            "seed_cv": float(seed_cv),
            "irregularity": float(irregularity),
            "prob_band_area": float(prob_band_area),
            "mean_entropy": float(mean_entropy),
            "max_entropy": float(max_entropy),
            "entropy_area": float(entropy_area),
            "cross_rates": cross_rates.tolist(),
        }
    
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
    
    entropy = {
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
    
    data = {}
    for case in d_null.keys():
        data[case] = {
            "d_null": d_null[case],
            "lambda_max": lambda_max[case],
            "hessian_entropy": entropy[case],
            "basin_count": basin_count[case],
            "info_cv": info_cv[case],
        }
    
    return data


# ═══════════════════════════════════════════════════════════
#  Phase 1: Prototype Analysis
# ═══════════════════════════════════════════════════════════

def phase1_prototype_analysis(degradation: Dict[str, Dict]) -> Dict[str, Any]:
    """Phase 1: Check if prototypes are correctly captured by metrics."""
    
    print("\n" + "=" * 60)
    print("PHASE 1: Prototype-Metric Consistency")
    print("=" * 60)
    
    # Group by prototype
    prototypes = {}
    for case, data in degradation.items():
        proto = data["prototype"]
        if proto not in prototypes:
            prototypes[proto] = []
        prototypes[proto].append(data)
    
    # Compute statistics per prototype
    proto_stats = {}
    metrics = ["boundary_width", "transition_width", "seed_cv", "irregularity",
               "prob_band_area", "mean_entropy", "max_entropy", "entropy_area"]
    
    for proto, cases in prototypes.items():
        proto_stats[proto] = {}
        for metric in metrics:
            values = [c[metric] for c in cases]
            proto_stats[proto][metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "median": float(np.median(values)),
                "n": len(values),
            }
    
    # Print results
    print("\n  Prototype Statistics:")
    for proto, stats in proto_stats.items():
        print(f"\n  {proto} (n={stats['boundary_width']['n']}):")
        for metric in metrics:
            print(f"    {metric}: mean={stats[metric]['mean']:.4f}, std={stats[metric]['std']:.4f}")
    
    # Task 1.2: Rank consistency
    print("\n  Task 1.2: Rank Consistency Analysis")
    
    # Theoretical ranking: Non-Degrading < Sharp < Intermediate < Broad
    theoretical_order = ["Non-Degrading", "Sharp Boundary", "Intermediate", "Broad Band"]
    
    # Compute mean values per prototype for each metric
    proto_means = {}
    for proto in theoretical_order:
        if proto in proto_stats:
            proto_means[proto] = {m: proto_stats[proto][m]["mean"] for m in metrics}
    
    # Compute Spearman correlation between theoretical rank and metric rank
    rank_correlations = {}
    for metric in metrics:
        # Get theoretical ranks
        theo_ranks = list(range(len(theoretical_order)))
        
        # Get metric values in theoretical order
        metric_values = [proto_means.get(p, {}).get(metric, 0) for p in theoretical_order]
        
        # Compute Spearman
        if len(metric_values) >= 3:
            corr, p = sp_stats.spearmanr(theo_ranks, metric_values)
            rank_correlations[metric] = {"correlation": float(corr), "p_value": float(p)}
            sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
            print(f"    {metric}: r={corr:.3f}, p={p:.3f} {sig}")
    
    return {
        "prototype_stats": proto_stats,
        "rank_correlations": rank_correlations,
    }


# ═══════════════════════════════════════════════════════════
#  Phase 2: Probability Band Metrics
# ═══════════════════════════════════════════════════════════

def phase2_probability_metrics(degradation: Dict[str, Dict]) -> Dict[str, Any]:
    """Phase 2: Compute probability band area and failure entropy."""
    
    print("\n" + "=" * 60)
    print("PHASE 2: Probability Band Metrics")
    print("=" * 60)
    
    results = {}
    
    for case, data in degradation.items():
        results[case] = {
            "display": data["display"],
            "prototype": data["prototype"],
            "prob_band_area": data["prob_band_area"],
            "mean_entropy": data["mean_entropy"],
            "max_entropy": data["max_entropy"],
            "entropy_area": data["entropy_area"],
        }
    
    # Print results
    print("\n  Probability Band Metrics:")
    print(f"  {'PDE':<20} {'prob_band':>10} {'mean_H':>10} {'max_H':>10} {'entropy_area':>12}")
    print(f"  {'-' * 65}")
    for case, data in results.items():
        print(f"  {data['display']:<20} {data['prob_band_area']:>10.3f} "
              f"{data['mean_entropy']:>10.4f} {data['max_entropy']:>10.4f} "
              f"{data['entropy_area']:>12.4f}")
    
    return results


# ═══════════════════════════════════════════════════════════
#  Phase 3: Factor-Behavior Correlation
# ═══════════════════════════════════════════════════════════

def phase3_factor_behavior(
    landscape: Dict[str, Dict],
    degradation: Dict[str, Dict],
) -> Dict[str, Any]:
    """Phase 3: Compute factor-behavior correlations."""
    
    print("\n" + "=" * 60)
    print("PHASE 3: Factor-Behavior Correlation Matrix")
    print("=" * 60)
    
    # Get common cases
    common_cases = [c for c in landscape if c in degradation]
    
    # Define correlations to test
    correlations = [
        ("d_null", "prob_band_area", "d_null <-> prob_band_area"),
        ("lambda_max", "transition_width", "lambda <-> transition_sharpness"),
        ("hessian_entropy", "mean_entropy", "entropy <-> mean_failure_entropy"),
        ("basin_count", "prob_band_area", "basin <-> prob_band_area"),
        ("info_cv", "irregularity", "infoCV <-> irregularity"),
        ("d_null", "boundary_width", "d_null <-> boundary_width"),
        ("d_null", "mean_entropy", "d_null <-> mean_failure_entropy"),
        ("info_cv", "prob_band_area", "infoCV <-> prob_band_area"),
    ]
    
    results = {}
    
    for x_metric, y_metric, label in correlations:
        x_vals = []
        y_vals = []
        case_names = []
        
        for case in common_cases:
            if x_metric in landscape[case] and y_metric in degradation[case]:
                x_vals.append(landscape[case][x_metric])
                y_vals.append(degradation[case][y_metric])
                case_names.append(case)
        
        if len(x_vals) >= 3:
            spearman_r, spearman_p = sp_stats.spearmanr(x_vals, y_vals)
            pearson_r, pearson_p = sp_stats.pearsonr(x_vals, y_vals)
            
            # Bootstrap CI for Spearman
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
                "bootstrap_ci_lower": ci_lower,
                "bootstrap_ci_upper": ci_upper,
                "n_cases": len(x_vals),
                "cases": case_names,
            }
            
            sig = "***" if spearman_p < 0.01 else "**" if spearman_p < 0.05 else "*" if spearman_p < 0.1 else "ns"
            print(f"  {label}: r={spearman_r:.3f} [{ci_lower:.3f}, {ci_upper:.3f}] {sig}")
    
    return results


# ═══════════════════════════════════════════════════════════
#  Phase 4: VIF and PCA
# ═══════════════════════════════════════════════════════════

def compute_vif(X: np.ndarray) -> np.ndarray:
    """Compute Variance Inflation Factor for each feature."""
    n_features = X.shape[1]
    vif = np.zeros(n_features)
    
    for i in range(n_features):
        y = X[:, i]
        X_other = np.delete(X, i, axis=1)
        X_with_intercept = np.column_stack([np.ones(len(y)), X_other])
        
        try:
            beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
            y_pred = X_with_intercept @ beta
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            vif[i] = 1 / (1 - r_squared) if r_squared < 1 else float('inf')
        except:
            vif[i] = float('inf')
    
    return vif


def phase4_collinearity(landscape: Dict[str, Dict]) -> Dict[str, Any]:
    """Phase 4: VIF and PCA analysis."""
    
    print("\n" + "=" * 60)
    print("PHASE 4: VIF and PCA Collinearity Analysis")
    print("=" * 60)
    
    cases = list(landscape.keys())
    metrics = ["d_null", "lambda_max", "hessian_entropy", "basin_count", "info_cv"]
    
    # Build data matrix
    X = np.array([[landscape[c][m] for m in metrics] for c in cases])
    
    # Standardize
    X_std = (X - X.mean(axis=0)) / X.std(axis=0)
    
    # VIF
    print("\n  Variance Inflation Factors:")
    vif = compute_vif(X_std)
    for i, m in enumerate(metrics):
        status = "** HIGH" if vif[i] > 5 else "* moderate" if vif[i] > 2.5 else ""
        print(f"    {m}: VIF={vif[i]:.2f} {status}")
    
    # PCA
    print("\n  PCA Analysis:")
    cov = np.cov(X_std.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    
    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Explained variance
    total_var = eigenvalues.sum()
    explained_ratio = eigenvalues / total_var
    cumulative_ratio = np.cumsum(explained_ratio)
    
    print(f"    Eigenvalues: {eigenvalues}")
    print(f"    Explained variance ratio: {explained_ratio}")
    print(f"    Cumulative variance ratio: {cumulative_ratio}")
    
    # Loading matrix
    print("\n    Loading Matrix (PC1, PC2):")
    for i, m in enumerate(metrics):
        print(f"    {m}: PC1={eigenvectors[i, 0]:.3f}, PC2={eigenvectors[i, 1]:.3f}")
    
    return {
        "metrics": metrics,
        "vif": vif.tolist(),
        "eigenvalues": eigenvalues.tolist(),
        "explained_ratio": explained_ratio.tolist(),
        "cumulative_ratio": cumulative_ratio.tolist(),
        "eigenvectors": eigenvectors.tolist(),
    }


# ═══════════════════════════════════════════════════════════
#  Phase 5: Model Comparison
# ═══════════════════════════════════════════════════════════

def fit_linear_model(X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    """Fit linear regression and return metrics."""
    n, p = X.shape
    X_with_intercept = np.column_stack([np.ones(n), X])
    
    try:
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
        y_pred = X_with_intercept @ beta
        
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - p - 1) if n > p + 1 else r_squared
        
        # AIC and BIC
        mse = ss_res / n
        aic = n * np.log(mse + 1e-10) + 2 * (p + 1)
        bic = n * np.log(mse + 1e-10) + (p + 1) * np.log(n)
        
        # LOOCV
        loocv_errors = []
        for i in range(n):
            X_train = np.delete(X_with_intercept, i, axis=0)
            y_train = np.delete(y, i)
            beta_i = np.linalg.lstsq(X_train, y_train, rcond=None)[0]
            y_pred_i = X_with_intercept[i] @ beta_i
            loocv_errors.append((y[i] - y_pred_i) ** 2)
        loocv_mse = np.mean(loocv_errors)
        loocv_r2 = 1 - loocv_mse / (np.var(y) + 1e-10)
        
        return {
            "r_squared": float(r_squared),
            "adj_r_squared": float(adj_r_squared),
            "aic": float(aic),
            "bic": float(bic),
            "loocv_r2": float(loocv_r2),
            "n_samples": n,
            "n_features": p,
        }
    except Exception as e:
        return {"error": str(e)}


def phase5_model_comparison(
    landscape: Dict[str, Dict],
    degradation: Dict[str, Dict],
) -> Dict[str, Any]:
    """Phase 5: Compare Model A (4-factor), B (3-factor), C (2-factor)."""
    
    print("\n" + "=" * 60)
    print("PHASE 5: Model A/B/C Comparison")
    print("=" * 60)
    
    common_cases = [c for c in landscape if c in degradation and "prob_band_area" in degradation[c]]
    
    if len(common_cases) < 5:
        print("  ERROR: Not enough cases with prob_band_area data")
        return {"error": "Not enough cases"}
    
    # Target: prob_band_area
    y = np.array([degradation[c]["prob_band_area"] for c in common_cases])
    
    # Model A: d_null, lambda_max, hessian_entropy, info_cv (4 factors)
    X_a = np.array([
        [landscape[c]["d_null"], landscape[c]["lambda_max"],
         landscape[c]["hessian_entropy"], landscape[c]["info_cv"]]
        for c in common_cases
    ])
    
    # Model B: d_null, lambda_max, hessian_entropy (3 factors, remove info_cv)
    X_b = np.array([
        [landscape[c]["d_null"], landscape[c]["lambda_max"],
         landscape[c]["hessian_entropy"]]
        for c in common_cases
    ])
    
    # Model C: d_null, landscape_complexity (2 factors)
    # landscape_complexity = lambda_max * hessian_entropy
    X_c = np.array([
        [landscape[c]["d_null"],
         landscape[c]["lambda_max"] * landscape[c]["hessian_entropy"]]
        for c in common_cases
    ])
    
    # Fit models
    model_a = fit_linear_model(X_a, y)
    model_b = fit_linear_model(X_b, y)
    model_c = fit_linear_model(X_c, y)
    
    # Print results
    print(f"\n  Model A (4 factors: d_null, lambda, entropy, infoCV):")
    print(f"    R2={model_a.get('r_squared', 0):.3f}, Adj R2={model_a.get('adj_r_squared', 0):.3f}")
    print(f"    AIC={model_a.get('aic', 0):.1f}, BIC={model_a.get('bic', 0):.1f}")
    print(f"    LOOCV R2={model_a.get('loocv_r2', 0):.3f}")
    
    print(f"\n  Model B (3 factors: d_null, lambda, entropy):")
    print(f"    R2={model_b.get('r_squared', 0):.3f}, Adj R2={model_b.get('adj_r_squared', 0):.3f}")
    print(f"    AIC={model_b.get('aic', 0):.1f}, BIC={model_b.get('bic', 0):.1f}")
    print(f"    LOOCV R2={model_b.get('loocv_r2', 0):.3f}")
    
    print(f"\n  Model C (2 factors: d_null, landscape_complexity):")
    print(f"    R2={model_c.get('r_squared', 0):.3f}, Adj R2={model_c.get('adj_r_squared', 0):.3f}")
    print(f"    AIC={model_c.get('aic', 0):.1f}, BIC={model_c.get('bic', 0):.1f}")
    print(f"    LOOCV R2={model_c.get('loocv_r2', 0):.3f}")
    
    return {
        "model_a": model_a,
        "model_b": model_b,
        "model_c": model_c,
        "n_cases": len(common_cases),
        "cases": common_cases,
    }


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_all_phases(
    phase1_results: Dict,
    phase2_results: Dict,
    phase3_results: Dict,
    phase4_results: Dict,
    phase5_results: Dict,
    degradation: Dict,
    landscape: Dict,
    output_dir: Path,
):
    """Generate all figures."""
    
    displays = {c: d["display"] for c, d in degradation.items()}
    prototypes = {c: d["prototype"] for c, d in degradation.items()}
    colors = {
        "Non-Degrading": "#2c7a5a",
        "Sharp Boundary": "#1f4e79",
        "Intermediate": "#FF8C00",
        "Broad Band": "#b64040",
    }
    
    # Figure 1: Prototype comparison
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    metrics = ["boundary_width", "transition_width", "seed_cv", "prob_band_area"]
    titles = ["Boundary Width", "Transition Width", "Seed CV", "Prob Band Area"]
    
    for ax, metric, title in zip(axes.flatten(), metrics, titles):
        proto_data = {}
        for case, data in degradation.items():
            proto = data["prototype"]
            if proto not in proto_data:
                proto_data[proto] = []
            proto_data[proto].append(data[metric])
        
        proto_names = list(proto_data.keys())
        proto_values = [proto_data[p] for p in proto_names]
        proto_colors = [colors.get(p, "#666") for p in proto_names]
        
        bp = ax.boxplot(proto_values, labels=proto_names, patch_artist=True)
        for patch, color in zip(bp["boxes"], proto_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(metric, fontsize=10)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis="y")
    
    fig.suptitle("Phase 1: Prototype Comparison", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig1_prototype_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig1_prototype_comparison.png")
    
    # Figure 2: Probability band metrics
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    p_metrics = ["prob_band_area", "mean_entropy", "entropy_area"]
    p_titles = ["Probability Band Area", "Mean Failure Entropy", "Entropy Area"]
    
    for ax, metric, title in zip(axes, p_metrics, p_titles):
        cases = list(phase2_results.keys())
        values = [phase2_results[c][metric] for c in cases]
        case_colors = [colors.get(phase2_results[c]["prototype"], "#666") for c in cases]
        
        bars = ax.bar(range(len(cases)), values, color=case_colors, alpha=0.8)
        ax.set_xticks(range(len(cases)))
        ax.set_xticklabels([displays[c] for c in cases], rotation=45, ha="right", fontsize=8)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(metric, fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")
    
    fig.suptitle("Phase 2: Probability Band Metrics", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig2_probability_metrics.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig2_probability_metrics.png")
    
    # Figure 3: Factor-behavior correlations
    n_corr = len(phase3_results)
    if n_corr > 0:
        n_cols = min(4, n_corr)
        n_rows = (n_corr + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
        if n_corr == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for idx, (label, result) in enumerate(phase3_results.items()):
            ax = axes[idx]
            
            x_vals = []
            y_vals = []
            for case in result["cases"]:
                x_metric = result["x_metric"]
                y_metric = result["y_metric"]
                if x_metric in landscape[case] and y_metric in degradation[case]:
                    x_vals.append(landscape[case][x_metric])
                    y_vals.append(degradation[case][y_metric])
            
            for i, (x, y, case) in enumerate(zip(x_vals, y_vals, result["cases"])):
                proto = degradation[case]["prototype"]
                ax.scatter(x, y, c=colors.get(proto, "#666"), s=100, alpha=0.8,
                          edgecolors="white", linewidth=1)
                ax.annotate(displays[case], (x, y), fontsize=7, ha="center", va="bottom",
                           xytext=(0, 5), textcoords="offset points")
            
            sig = "***" if result["spearman_p"] < 0.01 else "**" if result["spearman_p"] < 0.05 else "*" if result["spearman_p"] < 0.1 else "ns"
            ax.text(0.05, 0.95, f"r={result['spearman_r']:.3f} {sig}\n"
                    f"95% CI [{result['bootstrap_ci_lower']:.3f}, {result['bootstrap_ci_upper']:.3f}]",
                    transform=ax.transAxes, fontsize=9, va="top",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
            
            ax.set_xlabel(result["x_metric"], fontsize=10)
            ax.set_ylabel(result["y_metric"], fontsize=10)
            ax.set_title(label, fontsize=10)
            ax.grid(True, alpha=0.3)
        
        # Hide unused axes
        for idx in range(n_corr, len(axes)):
            axes[idx].set_visible(False)
        
        fig.suptitle("Phase 3: Factor-Behavior Correlations", fontsize=14)
        fig.tight_layout()
        fig.savefig(output_dir / "fig3_factor_behavior.png", dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: fig3_factor_behavior.png")
    
    # Figure 4: VIF
    if "vif" in phase4_results:
        fig, ax = plt.subplots(figsize=(8, 5))
        metrics = phase4_results["metrics"]
        vif_vals = phase4_results["vif"]
        
        colors_vif = ["#b64040" if v > 5 else "#FF8C00" if v > 2.5 else "#2c7a5a" for v in vif_vals]
        bars = ax.bar(metrics, vif_vals, color=colors_vif, alpha=0.8)
        
        ax.axhline(y=5, color="red", linestyle="--", alpha=0.5, label="VIF=5 threshold")
        ax.axhline(y=2.5, color="orange", linestyle="--", alpha=0.5, label="VIF=2.5 threshold")
        
        for bar, v in zip(bars, vif_vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"{v:.2f}", ha="center", fontsize=10)
        
        ax.set_ylabel("VIF", fontsize=12)
        ax.set_title("Phase 4: Variance Inflation Factors", fontsize=13)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis="y")
        
        fig.tight_layout()
        fig.savefig(output_dir / "fig4_vif.png", dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: fig4_vif.png")
    
    # Figure 5: Model comparison
    if "model_a" in phase5_results:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        models = ["model_a", "model_b", "model_c"]
        model_names = ["Model A\n(4 factors)", "Model B\n(3 factors)", "Model C\n(2 factors)"]
        metrics_comp = ["r_squared", "adj_r_squared", "loocv_r2"]
        metrics_labels = ["R²", "Adjusted R²", "LOOCV R²"]
        
        for ax, metric, label in zip(axes, metrics_comp, metrics_labels):
            values = [phase5_results[m].get(metric, 0) for m in models]
            bars = ax.bar(model_names, values, color=["#1f4e79", "#2c7a5a", "#b64040"], alpha=0.8)
            
            for bar, v in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f"{v:.3f}", ha="center", fontsize=10)
            
            ax.set_ylabel(label, fontsize=12)
            ax.set_title(label, fontsize=12)
            ax.set_ylim(0, 1.1)
            ax.grid(True, alpha=0.3, axis="y")
        
        fig.suptitle("Phase 5: Model Comparison", fontsize=14)
        fig.tight_layout()
        fig.savefig(output_dir / "fig5_model_comparison.png", dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: fig5_model_comparison.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    phase1_results: Dict,
    phase2_results: Dict,
    phase3_results: Dict,
    phase4_results: Dict,
    phase5_results: Dict,
) -> str:
    """Generate comprehensive summary report."""
    
    lines = [
        "# 综合退化机制分析报告",
        "",
        "## 概述",
        "",
        "本分析通过5个阶段验证退化原型和四因素理论。",
        "",
        "---",
        "",
        "## Phase 1: 原型与指标一致性检查",
        "",
        "### 各原型统计",
        "",
        "| 原型 | boundary_width | transition_width | seedCV | prob_band_area |",
        "|------|---------------|------------------|--------|----------------|",
    ]
    
    for proto, stats in phase1_results["prototype_stats"].items():
        lines.append(
            f"| {proto} | {stats['boundary_width']['mean']:.2f}±{stats['boundary_width']['std']:.2f} | "
            f"{stats['transition_width']['mean']:.3f}±{stats['transition_width']['std']:.3f} | "
            f"{stats['seed_cv']['mean']:.4f}±{stats['seed_cv']['std']:.4f} | "
            f"{stats['prob_band_area']['mean']:.3f}±{stats['prob_band_area']['std']:.3f} |"
        )
    
    lines.extend([
        "",
        "### 排序一致性 (Spearman)",
        "",
        "| 指标 | r | p | 显著性 |",
        "|------|---|---|--------|",
    ])
    
    for metric, vals in phase1_results["rank_correlations"].items():
        sig = "***" if vals["p_value"] < 0.01 else "**" if vals["p_value"] < 0.05 else "*" if vals["p_value"] < 0.1 else "ns"
        lines.append(f"| {metric} | {vals['correlation']:.3f} | {vals['p_value']:.3f} | {sig} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Phase 2: 概率带指标",
        "",
        "| PDE | 原型 | prob_band_area | mean_entropy | max_entropy | entropy_area |",
        "|-----|------|---------------|-------------|-------------|--------------|",
    ])
    
    for case, data in phase2_results.items():
        lines.append(
            f"| {data['display']} | {data['prototype']} | {data['prob_band_area']:.3f} | "
            f"{data['mean_entropy']:.4f} | {data['max_entropy']:.4f} | {data['entropy_area']:.4f} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Phase 3: 因素→行为相关矩阵",
        "",
        "| 相关性 | Spearman r | 95% CI | p | 显著性 |",
        "|--------|-----------|--------|---|--------|",
    ])
    
    for label, vals in phase3_results.items():
        sig = "***" if vals["spearman_p"] < 0.01 else "**" if vals["spearman_p"] < 0.05 else "*" if vals["spearman_p"] < 0.1 else "ns"
        lines.append(
            f"| {label} | {vals['spearman_r']:.3f} | "
            f"[{vals['bootstrap_ci_lower']:.3f}, {vals['bootstrap_ci_upper']:.3f}] | "
            f"{vals['spearman_p']:.3f} | {sig} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Phase 4: VIF和PCA",
        "",
        "### VIF",
        "",
        "| Factor | VIF | 状态 |",
        "|--------|-----|------|",
    ])
    
    for i, m in enumerate(phase4_results["metrics"]):
        v = phase4_results["vif"][i]
        status = "严重共线" if v > 5 else "中度共线" if v > 2.5 else "可接受"
        lines.append(f"| {m} | {v:.2f} | {status} |")
    
    lines.extend([
        "",
        "### PCA",
        "",
        "| PC | 特征值 | 解释率 | 累积解释率 |",
        "|----|--------|--------|-----------|",
    ])
    
    for i in range(len(phase4_results["eigenvalues"])):
        lines.append(
            f"| PC{i+1} | {phase4_results['eigenvalues'][i]:.3f} | "
            f"{phase4_results['explained_ratio'][i]:.3f} | "
            f"{phase4_results['cumulative_ratio'][i]:.3f} |"
        )
    
    lines.extend([
        "",
        "### Loading Matrix",
        "",
        "| Factor | PC1 | PC2 |",
        "|--------|-----|-----|",
    ])
    
    for i, m in enumerate(phase4_results["metrics"]):
        lines.append(f"| {m} | {phase4_results['eigenvectors'][i][0]:.3f} | {phase4_results['eigenvectors'][i][1]:.3f} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Phase 5: Model Comparison",
        "",
        "| Model | R² | Adj R² | AIC | BIC | LOOCV R² |",
        "|-------|-----|--------|-----|-----|----------|",
    ])
    
    for model, name in [("model_a", "A (4因素)"), ("model_b", "B (3因素)"), ("model_c", "C (2因素)")]:
        m = phase5_results[model]
        lines.append(
            f"| {name} | {m.get('r_squared', 0):.3f} | {m.get('adj_r_squared', 0):.3f} | "
            f"{m.get('aic', 0):.1f} | {m.get('bic', 0):.1f} | {m.get('loocv_r2', 0):.3f} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 结论",
        "",
        "### Phase 1 结论",
        "",
        "指标是否正确刻画了原型？",
        "",
        "### Phase 2 结论",
        "",
        "概率带指标是否比传统指标更好？",
        "",
        "### Phase 3 结论",
        "",
        "哪些因素→行为相关性最强？",
        "",
        "### Phase 4 结论",
        "",
        "四因素是否存在严重共线性？",
        "",
        "### Phase 5 结论",
        "",
        "哪个模型最优？",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Comprehensive Degradation Mechanism Analysis")
    print("=" * 60)
    
    # Load data
    print("\n[0/5] Loading data...")
    degradation = compute_degradation_metrics_all()
    landscape = load_landscape_metrics()
    print(f"  Loaded {len(degradation)} cases with degradation metrics")
    print(f"  Loaded {len(landscape)} cases with landscape metrics")
    
    # Phase 1
    phase1_results = phase1_prototype_analysis(degradation)
    
    # Phase 2
    phase2_results = phase2_probability_metrics(degradation)
    
    # Phase 3
    phase3_results = phase3_factor_behavior(landscape, degradation)
    
    # Phase 4
    phase4_results = phase4_collinearity(landscape)
    
    # Phase 5
    phase5_results = phase5_model_comparison(landscape, degradation)
    
    # Generate figures
    print("\n[FIG] Generating figures...")
    plot_all_phases(
        phase1_results, phase2_results, phase3_results,
        phase4_results, phase5_results,
        degradation, landscape, OUTPUT_DIR
    )
    
    # Save results
    print("\n[SAVE] Saving results...")
    
    all_results = {
        "phase1": phase1_results,
        "phase2": phase2_results,
        "phase3": phase3_results,
        "phase4": phase4_results,
        "phase5": phase5_results,
    }
    
    with open(OUTPUT_DIR / "comprehensive_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Saved: comprehensive_results.json")
    
    summary = generate_summary(
        phase1_results, phase2_results, phase3_results,
        phase4_results, phase5_results
    )
    (OUTPUT_DIR / "comprehensive_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: comprehensive_summary.md")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
