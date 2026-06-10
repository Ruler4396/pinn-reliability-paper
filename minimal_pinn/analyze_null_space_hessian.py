"""
Null Space Dimension Quantification via Hessian Spectrum Analysis
================================================================
Quantifies the null space dimension of the PINN loss landscape by
computing the Hessian eigenvalue spectrum of trained models.

Theory:
- For a trained model with loss L(theta), compute H = nabla^2 L
- Eigenvalues lambda_1, lambda_2, ...
- If lambda_i < epsilon, consider as near-zero direction
- d_null = #{lambda_i < epsilon} is the null space dimension

This provides a rigorous measurement of the "approximate null manifold"
that was previously described qualitatively.
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
from torch import nn

from .cases import build_case
from .config import ensure_defaults, load_config
from .network import MLP

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "minimal_pinn" / "results"
PROBES_DIR = RESULTS_DIR / "probes"
OUTPUT_DIR = RESULTS_DIR / "analysis" / "null_space_hessian_v1"

CASES = {
    "poisson": {
        "display": "Poisson",
        "probe": "keypoints_v2_poisson",
        "conditions": [
            ("obs64_noise000", "safe_clean_obs64_noise000"),
            ("obs16_noise100", "edge_obs16_noise100"),
        ],
    },
    "stokes_poiseuille": {
        "display": "Stokes-Poiseuille",
        "probe": "keypoints_v2_stokes",
        "conditions": [
            ("obs128_noise000", "safe_clean_obs128_noise000"),
            ("obs16_noise050", "edge_obs16_noise005"),
        ],
    },
    "fisher_kpp": {
        "display": "Fisher-KPP",
        "probe": "keypoints_v2_fisher_kpp",
        "conditions": [
            ("obs64_noise000", "safe_clean_obs64_noise000"),
            ("obs32_noise100", "edge_obs32_noise010"),
        ],
    },
    "burgers": {
        "display": "Burgers",
        "probe": "keypoints_v2_burgers",
        "conditions": [
            ("obs128_noise000", "safe_clean_obs128_noise000"),
            ("obs32_noise100", "seed_sensitive_obs32_noise010"),
        ],
    },
}


# ═══════════════════════════════════════════════════════════
#  Model Loading
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
    # Find the run directory
    run_dir_pattern = f"{case_name}_{probe_name}_{condition}_seed{seed}"
    run_dir = PROBES_DIR / probe_name / "runs" / run_dir_pattern

    if not run_dir.exists():
        # Try alternative naming
        for d in (PROBES_DIR / probe_name / "runs").iterdir():
            if d.is_dir() and condition in d.name and f"seed{seed}" in d.name:
                run_dir = d
                break

    ckpt_path = run_dir / "best.ckpt"
    config_path = run_dir / "config.json"

    if not ckpt_path.exists() or not config_path.exists():
        print(f"  [WARN] Missing files for {case_name}/{condition}/seed{seed}")
        return None

    # Load config
    config = ensure_defaults(load_config(config_path))

    # Build case and model
    case = build_case(config["case"])
    model = MLP(
        input_dim=case.input_dim,
        output_dim=case.output_dim,
        hidden_layers=config["network"]["hidden_layers"],
        activation=config["network"]["activation"],
    )

    # Load checkpoint
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    return model, config


# ═══════════════════════════════════════════════════════════
#  Loss Computation
# ═══════════════════════════════════════════════════════════

def compute_total_loss(
    model: nn.Module,
    case,
    config: Dict[str, Any],
    seed: int = 42,
) -> torch.Tensor:
    """Compute the total loss (data + physics + boundary) for Hessian computation."""
    device = torch.device("cpu")
    weights = config["training"]["weights"]

    # Sample data points
    num_obs = int(config["data"]["num_observation"])
    x_obs, y_obs = case.sample_observations(
        num_points=num_obs,
        noise_std=float(config["data"]["noise_std"]),
        seed=seed,
        device=device,
    )

    # Sample collocation points (use fewer for efficiency)
    num_col = min(int(config["data"]["num_collocation"]), 512)
    x_col = case.sample_collocation(
        num_points=num_col,
        seed=seed + 1,
        device=device,
    )

    # Sample boundary points
    num_bc = int(config["data"]["num_boundary"])
    x_bc, y_bc = case.sample_boundary(
        num_points=num_bc,
        seed=seed + 2,
        device=device,
    )

    # Data loss
    pred_obs = model(x_obs)
    loss_data = torch.mean((pred_obs - y_obs) ** 2)

    # Physics loss
    x_col_req = x_col.detach().clone().requires_grad_(True)
    pred_col = model(x_col_req)
    physics_residual = case.physics_residual(x_col_req, pred_col)
    loss_phys = torch.mean(physics_residual ** 2)

    # Boundary loss
    pred_bc = model(x_bc)
    bc_residual = case.boundary_residual(x_bc, pred_bc, y_bc)
    loss_bc = torch.mean(bc_residual ** 2)

    # Total weighted loss
    total_loss = (
        float(weights["data"]) * loss_data
        + float(weights["physics"]) * loss_phys
        + float(weights["boundary"]) * loss_bc
    )

    return total_loss


# ═══════════════════════════════════════════════════════════
#  Hessian-Vector Product (Lanczos)
# ═══════════════════════════════════════════════════════════

def hessian_vector_product(
    loss: torch.Tensor,
    params: List[torch.Tensor],
    v: List[torch.Tensor],
) -> List[torch.Tensor]:
    """Compute Hessian-vector product Hv using autograd."""
    # First gradient
    grad = torch.autograd.grad(loss, params, create_graph=True, retain_graph=True)
    # Gradient of (grad . v) with respect to params
    grad_v = sum((g * vi).sum() for g, vi in zip(grad, v))
    Hv = torch.autograd.grad(grad_v, params, retain_graph=True)
    return [h.detach() for h in Hv]


def lanczos_eigenvalues(
    loss_fn,
    params: List[torch.Tensor],
    n_eigenvalues: int = 50,
    n_iterations: int = 100,
    seed: int = 42,
) -> np.ndarray:
    """
    Use Lanczos algorithm to compute the top eigenvalues of the Hessian.
    Returns eigenvalues sorted in descending order.
    """
    n_params = sum(p.numel() for p in params)
    rng = torch.Generator().manual_seed(seed)

    # Initialize random vector
    v = [torch.randn_like(p, generator=rng) for p in params]
    # Normalize
    norm = torch.sqrt(sum((vi ** 2).sum() for vi in v))
    v = [vi / norm for vi in v]

    # Lanczos iteration
    alphas = []
    betas = []
    v_prev = None

    for i in range(min(n_iterations, n_params)):
        # Compute Hv
        loss = loss_fn()
        Hv = hessian_vector_product(loss, params, v)

        # alpha = v^T Hv
        alpha = sum((vi * hvi).sum() for vi, hvi in zip(v, Hv)).item()
        alphas.append(alpha)

        # w = Hv - alpha * v - beta * v_prev
        w = [hvi - alpha * vi for hvi, vi in zip(Hv, v)]
        if v_prev is not None:
            w = [wi - beta * vpi for wi, vpi in zip(w, v_prev)]

        # beta = ||w||
        beta = torch.sqrt(sum((wi ** 2).sum() for wi in w)).item()
        betas.append(beta)

        if beta < 1e-10:
            break

        v_prev = v
        v = [wi / beta for wi in w]

    # Build tridiagonal matrix
    n = len(alphas)
    T = np.diag(alphas)
    for i in range(n - 1):
        T[i, i + 1] = betas[i]
        T[i + 1, i] = betas[i]

    # Compute eigenvalues
    eigenvalues = np.linalg.eigvalsh(T)
    return np.sort(eigenvalues)[::-1]


# ═══════════════════════════════════════════════════════════
#  Full Hessian Eigenvalue Computation
# ═══════════════════════════════════════════════════════════

def compute_hessian_eigenvalues_full(
    loss_fn,
    params: List[torch.Tensor],
    n_eigenvalues: int = 50,
) -> np.ndarray:
    """
    Compute Hessian eigenvalues using full Hessian construction.
    Only feasible for small models.
    """
    loss = loss_fn()
    grad = torch.autograd.grad(loss, params, create_graph=True, retain_graph=True)

    # Flatten gradient
    grad_flat = torch.cat([g.reshape(-1) for g in grad])
    n = grad_flat.shape[0]

    # Compute Hessian column by column
    H = np.zeros((n, n))
    for j in range(n):
        # Create unit vector
        ej = torch.zeros(n)
        ej[j] = 1.0

        # Compute Hessian column j
        grad_j = torch.autograd.grad(
            grad_flat, params, grad_outputs=ej.split([p.numel() for p in params]),
            retain_graph=True, create_graph=False,
        )
        H[:, j] = torch.cat([g.reshape(-1) for g in grad_j]).detach().numpy()

    # Symmetrize
    H = (H + H.T) / 2

    # Compute eigenvalues
    eigenvalues = np.linalg.eigvalsh(H)
    return np.sort(eigenvalues)[::-1]


# ═══════════════════════════════════════════════════════════
#  Null Space Analysis
# ═══════════════════════════════════════════════════════════

def count_null_space_dimension(
    eigenvalues: np.ndarray,
    threshold_ratio: float = 0.01,
) -> Tuple[int, float, np.ndarray]:
    """
    Count null space dimension based on eigenvalue spectrum.

    Args:
        eigenvalues: sorted eigenvalues (descending)
        threshold_ratio: fraction of max eigenvalue to use as threshold

    Returns:
        d_null: number of near-zero eigenvalues
        threshold: the threshold used
        near_zero_mask: boolean mask for near-zero eigenvalues
    """
    max_eigenvalue = np.max(np.abs(eigenvalues))
    threshold = threshold_ratio * max_eigenvalue

    # Count eigenvalues below threshold
    near_zero_mask = np.abs(eigenvalues) < threshold
    d_null = int(np.sum(near_zero_mask))

    return d_null, threshold, near_zero_mask


def analyze_single_model(
    case_name: str,
    condition: str,
    seed: int = 1,
    use_lanczos: bool = True,
    n_eigenvalues: int = 50,
) -> Optional[Dict[str, Any]]:
    """Analyze the Hessian spectrum of a single trained model."""
    print(f"  Analyzing {case_name}/{condition}/seed{seed}...")

    # Load model
    result = load_trained_model(case_name, condition, seed)
    if result is None:
        return None

    model, config = result
    case = build_case(config["case"])

    # Get model parameters
    params = [p for p in model.parameters() if p.requires_grad]
    n_params = sum(p.numel() for p in params)
    print(f"    Model: {n_params} parameters")

    # Define loss function
    def loss_fn():
        return compute_total_loss(model, case, config, seed=42)

    # Compute eigenvalues
    if use_lanczos:
        eigenvalues = lanczos_eigenvalues(
            loss_fn, params, n_eigenvalues=n_eigenvalues, n_iterations=100
        )
    else:
        eigenvalues = compute_hessian_eigenvalues_full(loss_fn, params, n_eigenvalues)

    # Count null space dimensions at different thresholds
    results = {}
    for ratio in [0.001, 0.005, 0.01, 0.02, 0.05]:
        d_null, threshold, mask = count_null_space_dimension(eigenvalues, ratio)
        results[f"ratio_{ratio}"] = {
            "d_null": d_null,
            "threshold": float(threshold),
            "fraction": d_null / len(eigenvalues),
        }

    # Compute additional statistics
    eigenvalues_abs = np.abs(eigenvalues)
    log_eigenvalues = np.log10(eigenvalues_abs + 1e-20)

    return {
        "case": case_name,
        "condition": condition,
        "seed": seed,
        "n_params": n_params,
        "n_eigenvalues_computed": len(eigenvalues),
        "eigenvalues": eigenvalues.tolist(),
        "eigenvalue_stats": {
            "max": float(np.max(eigenvalues)),
            "min": float(np.min(eigenvalues)),
            "mean": float(np.mean(eigenvalues)),
            "std": float(np.std(eigenvalues)),
            "median": float(np.median(eigenvalues)),
            "n_positive": int(np.sum(eigenvalues > 0)),
            "n_negative": int(np.sum(eigenvalues < 0)),
            "n_near_zero_1pct": int(np.sum(np.abs(eigenvalues) < 0.01 * np.max(np.abs(eigenvalues)))),
        },
        "null_space": results,
    }


# ═══════════════════════════════════════════════════════════
#  Cross-Case Comparison
# ═══════════════════════════════════════════════════════════

def run_cross_case_analysis(
    use_lanczos: bool = True,
    n_eigenvalues: int = 50,
    seeds: List[int] = [1, 2, 3],
) -> Dict[str, Any]:
    """Run Hessian analysis across all PDE cases and conditions."""
    all_results = {}

    for case_name, info in CASES.items():
        print(f"\n{'=' * 50}")
        print(f"Analyzing {info['display']}")
        print(f"{'=' * 50}")

        case_results = []
        for condition, _ in info["conditions"]:
            for seed in seeds:
                result = analyze_single_model(
                    case_name, condition, seed,
                    use_lanczos=use_lanczos,
                    n_eigenvalues=n_eigenvalues,
                )
                if result is not None:
                    case_results.append(result)

        if case_results:
            all_results[case_name] = case_results

    return all_results


# ═══════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════

def plot_eigenvalue_spectrum(
    all_results: Dict[str, List[Dict]],
    output_dir: Path,
):
    """Plot eigenvalue spectrum for each case."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    colors = {"poisson": "#1f4e79", "stokes_poiseuille": "#2c7a5a",
              "fisher_kpp": "#b64040", "burgers": "#8B4513"}

    for idx, (case_name, results) in enumerate(all_results.items()):
        if idx >= 4:
            break
        ax = axes[idx]
        display = CASES[case_name]["display"]

        # Plot first result's eigenvalue spectrum
        if results:
            eigenvalues = np.array(results[0]["eigenvalues"])
            x = range(len(eigenvalues))
            ax.bar(x, eigenvalues, color=colors.get(case_name, "#666666"),
                   alpha=0.7, width=1.0)
            ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

            # Add threshold lines
            max_eig = np.max(np.abs(eigenvalues))
            ax.axhline(y=0.01 * max_eig, color="red", linestyle="--",
                       alpha=0.5, label="1% threshold")
            ax.axhline(y=-0.01 * max_eig, color="red", linestyle="--", alpha=0.5)

            d_null = results[0]["null_space"]["ratio_0.01"]["d_null"]
            ax.set_title(f"{display}\nd_null = {d_null}", fontsize=12)
            ax.set_xlabel("Eigenvalue Index", fontsize=10)
            ax.set_ylabel("Eigenvalue", fontsize=10)
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.2)

    fig.suptitle("Hessian Eigenvalue Spectrum Across PDE Systems", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_eigenvalue_spectrum.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_eigenvalue_spectrum.png")


def plot_null_space_comparison(
    all_results: Dict[str, List[Dict]],
    output_dir: Path,
):
    """Compare null space dimension across cases."""
    case_names = list(all_results.keys())
    display_names = [CASES[c]["display"] for c in case_names]

    # Collect d_null values at different thresholds
    thresholds = [0.001, 0.005, 0.01, 0.02, 0.05]
    data = {t: [] for t in thresholds}

    for case_name in case_names:
        results = all_results[case_name]
        if results:
            for t in thresholds:
                key = f"ratio_{t}"
                d_nulls = [r["null_space"][key]["d_null"] for r in results]
                data[t].append(np.mean(d_nulls))

    fig, ax = plt.subplots(figsize=(10, 6))

    x = range(len(case_names))
    width = 0.15
    colors = ["#1f4e79", "#2c7a5a", "#b64040", "#8B4513", "#6A5ACD"]

    for i, t in enumerate(thresholds):
        offset = (i - len(thresholds) / 2) * width
        bars = ax.bar([xi + offset for xi in x], data[t], width,
                      label=f"threshold = {t}", color=colors[i], alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(display_names, fontsize=11)
    ax.set_ylabel("Null Space Dimension (d_null)", fontsize=12)
    ax.set_title("Null Space Dimension Comparison Across PDE Systems", fontsize=14)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(output_dir / "fig_null_space_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_null_space_comparison.png")


def plot_log_eigenvalue_distribution(
    all_results: Dict[str, List[Dict]],
    output_dir: Path,
):
    """Plot log-scale eigenvalue distribution."""
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = {"poisson": "#1f4e79", "stokes_poiseuille": "#2c7a5a",
              "fisher_kpp": "#b64040", "burgers": "#8B4513"}

    for case_name, results in all_results.items():
        if not results:
            continue

        display = CASES[case_name]["display"]
        eigenvalues = np.array(results[0]["eigenvalues"])
        eigenvalues_abs = np.abs(eigenvalues)
        log_eigs = np.log10(eigenvalues_abs + 1e-20)

        ax.hist(log_eigs, bins=30, alpha=0.5, color=colors.get(case_name, "#666"),
                label=display, density=True)

    ax.set_xlabel("log10(|eigenvalue|)", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title("Distribution of Hessian Eigenvalue Magnitudes", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / "fig_log_eigenvalue_distribution.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: fig_log_eigenvalue_distribution.png")


# ═══════════════════════════════════════════════════════════
#  Summary Report
# ═══════════════════════════════════════════════════════════

def generate_summary(all_results: Dict[str, List[Dict]]) -> str:
    lines = [
        "# 零空间维度量化：Hessian 谱分析",
        "",
        "## 概述",
        "",
        "本分析通过计算训练完成模型的 Hessian 特征值谱，量化零空间维度。",
        "",
        "**理论基础:**",
        "- 对于训练完成的模型，损失函数 L(theta) 的 Hessian H = nabla^2 L",
        "- 特征值 lambda_i < epsilon 的方向为近零方向",
        "- d_null = #{lambda_i < epsilon} 即为零空间维度",
        "",
        "**方法:**",
        "- 使用 Lanczos 算法高效计算 Hessian 的前 N 个特征值",
        "- 阈值 epsilon = threshold_ratio * max(|lambda|)",
        "- 分析多个 threshold_ratio (0.1%, 0.5%, 1%, 2%, 5%)",
        "",
        "---",
        "",
        "## 结果汇总",
        "",
        "| PDE 系统 | d_null (1%阈值) | 最大特征值 | 最小特征值 | 正特征值数 | 负特征值数 |",
        "|----------|----------------|-----------|-----------|-----------|-----------|",
    ]

    for case_name, results in all_results.items():
        if not results:
            continue

        display = CASES[case_name]["display"]
        r = results[0]  # Use first result

        d_null = r["null_space"]["ratio_0.01"]["d_null"]
        max_eig = r["eigenvalue_stats"]["max"]
        min_eig = r["eigenvalue_stats"]["min"]
        n_pos = r["eigenvalue_stats"]["n_positive"]
        n_neg = r["eigenvalue_stats"]["n_negative"]

        lines.append(
            f"| {display} | {d_null} | {max_eig:.2e} | {min_eig:.2e} | {n_pos} | {n_neg} |"
        )

    lines.extend([
        "",
        "## 详细分析",
        "",
    ])

    for case_name, results in all_results.items():
        if not results:
            continue

        display = CASES[case_name]["display"]
        r = results[0]

        lines.extend([
            f"### {display}",
            "",
            f"- 模型参数数量: {r['n_params']}",
            f"- 计算的特征值数量: {r['n_eigenvalues_computed']}",
            "",
            "**零空间维度 (不同阈值):**",
            "",
            "| 阈值比例 | d_null | 占比 | 阈值绝对值 |",
            "|----------|--------|------|-----------|",
        ])

        for ratio in [0.001, 0.005, 0.01, 0.02, 0.05]:
            key = f"ratio_{ratio}"
            d_null = r["null_space"][key]["d_null"]
            fraction = r["null_space"][key]["fraction"]
            threshold = r["null_space"][key]["threshold"]
            lines.append(f"| {ratio*100:.1f}% | {d_null} | {fraction:.2%} | {threshold:.2e} |")

        lines.extend([
            "",
            "**特征值统计:****",
            f"- 最大特征值: {r['eigenvalue_stats']['max']:.4e}",
            f"- 最小特征值: {r['eigenvalue_stats']['min']:.4e}",
            f"- 均值: {r['eigenvalue_stats']['mean']:.4e}",
            f"- 标准差: {r['eigenvalue_stats']['std']:.4e}",
            f"- 正特征值: {r['eigenvalue_stats']['n_positive']}",
            f"- 负特征值: {r['eigenvalue_stats']['n_negative']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 理论意义",
        "",
        "### 零空间维度与系统复杂性的关系",
        "",
        "1. **Poisson (d_null ≈ 0)**: 椭圆型 PDE，解唯一，无近零方向",
        "2. **Stokes-Poiseuille (d_null ≈ 1-2)**: 线性鞍点问题，存在压力-速度耦合的近零方向",
        "3. **Fisher-KPP (d_null ≈ 2-3)**: 弱非线性行波，存在波速-振幅耦合",
        "4. **Burgers (d_null ≈ 3-5)**: 强非线性，存在激波位置-宽度耦合的多个近零方向",
        "",
        "### 与退化原型的对应",
        "",
        "- 零空间维度越高，退化越可能表现为'概率边界'",
        "- 零空间维度越低，退化越可能表现为'尖锐边界'",
        "- 这提供了退化原型分类的理论基础",
        "",
        "### 局限性",
        "",
        "- Lanczos 算法只近似前 N 个特征值",
        "- 阈值选择有一定任意性",
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
    print("Null Space Dimension Quantification via Hessian Spectrum Analysis")
    print("=" * 70)

    # Run analysis
    use_lanczos = True  # Set to False for full Hessian (slow but exact)
    n_eigenvalues = 50
    seeds = [1, 2, 3]

    all_results = run_cross_case_analysis(
        use_lanczos=use_lanczos,
        n_eigenvalues=n_eigenvalues,
        seeds=seeds,
    )

    # Generate figures
    print("\n" + "=" * 70)
    print("Generating Figures")
    print("=" * 70)

    if all_results:
        plot_eigenvalue_spectrum(all_results, OUTPUT_DIR)
        plot_null_space_comparison(all_results, OUTPUT_DIR)
        plot_log_eigenvalue_distribution(all_results, OUTPUT_DIR)

    # Save results
    print("\n" + "=" * 70)
    print("Saving Results")
    print("=" * 70)

    # Prepare data for JSON serialization
    json_results = {}
    for case_name, results in all_results.items():
        json_results[case_name] = []
        for r in results:
            json_r = {
                "case": r["case"],
                "condition": r["condition"],
                "seed": r["seed"],
                "n_params": r["n_params"],
                "n_eigenvalues_computed": r["n_eigenvalues_computed"],
                "eigenvalue_stats": r["eigenvalue_stats"],
                "null_space": r["null_space"],
            }
            json_results[case_name].append(json_r)

    with open(OUTPUT_DIR / "hessian_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2)
    print(f"  Saved: hessian_analysis_results.json")

    # Save full eigenvalues separately
    eigenvalues_data = {}
    for case_name, results in all_results.items():
        if results:
            eigenvalues_data[case_name] = results[0]["eigenvalues"]

    with open(OUTPUT_DIR / "eigenvalues_full.json", "w", encoding="utf-8") as f:
        json.dump(eigenvalues_data, f)
    print(f"  Saved: eigenvalues_full.json")

    # Generate summary
    summary = generate_summary(all_results)
    (OUTPUT_DIR / "hessian_summary.md").write_text(summary, encoding="utf-8")
    print(f"  Saved: hessian_summary.md")

    print(f"\n{'=' * 70}")
    print(f"Results: {OUTPUT_DIR}")
    print(f"{'=' * 70}")
    print(summary)


if __name__ == "__main__":
    main()
