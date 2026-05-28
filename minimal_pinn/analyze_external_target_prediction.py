from __future__ import annotations

import json
import math
from math import comb
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "results" / "variant_robustness" / "variant_robustness_v2" / "point_summary.csv"
OUTPUT_DIR = ROOT / "results" / "analysis" / "external_target_prediction_v1"

CASE_ORDER = ["poisson", "stokes_poiseuille", "fisher_kpp", "burgers"]
CASE_LABELS = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "fisher_kpp": "Fisher-KPP",
    "burgers": "Burgers",
    "all_cases": "All cases",
}

MODEL_FEATURES = {
    "rel_l2_only": ["rel_l2_mean"],
    "R_only": ["reliability_raw_recal_mean"],
    "four_dim_state": [
        "physics_consistency_recal_mean",
        "training_stability_recal_mean",
        "numerical_accuracy_recal_mean",
        "structural_stability_recal_mean",
    ],
}
MODEL_LABELS = {
    "rel_l2_only": "rel_l2 only",
    "R_only": "R only",
    "four_dim_state": "4D state",
}
TASKS = {
    "high_failure": "cross_rate >= 0.5",
    "seed_sensitive": "0 < cross_rate < 1",
}


def load_table() -> pd.DataFrame:
    df = pd.read_csv(INPUT_PATH)
    df["high_failure"] = (df["cross_rate"] >= 0.5).astype(int)
    df["seed_sensitive"] = ((df["cross_rate"] > 0.0) & (df["cross_rate"] < 1.0)).astype(int)
    return df


def standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    return (train - mean) / std, (test - mean) / std


def loocv_nearest_centroid_predict(X: np.ndarray, y: np.ndarray) -> np.ndarray:
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
        centroids = {cls: X_train_std[y_train == cls].mean(axis=0, keepdims=True) for cls in [0, 1]}
        d0 = np.linalg.norm(X_test_std - centroids[0], axis=1)[0]
        d1 = np.linalg.norm(X_test_std - centroids[1], axis=1)[0]
        preds[i] = 0 if d0 <= d1 else 1
    return preds


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return float("nan"), float("nan")
    p = successes / total
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p * (1.0 - p) / total) + (z**2) / (4.0 * total**2))
    return max(0.0, center - margin), min(1.0, center + margin)


def safe_div(num: float, den: float) -> float:
    if abs(den) < 1e-12:
        return float("nan")
    return num / den


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    total = len(y_true)
    correct = tp + tn
    acc = correct / total

    tpr = safe_div(tp, tp + fn)
    tnr = safe_div(tn, tn + fp)
    if math.isnan(tpr):
        bal_acc = tnr
    elif math.isnan(tnr):
        bal_acc = tpr
    else:
        bal_acc = 0.5 * (tpr + tnr)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    if math.isnan(precision) or math.isnan(recall) or abs(precision + recall) < 1e-12:
        f1 = float("nan")
    else:
        f1 = 2.0 * precision * recall / (precision + recall)

    ci_low, ci_high = wilson_interval(correct, total)
    return {
        "n_total": int(total),
        "n_positive": int((y_true == 1).sum()),
        "n_negative": int((y_true == 0).sum()),
        "accuracy": float(acc),
        "accuracy_ci_low": float(ci_low),
        "accuracy_ci_high": float(ci_high),
        "balanced_accuracy": float(bal_acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def exact_mcnemar(correct_a: np.ndarray, correct_b: np.ndarray) -> Dict[str, float]:
    correct_a = np.asarray(correct_a, dtype=int)
    correct_b = np.asarray(correct_b, dtype=int)
    a_only = int(((correct_a == 1) & (correct_b == 0)).sum())
    b_only = int(((correct_a == 0) & (correct_b == 1)).sum())
    n = a_only + b_only
    if n == 0:
        return {
            "a_only_correct": a_only,
            "b_only_correct": b_only,
            "n_discordant": n,
            "p_value_exact": 1.0,
        }
    k = min(a_only, b_only)
    p = 2.0 * sum(comb(n, i) for i in range(k + 1)) / (2**n)
    return {
        "a_only_correct": a_only,
        "b_only_correct": b_only,
        "n_discordant": n,
        "p_value_exact": float(min(1.0, p)),
    }


def evaluate_subset(df: pd.DataFrame, subset_name: str, task_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    y = df[task_name].to_numpy(dtype=int)
    metric_rows: List[Dict[str, float | int | str]] = []
    pred_rows: List[Dict[str, float | int | str]] = []
    compare_rows: List[Dict[str, float | int | str]] = []
    pred_store: Dict[str, np.ndarray] = {}

    for model_name, cols in MODEL_FEATURES.items():
        X = df[cols].to_numpy(dtype=float)
        preds = loocv_nearest_centroid_predict(X, y)
        pred_store[model_name] = preds
        metrics = binary_metrics(y, preds)
        metric_rows.append(
            {
                "subset": subset_name,
                "task": task_name,
                "task_rule": TASKS[task_name],
                "model": model_name,
                **metrics,
            }
        )
        for idx, row in df.reset_index(drop=True).iterrows():
            pred_rows.append(
                {
                    "subset": subset_name,
                    "task": task_name,
                    "model": model_name,
                    "case": row["case"],
                    "label": row["label"],
                    "variant": row["variant"],
                    "cross_rate": float(row["cross_rate"]),
                    "target": int(y[idx]),
                    "prediction": int(preds[idx]),
                    "correct": int(preds[idx] == y[idx]),
                    "rel_l2_mean": float(row["rel_l2_mean"]),
                    "reliability_raw_recal_mean": float(row["reliability_raw_recal_mean"]),
                    "physics_consistency_recal_mean": float(row["physics_consistency_recal_mean"]),
                    "training_stability_recal_mean": float(row["training_stability_recal_mean"]),
                    "numerical_accuracy_recal_mean": float(row["numerical_accuracy_recal_mean"]),
                    "structural_stability_recal_mean": float(row["structural_stability_recal_mean"]),
                }
            )

    model_pairs = [
        ("rel_l2_only", "R_only"),
        ("rel_l2_only", "four_dim_state"),
        ("R_only", "four_dim_state"),
    ]
    for model_a, model_b in model_pairs:
        correct_a = (pred_store[model_a] == y).astype(int)
        correct_b = (pred_store[model_b] == y).astype(int)
        compare_rows.append(
            {
                "subset": subset_name,
                "task": task_name,
                "model_a": model_a,
                "model_b": model_b,
                **exact_mcnemar(correct_a, correct_b),
                "accuracy_a": float(correct_a.mean()),
                "accuracy_b": float(correct_b.mean()),
                "accuracy_gain_b_minus_a": float(correct_b.mean() - correct_a.mean()),
            }
        )

    return pd.DataFrame(metric_rows), pd.DataFrame(pred_rows), pd.DataFrame(compare_rows)


def build_summary_note(metric_df: pd.DataFrame, compare_df: pd.DataFrame) -> str:
    pooled_high = metric_df[(metric_df["subset"] == "all_cases") & (metric_df["task"] == "high_failure")].copy()
    pooled_seed = metric_df[(metric_df["subset"] == "all_cases") & (metric_df["task"] == "seed_sensitive")].copy()
    pooled_high = pooled_high.set_index("model")
    pooled_seed = pooled_seed.set_index("model")

    cmp_high = compare_df[
        (compare_df["subset"] == "all_cases")
        & (compare_df["task"] == "high_failure")
        & (compare_df["model_a"] == "rel_l2_only")
        & (compare_df["model_b"] == "four_dim_state")
    ].iloc[0]
    cmp_high_r = compare_df[
        (compare_df["subset"] == "all_cases")
        & (compare_df["task"] == "high_failure")
        & (compare_df["model_a"] == "rel_l2_only")
        & (compare_df["model_b"] == "R_only")
    ].iloc[0]

    lines = [
        "# 单维 vs 多维预测外生标签",
        "",
        "本实验不再使用由多维框架自身定义的内部标签，而是转向多 seed 结果给出的外生标签：",
        "",
        "- `high_failure`：某工况在多 seed 下的越界率 `cross_rate >= 0.5`。",
        "- `seed_sensitive`：某工况的越界率满足 `0 < cross_rate < 1`。",
        "",
        "对比使用同一 LOOCV 最近质心分类器，仅改变输入表示：",
        "",
        "- `rel_l2 only`：单一误差基线。",
        "- `R only`：四维框架聚合后的单标量。",
        "- `4D state`：四个重标定维度组成的状态向量。",
        "",
        "## Pooled 结果",
        "",
        (
            f"- 在 `high_failure` 任务上，`rel_l2 only`、`R only` 与 `4D state` 的准确率分别为 "
            f"`{pooled_high.loc['rel_l2_only', 'accuracy']:.3f}`、"
            f"`{pooled_high.loc['R_only', 'accuracy']:.3f}` 与 "
            f"`{pooled_high.loc['four_dim_state', 'accuracy']:.3f}`；"
            f"对应 balanced accuracy 分别为 "
            f"`{pooled_high.loc['rel_l2_only', 'balanced_accuracy']:.3f}`、"
            f"`{pooled_high.loc['R_only', 'balanced_accuracy']:.3f}` 与 "
            f"`{pooled_high.loc['four_dim_state', 'balanced_accuracy']:.3f}`。"
        ),
        (
            f"- 相比单一 `rel_l2`，`R only` 的准确率提升约 "
            f"`{cmp_high_r['accuracy_gain_b_minus_a']:.3f}`，`4D state` 提升约 "
            f"`{cmp_high['accuracy_gain_b_minus_a']:.3f}`。"
            f" 但精确 McNemar 检验尚未达到显著：`rel_l2 -> R` 的 `p={cmp_high_r['p_value_exact']:.3f}`，"
            f"`rel_l2 -> 4D` 的 `p={cmp_high['p_value_exact']:.3f}`。"
        ),
        (
            f"- 在 `seed_sensitive` 任务上，`rel_l2 only` 的 balanced accuracy 为 "
            f"`{pooled_seed.loc['rel_l2_only', 'balanced_accuracy']:.3f}`，"
            f"高于 `R only` 与 `4D state` 的 `{pooled_seed.loc['R_only', 'balanced_accuracy']:.3f}`。"
            " 这说明多维框架当前更擅长预测“会不会跨 seed 大概率失效”，"
            "但还不足以替代专门的概率边界分析去识别“种子敏感而非必然失效”的中间态。"
        ),
        "",
        "## 解释",
        "",
        "- 这组结果补上了 `H2` 中最容易被质疑的一环：多维框架不只是更会解释自己的内部评分，它对跨 seed 的外生失败标签也更接近有效。",
        "- 但证据强度仍应写成“中等或初步支持”，不能写成“统计上已完全确证”。当前样本量只有 `39` 个点级样本，配对精确检验仍偏宽。",
        "- 更稳的表述应是：多维框架在 `high_failure` 这类外生失败风险标签上优于单一 `rel_l2`，而对 `seed_sensitive` 这类更细粒度的边界宽度标签，仍需要概率边界与多 seed 专项分析共同支撑。",
        "",
    ]
    return "\n".join(lines)


def plot_pooled(metric_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = metric_df[metric_df["subset"] == "all_cases"].copy()
    task_order = ["high_failure", "seed_sensitive"]
    model_order = ["rel_l2_only", "R_only", "four_dim_state"]
    x = np.arange(len(task_order))
    width = 0.22

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2), constrained_layout=True)
    for ax, metric_name, title in [
        (axes[0], "accuracy", "Accuracy"),
        (axes[1], "balanced_accuracy", "Balanced accuracy"),
    ]:
        for i, model_name in enumerate(model_order):
            vals = [
                float(
                    plot_df[
                        (plot_df["task"] == task_name) & (plot_df["model"] == model_name)
                    ][metric_name].iloc[0]
                )
                for task_name in task_order
            ]
            ax.bar(
                x + (i - 1) * width,
                vals,
                width=width,
                label=MODEL_LABELS[model_name],
            )
        ax.set_xticks(x)
        ax.set_xticklabels(["high_failure", "seed_sensitive"])
        ax.set_ylim(0.0, 1.0)
        ax.set_ylabel(title)
        ax.set_title(title)
    axes[0].legend(frameon=False)
    fig.suptitle("External-label prediction: single metric vs multidimensional reliability")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_case_high_failure(metric_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = metric_df[metric_df["task"] == "high_failure"].copy()
    plot_df = plot_df[plot_df["subset"].isin(CASE_ORDER)]
    model_order = ["rel_l2_only", "R_only", "four_dim_state"]
    x = np.arange(len(CASE_ORDER))
    width = 0.22

    fig, ax = plt.subplots(figsize=(8.6, 4.2), constrained_layout=True)
    for i, model_name in enumerate(model_order):
        vals = []
        for case_name in CASE_ORDER:
            sub = plot_df[(plot_df["subset"] == case_name) & (plot_df["model"] == model_name)]
            vals.append(float(sub["accuracy"].iloc[0]) if not sub.empty else np.nan)
        ax.bar(
            x + (i - 1) * width,
            vals,
            width=width,
            label=MODEL_LABELS[model_name],
        )
    ax.set_xticks(x)
    ax.set_xticklabels([CASE_LABELS[c] for c in CASE_ORDER])
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("LOOCV accuracy")
    ax.set_title("High-failure prediction by case")
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_table()

    metric_frames = []
    pred_frames = []
    compare_frames = []

    subsets: List[tuple[str, pd.DataFrame]] = [("all_cases", df)]
    for case_name in CASE_ORDER:
        case_df = df[df["case"] == case_name].copy()
        if not case_df.empty:
            subsets.append((case_name, case_df))

    for subset_name, subset_df in subsets:
        for task_name in TASKS:
            if subset_df[task_name].nunique() < 2:
                continue
            metric_df, pred_df, compare_df = evaluate_subset(subset_df, subset_name, task_name)
            metric_frames.append(metric_df)
            pred_frames.append(pred_df)
            compare_frames.append(compare_df)

    metric_df = pd.concat(metric_frames, ignore_index=True)
    pred_df = pd.concat(pred_frames, ignore_index=True)
    compare_df = pd.concat(compare_frames, ignore_index=True)

    metric_df.to_csv(OUTPUT_DIR / "external_target_prediction_metrics.csv", index=False)
    pred_df.to_csv(OUTPUT_DIR / "external_target_prediction_predictions.csv", index=False)
    compare_df.to_csv(OUTPUT_DIR / "external_target_prediction_mcnemar.csv", index=False)
    plot_pooled(metric_df, OUTPUT_DIR / "figure_44_external_target_prediction_pooled.png")
    plot_case_high_failure(metric_df, OUTPUT_DIR / "figure_45_external_target_prediction_high_failure_by_case.png")

    summary = {
        "input_path": str(INPUT_PATH),
        "n_rows": int(len(df)),
        "tasks": TASKS,
        "models": {k: v for k, v in MODEL_FEATURES.items()},
        "metrics": metric_df.to_dict(orient="records"),
        "mcnemar": compare_df.to_dict(orient="records"),
    }
    (OUTPUT_DIR / "external_target_prediction_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    note = build_summary_note(metric_df, compare_df)
    (ROOT.parent / "notes" / "external_target_prediction_results.md").write_text(note, encoding="utf-8")

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(metric_df.to_string(index=False))
    print(compare_df.to_string(index=False))


if __name__ == "__main__":
    main()
