from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
OUT = RESULTS / "analysis" / "review_strengthening_v1"
METRICS = ["physics_rms", "boundary_rms", "rel_l2", "structure_error", "loss_std", "loss_ratio"]
DIMENSIONS = {
    "physics_score": ["physics_rms", "boundary_rms"],
    "training_score": ["loss_std", "loss_ratio"],
    "reference_score": ["rel_l2"],
    "structure_score": ["structure_error"],
}
CASE_ORDER = ["poisson", "stokes_poiseuille", "fisher_kpp", "burgers"]
CASE_LABELS = {
    "poisson": "泊松方程",
    "stokes_poiseuille": "定常 Stokes-Poiseuille 流",
    "fisher_kpp": "Fisher-KPP 方程",
    "burgers": "黏性 Burgers 方程",
}


def configure_chinese_fonts() -> None:
    for candidate in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]:
        path = Path(candidate)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            name = font_manager.FontProperties(fname=str(path)).get_name()
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return


configure_chinese_fonts()


def logistic_score(value: float, good: float, fail: float) -> float:
    if math.isclose(good, fail):
        return 0.5
    mid = 0.5 * (good + fail)
    scale = max(abs(fail - good) / 6.0, 1e-12)
    z = (value - mid) / scale
    return float(1.0 / (1.0 + math.exp(z)))


def wilson(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def load_matrices() -> pd.DataFrame:
    frames = [
        pd.read_csv(RESULTS / "matrices" / "coarse_v1" / "matrix_summary.csv"),
        pd.read_csv(RESULTS / "matrices" / "coarse_fisher_kpp_v1" / "matrix_summary.csv"),
    ]
    return pd.concat(frames, ignore_index=True)


def make_scores(df: pd.DataFrame, anchors: dict[str, dict[str, float]]) -> pd.DataFrame:
    out = df.copy()
    for metric in METRICS:
        out[f"{metric}_score"] = [logistic_score(float(v), anchors[metric]["good"], anchors[metric]["fail"]) for v in out[metric]]
    for dim, metrics in DIMENSIONS.items():
        vals = np.ones(len(out))
        for metric in metrics:
            vals *= np.maximum(out[f"{metric}_score"].to_numpy(float), 1e-12)
        out[dim] = vals ** (1 / len(metrics))
    dim_cols = list(DIMENSIONS)
    out["R_lin_split"] = out[dim_cols].mean(axis=1)
    out["dominant_dimension_split"] = out[dim_cols].idxmin(axis=1)
    return out


def calibration_split_analysis(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_rows = []
    scored_frames = []
    split_defs = {
        "noise_holdout_odd": lambda d: d["noise_std"].round(3).isin([0.05, 0.15, 0.30]),
        "sparsity_holdout_low": lambda d: d["num_observation"].isin([8, 16]),
    }
    for split_name, is_eval in split_defs.items():
        for case in CASE_ORDER:
            cdf = df[df["case"] == case].copy()
            eval_mask = is_eval(cdf)
            if eval_mask.sum() < 3 or (~eval_mask).sum() < 3:
                continue
            cal = cdf[~eval_mask]
            ev = cdf[eval_mask]
            anchors = {}
            for metric in METRICS:
                good = float(cal[metric].quantile(0.15))
                fail = float(cal[metric].quantile(0.85))
                if math.isclose(good, fail):
                    span = max(abs(good) * 0.1, 1e-8)
                    good -= span
                    fail += span
                anchors[metric] = {"good": good, "fail": fail}
            scored = make_scores(ev, anchors)
            baseline = float(cdf[(cdf.noise_std == cdf.noise_std.min()) & (cdf.num_observation == cdf.num_observation.max())]["rel_l2"].mean())
            threshold = 1.5 * baseline
            scored["crosses_threshold"] = scored["rel_l2"] > threshold
            scored["split"] = split_name
            scored_frames.append(scored)
            high = scored[scored["crosses_threshold"]]
            dom = high["dominant_dimension_split"].value_counts().idxmax() if len(high) else scored["dominant_dimension_split"].value_counts().idxmax()
            rho = scored[["rel_l2", "R_lin_split"]].corr(method="spearman").iloc[0, 1]
            split_rows.append(
                {
                    "split": split_name,
                    "case": case,
                    "n_calibration": int(len(cal)),
                    "n_evaluation": int(len(ev)),
                    "threshold_rel_l2": threshold,
                    "evaluation_cross_rate": float(scored["crosses_threshold"].mean()),
                    "dominant_dimension": dom,
                    "spearman_rel_l2_vs_R_split": float(rho),
                    "R_lin_eval_median": float(scored["R_lin_split"].median()),
                }
            )
    return pd.DataFrame(split_rows), pd.concat(scored_frames, ignore_index=True)


def threshold_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for case in CASE_ORDER:
        cdf = df[df["case"] == case]
        baseline = float(cdf[(cdf.noise_std == cdf.noise_std.min()) & (cdf.num_observation == cdf.num_observation.max())]["rel_l2"].mean())
        for multiplier in [1.25, 1.5, 2.0]:
            threshold = multiplier * baseline
            rows.append(
                {
                    "case": case,
                    "multiplier": multiplier,
                    "baseline_rel_l2": baseline,
                    "threshold_rel_l2": threshold,
                    "n_cross": int((cdf["rel_l2"] > threshold).sum()),
                    "n_total": int(len(cdf)),
                    "cross_rate": float((cdf["rel_l2"] > threshold).mean()),
                }
            )
    return pd.DataFrame(rows)


def load_seed_runs() -> pd.DataFrame:
    frames = []
    candidates = [
        RESULTS / "probes" / "burgers_boundary_keypoints_v3_10seed" / "probe_runs.csv",
        RESULTS / "probes" / "burgers_boundary_keypoints_v4_extra_seed51_70" / "probe_runs.csv",
        RESULTS / "probes" / "burgers_boundary_keypoints_v5_transition_seed71_80" / "probe_runs.csv",
        RESULTS / "probes" / "fisher_kpp_boundary_keypoints_v1_10seed" / "probe_runs.csv",
        RESULTS / "probes" / "fisher_kpp_boundary_keypoints_v2_extra_seed51_70" / "probe_runs.csv",
        RESULTS / "probes" / "fisher_kpp_boundary_keypoints_v3_transition_seed71_80" / "probe_runs.csv",
    ]
    for path in candidates:
        if path.exists():
            frame = pd.read_csv(path)
            frame["source_file"] = str(path.relative_to(RESULTS))
            frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    df = df[df["case"].isin(["burgers", "fisher_kpp"])].copy()
    df["crosses_threshold"] = df["crosses_threshold"].astype(int)
    df["crosses_original_threshold"] = df["crosses_threshold"]
    df["analysis_threshold_rel_l2"] = np.nan
    for case, cdf in df.groupby("case"):
        clean = cdf[cdf["label"].astype(str).str.contains("safe_clean", regex=False)]
        original = float(cdf["threshold_rel_l2"].dropna().iloc[0])
        if len(clean):
            baseline_q90 = float(clean["rel_l2"].quantile(0.90))
            threshold = max(original, baseline_q90)
        else:
            baseline_q90 = float("nan")
            threshold = original
        mask = df["case"] == case
        df.loc[mask, "analysis_threshold_rel_l2"] = threshold
        df.loc[mask, "baseline_q90_rel_l2"] = baseline_q90
        df.loc[mask, "crosses_threshold"] = (df.loc[mask, "rel_l2"] >= threshold).astype(int)
    return df


def fit_logistic(df: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    data = df.copy()
    data["log_sparsity"] = np.log2(256 / data["num_observation"].astype(float))
    data["noise"] = data["noise_std"].astype(float)
    data["is_burgers"] = (data["case"] == "burgers").astype(float)
    x = np.column_stack(
        [
            np.ones(len(data)),
            data["log_sparsity"].to_numpy(float),
            data["noise"].to_numpy(float),
            data["is_burgers"].to_numpy(float),
            (data["log_sparsity"] * data["is_burgers"]).to_numpy(float),
            (data["noise"] * data["is_burgers"]).to_numpy(float),
        ]
    )
    y = data["crosses_threshold"].to_numpy(float)

    def loss(beta: np.ndarray) -> float:
        eta = x @ beta
        return float(np.sum(np.logaddexp(0, eta) - y * eta) + 0.5 * 1e-4 * np.sum(beta * beta))

    result = minimize(loss, np.zeros(x.shape[1]), method="BFGS")
    beta = result.x
    names = ["intercept", "log_sparsity", "noise", "burgers_shift", "burgers_x_sparsity", "burgers_x_noise"]
    rows = []
    for name, value in zip(names, beta):
        rows.append({"term": name, "coef": float(value), "odds_ratio": float(math.exp(max(min(value, 30), -30)))})
    return beta, pd.DataFrame(rows)


def bootstrap_logistic(df: pd.DataFrame, n_boot: int = 200, seed: int = 20260525) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    units = df[["case", "num_observation", "noise_std", "seed"]].drop_duplicates().reset_index(drop=True)
    rows = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(units), len(units))
        sample_units = units.iloc[idx]
        sample = sample_units.merge(df, on=["case", "num_observation", "noise_std", "seed"], how="left")
        try:
            _, coefs = fit_logistic(sample)
            rows.append(coefs.set_index("term")["coef"].to_dict())
        except Exception:
            continue
    boot = pd.DataFrame(rows)
    out = []
    for col in boot.columns:
        out.append(
            {
                "term": col,
                "coef_ci_low": float(boot[col].quantile(0.025)),
                "coef_ci_high": float(boot[col].quantile(0.975)),
                "n_boot_success": int(boot[col].notna().sum()),
            }
        )
    return pd.DataFrame(out)


def grouped_seed_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in df.groupby(["case", "num_observation", "noise_std"]):
        case, nobs, noise = keys
        n = len(group)
        k = int(group["crosses_threshold"].sum())
        lo, hi = wilson(k, n)
        rows.append(
            {
                "case": case,
                "num_observation": int(nobs),
                "noise_std": float(noise),
                "n_seed": int(n),
                "analysis_threshold_rel_l2": float(group["analysis_threshold_rel_l2"].iloc[0]),
                "baseline_q90_rel_l2": float(group["baseline_q90_rel_l2"].iloc[0]),
                "cross_count": k,
                "cross_rate": k / n,
                "wilson_low": lo,
                "wilson_high": hi,
                "wilson_width": hi - lo,
                "condition_label": f"N={int(nobs)}, σ={float(noise):.3f}",
            }
        )
    return pd.DataFrame(rows)


def plot_review_figures(cal_summary: pd.DataFrame, thresh: pd.DataFrame, seed_summary: pd.DataFrame) -> None:
    fig_dir = RESULTS / "paper_figures" / "v1"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2), constrained_layout=True)
    pivot = cal_summary.pivot_table(index="case", columns="split", values="spearman_rel_l2_vs_R_split").reindex(CASE_ORDER)
    im = axes[0].imshow(pivot.to_numpy(float), cmap="YlGnBu", vmin=-1, vmax=1, aspect="auto")
    split_labels = {"noise_holdout_odd": "噪声层级留出", "sparsity_holdout_low": "低观测层级留出"}
    axes[0].set_xticks(range(len(pivot.columns)), [split_labels.get(c, c) for c in pivot.columns], rotation=20, ha="right")
    axes[0].set_yticks(range(len(pivot.index)), [CASE_LABELS[c] for c in pivot.index])
    axes[0].set_title("留出评估中的排序一致性")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            axes[0].text(j, i, f"{pivot.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.03)

    for case in CASE_ORDER:
        sub = thresh[thresh["case"] == case]
        axes[1].plot(sub["multiplier"], sub["cross_rate"], marker="o", label=CASE_LABELS[case])
    axes[1].set_xlabel("边界阈值倍数")
    axes[1].set_ylabel("越界比例")
    axes[1].set_title("1.25/1.5/2.0 倍基线阈值敏感性")
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=7, frameon=False)
    fig.savefig(fig_dir / "figure_08_calibration_threshold_robustness.png", dpi=320, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), sharey=True, constrained_layout=True)
    for ax, case, color in zip(axes, ["fisher_kpp", "burgers"], ["#C18B21", "#B44B4B"]):
        sub = seed_summary[(seed_summary["case"] == case) & (seed_summary["n_seed"] >= 20)].sort_values(
            ["cross_rate", "noise_std", "num_observation"]
        )
        x = np.arange(len(sub))
        y = sub["cross_rate"].to_numpy(float)
        yerr_low = np.maximum(y - sub["wilson_low"].to_numpy(float), 0.0)
        yerr_high = np.maximum(sub["wilson_high"].to_numpy(float) - y, 0.0)
        ax.errorbar(
            x,
            y,
            yerr=[yerr_low, yerr_high],
            fmt="o",
            color=color,
            capsize=2,
            alpha=0.85,
        )
        ax.set_ylim(-0.04, 1.04)
        ax.set_xticks(x)
        ax.set_xticklabels(sub["condition_label"], rotation=35, ha="right", fontsize=7)
        ax.set_xlabel("高密度边界点")
        ax.set_title(CASE_LABELS[case])
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("越界率及 95% Wilson 区间")
    fig.suptitle("30-40 seed 高密度边界证据")
    fig.savefig(fig_dir / "figure_09_seed_statistical_uncertainty.png", dpi=320, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matrices = load_matrices()
    cal_summary, cal_scored = calibration_split_analysis(matrices)
    thresh = threshold_sensitivity(matrices)
    seed_runs = load_seed_runs()
    beta, coefs = fit_logistic(seed_runs)
    boot = bootstrap_logistic(seed_runs)
    seed_summary = grouped_seed_summary(seed_runs)
    coefs = coefs.merge(boot, on="term", how="left")

    cal_summary.to_csv(OUT / "calibration_split_summary.csv", index=False)
    cal_scored.to_csv(OUT / "calibration_split_scored_points.csv", index=False)
    thresh.to_csv(OUT / "threshold_sensitivity_summary.csv", index=False)
    seed_runs.to_csv(OUT / "seed_model_runs.csv", index=False)
    seed_summary.to_csv(OUT / "seed_group_summary.csv", index=False)
    coefs.to_csv(OUT / "logistic_interaction_coefficients.csv", index=False)
    plot_review_figures(cal_summary, thresh, seed_summary)

    summary = {
        "calibration_split": cal_summary.to_dict(orient="records"),
        "threshold_sensitivity": thresh.to_dict(orient="records"),
        "logistic_interaction_coefficients": coefs.to_dict(orient="records"),
        "seed_group_summary": seed_summary.to_dict(orient="records"),
        "notes": [
            "Calibration anchors are estimated on held-out splits rather than the same evaluation points.",
            "The logistic model is a unified binomial interaction model with cluster bootstrap, not a full mixed-effects model.",
            "The main seed analysis uses symmetric high-density keypoint probes for Burgers and Fisher-KPP; older five-seed matrices are exploratory.",
            "Seed exceedance uses max(original 1.5x baseline threshold, q90 of the clean high-density baseline) to avoid placing the boundary inside baseline stochastic variation.",
            "Thirty seeds per keypoint support boundary-width comparisons but not a precise deployed probability map.",
        ],
    }
    with (OUT / "review_strengthening_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
