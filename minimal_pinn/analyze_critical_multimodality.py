from __future__ import annotations

import json
from itertools import combinations
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
OUTPUT_DIR = ROOT / "results" / "analysis" / "critical_multimodality_v1"

FEATURES = [
    "transferred_R",
    "transferred_rel_l2",
    "structural_stability_recal",
    "training_stability_recal",
]
PAIRWISE_FEATURES = [
    "transferred_R",
    "transferred_rel_l2",
    "structural_stability_recal",
    "training_stability_recal",
]
VARIANT_ORDER = ["baseline", "capacity_v1", "weight_balanced_v2"]
SUBTYPE_ORDER = [
    "reliable",
    "critical_transition",
    "critical_instability",
    "unreliable",
]
SUBTYPE_LABELS = {
    "safe_obs64_noise005": "reliable",
    "transition_obs48_noise010": "critical_transition",
    "seed_sensitive_obs32_noise010": "critical_instability",
    "failure_obs32_noise0175": "unreliable",
}
COLORS = {
    "reliable": "#2f7d32",
    "critical_transition": "#e6a700",
    "critical_instability": "#c05a00",
    "unreliable": "#b42318",
}
MARKERS = {
    "baseline": "o",
    "capacity_v1": "s",
    "weight_balanced_v2": "^",
}


def load_runs() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    df = df[
        (df["method"] == "M3_order_constrained_piecewise") & (df["case"] == "burgers")
    ].copy()
    df["critical_subtype"] = df["label"].map(SUBTYPE_LABELS)
    return df


def summarize_subtypes(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for variant in VARIANT_ORDER + ["all_variants"]:
        subset = df if variant == "all_variants" else df[df["variant"] == variant]
        for subtype in SUBTYPE_ORDER:
            part = subset[subset["critical_subtype"] == subtype]
            if part.empty:
                continue
            row: Dict[str, object] = {
                "variant": variant,
                "critical_subtype": subtype,
                "n_run": int(len(part)),
            }
            for feature in FEATURES:
                row[f"{feature}_mean"] = float(part[feature].mean())
                row[f"{feature}_std"] = float(part[feature].std(ddof=0))
                row[f"{feature}_min"] = float(part[feature].min())
                row[f"{feature}_max"] = float(part[feature].max())
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["variant", "critical_subtype"])


def best_threshold_accuracy(
    positive: pd.Series, negative: pd.Series, positive_high: bool
) -> Dict[str, float]:
    values = np.sort(np.unique(np.concatenate([positive.to_numpy(), negative.to_numpy()])))
    if values.size == 1:
        threshold_grid = values
    else:
        threshold_grid = np.concatenate(
            ([values[0] - 1e-9], (values[:-1] + values[1:]) / 2.0, [values[-1] + 1e-9])
        )

    y_true = np.concatenate(
        [np.ones(len(positive), dtype=int), np.zeros(len(negative), dtype=int)]
    )
    x = np.concatenate([positive.to_numpy(), negative.to_numpy()])
    best_acc = -1.0
    best_threshold = float(threshold_grid[0])
    for threshold in threshold_grid:
        y_pred = (x >= threshold).astype(int) if positive_high else (x <= threshold).astype(int)
        acc = float((y_pred == y_true).mean())
        if acc > best_acc:
            best_acc = acc
            best_threshold = float(threshold)
    return {"best_threshold": best_threshold, "best_accuracy": best_acc}


def overlap_ratio(a: pd.Series, b: pd.Series) -> float:
    lo = max(float(a.min()), float(b.min()))
    hi = min(float(a.max()), float(b.max()))
    if hi <= lo:
        return 0.0
    union_lo = min(float(a.min()), float(b.min()))
    union_hi = max(float(a.max()), float(b.max()))
    if union_hi <= union_lo:
        return 0.0
    return float((hi - lo) / (union_hi - union_lo))


def standardized_centroids(subset: pd.DataFrame) -> Dict[str, np.ndarray]:
    z = subset[PAIRWISE_FEATURES].copy()
    std = z.std(ddof=0).replace(0.0, 1.0)
    z = (z - z.mean()) / std
    out = {}
    for subtype in SUBTYPE_ORDER:
        part = z[subset["critical_subtype"] == subtype]
        if not part.empty:
            out[subtype] = part.mean().to_numpy()
    return out


def pooled_cohens_d(transition: np.ndarray, instability: np.ndarray) -> float:
    n_t = len(transition)
    n_i = len(instability)
    if n_t < 2 or n_i < 2:
        return 0.0
    var_t = float(np.var(transition, ddof=1))
    var_i = float(np.var(instability, ddof=1))
    pooled_var = ((n_t - 1) * var_t + (n_i - 1) * var_i) / max(n_t + n_i - 2, 1)
    pooled_std = float(np.sqrt(max(pooled_var, 1e-12)))
    return float((float(instability.mean()) - float(transition.mean())) / pooled_std)


def exact_mean_gap_test(transition: np.ndarray, instability: np.ndarray) -> Dict[str, float]:
    combined = np.concatenate([transition, instability])
    n_t = len(transition)
    obs_gap = float(instability.mean() - transition.mean())
    obs_abs = abs(obs_gap)
    total = 0
    extreme = 0
    for idx in combinations(range(len(combined)), n_t):
        mask = np.zeros(len(combined), dtype=bool)
        mask[list(idx)] = True
        a = combined[mask]
        b = combined[~mask]
        stat = abs(float(b.mean() - a.mean()))
        total += 1
        if stat >= obs_abs - 1e-12:
            extreme += 1
    return {
        "observed_mean_gap": obs_gap,
        "observed_abs_mean_gap": obs_abs,
        "cohens_d": pooled_cohens_d(transition, instability),
        "p_value_exact": float(extreme / total),
        "n_permutations": int(total),
    }


def exact_centroid_distance_test(transition: np.ndarray, instability: np.ndarray) -> Dict[str, float]:
    combined = np.vstack([transition, instability])
    n_t = len(transition)
    obs = float(np.linalg.norm(instability.mean(axis=0) - transition.mean(axis=0)))
    total = 0
    extreme = 0
    for idx in combinations(range(len(combined)), n_t):
        mask = np.zeros(len(combined), dtype=bool)
        mask[list(idx)] = True
        a = combined[mask]
        b = combined[~mask]
        stat = float(np.linalg.norm(b.mean(axis=0) - a.mean(axis=0)))
        total += 1
        if stat >= obs - 1e-12:
            extreme += 1
    return {
        "observed_centroid_distance": obs,
        "p_value_exact": float(extreme / total),
        "n_permutations": int(total),
    }


def build_separation_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for variant in VARIANT_ORDER + ["all_variants"]:
        subset = df if variant == "all_variants" else df[df["variant"] == variant]
        transition = subset[subset["critical_subtype"] == "critical_transition"].copy()
        instability = subset[subset["critical_subtype"] == "critical_instability"].copy()
        if transition.empty or instability.empty:
            continue

        for feature in FEATURES:
            stats = exact_mean_gap_test(
                transition[feature].to_numpy(dtype=float),
                instability[feature].to_numpy(dtype=float),
            )
            rows.append(
                {
                    "analysis_type": "exact_mean_gap",
                    "variant": variant,
                    "feature": feature,
                    "transition_mean": float(transition[feature].mean()),
                    "instability_mean": float(instability[feature].mean()),
                    **stats,
                }
            )

        critical = pd.concat([transition, instability], ignore_index=True)
        z = critical[PAIRWISE_FEATURES].copy()
        std = z.std(ddof=0).replace(0.0, 1.0)
        z = (z - z.mean()) / std
        multivar = exact_centroid_distance_test(
            z.iloc[: len(transition)].to_numpy(dtype=float),
            z.iloc[len(transition) :].to_numpy(dtype=float),
        )
        rows.append(
            {
                "analysis_type": "exact_centroid_distance",
                "variant": variant,
                "feature": "all_features_zscore",
                "transition_mean": np.nan,
                "instability_mean": np.nan,
                "observed_mean_gap": np.nan,
                "observed_abs_mean_gap": np.nan,
                "cohens_d": np.nan,
                **multivar,
            }
        )

    return pd.DataFrame(rows)


def build_overlap_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for variant in VARIANT_ORDER + ["all_variants"]:
        subset = df if variant == "all_variants" else df[df["variant"] == variant]
        transition = subset[subset["critical_subtype"] == "critical_transition"]
        instability = subset[subset["critical_subtype"] == "critical_instability"]
        if transition.empty or instability.empty:
            continue

        for feature in FEATURES:
            positive_high = float(instability[feature].mean()) >= float(transition[feature].mean())
            stats = best_threshold_accuracy(
                positive=instability[feature],
                negative=transition[feature],
                positive_high=positive_high,
            )
            rows.append(
                {
                    "analysis_type": "feature_threshold",
                    "variant": variant,
                    "feature": feature,
                    "transition_mean": float(transition[feature].mean()),
                    "instability_mean": float(instability[feature].mean()),
                    "mean_gap": float(instability[feature].mean() - transition[feature].mean()),
                    "range_overlap_ratio": overlap_ratio(transition[feature], instability[feature]),
                    "best_threshold": stats["best_threshold"],
                    "best_accuracy": stats["best_accuracy"],
                    "instability_positive_high": positive_high,
                }
            )

        centroids = standardized_centroids(subset)
        if set(["reliable", "critical_transition", "critical_instability", "unreliable"]).issubset(
            centroids
        ):
            for subtype in ["critical_transition", "critical_instability"]:
                d_rel = float(np.linalg.norm(centroids[subtype] - centroids["reliable"]))
                d_unrel = float(np.linalg.norm(centroids[subtype] - centroids["unreliable"]))
                rows.append(
                    {
                        "analysis_type": "centroid_adjacency",
                        "variant": variant,
                        "feature": "all_features_zscore",
                        "subtype": subtype,
                        "distance_to_reliable": d_rel,
                        "distance_to_unreliable": d_unrel,
                        "closer_to": "reliable" if d_rel <= d_unrel else "unreliable",
                    }
                )

    return pd.DataFrame(rows)


def plot_subtypes(df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5), constrained_layout=True)
    panels = [
        ("transferred_rel_l2", "transferred_R", "Transferred rel_l2", "Transferred R"),
        (
            "structural_stability_recal",
            "training_stability_recal",
            "Structural stability",
            "Training stability",
        ),
    ]

    for ax, (x_col, y_col, x_label, y_label) in zip(axes, panels):
        for subtype in SUBTYPE_ORDER:
            for variant in VARIANT_ORDER:
                part = df[
                    (df["critical_subtype"] == subtype) & (df["variant"] == variant)
                ]
                if part.empty:
                    continue
                ax.scatter(
                    part[x_col],
                    part[y_col],
                    label=f"{subtype} | {variant}",
                    color=COLORS[subtype],
                    marker=MARKERS[variant],
                    alpha=0.8,
                    s=54,
                    edgecolor="white",
                    linewidth=0.6,
                )
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.grid(alpha=0.2)

    handles, labels = axes[1].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    axes[1].legend(
        unique.values(),
        unique.keys(),
        fontsize=8,
        frameon=False,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
    )
    fig.suptitle("Burgers critical band is multimodal under M3 transfer")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def build_summary_json(
    subtype_summary: pd.DataFrame, overlap_summary: pd.DataFrame, separation_tests: pd.DataFrame
) -> Dict[str, object]:
    payload: Dict[str, object] = {"pooled": {}, "variants": {}}

    pooled = overlap_summary[overlap_summary["variant"] == "all_variants"]
    pooled_tests = separation_tests[separation_tests["variant"] == "all_variants"]
    payload["pooled"]["best_feature_thresholds"] = (
        pooled[pooled["analysis_type"] == "feature_threshold"]
        .sort_values("feature")
        .to_dict(orient="records")
    )
    payload["pooled"]["centroid_adjacency"] = (
        pooled[pooled["analysis_type"] == "centroid_adjacency"]
        .sort_values("subtype")
        .to_dict(orient="records")
    )
    payload["pooled"]["exact_separation_tests"] = pooled_tests.sort_values(
        ["analysis_type", "feature"]
    ).to_dict(orient="records")

    for variant in VARIANT_ORDER:
        payload["variants"][variant] = {
            "subtype_summary": subtype_summary[subtype_summary["variant"] == variant].to_dict(
                orient="records"
            ),
            "overlap_summary": overlap_summary[overlap_summary["variant"] == variant].to_dict(
                orient="records"
            ),
            "exact_separation_tests": separation_tests[
                separation_tests["variant"] == variant
            ].sort_values(["analysis_type", "feature"]).to_dict(orient="records"),
        }
    return payload


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_runs()
    subtype_summary = summarize_subtypes(df)
    overlap_summary = build_overlap_summary(df)
    separation_tests = build_separation_tests(df)
    plot_subtypes(df, OUTPUT_DIR / "figure_30_burgers_critical_subtypes.png")

    subtype_summary.to_csv(OUTPUT_DIR / "critical_subtype_summary.csv", index=False)
    overlap_summary.to_csv(OUTPUT_DIR / "critical_feature_overlap.csv", index=False)
    separation_tests.to_csv(OUTPUT_DIR / "critical_separation_tests.csv", index=False)

    summary_json = build_summary_json(subtype_summary, overlap_summary, separation_tests)
    with (OUTPUT_DIR / "critical_multimodality_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, indent=2, ensure_ascii=False)

    print("Wrote:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
