from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path("/root/dev/pinn-reliability-paper")
RECAL_PATH = ROOT / "minimal_pinn/results/analysis/recalibrated_dimensions_v1/burgers_recalibrated_table.csv"
PROBE_PATH = ROOT / "minimal_pinn/results/probes/burgers_boundary_keypoints_v3_10seed/probe_runs_recalibrated.csv"
OUT_DIR = ROOT / "minimal_pinn/results/analysis/joint_failure_and_train_proxy_v1"

DIM_COLS = [
    "physics_consistency_recal",
    "training_stability_recal",
    "numerical_accuracy_recal",
    "structural_stability_recal",
]


def joint_failure_analysis() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(RECAL_PATH)
    sel = df[df["rel_l2"] >= df["threshold_rel_l2"]].copy()

    rows = []
    for threshold in (0.3, 0.4, 0.5):
        counts = (sel[DIM_COLS] < threshold).sum(axis=1)
        rows.append(
            {
                "rule": f"count_below_{threshold:.1f}",
                "n_selected": int(len(sel)),
                "single_low_count": int((counts == 1).sum()),
                "double_or_more_count": int((counts >= 2).sum()),
                "triple_or_more_count": int((counts >= 3).sum()),
                "double_or_more_share": float((counts >= 2).mean()),
            }
        )

    for eps in (0.03, 0.05, 0.10):
        pair_counts: dict[str, int] = {}
        joint_count = 0
        for _, row in sel.iterrows():
            ordered = sorted(((col, float(row[col])) for col in DIM_COLS), key=lambda x: x[1])
            if ordered[1][1] - ordered[0][1] <= eps:
                joint_count += 1
                names = sorted(c.replace("_recal", "") for c, _ in ordered[:2])
                pair_key = "+".join(names)
                pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
        rows.append(
            {
                "rule": f"top2_gap_le_{eps:.2f}",
                "n_selected": int(len(sel)),
                "single_low_count": None,
                "double_or_more_count": int(joint_count),
                "triple_or_more_count": None,
                "double_or_more_share": float(joint_count / len(sel)),
            }
        )
        for pair_key, count in sorted(pair_counts.items()):
            rows.append(
                {
                    "rule": f"top2_gap_le_{eps:.2f}:{pair_key}",
                    "n_selected": int(len(sel)),
                    "single_low_count": None,
                    "double_or_more_count": int(count),
                    "triple_or_more_count": None,
                    "double_or_more_share": float(count / len(sel)),
                }
            )

    summary = {
        "n_exceedance_points": int(len(sel)),
    }
    return pd.DataFrame(rows), summary


def train_proxy_analysis() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(PROBE_PATH)
    agg = (
        df.groupby("label")
        .agg(
            failure_rate=("crosses_threshold", "mean"),
            training_stability_recal_mean=("training_stability_recal", "mean"),
            training_stability_recal_std=("training_stability_recal", "std"),
            rel_l2_mean=("rel_l2", "mean"),
            reliability_raw_recal_mean=("reliability_raw_recal", "mean"),
        )
        .reset_index()
    )
    summary = {
        "n_keypoints": int(len(agg)),
        "spearman_failure_vs_training_mean": float(
            agg["failure_rate"].corr(agg["training_stability_recal_mean"], method="spearman")
        ),
        "pearson_failure_vs_training_mean": float(
            agg["failure_rate"].corr(agg["training_stability_recal_mean"], method="pearson")
        ),
    }
    return agg, summary


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    joint_df, joint_summary = joint_failure_analysis()
    proxy_df, proxy_summary = train_proxy_analysis()

    joint_df.to_csv(OUT_DIR / "joint_failure_summary.csv", index=False)
    proxy_df.to_csv(OUT_DIR / "training_proxy_summary.csv", index=False)

    summary = {
        "joint_failure": joint_summary,
        "training_proxy": proxy_summary,
    }
    (OUT_DIR / "joint_failure_and_train_proxy_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    note = ROOT / "notes/joint_failure_and_train_proxy_results.md"
    with note.open("w", encoding="utf-8") as fh:
        fh.write("# 联合失效与训练稳定性代理分析\n\n")
        fh.write(f"- 输出目录：[{OUT_DIR}]({OUT_DIR})\n\n")
        fh.write("## 1. Burgers 越界点的联合失效\n\n")
        fh.write(f"- 越界点数量：`{joint_summary['n_exceedance_points']}`\n")
        fh.write("- 以固定绝对阈值统计时，双低/多低现象存在，但并不占多数。\n")
        fh.write("- 更能体现复杂性的证据来自前两弱维度的接近性，而不是所有点同时跌破同一阈值。\n\n")
        fh.write("## 2. D_train 与 failure rate 的关系\n\n")
        fh.write(f"- keypoint 数量：`{proxy_summary['n_keypoints']}`\n")
        fh.write(
            f"- failure rate 与平均 `training_stability_recal` 的 Spearman 相关：`{proxy_summary['spearman_failure_vs_training_mean']:.3f}`\n"
        )
        fh.write(
            f"- failure rate 与平均 `training_stability_recal` 的 Pearson 相关：`{proxy_summary['pearson_failure_vs_training_mean']:.3f}`\n"
        )
        fh.write("\n")
        fh.write("这表明当前 `D_train` 与跨 seed 失败率具有明显负相关，因此可被视为 inter-run sensitivity 的一个有效代理，但二者并不等同：单次训练内部稳定性无法完全替代多 seed 概率边界分析。\n")


if __name__ == "__main__":
    main()
