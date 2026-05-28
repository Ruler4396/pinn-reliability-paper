from __future__ import annotations

from math import log10
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path("/root/dev/pinn-reliability-paper")
INPUT = ROOT / "minimal_pinn/results/matrices/coarse_v1/matrix_summary.csv"
OUT_DIR = ROOT / "minimal_pinn/results/analysis/raw_scale_cross_case_v1"
FIG = OUT_DIR / "figure_40_raw_metric_parallel_coordinates.png"
SUMMARY_CSV = OUT_DIR / "raw_metric_case_summary.csv"

RAW_METRICS = [
    "rel_l2",
    "physics_rms",
    "boundary_rms",
    "structure_error",
    "loss_std",
    "loss_ratio",
]

CASE_ORDER = ["poisson", "stokes_poiseuille", "burgers"]
CASE_LABELS = {
    "poisson": "Poisson",
    "stokes_poiseuille": "Stokes-Poiseuille",
    "burgers": "Burgers",
}
COLORS = {
    "poisson": "#4C78A8",
    "stokes_poiseuille": "#F58518",
    "burgers": "#E45756",
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT)
    df = df[df["case"].isin(CASE_ORDER)].copy()

    summary = df.groupby("case")[RAW_METRICS].agg(["median", "min", "max"]).reset_index()
    summary.columns = [
        "case" if col == ("case", "") else f"{col[0]}_{col[1]}"
        for col in summary.columns.to_flat_index()
    ]
    summary.to_csv(SUMMARY_CSV, index=False)

    # Use log10-median profiles to compare absolute raw scales across cases.
    medians = df.groupby("case")[RAW_METRICS].median().reindex(CASE_ORDER)
    log_medians = medians.copy()
    for metric in RAW_METRICS:
        log_medians[metric] = log_medians[metric].map(lambda x: log10(max(float(x), 1e-12)))

    fig, ax = plt.subplots(figsize=(11, 5.5), constrained_layout=True)
    x = range(len(RAW_METRICS))
    for case in CASE_ORDER:
        y = log_medians.loc[case, RAW_METRICS].values
        ax.plot(
            x,
            y,
            marker="o",
            linewidth=2.5,
            markersize=6,
            color=COLORS[case],
            label=CASE_LABELS[case],
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [
            r"$rel_{L2}$",
            r"$m_{phys}$",
            r"$m_{bc}$",
            r"$m_{str}$",
            r"$m_{std}$",
            r"$m_{ratio}$",
        ],
        fontsize=10,
    )
    ax.set_ylabel(r"log$_{10}$(raw metric median)")
    ax.set_title("Cross-case comparison on uncalibrated raw metric scales")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="upper right")
    fig.savefig(FIG, dpi=220)

    note = ROOT / "notes/raw_scale_cross_case_results.md"
    with note.open("w", encoding="utf-8") as fh:
        fh.write("# 未校准原始指标的跨系统对照\n\n")
        fh.write(f"- 输入：[{INPUT}]({INPUT})\n")
        fh.write(f"- 图：[{FIG}]({FIG})\n")
        fh.write(f"- 汇总：[{SUMMARY_CSV}]({SUMMARY_CSV})\n\n")
        fh.write("本分析直接在未校准的原始量纲上比较三个系统的六个基础指标中位数，用于说明案例内分位数重标定并不意味着跨系统绝对严重度被对齐。\n\n")
        for case in CASE_ORDER:
            vals = medians.loc[case, RAW_METRICS]
            fh.write(f"## {CASE_LABELS[case]}\n\n")
            for metric in RAW_METRICS:
                fh.write(f"- `{metric}` median = `{vals[metric]:.6g}`\n")
            fh.write("\n")


if __name__ == "__main__":
    main()
