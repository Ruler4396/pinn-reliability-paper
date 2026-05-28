from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ensure_defaults
from .trainer import run_training


BASE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "poisson": {
        "case": {"name": "poisson"},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 300,
            "lr": 0.001,
            "print_every": 100,
            "weights": {"data": 10.0, "physics": 1.0, "boundary": 10.0},
        },
        "data": {
            "num_observation": 256,
            "num_collocation": 2048,
            "num_boundary": 256,
            "num_eval": 51,
            "noise_std": 0.0,
        },
    },
    "burgers": {
        "case": {"name": "burgers"},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 300,
            "lr": 0.001,
            "print_every": 100,
            "weights": {"data": 10.0, "physics": 1.0, "boundary": 10.0},
        },
        "data": {
            "num_observation": 256,
            "num_collocation": 2048,
            "num_boundary": 256,
            "num_eval": 51,
            "noise_std": 0.0,
        },
    },
    "stokes_poiseuille": {
        "case": {"name": "stokes_poiseuille"},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 300,
            "lr": 0.001,
            "print_every": 100,
            "weights": {"data": 10.0, "physics": 1.0, "boundary": 10.0},
        },
        "data": {
            "num_observation": 256,
            "num_collocation": 2048,
            "num_boundary": 256,
            "num_eval": 51,
            "noise_std": 0.0,
        },
    },
}


SWEEP_SPECS: List[Dict[str, Any]] = [
    {"case": "poisson", "tag": "baseline", "num_observation": 256, "noise_std": 0.0},
    {"case": "poisson", "tag": "s64_n10", "num_observation": 64, "noise_std": 0.10},
    {"case": "poisson", "tag": "s16_n20", "num_observation": 16, "noise_std": 0.20},
    {"case": "poisson", "tag": "s8_n20", "num_observation": 8, "noise_std": 0.20},
    {"case": "poisson", "tag": "s8_n40", "num_observation": 8, "noise_std": 0.40},
    {"case": "burgers", "tag": "baseline", "num_observation": 256, "noise_std": 0.0},
    {"case": "burgers", "tag": "s64_n10", "num_observation": 64, "noise_std": 0.10},
    {"case": "burgers", "tag": "s32_n10", "num_observation": 32, "noise_std": 0.10},
    {"case": "burgers", "tag": "s16_n20", "num_observation": 16, "noise_std": 0.20},
    {"case": "burgers", "tag": "s8_n20", "num_observation": 8, "noise_std": 0.20},
    {
        "case": "stokes_poiseuille",
        "tag": "baseline",
        "num_observation": 256,
        "noise_std": 0.0,
    },
    {
        "case": "stokes_poiseuille",
        "tag": "s64_n10",
        "num_observation": 64,
        "noise_std": 0.10,
    },
    {
        "case": "stokes_poiseuille",
        "tag": "s32_n10",
        "num_observation": 32,
        "noise_std": 0.10,
    },
    {
        "case": "stokes_poiseuille",
        "tag": "s16_n20",
        "num_observation": 16,
        "noise_std": 0.20,
    },
    {
        "case": "stokes_poiseuille",
        "tag": "s8_n20",
        "num_observation": 8,
        "noise_std": 0.20,
    },
]


def build_config(case_name: str, tag: str, num_observation: int, noise_std: float) -> Dict[str, Any]:
    config = json.loads(json.dumps(BASE_CONFIGS[case_name]))
    config["run_name"] = f"{case_name}_boundary_{tag}"
    config["data"]["num_observation"] = num_observation
    config["data"]["noise_std"] = noise_std
    return ensure_defaults(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a coarse boundary sweep.")
    parser.add_argument(
        "--cases",
        default="poisson,burgers,stokes_poiseuille",
        help="Comma-separated case names to run.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional explicit path for the sweep summary CSV.",
    )
    args = parser.parse_args()

    allowed = {item.strip() for item in args.cases.split(",") if item.strip()}
    base_dir = Path(__file__).resolve().parent
    results_dir = base_dir / "results"

    rows: List[Dict[str, Any]] = []
    for spec in SWEEP_SPECS:
        if spec["case"] not in allowed:
            continue
        config = build_config(
            case_name=str(spec["case"]),
            tag=str(spec["tag"]),
            num_observation=int(spec["num_observation"]),
            noise_std=float(spec["noise_std"]),
        )
        output_dir = results_dir / str(config["run_name"])
        print(
            f"[run] case={spec['case']} tag={spec['tag']} "
            f"obs={spec['num_observation']} noise={spec['noise_std']}",
            flush=True,
        )
        metrics = run_training(config=config, output_dir=output_dir)
        rows.append(
            {
                "case": spec["case"],
                "tag": spec["tag"],
                "num_observation": spec["num_observation"],
                "noise_std": spec["noise_std"],
                "rel_l2": metrics["scalar_metrics"]["rel_l2"],
                "reliability_raw": metrics["reliability"]["reliability_raw"],
                "physics_rms": metrics["scalar_metrics"]["physics_rms"],
                "boundary_rms": metrics["scalar_metrics"]["boundary_rms"],
                "structure_error": metrics["scalar_metrics"]["structure_error"],
            }
        )

    csv_path = (
        Path(args.output_csv)
        if args.output_csv
        else results_dir / "boundary_sweep_summary.csv"
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "case",
                "tag",
                "num_observation",
                "noise_std",
                "rel_l2",
                "reliability_raw",
                "physics_rms",
                "boundary_rms",
                "structure_error",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"[done] summary_csv={csv_path}")


if __name__ == "__main__":
    main()

