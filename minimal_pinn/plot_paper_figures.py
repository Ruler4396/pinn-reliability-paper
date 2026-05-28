from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import ListedColormap

from .cases import build_case
from .config import ensure_defaults
from .network import MLP


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
FIG_DIR = RESULTS_DIR / "paper_figures" / "v1"


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_matrix_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def plot_phase_maps(df: pd.DataFrame, metric: str, cases: Iterable[str], output_path: Path) -> None:
    case_titles = {
        "poisson": "Poisson",
        "burgers": "Burgers",
        "stokes_poiseuille": "Stokes-Poiseuille",
    }
    value_tables = []
    for case_name in cases:
        case_df = df[df["case"] == case_name].copy()
        pivot = (
            case_df.pivot(index="noise_std", columns="num_observation", values=metric)
            .sort_index()
            .sort_index(axis=1)
        )
        value_tables.append(pivot)

    vmin = min(float(table.min().min()) for table in value_tables)
    vmax = max(float(table.max().max()) for table in value_tables)

    fig, axes = plt.subplots(1, len(value_tables), figsize=(13, 4.2), constrained_layout=True)
    axes = np.atleast_1d(axes)

    im = None
    for ax, case_name, table in zip(axes, cases, value_tables):
        im = ax.imshow(
            table.values,
            origin="lower",
            aspect="auto",
            vmin=vmin,
            vmax=vmax,
            cmap="viridis",
        )
        ax.set_title(case_titles[case_name])
        ax.set_xlabel("Observation Count")
        ax.set_ylabel("Noise Std")
        ax.set_xticks(range(len(table.columns)))
        ax.set_xticklabels([str(int(col)) for col in table.columns], rotation=45, ha="right")
        ax.set_yticks(range(len(table.index)))
        ax.set_yticklabels([f"{val:.3f}" for val in table.index])

    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.9)
        cbar.set_label(metric)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _build_regime_matrix(analysis: Dict) -> pd.DataFrame:
    baseline = float(analysis["baseline"]["rel_l2"])
    threshold = float(analysis["threshold_rel_l2"])
    reliable_cutoff = baseline * 1.2

    pivot = pd.DataFrame(analysis["pivot_rel_l2"]).T
    pivot.index = pivot.index.astype(float)
    pivot.columns = pivot.columns.astype(int)
    pivot = pivot.sort_index().sort_index(axis=1)

    regime = pd.DataFrame(index=pivot.index, columns=pivot.columns, dtype=int)
    regime[pivot <= reliable_cutoff] = 0
    regime[(pivot > reliable_cutoff) & (pivot < threshold)] = 1
    regime[pivot >= threshold] = 2
    return regime


def plot_regime_maps(burgers_analysis: Dict, stokes_analysis: Dict, output_path: Path) -> None:
    regime_tables = [
        ("Burgers", _build_regime_matrix(burgers_analysis)),
        ("Stokes-Poiseuille", _build_regime_matrix(stokes_analysis)),
    ]
    cmap = ListedColormap(["#2c7a5a", "#d8a529", "#b64040"])

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
    for ax, (title, table) in zip(axes, regime_tables):
        ax.imshow(table.values, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=2)
        ax.set_title(title)
        ax.set_xlabel("Observation Count")
        ax.set_ylabel("Noise Std")
        ax.set_xticks(range(len(table.columns)))
        ax.set_xticklabels([str(int(col)) for col in table.columns], rotation=45, ha="right")
        ax.set_yticks(range(len(table.index)))
        ax.set_yticklabels([f"{val:.3f}" for val in table.index])

    handles = [
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#2c7a5a", markersize=12, label="Reliable"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#d8a529", markersize=12, label="Critical"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#b64040", markersize=12, label="Unreliable"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_multiseed_boxplot(probe_runs_csv: Path, threshold_rel_l2: float, output_path: Path) -> None:
    df = pd.read_csv(probe_runs_csv)
    order = list(df["label"].drop_duplicates())
    grouped = [df[df["label"] == label]["rel_l2"].values for label in order]

    fig, ax = plt.subplots(figsize=(11, 4.8), constrained_layout=True)
    ax.boxplot(grouped, tick_labels=order, patch_artist=True)
    for idx, label in enumerate(order, start=1):
        y = df[df["label"] == label]["rel_l2"].values
        x = np.linspace(idx - 0.18, idx + 0.18, num=len(y))
        ax.scatter(x, y, color="#1f4e79", s=26, zorder=3)
    ax.axhline(threshold_rel_l2, color="#b64040", linestyle="--", linewidth=1.3, label="Boundary Threshold")
    ax.set_ylabel("rel_l2")
    ax.set_title("Burgers multi-seed reproducibility at selected anomalous grid points")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _load_model(run_dir: Path):
    config = ensure_defaults(load_json(run_dir / "config.json"))
    case = build_case(config["case"]["name"])
    model = MLP(
        input_dim=case.input_dim,
        output_dim=case.output_dim,
        hidden_layers=config["network"]["hidden_layers"],
        activation=config["network"]["activation"],
    )
    checkpoint = torch.load(run_dir / "best.ckpt", map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, case, config


def _find_run_dir(case_name: str, matrix_dir: Path, num_observation: int, noise_std: float) -> Path:
    summary = pd.read_csv(matrix_dir / "matrix_summary.csv")
    row = summary[
        (summary["case"] == case_name)
        & (summary["num_observation"] == num_observation)
        & (np.isclose(summary["noise_std"], noise_std))
    ]
    if row.empty:
        raise ValueError(f"Run not found for {case_name} obs={num_observation} noise={noise_std}")
    run_name = row.iloc[0]["run_name"]
    return matrix_dir / "runs" / run_name


def _predict_grid(run_dir: Path, field_index: int = 0):
    model, case, config = _load_model(run_dir)
    num_eval = int(config["data"]["num_eval"])
    x_eval = case.sample_eval(num_eval=num_eval, device=torch.device("cpu"))
    with torch.no_grad():
        pred = model(x_eval).cpu().numpy()
        truth = case.truth(x_eval).cpu().numpy()
    coords = x_eval.cpu().numpy()
    shape = (num_eval, num_eval)
    coord0 = coords[:, 0].reshape(shape)
    coord1 = coords[:, 1].reshape(shape)
    field_truth = truth[:, field_index].reshape(shape)
    field_pred = pred[:, field_index].reshape(shape)
    field_err = np.abs(field_pred - field_truth)
    return coord0, coord1, field_truth, field_pred, field_err


def plot_representative_fields(output_path: Path) -> None:
    selections = [
        (
            "Burgers",
            ROOT / "results" / "matrices" / "refine_burgers_v1",
            "burgers",
            [
                ("Reliable", 128, 0.0),
                ("Critical", 40, 0.125),
                ("Unreliable", 32, 0.175),
            ],
        ),
        (
            "Stokes u-field",
            ROOT / "results" / "matrices" / "refine_stokes_v1",
            "stokes_poiseuille",
            [
                ("Reliable", 64, 0.0),
                ("Critical", 8, 0.125),
                ("Unreliable", 8, 0.2),
            ],
        ),
    ]

    fig, axes = plt.subplots(6, 3, figsize=(12, 13), constrained_layout=True)
    for block_idx, (case_title, matrix_dir, case_name, cases) in enumerate(selections):
        for col_idx, (label, obs, noise) in enumerate(cases):
            run_dir = _find_run_dir(case_name, matrix_dir, obs, noise)
            _, _, truth, pred, err = _predict_grid(run_dir, field_index=0)
            row_offset = block_idx * 3
            images = [truth, pred, err]
            row_titles = ["Truth", "Prediction", "Abs Error"]
            cmaps = ["viridis", "viridis", "magma"]
            for local_row, (image, row_title, cmap) in enumerate(zip(images, row_titles, cmaps)):
                ax = axes[row_offset + local_row, col_idx]
                im = ax.imshow(image.T, origin="lower", aspect="auto", cmap=cmap)
                if local_row == 0:
                    ax.set_title(f"{case_title}\n{label}\nobs={obs}, noise={noise:.3f}")
                if col_idx == 0:
                    ax.set_ylabel(row_title)
                ax.set_xticks([])
                ax.set_yticks([])
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_recalibrated_dimension_maps(case_name: str, table_csv: Path, output_path: Path) -> None:
    case_titles = {
        "burgers": "Burgers",
        "stokes_poiseuille": "Stokes-Poiseuille",
    }
    dim_specs = [
        ("physics_consistency_recal", "Physics"),
        ("training_stability_recal", "Training"),
        ("numerical_accuracy_recal", "Numerical"),
        ("structural_stability_recal", "Structural"),
    ]
    df = pd.read_csv(table_csv)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.6), constrained_layout=True)
    axes = axes.flatten()
    for ax, (col, title) in zip(axes, dim_specs):
        table = (
            df.pivot(index="noise_std", columns="num_observation", values=col)
            .sort_index()
            .sort_index(axis=1)
        )
        im = ax.imshow(
            table.values,
            origin="lower",
            aspect="auto",
            vmin=0.0,
            vmax=1.0,
            cmap="viridis",
        )
        ax.set_title(title)
        ax.set_xlabel("Observation Count")
        ax.set_ylabel("Noise Std")
        ax.set_xticks(range(len(table.columns)))
        ax.set_xticklabels([str(int(col_name)) for col_name in table.columns], rotation=45, ha="right")
        ax.set_yticks(range(len(table.index)))
        ax.set_yticklabels([f"{val:.3f}" for val in table.index])
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle(f"{case_titles[case_name]} recalibrated dimension-score maps", fontsize=13)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    coarse_df = load_matrix_csv(RESULTS_DIR / "matrices" / "coarse_v1" / "matrix_summary.csv")
    coarse_cases = ["poisson", "burgers", "stokes_poiseuille"]
    plot_phase_maps(
        df=coarse_df,
        metric="rel_l2",
        cases=coarse_cases,
        output_path=FIG_DIR / "figure_01_rel_l2_phase_maps.png",
    )
    plot_phase_maps(
        df=coarse_df,
        metric="reliability_raw",
        cases=coarse_cases,
        output_path=FIG_DIR / "figure_02_reliability_phase_maps.png",
    )

    burgers_analysis = load_json(RESULTS_DIR / "matrices" / "refine_burgers_v1" / "analysis" / "matrix_analysis.json")["burgers"]
    stokes_analysis = load_json(RESULTS_DIR / "matrices" / "refine_stokes_v1" / "analysis" / "matrix_analysis.json")["stokes_poiseuille"]
    plot_regime_maps(
        burgers_analysis=burgers_analysis,
        stokes_analysis=stokes_analysis,
        output_path=FIG_DIR / "figure_03_regime_maps.png",
    )

    probe_summary = load_json(RESULTS_DIR / "probes" / "burgers_multiseed_anomaly_v1" / "probe_summary.json")
    plot_multiseed_boxplot(
        probe_runs_csv=RESULTS_DIR / "probes" / "burgers_multiseed_anomaly_v1" / "probe_runs.csv",
        threshold_rel_l2=float(probe_summary["threshold_rel_l2"]),
        output_path=FIG_DIR / "figure_04_burgers_multiseed_boxplot.png",
    )

    plot_representative_fields(output_path=FIG_DIR / "figure_05_representative_fields.png")
    plot_recalibrated_dimension_maps(
        case_name="burgers",
        table_csv=RESULTS_DIR / "analysis" / "recalibrated_dimensions_v1" / "burgers_recalibrated_table.csv",
        output_path=FIG_DIR / "figure_10_burgers_recalibrated_dimension_maps.png",
    )
    plot_recalibrated_dimension_maps(
        case_name="stokes_poiseuille",
        table_csv=RESULTS_DIR / "analysis" / "recalibrated_dimensions_v1" / "stokes_poiseuille_recalibrated_table.csv",
        output_path=FIG_DIR / "figure_11_stokes_recalibrated_dimension_maps.png",
    )
    print(f"[done] figure_dir={FIG_DIR}")


if __name__ == "__main__":
    main()
