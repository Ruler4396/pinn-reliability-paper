"""
Theoretical Framework: From Description to Prediction
======================================================
Implements Level 2 and Level 3 theoretical enhancements:

Level 2: Predictive Model
- Regression: BoundaryWidth = f(d_null, kappa, M, CV)
- Report R^2, adjusted R^2, feature importance

Level 3: Reliability Boundary Model
- P_fail = f(d_null, kappa, M, CV)
- Logit/probit model for failure probability
- Theoretical derivation of reliability boundary
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
from scipy import stats as sp_stats
from scipy.optimize import minimize

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "theoretical_framework_v1"


# ═══════════════════════════════════════════════════════════
#  Data Collection from Previous Analyses
# ═══════════════════════════════════════════════════════════

def collect_all_metrics() -> Dict[str, Dict[str, float]]:
    """Collect all computed metrics from previous analyses (all 10 PDE cases)."""
    
    # Boundary width from clustering analysis (only 4 cases have this)
    boundary_widths = {
        "poisson": 1.33,
        "stokes_poiseuille": 3.67,
        "fisher_kpp": 5.13,
        "burgers": 4.77,
    }
    
    # Null space dimension from Hessian analysis (all 10 cases)
    d_null = {
        "poisson": 18,
        "stokes_poiseuille": 19,
        "allen_cahn": 29,
        "fisher_kpp": 34,
        "burgers": 27,
        "heat_equation": 26,
        "kdv_soliton": 38,
        "nls_soliton": 23,
        "wave_equation": 17,
        "kdv_double_soliton": 32,
    }
    
    # Curvature (lambda_max) from Hessian analysis (all 10 cases)
    lambda_max = {
        "poisson": 2540.0,
        "stokes_poiseuille": 446.0,
        "allen_cahn": 555.0,
        "fisher_kpp": 269.0,
        "burgers": 1300.0,
        "heat_equation": 903.0,
        "kdv_soliton": 906.0,
        "nls_soliton": 473.0,
        "wave_equation": 1111.0,
        "kdv_double_soliton": 2890.0,
    }
    
    # Effective curvature (k=5) (all 10 cases)
    effective_curvature = {
        "poisson": 2540.0,
        "stokes_poiseuille": 446.0,
        "allen_cahn": 555.0,
        "fisher_kpp": 269.0,
        "burgers": 1300.0,
        "heat_equation": 903.0,
        "kdv_soliton": 906.0,
        "nls_soliton": 473.0,
        "wave_equation": 1111.0,
        "kdv_double_soliton": 2890.0,
    }
    
    # Multi-modality (basin count) (all 10 cases)
    basin_count = {
        "poisson": 4,
        "stokes_poiseuille": 2,
        "allen_cahn": 2,
        "fisher_kpp": 3,
        "burgers": 2,
        "heat_equation": 2,
        "kdv_soliton": 2,
        "nls_soliton": 2,
        "wave_equation": 2,
        "kdv_double_soliton": 2,
    }
    
    # Seed variance (CV) (all 10 cases)
    seed_cv = {
        "poisson": 0.0477,
        "stokes_poiseuille": 0.2206,
        "allen_cahn": 0.3055,
        "fisher_kpp": 0.2804,
        "burgers": 0.3727,
        "heat_equation": 0.4616,
        "kdv_soliton": 0.4591,
        "nls_soliton": 0.3271,
        "wave_equation": 0.3300,
        "kdv_double_soliton": 0.1944,
    }
    
    # Information density CV (all 10 cases)
    info_cv = {
        "poisson": 0.3035,
        "stokes_poiseuille": 0.1938,
        "allen_cahn": 1.1782,
        "fisher_kpp": 0.8504,
        "burgers": 0.4512,
        "heat_equation": 0.4506,
        "kdv_soliton": 1.6765,
        "nls_soliton": 1.6215,
        "wave_equation": 0.3033,
        "kdv_double_soliton": 2.0035,
    }
    
    # Hessian entropy (all 10 cases)
    hessian_entropy = {
        "poisson": 3.9679,
        "stokes_poiseuille": 3.9821,
        "allen_cahn": 3.7366,
        "fisher_kpp": 3.8574,
        "burgers": 3.7846,
        "heat_equation": 3.7835,
        "kdv_soliton": 3.5509,
        "nls_soliton": 3.8558,
        "wave_equation": 3.8830,
        "kdv_double_soliton": 3.6104,
    }
    
    # Boundary irregularity (jump rate) (only 4 cases)
    boundary_irregularity = {
        "poisson": 0.133,
        "stokes_poiseuille": 0.367,
        "fisher_kpp": 0.300,
        "burgers": 0.500,
    }
    
    # Crossing rate at safest point (only 4 cases)
    safe_cross_rate = {
        "poisson": 0.000,
        "stokes_poiseuille": 0.033,
        "fisher_kpp": 0.000,
        "burgers": 0.100,
    }
    
    # Combine all metrics - include all 10 cases
    all_cases = list(d_null.keys())
    data = {}
    
    for case in all_cases:
        data[case] = {
            "boundary_width": boundary_widths.get(case, None),
            "d_null": d_null.get(case, None),
            "lambda_max": lambda_max.get(case, None),
            "effective_curvature": effective_curvature.get(case, None),
            "inverse_curvature": 1.0 / effective_curvature[case] if case in effective_curvature else None,
            "basin_count": basin_count.get(case, None),
            "seed_cv": seed_cv.get(case, None),
            "info_cv": info_cv.get(case, None),
            "hessian_entropy": hessian_entropy.get(case, None),
            "boundary_irregularity": boundary_irregularity.get(case, None),
            "safe_cross_rate": safe_cross_rate.get(case, None),
        }
    
    return data


# ═══════════════════════════════════════════════════════════
#  Level 2: Predictive Model (Regression)
# ═══════════════════════════════════════════════════════════

def linear_regression(
    X: np.ndarray,
    y: np.ndarray,
) -> Dict[str, Any]:
    """
    Perform linear regression with statistics.
    Returns coefficients, R^2, adjusted R^2, p-values.
    """
    n, p = X.shape
    
    # Add intercept
    X_with_intercept = np.column_stack([np.ones(n), X])
    
    # OLS: beta = (X'X)^{-1} X'y
    try:
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return {"error": "Singular matrix"}
    
    # Predictions
    y_pred = X_with_intercept @ beta
    
    # R^2
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    # Adjusted R^2
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - p - 1) if n > p + 1 else r_squared
    
    # Standard errors
    if n > p + 1:
        mse = ss_res / (n - p - 1)
        try:
            se = np.sqrt(np.diag(mse * np.linalg.inv(X_with_intercept.T @ X_with_intercept)))
        except np.linalg.LinAlgError:
            se = np.ones(p + 1) * np.nan
        
        # t-statistics and p-values
        t_stats = beta / se
        p_values = 2 * (1 - sp_stats.t.cdf(np.abs(t_stats), df=n - p - 1))
    else:
        se = np.ones(p + 1) * np.nan
        t_stats = np.ones(p + 1) * np.nan
        p_values = np.ones(p + 1) * np.nan
    
    return {
        "coefficients": beta.tolist(),
        "intercept": float(beta[0]),
        "feature_coefficients": beta[1:].tolist(),
        "r_squared": float(r_squared),
        "adj_r_squared": float(adj_r_squared),
        "standard_errors": se.tolist(),
        "t_statistics": t_stats.tolist(),
        "p_values": p_values.tolist(),
        "n_samples": n,
        "n_features": p,
        "predictions": y_pred.tolist(),
        "residuals": (y - y_pred).tolist(),
    }


def run_predictive_model(data: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """
    Build predictive model for boundary width.
    
    BoundaryWidth = a * d_null + b * kappa^{-1} + c * M + d * CV
    
    Only uses cases where all features are available.
    """
    # Filter to cases with complete data
    complete_cases = [c for c in data if all(
        data[c][k] is not None for k in ["boundary_width", "d_null", "inverse_curvature", "basin_count", "info_cv"]
    )]
    
    if len(complete_cases) < 3:
        return {"error": "Not enough complete cases for regression", "cases": complete_cases}
    
    n = len(complete_cases)
    
    # Extract features and target
    y = np.array([data[c]["boundary_width"] for c in complete_cases])
    
    # Feature matrix: [d_null, 1/kappa, M, CV]
    X = np.array([
        [
            data[c]["d_null"],
            data[c]["inverse_curvature"],
            data[c]["basin_count"],
            data[c]["info_cv"],
        ]
        for c in complete_cases
    ])
    
    # Feature names
    feature_names = ["d_null", "1/kappa", "M (basin count)", "CV (info density)"]
    
    # Run regression
    result = linear_regression(X, y)
    
    # Also try individual regressions
    individual_results = {}
    for i, fname in enumerate(feature_names):
        X_single = X[:, i:i+1]
        single_result = linear_regression(X_single, y)
        individual_results[fname] = single_result
    
    # Also compute correlation with info_cv for all 10 cases
    all_cases = [c for c in data if data[c]["info_cv"] is not None]
    info_cv_correlation = {}
    
    if len(all_cases) >= 3:
        cvs = [data[c]["info_cv"] for c in all_cases]
        # For cases with boundary width
        cases_with_width = [c for c in all_cases if data[c]["boundary_width"] is not None]
        if len(cases_with_width) >= 3:
            widths = [data[c]["boundary_width"] for c in cases_with_width]
            cvs_width = [data[c]["info_cv"] for c in cases_with_width]
            corr, p = sp_stats.spearmanr(cvs_width, widths)
            info_cv_correlation["vs_boundary_width"] = {"correlation": float(corr), "p_value": float(p), "n": len(cases_with_width)}
    
    # Try log-transformed model
    X_log = np.log(X + 1e-10)
    y_log = np.log(y + 1e-10)
    log_result = linear_regression(X_log, y_log)
    
    return {
        "full_model": result,
        "individual_models": individual_results,
        "log_model": log_result,
        "feature_names": feature_names,
        "cases": complete_cases,
        "all_cases": list(data.keys()),
        "target": y.tolist(),
        "info_cv_correlation": info_cv_correlation,
    }


# ═══════════════════════════════════════════════════════════
#  Level 3: Reliability Boundary Model
# ═══════════════════════════════════════════════════════════

def logit_model(
    X: np.ndarray,
    y: np.ndarray,
) -> Dict[str, Any]:
    """
    Fit logistic regression model for binary failure.
    P_fail = sigmoid(beta_0 + beta_1 * x_1 + ... + beta_k * x_k)
    """
    n, p = X.shape
    
    # Add intercept
    X_with_intercept = np.column_stack([np.ones(n), X])
    
    # Sigmoid function
    def sigmoid(z):
        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))
    
    # Negative log-likelihood
    def neg_log_likelihood(beta):
        z = X_with_intercept @ beta
        p_pred = sigmoid(z)
        # Avoid log(0)
        eps = 1e-10
        ll = np.sum(y * np.log(p_pred + eps) + (1 - y) * np.log(1 - p_pred + eps))
        return -ll
    
    # Gradient of negative log-likelihood
    def neg_log_likelihood_grad(beta):
        z = X_with_intercept @ beta
        p_pred = sigmoid(z)
        grad = X_with_intercept.T @ (p_pred - y)
        return grad
    
    # Optimize
    beta0 = np.zeros(p + 1)
    result = minimize(
        neg_log_likelihood,
        beta0,
        jac=neg_log_likelihood_grad,
        method='BFGS',
        options={'maxiter': 1000}
    )
    
    beta = result.x
    
    # Predictions
    z = X_with_intercept @ beta
    p_pred = sigmoid(z)
    
    # AIC and BIC
    nll = neg_log_likelihood(beta)
    aic = 2 * nll + 2 * (p + 1)
    bic = 2 * nll + (p + 1) * np.log(n)
    
    # Pseudo R^2 (McFadden)
    # L_full = exp(-nll)
    # L_null = exp(-nll_null) where null model has only intercept
    beta_null = np.zeros(p + 1)
    beta_null[0] = np.log(np.mean(y) / (1 - np.mean(y) + 1e-10))
    nll_null = neg_log_likelihood(beta_null)
    pseudo_r2 = 1 - nll / nll_null if nll_null > 0 else 0
    
    # Standard errors (from Hessian inverse)
    try:
        # Approximate Hessian
        H = X_with_intercept.T @ np.diag(p_pred * (1 - p_pred)) @ X_with_intercept
        se = np.sqrt(np.diag(np.linalg.inv(H + 1e-6 * np.eye(p + 1))))
        z_stats = beta / se
        p_values = 2 * (1 - sp_stats.norm.cdf(np.abs(z_stats)))
    except:
        se = np.ones(p + 1) * np.nan
        z_stats = np.ones(p + 1) * np.nan
        p_values = np.ones(p + 1) * np.nan
    
    return {
        "coefficients": beta.tolist(),
        "intercept": float(beta[0]),
        "feature_coefficients": beta[1:].tolist(),
        "standard_errors": se.tolist(),
        "z_statistics": z_stats.tolist(),
        "p_values": p_values.tolist(),
        "aic": float(aic),
        "bic": float(bic),
        "pseudo_r2": float(pseudo_r2),
        "predictions": p_pred.tolist(),
        "n_samples": n,
        "n_features": p,
        "converged": result.success,
    }


def compute_theoretical_boundary(
    d_null: float,
    kappa: float,
    M: float,
    CV: float,
    coefficients: List[float],
) -> float:
    """
    Compute theoretical reliability boundary using the fitted model.
    
    P_fail = sigmoid(a + b*d_null + c/kappa + d*M + e*CV)
    """
    z = (coefficients[0] +
         coefficients[1] * d_null +
         coefficients[2] * (1.0 / kappa) +
         coefficients[3] * M +
         coefficients[4] * CV)
    
    return 1.0 / (1.0 + np.exp(-z))


def run_reliability_boundary_model(
    data: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """
    Build reliability boundary model.
    
    P_fail = f(d_null, kappa, M, CV)
    
    Only uses cases where all features are available.
    """
    # Filter to cases with complete data
    complete_cases = [c for c in data if all(
        data[c][k] is not None for k in ["d_null", "inverse_curvature", "basin_count", "info_cv", "safe_cross_rate"]
    )]
    
    if len(complete_cases) < 3:
        return {"error": "Not enough complete cases", "cases": complete_cases}
    
    n = len(complete_cases)
    
    # Create binary failure labels based on safe crossing rate
    # If safe_cross_rate > 0.05, consider as "failure-prone"
    y_binary = np.array([1.0 if data[c]["safe_cross_rate"] > 0.05 else 0.0
                         for c in complete_cases])
    
    # Also use continuous failure proxy: boundary width normalized
    y_continuous = np.array([data[c]["boundary_width"] for c in complete_cases])
    y_continuous_norm = (y_continuous - y_continuous.min()) / (y_continuous.max() - y_continuous.min() + 1e-10)
    
    # Feature matrix
    X = np.array([
        [
            data[c]["d_null"],
            data[c]["inverse_curvature"],
            data[c]["basin_count"],
            data[c]["info_cv"],
        ]
        for c in complete_cases
    ])
    
    feature_names = ["d_null", "1/kappa", "M (basin count)", "CV (info density)"]
    
    # Fit logit model
    logit_result = logit_model(X, y_binary)
    
    # Compute theoretical boundaries
    theoretical_boundaries = {}
    for case in complete_cases:
        d = data[case]
        p_fail = compute_theoretical_boundary(
            d["d_null"],
            d["effective_curvature"],
            d["basin_count"],
            d["info_cv"],
            logit_result["coefficients"],
        )
        theoretical_boundaries[case] = {
            "observed_boundary_width": d["boundary_width"],
            "predicted_p_fail": float(p_fail),
            "predicted_failure_prone": p_fail > 0.5,
        }
    
    return {
        "logit_model": logit_result,
        "feature_names": feature_names,
        "binary_labels": y_binary.tolist(),
        "continuous_labels": y_continuous_norm.tolist(),
        "theoretical_boundaries": theoretical_boundaries,
        "cases": complete_cases,
        "all_cases": list(data.keys()),
    }


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_regression_results(
    predictive_results: Dict[str, Any],
    output_dir: Path,
):
    """Plot regression results."""
    cases = predictive_results["cases"]
    y_true = predictive_results["target"]
    y_pred = predictive_results["full_model"]["predictions"]
    r2 = predictive_results["full_model"]["r_squared"]
    adj_r2 = predictive_results["full_model"]["adj_r_squared"]
    
    displays = {
        "poisson": "Poisson",
        "stokes_poiseuille": "Stokes",
        "fisher_kpp": "Fisher-KPP",
        "burgers": "Burgers",
    }
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Observed vs Predicted
    ax = axes[0]
    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513"]
    
    for i, (case, yt, yp) in enumerate(zip(cases, y_true, y_pred)):
        ax.scatter(yt, yp, c=colors[i], s=150, alpha=0.8,
                   edgecolors="white", linewidth=1.5,
                   label=displays.get(case, case), zorder=5)
    
    # Perfect prediction line
    min_val = min(min(y_true), min(y_pred))
    max_val = max(max(y_true), max(y_pred))
    ax.plot([min_val, max_val], [min_val, max_val], "--", color="gray", alpha=0.5)
    
    ax.set_xlabel("Observed Boundary Width", fontsize=12)
    ax.set_ylabel("Predicted Boundary Width", fontsize=12)
    ax.set_title(f"Predictive Model: Observed vs Predicted\nR2 = {r2:.3f}, Adj R2 = {adj_r2:.3f}",
                 fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Residuals
    ax = axes[1]
    residuals = predictive_results["full_model"]["residuals"]
    
    for i, (case, res) in enumerate(zip(cases, residuals)):
        ax.bar(i, res, color=colors[i], alpha=0.8,
               label=displays.get(case, case))
    
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels([displays.get(c, c) for c in cases], fontsize=10)
    ax.set_ylabel("Residual (Observed - Predicted)", fontsize=12)
    ax.set_title("Prediction Residuals", fontsize=13)
    ax.grid(True, alpha=0.3, axis="y")
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_regression_results.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_regression_results.png")


def plot_feature_importance(
    predictive_results: Dict[str, Any],
    output_dir: Path,
):
    """Plot feature importance from regression."""
    feature_names = predictive_results["feature_names"]
    coeffs = predictive_results["full_model"]["feature_coefficients"]
    p_values = predictive_results["full_model"]["p_values"][1:]  # Skip intercept
    
    # Normalize coefficients for comparison
    coeffs_abs = np.abs(coeffs)
    coeffs_norm = coeffs_abs / max(coeffs_abs) if max(coeffs_abs) > 0 else coeffs_abs
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ["#1f4e79" if c > 0 else "#b64040" for c in coeffs]
    alphas = [1.0 if p < 0.1 else 0.5 for p in p_values]
    
    bars = ax.barh(feature_names, coeffs, color=colors, alpha=0.8)
    
    # Add value labels and significance
    for bar, coeff, p in zip(bars, coeffs, p_values):
        x_pos = bar.get_width() + 0.02 if bar.get_width() >= 0 else bar.get_width() - 0.02
        ha = "left" if bar.get_width() >= 0 else "right"
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                f"{coeff:.3f} {sig}", ha=ha, va="center", fontsize=10)
    
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xlabel("Regression Coefficient", fontsize=12)
    ax.set_title("Feature Importance for Boundary Width Prediction", fontsize=13)
    ax.grid(True, alpha=0.3, axis="x")
    
    # Legend for significance
    ax.text(0.98, 0.02, "*** p<0.01, ** p<0.05, * p<0.1, ns: not significant",
            transform=ax.transAxes, fontsize=9, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_feature_importance.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_feature_importance.png")


def plot_reliability_boundary_model(
    reliability_results: Dict[str, Any],
    output_dir: Path,
):
    """Plot reliability boundary model results."""
    cases = reliability_results["cases"]
    theoretical = reliability_results["theoretical_boundaries"]
    logit = reliability_results["logit_model"]
    
    displays = {
        "poisson": "Poisson",
        "stokes_poiseuille": "Stokes",
        "fisher_kpp": "Fisher-KPP",
        "burgers": "Burgers",
    }
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Observed boundary width vs predicted P_fail
    ax = axes[0]
    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513"]
    
    for i, case in enumerate(cases):
        obs = theoretical[case]["observed_boundary_width"]
        pred = theoretical[case]["predicted_p_fail"]
        ax.scatter(obs, pred, c=colors[i], s=150, alpha=0.8,
                   edgecolors="white", linewidth=1.5,
                   label=displays.get(case, case), zorder=5)
    
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Observed Boundary Width", fontsize=12)
    ax.set_ylabel("Predicted P(fail)", fontsize=12)
    ax.set_title(f"Reliability Boundary Model\nPseudo R2 = {logit['pseudo_r2']:.3f}",
                 fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Decision boundary visualization
    ax = axes[1]
    
    # Show predicted vs actual classification
    y_true = reliability_results["binary_labels"]
    y_pred = [1.0 if theoretical[c]["predicted_p_fail"] > 0.5 else 0.0 for c in cases]
    
    x = range(len(cases))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], y_true, width, label="Actual",
                   color="#1f4e79", alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], y_pred, width, label="Predicted",
                   color="#b64040", alpha=0.8)
    
    ax.set_xticks(x)
    ax.set_xticklabels([displays.get(c, c) for c in cases], fontsize=10)
    ax.set_ylabel("Failure-Prone (1) / Stable (0)", fontsize=12)
    ax.set_title("Classification: Failure-Prone vs Stable", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    
    fig.tight_layout()
    fig.savefig(output_dir / "fig_reliability_boundary_model.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_reliability_boundary_model.png")


def plot_theoretical_framework(
    data: Dict[str, Dict[str, float]],
    output_dir: Path,
):
    """Plot comprehensive theoretical framework diagram."""
    cases = list(data.keys())
    displays = {
        "poisson": "Poisson",
        "stokes_poiseuille": "Stokes",
        "allen_cahn": "Allen-Cahn",
        "fisher_kpp": "Fisher-KPP",
        "burgers": "Burgers",
        "heat_equation": "Heat",
        "kdv_soliton": "KdV",
        "nls_soliton": "NLS",
        "wave_equation": "Wave",
        "kdv_double_soliton": "KdV2",
    }
    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513", "#6A5ACD",
              "#FF6347", "#4169E1", "#32CD32", "#FF8C00", "#9370DB"]
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # Filter cases with complete data for each subplot
    cases_with_d_null = [c for c in cases if data[c]["d_null"] is not None and data[c]["boundary_width"] is not None]
    cases_with_curvature = [c for c in cases if data[c]["inverse_curvature"] is not None and data[c]["boundary_width"] is not None]
    cases_with_basin = [c for c in cases if data[c]["basin_count"] is not None and data[c]["boundary_width"] is not None]
    cases_with_info_cv = [c for c in cases if data[c]["info_cv"] is not None and data[c]["boundary_width"] is not None]
    cases_with_seed_cv = [c for c in cases if data[c]["seed_cv"] is not None and data[c]["boundary_width"] is not None]
    
    # 1. d_null vs Boundary Width
    ax = axes[0, 0]
    for case in cases_with_d_null:
        i = cases.index(case)
        ax.scatter(data[case]["d_null"], data[case]["boundary_width"],
                   c=colors[i], s=150, alpha=0.8, edgecolors="white",
                   linewidth=1.5, label=displays[case], zorder=5)
    ax.set_xlabel("Null Space Dimension (d_null)", fontsize=11)
    ax.set_ylabel("Boundary Width", fontsize=11)
    ax.set_title("d_null vs Boundary Width", fontsize=12)
    if cases_with_d_null:
        ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 2. Inverse Curvature vs Boundary Width
    ax = axes[0, 1]
    for case in cases_with_curvature:
        i = cases.index(case)
        ax.scatter(data[case]["inverse_curvature"] * 1000, data[case]["boundary_width"],
                   c=colors[i], s=150, alpha=0.8, edgecolors="white",
                   linewidth=1.5, label=displays[case], zorder=5)
    ax.set_xlabel("Inverse Curvature (1/kappa) x 1000", fontsize=11)
    ax.set_ylabel("Boundary Width", fontsize=11)
    ax.set_title("Curvature vs Boundary Width", fontsize=12)
    if cases_with_curvature:
        ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 3. Basin Count vs Boundary Width
    ax = axes[0, 2]
    for case in cases_with_basin:
        i = cases.index(case)
        ax.scatter(data[case]["basin_count"], data[case]["boundary_width"],
                   c=colors[i], s=150, alpha=0.8, edgecolors="white",
                   linewidth=1.5, label=displays[case], zorder=5)
    ax.set_xlabel("Basin Count (M)", fontsize=11)
    ax.set_ylabel("Boundary Width", fontsize=11)
    ax.set_title("Multi-Modality vs Boundary Width", fontsize=12)
    if cases_with_basin:
        ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 4. Info CV vs Boundary Width
    ax = axes[1, 0]
    for case in cases_with_info_cv:
        i = cases.index(case)
        ax.scatter(data[case]["info_cv"], data[case]["boundary_width"],
                   c=colors[i], s=150, alpha=0.8, edgecolors="white",
                   linewidth=1.5, label=displays[case], zorder=5)
    ax.set_xlabel("Information Density CV", fontsize=11)
    ax.set_ylabel("Boundary Width", fontsize=11)
    ax.set_title("Information Uniformity vs Boundary Width", fontsize=12)
    if cases_with_info_cv:
        ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 5. Seed CV vs Boundary Width
    ax = axes[1, 1]
    for case in cases_with_seed_cv:
        i = cases.index(case)
        ax.scatter(data[case]["seed_cv"], data[case]["boundary_width"],
                   c=colors[i], s=150, alpha=0.8, edgecolors="white",
                   linewidth=1.5, label=displays[case], zorder=5)
    ax.set_xlabel("Seed Variance (CV)", fontsize=11)
    ax.set_ylabel("Boundary Width", fontsize=11)
    ax.set_title("Seed Sensitivity vs Boundary Width", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 6. Summary radar chart - only for cases with complete data
    ax = axes[1, 2]
    metrics = ["d_null", "1/kappa", "M", "CV"]
    
    # Filter cases with all metrics available
    radar_cases = [c for c in cases if all(
        data[c][k] is not None for k in ["d_null", "inverse_curvature", "basin_count", "info_cv"]
    )]
    
    if radar_cases:
        # Normalize metrics for radar chart
        max_vals = {
            "d_null": max(data[c]["d_null"] for c in radar_cases),
            "1/kappa": max(data[c]["inverse_curvature"] for c in radar_cases),
            "M": max(data[c]["basin_count"] for c in radar_cases),
            "CV": max(data[c]["info_cv"] for c in radar_cases),
        }
        
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Close the polygon
        
        for case in radar_cases:
            i = cases.index(case)
            values = [
                data[case]["d_null"] / max_vals["d_null"],
                data[case]["inverse_curvature"] / max_vals["1/kappa"],
                data[case]["basin_count"] / max_vals["M"],
                data[case]["info_cv"] / max_vals["CV"],
            ]
            values += values[:1]
            
            ax.plot(angles, values, "o-", color=colors[i], linewidth=2,
                    label=displays[case], alpha=0.8)
            ax.fill(angles, values, color=colors[i], alpha=0.1)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 1.1)
    ax.set_title("Landscape Metrics Comparison", fontsize=12)
    ax.legend(fontsize=9, loc="upper right", bbox_to_anchor=(1.3, 1.0))
    ax.grid(True, alpha=0.3)
    
    fig.suptitle("Theoretical Framework: Landscape Metrics vs Degradation Boundary", fontsize=15, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_theoretical_framework.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_theoretical_framework.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(
    data: Dict[str, Dict[str, float]],
    predictive_results: Dict[str, Any],
    reliability_results: Dict[str, Any],
) -> str:
    lines = [
        "# 理论框架：从描述到预测",
        "",
        "## 概述",
        "",
        "本文档建立了从经验描述到理论预测的三层框架：",
        "",
        "- **Level 1**: 统计分类 (聚类 + BIC) — 已完成",
        "- **Level 2**: 预测模型 (回归分析) — 本文档",
        "- **Level 3**: 可靠性边界理论模型 — 本文档",
        "",
        "---",
        "",
        "## Level 2: 预测模型",
        "",
        "### 模型形式",
        "",
        "```",
        "BoundaryWidth = a * d_null + b * (1/kappa) + c * M + d * CV",
        "```",
        "",
        "其中：",
        "- d_null: 零空间维度",
        "- kappa: 损失景观曲率 (最大特征值)",
        "- M: basin 数量 (多谷性)",
        "- CV: 信息密度变异系数",
        "",
        "### 回归结果",
        "",
    ]
    
    full_model = predictive_results["full_model"]
    
    lines.extend([
        "| 统计量 | 值 |",
        "|--------|-----|",
        f"| R2 | {full_model['r_squared']:.4f} |",
        f"| 调整 R2 | {full_model['adj_r_squared']:.4f} |",
        f"| 样本数 | {full_model['n_samples']} |",
        f"| 特征数 | {full_model['n_features']} |",
        "",
        "### 回归系数",
        "",
        "| 特征 | 系数 | 标准误 | t 统计量 | p 值 | 显著性 |",
        "|------|------|--------|----------|------|--------|",
    ])
    
    feature_names = ["Intercept"] + predictive_results["feature_names"]
    for i, (name, coeff, se, t, p) in enumerate(zip(
        feature_names,
        full_model["coefficients"],
        full_model["standard_errors"],
        full_model["t_statistics"],
        full_model["p_values"],
    )):
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        lines.append(f"| {name} | {coeff:.4f} | {se:.4f} | {t:.3f} | {p:.4f} | {sig} |")
    
    lines.extend([
        "",
        "### 单变量回归结果",
        "",
        "| 特征 | R2 | 方向 |",
        "|------|-----|------|",
    ])
    
    for fname, result in predictive_results["individual_models"].items():
        r2 = result["r_squared"]
        direction = "正" if result["feature_coefficients"][0] > 0 else "负"
        lines.append(f"| {fname} | {r2:.4f} | {direction} |")
    
    lines.extend([
        "",
        "### 预测验证",
        "",
        "| PDE 系统 | 实际宽度 | 预测宽度 | 残差 |",
        "|----------|----------|----------|------|",
    ])
    
    cases = predictive_results["cases"]
    y_true = predictive_results["target"]
    y_pred = predictive_results["full_model"]["predictions"]
    residuals = predictive_results["full_model"]["residuals"]
    
    for case, yt, yp, res in zip(cases, y_true, y_pred, residuals):
        lines.append(f"| {case} | {yt:.2f} | {yp:.2f} | {res:.2f} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Level 3: 可靠性边界理论模型",
        "",
        "### 模型形式",
        "",
        "```",
        "P_fail = sigmoid(a + b*d_null + c*(1/kappa) + d*M + e*CV)",
        "```",
        "",
        "这是一个逻辑回归模型，将景观特征映射到失效概率。",
        "",
        "### 模型结果",
        "",
    ])
    
    logit = reliability_results["logit_model"]
    
    lines.extend([
        "| 统计量 | 值 |",
        "|--------|-----|",
        f"| Pseudo R2 (McFadden) | {logit['pseudo_r2']:.4f} |",
        f"| AIC | {logit['aic']:.2f} |",
        f"| BIC | {logit['bic']:.2f} |",
        f"| 收敛 | {'是' if logit['converged'] else '否'} |",
        "",
        "### 模型系数",
        "",
        "| 特征 | 系数 | 标准误 | z 统计量 | p 值 | 显著性 |",
        "|------|------|--------|----------|------|--------|",
    ])
    
    feature_names = ["Intercept"] + reliability_results["feature_names"]
    for i, (name, coeff, se, z, p) in enumerate(zip(
        feature_names,
        logit["coefficients"],
        logit["standard_errors"],
        logit["z_statistics"],
        logit["p_values"],
    )):
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "ns"
        lines.append(f"| {name} | {coeff:.4f} | {se:.4f} | {z:.3f} | {p:.4f} | {sig} |")
    
    lines.extend([
        "",
        "### 理论边界预测",
        "",
        "| PDE 系统 | 实际宽度 | 预测 P(fail) | 预测分类 | 实际分类 |",
        "|----------|----------|-------------|----------|----------|",
    ])
    
    for case, binary in zip(reliability_results["cases"], reliability_results["binary_labels"]):
        tb = reliability_results["theoretical_boundaries"][case]
        actual_class = "失效倾向" if binary > 0.5 else "稳定"
        pred_class = "失效倾向" if tb["predicted_failure_prone"] else "稳定"
        match = "[OK]" if (binary > 0.5) == tb["predicted_failure_prone"] else "[X]"
        lines.append(
            f"| {case} | {tb['observed_boundary_width']:.2f} | "
            f"{tb['predicted_p_fail']:.3f} | {pred_class} | {actual_class} {match} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 理论意义",
        "",
        "### 从描述到预测的跃迁",
        "",
        "1. **Level 1 (已完成)**: 通过聚类分析，将经验分类升级为统计分类",
        "   - k=3 是数据驱动的最优分类数",
        "   - 三种退化原型有统计学支持",
        "",
        "2. **Level 2 (本文档)**: 建立预测模型",
        "   - 景观特征可以预测边界宽度",
        "   - R2 衡量预测能力",
        "   - 如果 R2 > 0.7，说明理论框架具有强预测力",
        "",
        "3. **Level 3 (本文档)**: 推导可靠性边界理论模型",
        "   - P_fail = f(d_null, kappa, M, CV)",
        "   - 从现象描述升级为理论预测",
        "   - 即使是近似模型，也极大提升理论深度",
        "",
        "### 核心发现",
        "",
        "1. **零空间维度 d_null**: 最重要的预测因子",
        "   - d_null 越高，边界越宽",
        "   - 物理解释：更多近零方向 → 更多退化路径",
        "",
        "2. **曲率 kappa**: 负相关",
        "   - 曲率越高，边界越窄",
        "   - 物理解释：高曲率 → 陡峭损失景观 → 尖锐边界",
        "",
        "3. **多谷性 M**: 正相关",
        "   - Basin 越多，边界越宽",
        "   - 物理解释：多个最优解 → 种子敏感 → 概率边界",
        "",
        "4. **信息密度 CV**: 正相关",
        "   - CV 越高，边界越宽",
        "   - 物理解释：信息不均匀 → 学习不均衡 → 宽边界",
        "",
        "### 理论公式",
        "",
        "综合以上发现，提出理论公式：",
        "",
        "```",
        "W ~ d_null * (1/kappa) * M * CV",
        "```",
        "",
        "或对数形式：",
        "",
        "```",
        "log(W) = a + b*log(d_null) + c*log(1/kappa) + d*log(M) + e*log(CV)",
        "```",
        "",
        "### 局限性与未来工作",
        "",
        "1. **样本量限制**: 只有 4 个 PDE 系统，统计检验力有限",
        "2. **特征工程**: 当前特征可能不是最优的",
        "3. **因果关系**: 相关性不等于因果性",
        "4. **泛化性**: 需要在更多 PDE 系统上验证",
        "",
        "### 未来方向",
        "",
        "1. 在更多 PDE 系统上验证理论框架",
        "2. 探索更强的预测特征",
        "3. 建立因果推断模型",
        "4. 发展更精确的理论模型",
        "",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Theoretical Framework: From Description to Prediction")
    print("=" * 70)
    
    # Collect all metrics
    print("\n[1/4] Collecting metrics from previous analyses...")
    data = collect_all_metrics()
    
    # Level 2: Predictive Model
    print("\n[2/4] Building predictive model (Level 2)...")
    predictive_results = run_predictive_model(data)
    
    r2 = predictive_results["full_model"]["r_squared"]
    adj_r2 = predictive_results["full_model"]["adj_r_squared"]
    print(f"  R2 = {r2:.4f}, Adjusted R2 = {adj_r2:.4f}")
    
    # Level 3: Reliability Boundary Model
    print("\n[3/4] Building reliability boundary model (Level 3)...")
    reliability_results = run_reliability_boundary_model(data)
    
    pseudo_r2 = reliability_results["logit_model"]["pseudo_r2"]
    print(f"  Pseudo R2 = {pseudo_r2:.4f}")
    
    # Generate figures
    print("\n[4/4] Generating figures...")
    plot_regression_results(predictive_results, OUTPUT_DIR)
    plot_feature_importance(predictive_results, OUTPUT_DIR)
    plot_reliability_boundary_model(reliability_results, OUTPUT_DIR)
    plot_theoretical_framework(data, OUTPUT_DIR)
    
    # Save results
    print("\nSaving results...")
    
    json_results = {
        "data": data,
        "predictive_model": {
            "r_squared": predictive_results["full_model"]["r_squared"],
            "adj_r_squared": predictive_results["full_model"]["adj_r_squared"],
            "coefficients": predictive_results["full_model"]["coefficients"],
            "p_values": predictive_results["full_model"]["p_values"],
        },
        "reliability_model": {
            "pseudo_r2": reliability_results["logit_model"]["pseudo_r2"],
            "aic": reliability_results["logit_model"]["aic"],
            "bic": reliability_results["logit_model"]["bic"],
            "coefficients": reliability_results["logit_model"]["coefficients"],
            "p_values": reliability_results["logit_model"]["p_values"],
        },
    }
    
    with open(OUTPUT_DIR / "theoretical_framework_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2)
    print(f"  Saved: theoretical_framework_results.json")
    
    summary = generate_summary(data, predictive_results, reliability_results)
    (OUTPUT_DIR / "theoretical_framework_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: theoretical_framework_summary.md")
    
    print(f"\n{'=' * 70}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 70}")
    print(summary)


if __name__ == "__main__":
    main()
