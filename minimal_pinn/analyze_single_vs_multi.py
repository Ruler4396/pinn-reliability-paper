from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "results" / "analysis" / "recalibrated_dimensions_v1"
OUTPUT_DIR = ROOT / "results" / "analysis" / "single_vs_multi_v1"

CASE_TABLES = {
    "poisson": INPUT_DIR / "poisson_recalibrated_table.csv",
    "burgers": INPUT_DIR / "burgers_recalibrated_table.csv",
    "stokes_poiseuille": INPUT_DIR / "stokes_poiseuille_recalibrated_table.csv",
    "fisher_kpp": INPUT_DIR / "fisher_kpp_recalibrated_table.csv",
}

DIM_COLS = [
    "physics_consistency_recal",
    "training_stability_recal",
    "numerical_accuracy_recal",
    "structural_stability_recal",
]

EXTRA_COLS = ["rel_l2", "reliability_raw_recal"]
CASE_ORDER = ["poisson", "stokes_poiseuille", "fisher_kpp", "burgers"]
CASE_LABELS = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes",
    "fisher_kpp": "Fisher-KPP",
    "burgers": "Burgers",
}


def select_risk_label(df: pd.DataFrame) -> Tuple[pd.Series, str]:
    threshold_rel_l2 = float(df["threshold_rel_l2"].iloc[0])
    label = (df["rel_l2"] >= threshold_rel_l2).astype(int)
    if int(label.sum()) == 0:
        q = float(df["rel_l2"].quantile(0.75))
        label = (df["rel_l2"] >= q).astype(int)
        return label, "top_quartile_rel_l2"
    return label, "threshold_rel_l2"


def select_low_reliability_label(df: pd.DataFrame, q: float = 0.25) -> Tuple[pd.Series, str]:
    threshold = float(df["reliability_raw_recal"].quantile(q))
    label = (df["reliability_raw_recal"] <= threshold).astype(int)
    return label, f"bottom_{int(q*100)}pct_R"


def standardize(train: np.ndarray, test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    return (train - mean) / std, (test - mean) / std


def nearest_centroid_balanced_accuracy(X: np.ndarray, y: np.ndarray) -> float:
    n = len(y)
    preds = np.zeros(n, dtype=int)
    for i in range(n):
        train_mask = np.ones(n, dtype=bool)
        train_mask[i] = False
        X_train = X[train_mask]
        y_train = y[train_mask]
        X_test = X[i : i + 1]

        if len(np.unique(y_train)) < 2:
            preds[i] = int(np.round(y_train.mean()))
            continue

        X_train_std, X_test_std = standardize(X_train, X_test)
        centroids = {}
        for cls in [0, 1]:
            centroids[cls] = X_train_std[y_train == cls].mean(axis=0, keepdims=True)
        d0 = np.linalg.norm(X_test_std - centroids[0], axis=1)[0]
        d1 = np.linalg.norm(X_test_std - centroids[1], axis=1)[0]
        preds[i] = 0 if d0 <= d1 else 1

    pos_mask = y == 1
    neg_mask = y == 0
    tpr = float((preds[pos_mask] == 1).mean()) if pos_mask.any() else float("nan")
    tnr = float((preds[neg_mask] == 0).mean()) if neg_mask.any() else float("nan")
    if math.isnan(tpr):
        return tnr
    if math.isnan(tnr):
        return tpr
    return 0.5 * (tpr + tnr)


def pca_summary(X: np.ndarray) -> Dict[str, float]:
    X = np.asarray(X, dtype=float)
    mean = X.mean(axis=0, keepdims=True)
    std = X.std(axis=0, keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    Z = (X - mean) / std
    _, s, _ = np.linalg.svd(Z, full_matrices=False)
    var = (s**2) / max(len(X) - 1, 1)
    ratio = var / var.sum()
    return {
        "pc1_explained": float(ratio[0]),
        "pc2_explained": float(ratio[1]) if len(ratio) > 1 else 0.0,
        "pc1_pc2_explained": float(ratio[:2].sum()),
    }


def linear_r2(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float)
    X = np.concatenate([np.ones((len(x), 1)), x], axis=1)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot < 1e-12:
        return 1.0
    return max(0.0, 1.0 - ss_res / ss_tot)


def analyze_case(case_name: str, df: pd.DataFrame) -> Dict:
    corr_pearson = df[DIM_COLS + EXTRA_COLS].corr(method="pearson")
    corr_spearman = df[DIM_COLS + EXTRA_COLS].corr(method="spearman")

    label, selection_rule = select_risk_label(df)
    low_r_label, low_r_rule = select_low_reliability_label(df)
    X1 = df[["rel_l2"]].to_numpy(dtype=float)
    X4 = df[DIM_COLS].to_numpy(dtype=float)
    y = label.to_numpy(dtype=int)
    y_low_r = low_r_label.to_numpy(dtype=int)

    pca = pca_summary(X4)
    balacc_1d = nearest_centroid_balanced_accuracy(X1, y)
    balacc_4d = nearest_centroid_balanced_accuracy(X4, y)
    balacc_low_r_1d = nearest_centroid_balanced_accuracy(X1, y_low_r)
    balacc_low_r_4d = nearest_centroid_balanced_accuracy(X4, y_low_r)

    r2_table = {}
    for col in DIM_COLS + ["reliability_raw_recal"]:
        r2_table[col] = linear_r2(df["rel_l2"].to_numpy(dtype=float), df[col].to_numpy(dtype=float))

    residual_summary = {}
    x = df["rel_l2"].to_numpy(dtype=float)
    X = np.concatenate([np.ones((len(x), 1)), x.reshape(-1, 1)], axis=1)
    for col in ["training_stability_recal", "structural_stability_recal"]:
        y_col = df[col].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(X, y_col, rcond=None)
        residual = y_col - (X @ beta)
        residual_summary[col] = {
            "high_risk_mean_residual": float(residual[y == 1].mean()) if (y == 1).any() else 0.0,
            "low_risk_mean_residual": float(residual[y == 0].mean()) if (y == 0).any() else 0.0,
            "residual_std": float(residual.std()),
        }

    return {
        "n_rows": int(len(df)),
        "selection_rule": selection_rule,
        "n_high_risk": int(y.sum()),
        "low_reliability_rule": low_r_rule,
        "n_low_reliability": int(y_low_r.sum()),
        "pearson_correlation": corr_pearson.to_dict(),
        "spearman_correlation": corr_spearman.to_dict(),
        "pca": pca,
        "balanced_accuracy_rel_l2_only": float(balacc_1d),
        "balanced_accuracy_4d": float(balacc_4d),
        "balanced_accuracy_gain_4d_minus_1d": float(balacc_4d - balacc_1d),
        "balanced_accuracy_low_R_rel_l2_only": float(balacc_low_r_1d),
        "balanced_accuracy_low_R_4d": float(balacc_low_r_4d),
        "balanced_accuracy_low_R_gain_4d_minus_1d": float(balacc_low_r_4d - balacc_low_r_1d),
        "r2_vs_rel_l2": r2_table,
        "residual_summary": residual_summary,
    }


def plot_pca(summary: Dict[str, Dict], output_path: Path) -> None:
    order = CASE_ORDER
    labels = [CASE_LABELS[c] for c in order]
    pc1 = [summary[c]["pca"]["pc1_explained"] for c in order]
    pc12 = [summary[c]["pca"]["pc1_pc2_explained"] for c in order]
    x = np.arange(len(order))

    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    ax.bar(x - 0.17, pc1, width=0.34, label="PC1")
    ax.bar(x + 0.17, pc12, width=0.34, label="PC1+PC2")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Explained variance ratio")
    ax.set_title("Dimensionality of recalibrated reliability scores")
    ax.legend()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_balacc(summary: Dict[str, Dict], output_path: Path) -> None:
    order = CASE_ORDER
    labels = [CASE_LABELS[c] for c in order]
    one_d = [summary[c]["balanced_accuracy_rel_l2_only"] for c in order]
    four_d = [summary[c]["balanced_accuracy_4d"] for c in order]
    one_d_low_r = [summary[c]["balanced_accuracy_low_R_rel_l2_only"] for c in order]
    four_d_low_r = [summary[c]["balanced_accuracy_low_R_4d"] for c in order]
    x = np.arange(len(order))

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), constrained_layout=True)
    axes[0].bar(x - 0.17, one_d, width=0.34, label="rel_l2 only")
    axes[0].bar(x + 0.17, four_d, width=0.34, label="4D scores")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels)
    axes[0].set_ylim(0.0, 1.0)
    axes[0].set_ylabel("Leave-one-out balanced accuracy")
    axes[0].set_title("Target: high rel_l2")
    axes[0].legend()

    axes[1].bar(x - 0.17, one_d_low_r, width=0.34, label="rel_l2 only")
    axes[1].bar(x + 0.17, four_d_low_r, width=0.34, label="4D scores")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylim(0.0, 1.0)
    axes[1].set_ylabel("Leave-one-out balanced accuracy")
    axes[1].set_title("Target: low R")
    axes[1].legend()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_r2(summary: Dict[str, Dict], output_path: Path) -> None:
    order = CASE_ORDER
    labels = [CASE_LABELS[c] for c in order]
    metric_order = [
        "physics_consistency_recal",
        "training_stability_recal",
        "numerical_accuracy_recal",
        "structural_stability_recal",
        "reliability_raw_recal",
    ]
    metric_labels = ["physics", "training", "numerical", "structural", "R"]
    x = np.arange(len(metric_order))
    width = 0.18

    fig, ax = plt.subplots(figsize=(9.0, 4.4), constrained_layout=True)
    for idx, case_name in enumerate(order):
        values = [summary[case_name]["r2_vs_rel_l2"][m] for m in metric_order]
        ax.bar(x + (idx - (len(order) - 1) / 2.0) * width, values, width=width, label=labels[idx])
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Linear R^2 against rel_l2")
    ax.set_title("How much of each score is explained by rel_l2 alone")
    ax.legend()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Dict] = {}
    rows: List[Dict[str, float | str]] = []

    for case_name, path in CASE_TABLES.items():
        df = pd.read_csv(path)
        result = analyze_case(case_name, df)
        summary[case_name] = result

        pd.DataFrame(result["pearson_correlation"]).to_csv(OUTPUT_DIR / f"{case_name}_pearson.csv")
        pd.DataFrame(result["spearman_correlation"]).to_csv(OUTPUT_DIR / f"{case_name}_spearman.csv")

        rows.append(
            {
                "case": case_name,
                "n_rows": result["n_rows"],
                "selection_rule": result["selection_rule"],
                "n_high_risk": result["n_high_risk"],
                "low_reliability_rule": result["low_reliability_rule"],
                "n_low_reliability": result["n_low_reliability"],
                "pc1_explained": result["pca"]["pc1_explained"],
                "pc1_pc2_explained": result["pca"]["pc1_pc2_explained"],
                "balanced_accuracy_rel_l2_only": result["balanced_accuracy_rel_l2_only"],
                "balanced_accuracy_4d": result["balanced_accuracy_4d"],
                "balanced_accuracy_gain_4d_minus_1d": result["balanced_accuracy_gain_4d_minus_1d"],
                "balanced_accuracy_low_R_rel_l2_only": result["balanced_accuracy_low_R_rel_l2_only"],
                "balanced_accuracy_low_R_4d": result["balanced_accuracy_low_R_4d"],
                "balanced_accuracy_low_R_gain_4d_minus_1d": result["balanced_accuracy_low_R_gain_4d_minus_1d"],
                "r2_physics_vs_rel_l2": result["r2_vs_rel_l2"]["physics_consistency_recal"],
                "r2_training_vs_rel_l2": result["r2_vs_rel_l2"]["training_stability_recal"],
                "r2_numerical_vs_rel_l2": result["r2_vs_rel_l2"]["numerical_accuracy_recal"],
                "r2_structural_vs_rel_l2": result["r2_vs_rel_l2"]["structural_stability_recal"],
                "r2_R_vs_rel_l2": result["r2_vs_rel_l2"]["reliability_raw_recal"],
            }
        )

    pd.DataFrame(rows).to_csv(OUTPUT_DIR / "single_vs_multi_summary.csv", index=False)
    with (OUTPUT_DIR / "single_vs_multi_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    plot_pca(summary, OUTPUT_DIR / "figure_20_pca_explained_variance.png")
    plot_balacc(summary, OUTPUT_DIR / "figure_21_risk_separability.png")
    plot_r2(summary, OUTPUT_DIR / "figure_22_rel_l2_r2.png")

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
