from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "results" / "variant_robustness" / "variant_robustness_v2" / "point_runs.csv"
OUTPUT_DIR = ROOT / "results" / "analysis" / "few_shot_transfer_calibration_v1"

R_RELIABLE = 0.9
R_UNRELIABLE = 0.7
CASE_ORDER = ["stokes_poiseuille", "fisher_kpp", "burgers"]
CASE_TITLES = {
    "stokes_poiseuille": "Stokes-Poiseuille",
    "fisher_kpp": "Fisher-KPP",
    "burgers": "Burgers",
}
VARIANT_ORDER = ["baseline", "capacity_v1", "weight_balanced_v2"]
TRANSFER_VARIANTS = ["capacity_v1", "weight_balanced_v2"]
METHOD_ORDER = [
    "M0_raw",
    "M1_two_anchor_linear",
    "M2_three_anchor_piecewise",
    "M3_order_constrained_piecewise",
    "M4_rel2_constrained_R",
]

SEVERITY_MAP = {
    ("stokes_poiseuille", "safe_obs64_noise000"): 0,
    ("stokes_poiseuille", "critical_obs8_noise0125"): 1,
    ("stokes_poiseuille", "failure_obs8_noise0175"): 2,
    ("fisher_kpp", "safe_obs64_noise000"): 0,
    ("fisher_kpp", "edge_obs16_noise005"): 1,
    ("fisher_kpp", "transition_obs128_noise020"): 2,
    ("fisher_kpp", "failure_obs16_noise030"): 3,
    ("burgers", "safe_obs64_noise005"): 0,
    ("burgers", "transition_obs48_noise010"): 1,
    ("burgers", "seed_sensitive_obs32_noise010"): 2,
    ("burgers", "failure_obs32_noise0175"): 3,
}

ANCHORS = {
    "stokes_poiseuille": {
        "M1_two_anchor_linear": ["safe_obs64_noise000", "failure_obs8_noise0175"],
        "M2_three_anchor_piecewise": [
            "safe_obs64_noise000",
            "critical_obs8_noise0125",
            "failure_obs8_noise0175",
        ],
    },
    "fisher_kpp": {
        "M1_two_anchor_linear": ["safe_obs64_noise000", "failure_obs16_noise030"],
        "M2_three_anchor_piecewise": [
            "safe_obs64_noise000",
            "transition_obs128_noise020",
            "failure_obs16_noise030",
        ],
    },
    "burgers": {
        "M1_two_anchor_linear": ["safe_obs64_noise005", "failure_obs32_noise0175"],
        "M2_three_anchor_piecewise": [
            "safe_obs64_noise005",
            "transition_obs48_noise010",
            "failure_obs32_noise0175",
        ],
    },
}

BASELINE_R_ANCHORS = {
    "stokes_poiseuille": ["safe_obs64_noise000", "critical_obs8_noise0125", "failure_obs8_noise0175"],
    "fisher_kpp": ["safe_obs64_noise000", "transition_obs128_noise020", "failure_obs16_noise030"],
    "burgers": ["safe_obs64_noise005", "transition_obs48_noise010", "failure_obs32_noise0175"],
}


@dataclass
class MappingSpec:
    method: str
    case: str
    variant: str
    metric: str
    anchors: List[str]
    source_points: List[float]
    target_points: List[float]
    monotonic_mode: str | None = None

    def transform(self, values: Iterable[float]) -> np.ndarray:
        x = np.asarray(list(values), dtype=float)
        if self.method == "M0_raw" or len(self.source_points) == 0:
            return x.copy()
        if len(self.source_points) == 2:
            return _linear_map(
                x,
                float(self.source_points[0]),
                float(self.source_points[1]),
                float(self.target_points[0]),
                float(self.target_points[1]),
            )
        return _piecewise_map(
            x,
            np.asarray(self.source_points, dtype=float),
            np.asarray(self.target_points, dtype=float),
        )


def _linear_map(x: np.ndarray, x0: float, x1: float, y0: float, y1: float) -> np.ndarray:
    if np.isclose(x0, x1):
        return np.full_like(x, fill_value=(y0 + y1) / 2.0)
    a = (y1 - y0) / (x1 - x0)
    b = y0 - a * x0
    return a * x + b


def _piecewise_map(x: np.ndarray, source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray:
    order = np.argsort(source_points)
    xp = source_points[order]
    fp = target_points[order]
    if np.unique(xp).size != xp.size:
        # Collapse duplicates conservatively.
        unique_x = []
        unique_y = []
        for value in np.unique(xp):
            mask = xp == value
            unique_x.append(float(value))
            unique_y.append(float(fp[mask].mean()))
        xp = np.asarray(unique_x, dtype=float)
        fp = np.asarray(unique_y, dtype=float)
    if xp.size == 1:
        return np.full_like(x, fill_value=float(fp[0]))

    y = np.interp(x, xp, fp)
    left_mask = x < xp[0]
    right_mask = x > xp[-1]
    if left_mask.any():
        y[left_mask] = _linear_map(x[left_mask], xp[0], xp[1], fp[0], fp[1])
    if right_mask.any():
        y[right_mask] = _linear_map(x[right_mask], xp[-2], xp[-1], fp[-2], fp[-1])
    return y


def _isotonic_project(values: List[float], increasing: bool) -> List[float]:
    seq = [float(v) for v in values]
    if not increasing:
        seq = [-v for v in seq]

    blocks: List[Dict[str, float | int]] = []
    for value in seq:
        blocks.append({"sum": value, "count": 1, "mean": value})
        while len(blocks) >= 2 and float(blocks[-2]["mean"]) > float(blocks[-1]["mean"]):
            right = blocks.pop()
            left = blocks.pop()
            new_sum = float(left["sum"]) + float(right["sum"])
            new_count = int(left["count"]) + int(right["count"])
            blocks.append(
                {
                    "sum": new_sum,
                    "count": new_count,
                    "mean": new_sum / new_count,
                }
            )

    projected: List[float] = []
    for block in blocks:
        projected.extend([float(block["mean"])] * int(block["count"]))
    if not increasing:
        projected = [-v for v in projected]
    return projected


def r_regime(value: float) -> str:
    if value >= R_RELIABLE:
        return "reliable"
    if value >= R_UNRELIABLE:
        return "critical"
    return "unreliable"


def majority_label(series: pd.Series) -> str:
    return str(series.value_counts().idxmax())


def build_baseline_semantics(runs: pd.DataFrame) -> pd.DataFrame:
    baseline = runs[runs["variant"] == "baseline"].copy()
    baseline["baseline_rel_label"] = np.where(
        baseline["rel_l2"] >= baseline["threshold_rel_l2"], "cross", "safe"
    )
    baseline["baseline_r_label"] = baseline["reliability_raw_recal"].map(r_regime)
    semantics = (
        baseline.groupby(["case", "label"])
        .agg(
            baseline_threshold_rel_l2=("threshold_rel_l2", "first"),
            baseline_rel_label=("baseline_rel_label", majority_label),
            baseline_r_label=("baseline_r_label", majority_label),
            baseline_rel_l2_mean=("rel_l2", "mean"),
            baseline_r_mean=("reliability_raw_recal", "mean"),
        )
        .reset_index()
    )
    semantics["severity"] = [SEVERITY_MAP[(c, l)] for c, l in zip(semantics["case"], semantics["label"])]
    return semantics


def build_mapping_specs(runs: pd.DataFrame, semantics: pd.DataFrame) -> List[MappingSpec]:
    rows: List[MappingSpec] = []
    for case in CASE_ORDER:
        case_base = semantics[semantics["case"] == case].set_index("label")
        for variant in VARIANT_ORDER:
            variant_runs = runs[(runs["case"] == case) & (runs["variant"] == variant)]
            for metric in ["rel_l2", "reliability_raw_recal"]:
                rows.append(
                    MappingSpec(
                        method="M0_raw",
                        case=case,
                        variant=variant,
                        metric=metric,
                        anchors=[],
                        source_points=[],
                        target_points=[],
                    )
                )
                if variant == "baseline":
                    for method in [
                        "M1_two_anchor_linear",
                        "M2_three_anchor_piecewise",
                        "M3_order_constrained_piecewise",
                        "M4_rel2_constrained_R",
                    ]:
                        rows.append(
                            MappingSpec(
                                method=method,
                                case=case,
                                variant=variant,
                                metric=metric,
                                anchors=[],
                                source_points=[],
                                target_points=[],
                            )
                        )
                    continue
                for method in ["M1_two_anchor_linear", "M2_three_anchor_piecewise"]:
                    anchors = ANCHORS[case][method]
                    source = [
                        float(variant_runs[variant_runs["label"] == label][metric].mean())
                        for label in anchors
                    ]
                    target_metric = "baseline_rel_l2_mean" if metric == "rel_l2" else "baseline_r_mean"
                    target = [float(case_base.loc[label, target_metric]) for label in anchors]
                    rows.append(
                        MappingSpec(
                            method=method,
                            case=case,
                            variant=variant,
                            metric=metric,
                            anchors=anchors,
                            source_points=source,
                            target_points=target,
                        )
                    )
                    if method == "M2_three_anchor_piecewise":
                        increasing = metric == "rel_l2"
                        rows.append(
                            MappingSpec(
                                method="M3_order_constrained_piecewise",
                                case=case,
                                variant=variant,
                                metric=metric,
                                anchors=anchors,
                                source_points=_isotonic_project(source, increasing=increasing),
                                target_points=target,
                                monotonic_mode="increasing" if increasing else "decreasing",
                            )
                        )
                        rows.append(
                            MappingSpec(
                                method="M4_rel2_constrained_R",
                                case=case,
                                variant=variant,
                                metric=metric,
                                anchors=anchors,
                                source_points=_isotonic_project(source, increasing=increasing),
                                target_points=target,
                                monotonic_mode="increasing" if increasing else "decreasing",
                            )
                        )
    return rows


def apply_transfer(
    runs: pd.DataFrame,
    semantics: pd.DataFrame,
    mapping_specs: List[MappingSpec],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    semantics_lookup = semantics.set_index(["case", "label"])
    map_lookup = {(m.method, m.case, m.variant, m.metric): m for m in mapping_specs}
    out_rows: List[Dict[str, object]] = []
    baseline_r_anchor_map: Dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for case in CASE_ORDER:
        anchors = BASELINE_R_ANCHORS[case]
        rel_points = np.asarray(
            [float(semantics_lookup.loc[(case, label), "baseline_rel_l2_mean"]) for label in anchors],
            dtype=float,
        )
        r_points = np.asarray(
            [float(semantics_lookup.loc[(case, label), "baseline_r_mean"]) for label in anchors],
            dtype=float,
        )
        baseline_r_anchor_map[case] = (rel_points, r_points)

    for method in METHOD_ORDER:
        for case in CASE_ORDER:
            for variant in VARIANT_ORDER:
                subset = runs[(runs["case"] == case) & (runs["variant"] == variant)].copy()
                if subset.empty:
                    continue
                rel_map = map_lookup[(method, case, variant, "rel_l2")]
                r_map = map_lookup[(method, case, variant, "reliability_raw_recal")]
                subset["transferred_rel_l2"] = rel_map.transform(subset["rel_l2"].tolist())
                subset["transferred_R"] = np.clip(
                    r_map.transform(subset["reliability_raw_recal"].tolist()),
                    0.0,
                    1.0,
                )
                if method == "M4_rel2_constrained_R":
                    rel_anchor_x, rel_anchor_y = baseline_r_anchor_map[case]
                    r_from_rel = _piecewise_map(
                        subset["transferred_rel_l2"].to_numpy(dtype=float),
                        rel_anchor_x,
                        rel_anchor_y,
                    )
                    subset["transferred_R"] = np.minimum(
                        subset["transferred_R"].to_numpy(dtype=float),
                        np.clip(r_from_rel, 0.0, 1.0),
                    )
                baseline_threshold = float(semantics_lookup.loc[(case, subset["label"].iloc[0]), "baseline_threshold_rel_l2"])
                subset["pred_rel_label"] = np.where(subset["transferred_rel_l2"] >= baseline_threshold, "cross", "safe")
                subset["pred_r_label"] = subset["transferred_R"].map(r_regime)
                subset["baseline_rel_label"] = [
                    str(semantics_lookup.loc[(c, l), "baseline_rel_label"]) for c, l in zip(subset["case"], subset["label"])
                ]
                subset["baseline_r_label"] = [
                    str(semantics_lookup.loc[(c, l), "baseline_r_label"]) for c, l in zip(subset["case"], subset["label"])
                ]
                subset["severity"] = [int(semantics_lookup.loc[(c, l), "severity"]) for c, l in zip(subset["case"], subset["label"])]
                subset["is_anchor"] = subset["label"].isin(ANCHORS.get(case, {}).get(method, []))
                subset["method"] = method
                subset["rel_match"] = subset["pred_rel_label"] == subset["baseline_rel_label"]
                subset["r_match"] = subset["pred_r_label"] == subset["baseline_r_label"]
                out_rows.extend(subset.to_dict(orient="records"))

    transformed = pd.DataFrame(out_rows)

    point_summary = (
        transformed.groupby(["method", "case", "variant", "label"])
        .agg(
            n_seed=("seed", "count"),
            transferred_rel_l2_mean=("transferred_rel_l2", "mean"),
            transferred_R_mean=("transferred_R", "mean"),
            pred_rel_majority=("pred_rel_label", majority_label),
            pred_r_majority=("pred_r_label", majority_label),
            baseline_rel_label=("baseline_rel_label", "first"),
            baseline_r_label=("baseline_r_label", "first"),
            severity=("severity", "first"),
            eval_only=("is_anchor", lambda s: int((~s).all())),
        )
        .reset_index()
    )
    return transformed, point_summary


def evaluate_methods(transformed: pd.DataFrame, point_summary: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, variant), run_group in transformed.groupby(["method", "case", "variant"]):
        point_group = point_summary[
            (point_summary["method"] == method)
            & (point_summary["case"] == case)
            & (point_summary["variant"] == variant)
        ].copy()
        eval_points = point_group[point_group["eval_only"] == 1].copy()
        if eval_points.empty:
            eval_points = point_group.copy()

        rel_rho = float(point_group["severity"].corr(point_group["transferred_rel_l2_mean"], method="spearman"))
        r_rho = float(point_group["severity"].corr(-point_group["transferred_R_mean"], method="spearman"))
        rows.append(
            {
                "method": method,
                "case": case,
                "variant": variant,
                "n_run": int(len(run_group)),
                "n_point": int(len(point_group)),
                "n_eval_point": int(len(eval_points)),
                "run_rel_label_accuracy": float(run_group["rel_match"].mean()),
                "run_r_label_accuracy": float(run_group["r_match"].mean()),
                "eval_point_rel_label_accuracy": float((eval_points["pred_rel_majority"] == eval_points["baseline_rel_label"]).mean()),
                "eval_point_r_label_accuracy": float((eval_points["pred_r_majority"] == eval_points["baseline_r_label"]).mean()),
                "severity_rho_rel_l2": rel_rho,
                "severity_rho_neg_R": r_rho,
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "variant", "method"])


def build_disagreement_table(point_summary: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (method, case, label), group in point_summary.groupby(["method", "case", "label"]):
        rows.append(
            {
                "method": method,
                "case": case,
                "label": label,
                "pred_rel_unique_count": int(group["pred_rel_majority"].nunique()),
                "pred_r_unique_count": int(group["pred_r_majority"].nunique()),
                "pred_rel_disagreement": int(group["pred_rel_majority"].nunique() > 1),
                "pred_r_disagreement": int(group["pred_r_majority"].nunique() > 1),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "label", "method"])


def build_mapping_table(mapping_specs: List[MappingSpec]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for spec in mapping_specs:
        if spec.method == "M0_raw":
            continue
        rows.append(
            {
                "method": spec.method,
                "case": spec.case,
                "variant": spec.variant,
                "metric": spec.metric,
                "anchors": ",".join(spec.anchors),
                "source_points": ",".join(f"{x:.6f}" for x in spec.source_points),
                "target_points": ",".join(f"{x:.6f}" for x in spec.target_points),
            }
        )
    return pd.DataFrame(rows).sort_values(["case", "variant", "metric", "method"])


def plot_label_agreement(summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True, sharey=True)
    metrics = [
        ("eval_point_rel_label_accuracy", "rel_l2 label agreement"),
        ("eval_point_r_label_accuracy", "R label agreement"),
    ]
    colors = {
        "M0_raw": "#7a7a7a",
        "M1_two_anchor_linear": "#1f4e79",
        "M2_three_anchor_piecewise": "#2c7a5a",
        "M3_order_constrained_piecewise": "#8a5bd1",
        "M4_rel2_constrained_R": "#c07a00",
    }
    for ax, (metric, title) in zip(axes, metrics):
        plot_df = summary[summary["variant"].isin(TRANSFER_VARIANTS)].groupby(["method", "case"])[metric].mean().reset_index()
        x = np.arange(len(CASE_ORDER))
        width = 0.15
        for idx, method in enumerate(METHOD_ORDER):
            vals = [
                float(plot_df[(plot_df["method"] == method) & (plot_df["case"] == case)][metric].mean())
                for case in CASE_ORDER
            ]
            ax.bar(x + (idx - 2.0) * width, vals, width=width, label=method, color=colors[method])
        ax.set_xticks(x)
        ax.set_xticklabels([CASE_TITLES[c] for c in CASE_ORDER])
        ax.set_ylim(0.0, 1.05)
        ax.set_title(title)
        ax.set_ylabel("Accuracy")
    axes[0].legend(frameon=False, fontsize=9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_disagreement(disagreement: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True, sharey=True)
    metrics = [
        ("pred_rel_disagreement", "Cross-variant rel_l2 disagreement"),
        ("pred_r_disagreement", "Cross-variant R disagreement"),
    ]
    colors = {
        "M0_raw": "#7a7a7a",
        "M1_two_anchor_linear": "#1f4e79",
        "M2_three_anchor_piecewise": "#2c7a5a",
        "M3_order_constrained_piecewise": "#8a5bd1",
        "M4_rel2_constrained_R": "#c07a00",
    }
    for ax, (metric, title) in zip(axes, metrics):
        plot_df = disagreement.groupby(["method", "case"])[metric].mean().reset_index()
        x = np.arange(len(CASE_ORDER))
        width = 0.15
        for idx, method in enumerate(METHOD_ORDER):
            vals = [
                float(plot_df[(plot_df["method"] == method) & (plot_df["case"] == case)][metric].mean())
                for case in CASE_ORDER
            ]
            ax.bar(x + (idx - 2.0) * width, vals, width=width, label=method, color=colors[method])
        ax.set_xticks(x)
        ax.set_xticklabels([CASE_TITLES[c] for c in CASE_ORDER])
        ax.set_ylim(0.0, 1.05)
        ax.set_title(title)
        ax.set_ylabel("Fraction of labels with disagreement")
    axes[0].legend(frameon=False, fontsize=9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_ordering(summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True, sharey=True)
    metrics = [
        ("severity_rho_rel_l2", "Severity rho with transferred rel_l2"),
        ("severity_rho_neg_R", "Severity rho with -transferred R"),
    ]
    colors = {
        "M0_raw": "#7a7a7a",
        "M1_two_anchor_linear": "#1f4e79",
        "M2_three_anchor_piecewise": "#2c7a5a",
        "M3_order_constrained_piecewise": "#8a5bd1",
        "M4_rel2_constrained_R": "#c07a00",
    }
    for ax, (metric, title) in zip(axes, metrics):
        plot_df = summary[summary["variant"].isin(TRANSFER_VARIANTS)].groupby(["method", "case"])[metric].mean().reset_index()
        x = np.arange(len(CASE_ORDER))
        width = 0.15
        for idx, method in enumerate(METHOD_ORDER):
            vals = [
                float(plot_df[(plot_df["method"] == method) & (plot_df["case"] == case)][metric].mean())
                for case in CASE_ORDER
            ]
            ax.bar(x + (idx - 2.0) * width, vals, width=width, label=method, color=colors[method])
        ax.set_xticks(x)
        ax.set_xticklabels([CASE_TITLES[c] for c in CASE_ORDER])
        ax.set_ylim(0.0, 1.05)
        ax.set_title(title)
        ax.set_ylabel("Spearman rho")
    axes[0].legend(frameon=False, fontsize=9)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_summary_json(summary: pd.DataFrame, disagreement: pd.DataFrame) -> Dict[str, object]:
    out: Dict[str, object] = {"cases": {}}
    for case in CASE_ORDER:
        case_summary = summary[(summary["case"] == case) & (summary["variant"].isin(TRANSFER_VARIANTS))]
        case_dis = disagreement[disagreement["case"] == case]
        out["cases"][case] = {
            "method_summary": {},
            "disagreement_fraction": {},
        }
        for method in METHOD_ORDER:
            ms = case_summary[case_summary["method"] == method]
            ds = case_dis[case_dis["method"] == method]
            out["cases"][case]["method_summary"][method] = {
                "mean_eval_point_rel_label_accuracy": float(ms["eval_point_rel_label_accuracy"].mean()),
                "mean_eval_point_r_label_accuracy": float(ms["eval_point_r_label_accuracy"].mean()),
                "mean_severity_rho_rel_l2": float(ms["severity_rho_rel_l2"].mean()),
                "mean_severity_rho_neg_R": float(ms["severity_rho_neg_R"].mean()),
            }
            out["cases"][case]["disagreement_fraction"][method] = {
                "rel": float(ds["pred_rel_disagreement"].mean()),
                "R": float(ds["pred_r_disagreement"].mean()),
            }
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(INPUT_CSV)
    runs = runs[runs["case"].isin(CASE_ORDER)].copy()
    semantics = build_baseline_semantics(runs)
    mapping_specs = build_mapping_specs(runs, semantics)
    transformed, point_summary = apply_transfer(runs, semantics, mapping_specs)
    summary = evaluate_methods(transformed, point_summary)
    disagreement = build_disagreement_table(point_summary)
    mapping_table = build_mapping_table(mapping_specs)
    summary_json = build_summary_json(summary, disagreement)

    transformed.to_csv(OUTPUT_DIR / "transfer_run_predictions.csv", index=False)
    point_summary.to_csv(OUTPUT_DIR / "transfer_point_predictions.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "transfer_calibration_summary.csv", index=False)
    disagreement.to_csv(OUTPUT_DIR / "transfer_disagreement_summary.csv", index=False)
    mapping_table.to_csv(OUTPUT_DIR / "per_case_variant_mapping.csv", index=False)

    plot_label_agreement(summary, OUTPUT_DIR / "figure_25_transfer_label_agreement.png")
    plot_disagreement(disagreement, OUTPUT_DIR / "figure_26_transfer_disagreement_reduction.png")
    plot_ordering(summary, OUTPUT_DIR / "figure_27_transfer_ordering_rho.png")

    with (OUTPUT_DIR / "transfer_calibration_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary_json, fh, ensure_ascii=False, indent=2)

    print(f"[done] output_dir={OUTPUT_DIR}")
    print(json.dumps(summary_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
