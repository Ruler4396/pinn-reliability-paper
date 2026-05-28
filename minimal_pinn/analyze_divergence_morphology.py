"""
Morphology plots for R-only vs rel_l2-only divergence cases (A2).
For each case, visualizes predicted vs true solution for cells where
the 4D R and rel_l2 rankings disagree most.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from minimal_pinn.cases import build_case
from minimal_pinn.network import MLP

PROJECT = Path(__file__).resolve().parent.parent
PROB = PROJECT / "minimal_pinn" / "results" / "probability_matrices"
OUTPUT = PROJECT / "minimal_pinn" / "results" / "analysis" / "divergence_morphology_v1"

# Hand-picked divergence cells from A1 analysis
CASES = [
    {
        "name": "burgers",
        "display": "Burgers",
        "matrix": "burgers_probability_boundary_v2_5seed",
        "cells": [
            {
                "label": "R-worst (not L2-worst)",
                "run": "burgers_burgers_probability_boundary_v2_5seed_obs64_noise175_seed43",
                "obs": 64, "noise": 0.175,
            },
            {
                "label": "L2-worst (not R-worst)",
                "run": "burgers_burgers_probability_boundary_v2_5seed_obs32_noise150_seed43",
                "obs": 32, "noise": 0.150,
            },
        ],
        "output_dim": 1,
    },
    {
        "name": "fisher_kpp",
        "display": "Fisher-KPP",
        "matrix": "fisher_kpp_probability_boundary_v1",
        "cells": [
            {
                "label": "R-worst (not L2-worst)",
                "run": "fisher_kpp_fisher_kpp_probability_boundary_v1_obs32_noise200_seed43",
                "obs": 32, "noise": 0.200,
            },
            {
                "label": "L2-worst (not R-worst)",
                "run": "fisher_kpp_fisher_kpp_probability_boundary_v1_obs8_noise125_seed43",
                "obs": 8, "noise": 0.125,
            },
        ],
        "output_dim": 1,
    },
    {
        "name": "stokes_poiseuille",
        "display": "Stokes-Poiseuille",
        "matrix": "stokes_probability_boundary_v1",
        "cells": [
            {
                "label": "R-worst (not L2-worst)",
                "run": "stokes_poiseuille_stokes_probability_boundary_v1_obs16_noise150_seed43",
                "obs": 16, "noise": 0.150,
            },
            {
                "label": "L2-worst (not R-worst)",
                "run": "stokes_poiseuille_stokes_probability_boundary_v1_obs12_noise150_seed43",
                "obs": 12, "noise": 0.150,
            },
        ],
        "output_dim": 3,  # u, v, p
        "output_names": ["u (x-velocity)", "v (y-velocity)", "p (pressure)"],
    },
]


def load_model_and_config(run_name: str, matrix_name: str):
    run_dir = PROB / matrix_name / "runs" / run_name
    ckpt_path = run_dir / "best.ckpt"
    config_path = run_dir / "config.json"
    metrics_path = run_dir / "metrics.json"

    if not ckpt_path.exists():
        print(f"  WARN: no checkpoint at {ckpt_path}")
        return None, None, None

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    with open(config_path) as f:
        config = json.load(f)
    with open(metrics_path) as f:
        metrics = json.load(f)

    case = build_case(config["case"])
    model = MLP(
        input_dim=case.input_dim,
        output_dim=case.output_dim,
        hidden_layers=config["network"]["hidden_layers"],
        activation=config["network"]["activation"],
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    return model, case, metrics


def plot_comparison(model, case, metrics, cell_info, case_display, output_dim, output_names, output_path):
    """Plot true vs predicted solution for a given cell."""
    device = torch.device("cpu")

    # Evaluation grid
    num_eval = 51
    x_eval = case.sample_eval(num_eval=num_eval, device=device)
    y_true = case.truth(x_eval)

    with torch.no_grad():
        pred_raw = model(x_eval)
        y_pred = case.observable_prediction(x_eval, pred_raw)

    y_true_np = y_true.cpu().numpy()
    y_pred_np = y_pred.cpu().numpy()

    if output_dim == 1:
        # 2D field: reshape to grid
        grid_size = int(np.sqrt(len(y_true_np)))
        if grid_size * grid_size == len(y_true_np):
            true_2d = y_true_np.reshape(grid_size, grid_size)
            pred_2d = y_pred_np.reshape(grid_size, grid_size)
            diff_2d = pred_2d - true_2d

            fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), constrained_layout=True)
            titles = ["True Solution", "Predicted Solution", "Difference"]
            arrays = [true_2d, pred_2d, diff_2d]
            cmaps = ["viridis", "viridis", "RdBu_r"]

            for ax, arr, title, cmap in zip(axes, arrays, titles, cmaps):
                vmax = max(abs(arr.min()), abs(arr.max()))
                im = ax.imshow(arr.T, origin="lower", cmap=cmap, aspect="auto",
                               vmin=-vmax if cmap == "RdBu_r" else arr.min(),
                               vmax=vmax if cmap == "RdBu_r" else arr.max())
                ax.set_title(title)
                plt.colorbar(im, ax=ax, shrink=0.8)

            s = metrics["scalar_metrics"]
            fig.suptitle(
                f"{case_display} — {cell_info['label']}\n"
                f"obs={cell_info['obs']}, noise={cell_info['noise']}  |  "
                f"rel_l2={s['rel_l2']:.4f}, physics_rms={s['physics_rms']:.4f}, "
                f"structure={s['structure_error']:.4f}",
                fontsize=10,
            )
            fig.savefig(output_path, dpi=200, bbox_inches="tight")
            plt.close(fig)
        else:
            # 1D profile
            fig, ax = plt.subplots(figsize=(10, 4))
            x = np.linspace(0, 1, len(y_true_np))
            ax.plot(x, y_true_np, "k-", label="True", linewidth=2)
            ax.plot(x, y_pred_np, "r--", label="Predicted", linewidth=1.5)
            ax.legend()
            s = metrics["scalar_metrics"]
            ax.set_title(
                f"{case_display} — {cell_info['label']}\n"
                f"obs={cell_info['obs']}, noise={cell_info['noise']}  |  "
                f"rel_l2={s['rel_l2']:.4f}, physics_rms={s['physics_rms']:.4f}",
                fontsize=10,
            )
            fig.savefig(output_path, dpi=200, bbox_inches="tight")
            plt.close(fig)
    else:
        # Multi-output: plot each component
        grid_size = int(np.sqrt(len(y_true_np)))
        n_outputs = output_dim
        fig, axes = plt.subplots(3, n_outputs, figsize=(4 * n_outputs, 10), constrained_layout=True)

        for j in range(n_outputs):
            true_1d = y_true_np[:, j]
            pred_1d = y_pred_np[:, j]

            if grid_size * grid_size == len(y_true_np):
                true_2d = true_1d.reshape(grid_size, grid_size)
                pred_2d = pred_1d.reshape(grid_size, grid_size)
                diff_2d = pred_2d - true_2d

                vmax = max(abs(true_2d.max()), abs(true_2d.min())) if abs(true_2d.max()) > 0 else 1
                axes[0, j].imshow(true_2d.T, origin="lower", cmap="viridis", aspect="auto",
                                  vmin=-vmax, vmax=vmax)
                axes[0, j].set_title(f"True {output_names[j]}" if output_names else f"True comp {j}")
                axes[1, j].imshow(pred_2d.T, origin="lower", cmap="viridis", aspect="auto",
                                  vmin=-vmax, vmax=vmax)
                axes[1, j].set_title(f"Pred {output_names[j]}" if output_names else f"Pred comp {j}")
                vmax_diff = max(abs(diff_2d.min()), abs(diff_2d.max()))
                im = axes[2, j].imshow(diff_2d.T, origin="lower", cmap="RdBu_r", aspect="auto",
                                       vmin=-vmax_diff, vmax=vmax_diff)
                axes[2, j].set_title(f"Diff {output_names[j]}" if output_names else f"Diff comp {j}")
                plt.colorbar(im, ax=axes[2, j], shrink=0.8)
            else:
                # Fallback to line plot
                for ax_row in axes[:, j]:
                    ax_row.set_visible(False)

        s = metrics["scalar_metrics"]
        fig.suptitle(
            f"{case_display} — {cell_info['label']}  (obs={cell_info['obs']}, noise={cell_info['noise']})\n"
            f"rel_l2={s['rel_l2']:.4f}, phys={s['physics_rms']:.4f}, struct={s['structure_error']:.4f}, "
            f"loss_std={s['loss_std']:.6f}",
            fontsize=9,
        )
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for case_spec in CASES:
        case_name = case_spec["name"]
        case_display = case_spec["display"]
        matrix_name = case_spec["matrix"]
        output_dim = case_spec["output_dim"]
        output_names = case_spec.get("output_names", [])

        print(f"\n{case_display}:")

        for cell_info in case_spec["cells"]:
            run_name = cell_info["run"]
            print(f"  {cell_info['label']}: {run_name}")

            model, case, metrics = load_model_and_config(run_name, matrix_name)
            if model is None:
                print(f"    SKIP: no model")
                continue

            s = metrics["scalar_metrics"]
            print(f"    rel_l2={s['rel_l2']:.4f}, phys={s['physics_rms']:.4f}, "
                  f"loss_std={s['loss_std']:.6f}, struct={s['structure_error']:.4f}")

            safe_label = cell_info["label"].replace(" ", "_").replace("(", "").replace(")", "")
            output_path = OUTPUT / f"{case_name}_{safe_label}.png"
            plot_comparison(
                model, case, metrics, cell_info, case_display,
                output_dim, output_names, output_path
            )
            print(f"    Saved: {output_path}")

    print(f"\nDone. Output: {OUTPUT}")


if __name__ == "__main__":
    main()
