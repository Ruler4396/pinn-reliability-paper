from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
TRANSFER_CSV = (
    ROOT
    / "results"
    / "analysis"
    / "few_shot_transfer_calibration_v1"
    / "transfer_run_predictions.csv"
)
PARTITION_CSV = (
    ROOT
    / "results"
    / "analysis"
    / "r_partition_transfer_v1"
    / "partition_run_predictions.csv"
)
OUTPUT_DIR = ROOT / "results" / "analysis" / "local_boundary_transfer_v1"

CASE_ORDER = ["stokes_poiseuille", "burgers"]
CASE_TITLES = {
    "stokes_poiseuille": "Stokes-Poiseuille",
    "burgers": "Burgers",
}
VARIANT_ORDER = ["baseline", "capacity_v1", "weight_balanced_v2"]
TRANSFER_VARIANTS = ["capacity_v1", "weight_balanced_v2"]
TASK_ORDER = ["safe_boundary", "failure_boundary"]
METHOD_ORDER = [
    "REF_P1_global_partition",
    "L0_rel2_midpoint",
    "L1_pair_prototype_2d",
    "L2_pair_prototype_3d",
]
TASK_SPECS = {
    "stokes_poiseuille": {
        "safe_boundary": {
            "positive_labels": ["safe_obs64_noise000"],
            "boundary_negative_label": "critical_obs8_noise0125",
            "all_negative_labels": ["critical_obs8_noise0125", "failure_obs8_noise0175"],
        },
        "failure_boundary": {
            "positive_labels": ["failure_obs8_noise0175"],
            "boundary_negative_label": "critical_obs8_noise0125",
            "all_negative_labels": ["safe_obs64_noise000", "critical_obs8_noise0125"],
        },
    },
    "burgers": {
        "safe_boundary": {
            "positive_labels": ["safe_obs64_noise005"],
            "boundary_negative_label": "transition_obs48_noise010",
            "all_negative_labels": [
                "transition_obs48_noise010",
                "seed_sensitive_obs32_noise010",
                "failure_obs32_noise0175",
            ],
        },
        "failure_boundary": {
            "positive_labels": ["failure_obs32_noise0175"],
            "boundary_negative_label": "seed_sensitive_obs32_noise010",
            "all_negative_labels": [
                "safe_obs64_noise005",
                "transition_obs48_noise010",
                "seed_sensitive_obs32_noise010",
            ],
        },
    },
}
COLORS = {
    "REF_P1_global_partition": "#6b7280",
    "L0_rel2_midpoint": "#c05a00",
    "L1_pair_prototype_2d": "#1f77b4",
    "L2_pair_prototype_3d": "#8a5bd1",
}


def binary_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if tp + fp > 0 else 0.0
    recall = tp / (tp + fn) if tp + fn > 0 else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0


def load_transfer_runs() -> pd.DataFrame:
    df = pd.read_csv(TRANSFER_CSV)
    return df[df["method"] == "M3_order_constrained_piecewise"].copy()


def load_partition_reference() -> pd.DataFrame:
    df = pd.read_csv(PARTITION_CSV)
    return df[df["partition_method"] == "P1_anchor_mean_midpoint"].copy()


def build_task_labels(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for case in CASE_ORDER:
        for task in TASK_ORDER:
            spec = TASK_SPECS[case][task]
            subset = df[df["case"] == case].copy()
            subset["task"] = task
            subset["target_positive"] = subset["label"].isin(spec["positive_labels"]).astype(int)
            rows.extend(subset.to_dict(orient="records"))
    return pd.DataFrame(rows)


def midpoint_predict(
    full_task_df: pd.DataFrame,
    case: str,
    task: str,
    variant: str,
) -> tuple[np.ndarray, float]:
    spec = TASK_SPECS[case][task]
    subset = full_task_df[(full_task_df["case"] == case) & (full_task_df["task"] == task)]
    baseline = subset[subset["variant"] == "baseline"]
    pos_vals = baseline[baseline["label"].isin(spec["positive_labels"])]["transferred_rel_l2"]
    neg_vals = baseline[baseline["label"] == spec["boundary_negative_label"]]["transferred_rel_l2"]
    threshold = float((pos_vals.mean() + neg_vals.mean()) / 2.0)
    variant_df = subset[subset["variant"] == variant]
    pred = (variant_df["transferred_rel_l2"] <= threshold).astype(int).to_numpy()
    return pred, threshold


def prototype_predict(
    full_task_df: pd.DataFrame,
    case: str,
    task: str,
    variant: str,
    features: List[str],
) -> tuple[np.ndarray, Dict[str, object]]:
    spec = TASK_SPECS[case][task]
    subset = full_task_df[(full_task_df["case"] == case) & (full_task_df["task"] == task)]
    baseline = subset[subset["variant"] == "baseline"].copy()
    variant_df = subset[subset["variant"] == variant].copy()

    mu = baseline[features].mean()
    sigma = baseline[features].std(ddof=0).replace(0.0, 1.0)
    baseline_z = (baseline[features] - mu) / sigma
    variant_z = (variant_df[features] - mu) / sigma

    pos_proto = baseline_z[baseline["label"].isin(spec["positive_labels"])].mean().to_numpy()
    neg_proto = baseline_z[baseline["label"] == spec["boundary_negative_label"]].mean().to_numpy()

    out: List[int] = []
    for _, row in variant_z.iterrows():
        x = row.to_numpy()
        d_pos = float(np.linalg.norm(x - pos_proto))
        d_neg = float(np.linalg.norm(x - neg_proto))
        out.append(1 if d_pos <= d_neg else 0)
    return np.asarray(out, dtype=int), {
        "prototype_features": ",".join(features),
        "positive_anchor": ",".join(spec["positive_labels"]),
        "negative_anchor": spec["boundary_negative_label"],
    }


def apply_local_methods(task_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for case in CASE_ORDER:
        for task in TASK_ORDER:
            for variant in VARIANT_ORDER:
                variant_df = task_df[
                    (task_df["case"] == case) & (task_df["task"] == task) & (task_df["variant"] == variant)
                ].copy()
                if variant_df.empty:
                    continue
                y_true = variant_df["target_positive"].to_numpy()

                pred, threshold = midpoint_predict(task_df, case, task, variant)
                temp = variant_df.copy()
                temp["boundary_method"] = "L0_rel2_midpoint"
                temp["pred_positive"] = pred
                temp["method_meta"] = f"threshold={threshold:.6f}"
                rows.extend(temp.to_dict(orient="records"))

                pred, meta = prototype_predict(
                    task_df, case, task, variant, ["transferred_rel_l2", "transferred_R"]
                )
                temp = variant_df.copy()
                temp["boundary_method"] = "L1_pair_prototype_2d"
                temp["pred_positive"] = pred
                temp["method_meta"] = json.dumps(meta, ensure_ascii=False)
                rows.extend(temp.to_dict(orient="records"))

                pred, meta = prototype_predict(
                    task_df,
                    case,
                    task,
                    variant,
                    ["transferred_rel_l2", "transferred_R", "structural_stability_recal"],
                )
                temp = variant_df.copy()
                temp["boundary_method"] = "L2_pair_prototype_3d"
                temp["pred_positive"] = pred
                temp["method_meta"] = json.dumps(meta, ensure_ascii=False)
                rows.extend(temp.to_dict(orient="records"))
    return pd.DataFrame(rows)


def apply_reference_partition(partition_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for case in CASE_ORDER:
        for task in TASK_ORDER:
            subset = partition_df[partition_df["case"] == case].copy()
            if task == "safe_boundary":
                subset["target_positive"] = (subset["target_partition_label"] == "reliable").astype(int)
                subset["pred_positive"] = (subset["pred_partition_label"] == "reliable").astype(int)
            else:
                subset["target_positive"] = (subset["target_partition_label"] == "unreliable").astype(int)
                subset["pred_positive"] = (subset["pred_partition_label"] == "unreliable").astype(int)
            subset["task"] = task
            subset["boundary_method"] = "REF_P1_global_partition"
            subset["method_meta"] = "partition_method=P1_anchor_mean_midpoint"
            rows.extend(subset.to_dict(orient="records"))
    out = pd.DataFrame(rows)
    common_cols = [
        "case",
        "variant",
        "label",
        "seed",
        "task",
        "boundary_method",
        "target_positive",
        "pred_positive",
        "method_meta",
    ]
    return out[common_cols]


def merge_reference(local_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "case",
        "variant",
        "label",
        "seed",
        "task",
        "boundary_method",
        "target_positive",
        "pred_positive",
        "method_meta",
    ]
    local_df = local_df.copy()
    local_df = local_df.rename(columns={"boundary_method": "boundary_method"})
    return pd.concat([reference_df[keep_cols], local_df[keep_cols]], ignore_index=True)


def summarize_runs(all_preds: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, task, variant), group in all_preds.groupby(
        ["boundary_method", "case", "task", "variant"]
    ):
        y_true = group["target_positive"].to_numpy()
        y_pred = group["pred_positive"].to_numpy()
        rows.append(
            {
                "method": method,
                "case": case,
                "task": task,
                "variant": variant,
                "n_run": int(len(group)),
                "accuracy": float((y_true == y_pred).mean()),
                "f1": float(binary_f1(y_true, y_pred)),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "task", "variant", "method"])


def summarize_points(all_preds: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, task, variant, label), group in all_preds.groupby(
        ["boundary_method", "case", "task", "variant", "label"]
    ):
        pred_majority = int(group["pred_positive"].value_counts().idxmax())
        target = int(group["target_positive"].iloc[0])
        rows.append(
            {
                "method": method,
                "case": case,
                "task": task,
                "variant": variant,
                "label": label,
                "pred_majority": pred_majority,
                "target_positive": target,
                "point_accuracy": int(pred_majority == target),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "task", "variant", "method", "label"])


def summarize_disagreement(point_summary: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, task, label), group in point_summary.groupby(["method", "case", "task", "label"]):
        unique_count = int(group["pred_majority"].nunique())
        rows.append(
            {
                "method": method,
                "case": case,
                "task": task,
                "label": label,
                "pred_unique_count": unique_count,
                "boundary_disagreement": int(unique_count > 1),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "task", "label", "method"])


def summarize_transfer_means(run_summary: pd.DataFrame, disagreement: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, task), group in run_summary[run_summary["variant"].isin(TRANSFER_VARIANTS)].groupby(
        ["method", "case", "task"]
    ):
        dis = disagreement[
            (disagreement["method"] == method)
            & (disagreement["case"] == case)
            & (disagreement["task"] == task)
        ]
        rows.append(
            {
                "method": method,
                "case": case,
                "task": task,
                "mean_transfer_accuracy": float(group["accuracy"].mean()),
                "mean_transfer_f1": float(group["f1"].mean()),
                "point_disagreement_rate": float(dis["boundary_disagreement"].mean()) if not dis.empty else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "task", "method"])


def plot_boundary_accuracy(summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True, sharey=True)
    for ax, case in zip(axes, CASE_ORDER):
        subset = summary[summary["case"] == case].copy()
        x = np.arange(len(TASK_ORDER))
        width = 0.18
        for idx, method in enumerate(METHOD_ORDER):
            method_df = subset[subset["method"] == method].set_index("task").reindex(TASK_ORDER)
            vals = method_df["mean_transfer_accuracy"].to_numpy()
            ax.bar(
                x + (idx - 1.5) * width,
                vals,
                width=width,
                color=COLORS[method],
                label=method,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(["safe", "failure"])
        ax.set_ylim(0, 1.05)
        ax.set_title(CASE_TITLES[case])
        ax.set_ylabel("Mean transfer accuracy")
        ax.grid(axis="y", alpha=0.2)
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles, labels, fontsize=8, frameon=False, loc="lower left")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_boundary_disagreement(summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True, sharey=True)
    for ax, case in zip(axes, CASE_ORDER):
        subset = summary[summary["case"] == case].copy()
        x = np.arange(len(TASK_ORDER))
        width = 0.18
        for idx, method in enumerate(METHOD_ORDER):
            method_df = subset[subset["method"] == method].set_index("task").reindex(TASK_ORDER)
            vals = method_df["point_disagreement_rate"].to_numpy()
            ax.bar(
                x + (idx - 1.5) * width,
                vals,
                width=width,
                color=COLORS[method],
                label=method,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(["safe", "failure"])
        ax.set_ylim(0, 1.05)
        ax.set_title(CASE_TITLES[case])
        ax.set_ylabel("Point disagreement rate")
        ax.grid(axis="y", alpha=0.2)
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles, labels, fontsize=8, frameon=False, loc="upper right")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def build_summary_json(
    run_summary: pd.DataFrame,
    point_summary: pd.DataFrame,
    disagreement: pd.DataFrame,
    transfer_summary: pd.DataFrame,
) -> Dict[str, object]:
    return {
        "run_summary": run_summary.to_dict(orient="records"),
        "point_summary": point_summary.to_dict(orient="records"),
        "disagreement": disagreement.to_dict(orient="records"),
        "transfer_summary": transfer_summary.to_dict(orient="records"),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    transfer_runs = load_transfer_runs()
    task_df = build_task_labels(transfer_runs)
    local_preds = apply_local_methods(task_df)
    reference_preds = apply_reference_partition(load_partition_reference())
    all_preds = merge_reference(local_preds, reference_preds)

    run_summary = summarize_runs(all_preds)
    point_summary = summarize_points(all_preds)
    disagreement = summarize_disagreement(point_summary)
    transfer_summary = summarize_transfer_means(run_summary, disagreement)

    all_preds.to_csv(OUTPUT_DIR / "local_boundary_run_predictions.csv", index=False)
    point_summary.to_csv(OUTPUT_DIR / "local_boundary_point_predictions.csv", index=False)
    run_summary.to_csv(OUTPUT_DIR / "local_boundary_run_summary.csv", index=False)
    disagreement.to_csv(OUTPUT_DIR / "local_boundary_disagreement.csv", index=False)
    transfer_summary.to_csv(OUTPUT_DIR / "local_boundary_summary.csv", index=False)

    plot_boundary_accuracy(transfer_summary, OUTPUT_DIR / "figure_31_local_boundary_accuracy.png")
    plot_boundary_disagreement(
        transfer_summary, OUTPUT_DIR / "figure_32_local_boundary_disagreement.png"
    )

    with (OUTPUT_DIR / "local_boundary_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(
            build_summary_json(run_summary, point_summary, disagreement, transfer_summary),
            fh,
            indent=2,
            ensure_ascii=False,
        )

    print("Wrote:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
