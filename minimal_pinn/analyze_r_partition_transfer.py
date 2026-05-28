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
INPUT_CSV = (
    ROOT
    / "results"
    / "analysis"
    / "few_shot_transfer_calibration_v1"
    / "transfer_run_predictions.csv"
)
OUTPUT_DIR = ROOT / "results" / "analysis" / "r_partition_transfer_v1"

CASE_ORDER = ["stokes_poiseuille", "burgers"]
CASE_TITLES = {
    "stokes_poiseuille": "Stokes-Poiseuille",
    "burgers": "Burgers",
}
VARIANT_ORDER = ["baseline", "capacity_v1", "weight_balanced_v2"]
TRANSFER_VARIANTS = ["capacity_v1", "weight_balanced_v2"]
METHOD_ORDER = ["P0_fixed_cutoffs", "P1_anchor_mean_midpoint", "P2_anchor_median_midpoint"]
CLASS_ORDER = ["reliable", "critical", "unreliable"]
CLASS_SCORE = {"reliable": 0, "critical": 1, "unreliable": 2}

ANCHOR_LABELS = {
    "stokes_poiseuille": {
        "reliable": "safe_obs64_noise000",
        "critical": "critical_obs8_noise0125",
        "unreliable": "failure_obs8_noise0175",
    },
    "burgers": {
        "reliable": "safe_obs64_noise005",
        "critical": "transition_obs48_noise010",
        "unreliable": "failure_obs32_noise0175",
    },
}

TARGET_LABELS = {
    "stokes_poiseuille": {
        "safe_obs64_noise000": "reliable",
        "critical_obs8_noise0125": "critical",
        "failure_obs8_noise0175": "unreliable",
    },
    "burgers": {
        "safe_obs64_noise005": "reliable",
        "transition_obs48_noise010": "critical",
        "seed_sensitive_obs32_noise010": "critical",
        "failure_obs32_noise0175": "unreliable",
    },
}


def isotonic_decreasing(values: List[float]) -> List[float]:
    seq = [-float(v) for v in values]
    blocks: List[Dict[str, float | int]] = []
    for value in seq:
        blocks.append({"sum": value, "count": 1, "mean": value})
        while len(blocks) >= 2 and float(blocks[-2]["mean"]) > float(blocks[-1]["mean"]):
            right = blocks.pop()
            left = blocks.pop()
            total = float(left["sum"]) + float(right["sum"])
            count = int(left["count"]) + int(right["count"])
            blocks.append({"sum": total, "count": count, "mean": total / count})
    out: List[float] = []
    for block in blocks:
        out.extend([-float(block["mean"])] * int(block["count"]))
    return out


def classify_r(value: float, tau_high: float, tau_low: float) -> str:
    if value >= tau_high:
        return "reliable"
    if value >= tau_low:
        return "critical"
    return "unreliable"


def compute_macro_f1(y_true: List[str], y_pred: List[str]) -> float:
    per_class = []
    for cls in CLASS_ORDER:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp == cls)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != cls and yp == cls)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp != cls)
        precision = tp / (tp + fp) if tp + fp > 0 else 0.0
        recall = tp / (tp + fn) if tp + fn > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
        per_class.append(f1)
    return float(sum(per_class) / len(per_class))


def majority_label(series: pd.Series) -> str:
    return str(series.value_counts().idxmax())


def load_runs() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    df = df[(df["method"] == "M3_order_constrained_piecewise") & (df["case"].isin(CASE_ORDER))].copy()
    df["target_partition_label"] = [TARGET_LABELS[c][l] for c, l in zip(df["case"], df["label"])]
    return df


def build_cutpoints(runs: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for case in CASE_ORDER:
        for variant in VARIANT_ORDER:
            subset = runs[(runs["case"] == case) & (runs["variant"] == variant)]
            if subset.empty:
                continue

            rows.append(
                {
                    "method": "P0_fixed_cutoffs",
                    "case": case,
                    "variant": variant,
                    "tau_high": 0.9,
                    "tau_low": 0.7,
                    "anchor_reliable": np.nan,
                    "anchor_critical": np.nan,
                    "anchor_unreliable": np.nan,
                }
            )

            anchor_map = ANCHOR_LABELS[case]
            anchor_series = {}
            for cls, label in anchor_map.items():
                vals = subset.loc[subset["label"] == label, "transferred_R"].astype(float)
                anchor_series[cls] = vals

            mean_locs = [
                float(anchor_series["reliable"].mean()),
                float(anchor_series["critical"].mean()),
                float(anchor_series["unreliable"].mean()),
            ]
            mean_locs = isotonic_decreasing(mean_locs)
            rows.append(
                {
                    "method": "P1_anchor_mean_midpoint",
                    "case": case,
                    "variant": variant,
                    "tau_high": float((mean_locs[0] + mean_locs[1]) / 2.0),
                    "tau_low": float((mean_locs[1] + mean_locs[2]) / 2.0),
                    "anchor_reliable": mean_locs[0],
                    "anchor_critical": mean_locs[1],
                    "anchor_unreliable": mean_locs[2],
                }
            )

            median_locs = [
                float(anchor_series["reliable"].median()),
                float(anchor_series["critical"].median()),
                float(anchor_series["unreliable"].median()),
            ]
            median_locs = isotonic_decreasing(median_locs)
            rows.append(
                {
                    "method": "P2_anchor_median_midpoint",
                    "case": case,
                    "variant": variant,
                    "tau_high": float((median_locs[0] + median_locs[1]) / 2.0),
                    "tau_low": float((median_locs[1] + median_locs[2]) / 2.0),
                    "anchor_reliable": median_locs[0],
                    "anchor_critical": median_locs[1],
                    "anchor_unreliable": median_locs[2],
                }
            )

    return pd.DataFrame(rows).sort_values(["case", "variant", "method"])


def apply_partition_transfer(runs: pd.DataFrame, cutpoints: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    cp_lookup = {
        (r["method"], r["case"], r["variant"]): (float(r["tau_high"]), float(r["tau_low"]))
        for _, r in cutpoints.iterrows()
    }
    for method in METHOD_ORDER:
        for case in CASE_ORDER:
            for variant in VARIANT_ORDER:
                subset = runs[(runs["case"] == case) & (runs["variant"] == variant)].copy()
                if subset.empty:
                    continue
                tau_high, tau_low = cp_lookup[(method, case, variant)]
                subset["partition_method"] = method
                subset["tau_high"] = tau_high
                subset["tau_low"] = tau_low
                subset["pred_partition_label"] = [
                    classify_r(float(v), tau_high=tau_high, tau_low=tau_low)
                    for v in subset["transferred_R"]
                ]
                subset["partition_match"] = subset["pred_partition_label"] == subset["target_partition_label"]
                rows.extend(subset.to_dict(orient="records"))
    return pd.DataFrame(rows)


def summarize_partition_runs(partition_runs: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, variant), group in partition_runs.groupby(["partition_method", "case", "variant"]):
        y_true = group["target_partition_label"].tolist()
        y_pred = group["pred_partition_label"].tolist()
        rows.append(
            {
                "method": method,
                "case": case,
                "variant": variant,
                "run_accuracy": float(group["partition_match"].mean()),
                "macro_f1": compute_macro_f1(y_true, y_pred),
                "tau_high": float(group["tau_high"].iloc[0]),
                "tau_low": float(group["tau_low"].iloc[0]),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "variant", "method"])


def summarize_partition_points(partition_runs: pd.DataFrame) -> pd.DataFrame:
    out = (
        partition_runs.groupby(["partition_method", "case", "variant", "label"])
        .agg(
            n_seed=("seed", "count"),
            transferred_R_mean=("transferred_R", "mean"),
            pred_partition_majority=("pred_partition_label", majority_label),
            target_partition_label=("target_partition_label", "first"),
            severity=("severity", "first"),
        )
        .reset_index()
        .rename(columns={"partition_method": "method"})
    )
    out["point_accuracy"] = out["pred_partition_majority"] == out["target_partition_label"]
    return out.sort_values(["case", "variant", "method", "label"])


def summarize_disagreement(point_summary: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, label), group in point_summary.groupby(["method", "case", "label"]):
        rows.append(
            {
                "method": method,
                "case": case,
                "label": label,
                "pred_partition_unique_count": int(group["pred_partition_majority"].nunique()),
                "pred_partition_disagreement": int(group["pred_partition_majority"].nunique() > 1),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "label", "method"])


def plot_accuracy(summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True, sharey=True)
    metrics = [("run_accuracy", "Run accuracy"), ("macro_f1", "Macro F1")]
    colors = {
        "P0_fixed_cutoffs": "#7a7a7a",
        "P1_anchor_mean_midpoint": "#1f4e79",
        "P2_anchor_median_midpoint": "#2c7a5a",
    }
    for ax, (metric, title) in zip(axes, metrics):
        plot_df = summary[summary["variant"].isin(TRANSFER_VARIANTS)].groupby(["method", "case"])[metric].mean().reset_index()
        x = np.arange(len(CASE_ORDER))
        width = 0.22
        for idx, method in enumerate(METHOD_ORDER):
            vals = [
                float(plot_df[(plot_df["method"] == method) & (plot_df["case"] == case)][metric].mean())
                for case in CASE_ORDER
            ]
            ax.bar(x + (idx - 1) * width, vals, width=width, label=method, color=colors[method])
        ax.set_xticks(x)
        ax.set_xticklabels([CASE_TITLES[c] for c in CASE_ORDER])
        ax.set_ylim(0.0, 1.05)
        ax.set_title(title)
        ax.set_ylabel("Score")
    axes[0].legend(frameon=False, fontsize=9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_disagreement(disagreement: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.2), constrained_layout=True)
    plot_df = disagreement.groupby(["method", "case"])["pred_partition_disagreement"].mean().reset_index()
    x = np.arange(len(CASE_ORDER))
    width = 0.22
    colors = {
        "P0_fixed_cutoffs": "#7a7a7a",
        "P1_anchor_mean_midpoint": "#1f4e79",
        "P2_anchor_median_midpoint": "#2c7a5a",
    }
    for idx, method in enumerate(METHOD_ORDER):
        vals = [
            float(plot_df[(plot_df["method"] == method) & (plot_df["case"] == case)]["pred_partition_disagreement"].mean())
            for case in CASE_ORDER
        ]
        ax.bar(x + (idx - 1) * width, vals, width=width, label=method, color=colors[method])
    ax.set_xticks(x)
    ax.set_xticklabels([CASE_TITLES[c] for c in CASE_ORDER])
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Fraction of labels with disagreement")
    ax.set_title("Cross-variant partition disagreement")
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_summary_json(summary: pd.DataFrame, disagreement: pd.DataFrame) -> Dict[str, object]:
    out: Dict[str, object] = {"cases": {}}
    for case in CASE_ORDER:
        case_summary = summary[(summary["case"] == case) & (summary["variant"].isin(TRANSFER_VARIANTS))]
        case_dis = disagreement[disagreement["case"] == case]
        out["cases"][case] = {"methods": {}}
        for method in METHOD_ORDER:
            ms = case_summary[case_summary["method"] == method]
            ds = case_dis[case_dis["method"] == method]
            out["cases"][case]["methods"][method] = {
                "mean_run_accuracy": float(ms["run_accuracy"].mean()),
                "mean_macro_f1": float(ms["macro_f1"].mean()),
                "mean_partition_disagreement": float(ds["pred_partition_disagreement"].mean()),
            }
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    cutpoints = build_cutpoints(runs)
    partition_runs = apply_partition_transfer(runs, cutpoints)
    summary = summarize_partition_runs(partition_runs)
    point_summary = summarize_partition_points(partition_runs)
    disagreement = summarize_disagreement(point_summary)
    summary_json = build_summary_json(summary, disagreement)

    cutpoints.to_csv(OUTPUT_DIR / "per_case_variant_cutpoints.csv", index=False)
    partition_runs.to_csv(OUTPUT_DIR / "partition_run_predictions.csv", index=False)
    point_summary.to_csv(OUTPUT_DIR / "partition_point_predictions.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "r_partition_transfer_summary.csv", index=False)
    disagreement.to_csv(OUTPUT_DIR / "r_partition_disagreement_summary.csv", index=False)

    plot_accuracy(summary, OUTPUT_DIR / "figure_28_r_partition_accuracy.png")
    plot_disagreement(disagreement, OUTPUT_DIR / "figure_29_r_partition_disagreement.png")

    with (OUTPUT_DIR / "r_partition_transfer_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
