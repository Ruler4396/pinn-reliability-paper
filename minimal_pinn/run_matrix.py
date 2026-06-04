from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .matrix_specs import build_run_config, load_matrix_spec
from .trainer import run_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a formal matrix workflow.")
    parser.add_argument(
        "--spec",
        required=True,
        help="Path to a matrix JSON spec.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory for matrix outputs.",
    )
    args = parser.parse_args()

    spec = load_matrix_spec(args.spec)
    base_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else base_dir / "results" / "matrices" / str(spec["matrix_name"])
    )
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    cases = spec["cases"]
    observation_counts = [int(x) for x in spec["observation_counts"]]
    noise_levels = [float(x) for x in spec["noise_levels"]]
    seeds = [int(x) for x in spec.get("seeds", [42])]
    overrides = spec.get("overrides", {})

    for case_name in cases:
        case_overrides = overrides.get(case_name, {})
        for noise_std in noise_levels:
            for num_observation in observation_counts:
                for seed in seeds:
                    run_config = build_run_config(
                        case_name=case_name,
                        num_observation=num_observation,
                        noise_std=noise_std,
                        overrides=case_overrides,
                    )
                    run_config["seed"] = seed
                    noise_pct = int(round(noise_std * 1000))
                    tag = f"obs{num_observation}_noise{noise_pct:03d}_seed{seed}"
                    run_name = f"{case_name}_{spec['matrix_name']}_{tag}"
                    run_config["run_name"] = run_name
                    case_output_dir = runs_dir / run_name
                    print(
                        f"[run] matrix={spec['matrix_name']} case={case_name} "
                        f"obs={num_observation} noise={noise_std} seed={seed}",
                        flush=True,
                    )
                    metrics = run_training(run_config, case_output_dir)
                    rows.append(
                        {
                            "matrix_name": spec["matrix_name"],
                            "case": case_name,
                            "num_observation": num_observation,
                            "noise_std": noise_std,
                            "seed": seed,
                            "observation_ratio": (
                                num_observation / max(observation_counts)
                                if observation_counts
                                else 0.0
                            ),
                            "run_name": run_name,
                            "rel_l2": metrics["scalar_metrics"]["rel_l2"],
                            "reliability_raw": metrics["reliability"]["reliability_raw"],
                            "physics_rms": metrics["scalar_metrics"]["physics_rms"],
                            "boundary_rms": metrics["scalar_metrics"]["boundary_rms"],
                            "structure_error": metrics["scalar_metrics"]["structure_error"],
                            "loss_std": metrics["scalar_metrics"]["loss_std"],
                            "loss_ratio": metrics["scalar_metrics"]["loss_ratio"],
                        }
                    )

    with (output_dir / "matrix_spec.json").open("w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    with (output_dir / "matrix_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "matrix_name",
                "case",
                "num_observation",
                "noise_std",
                "seed",
                "observation_ratio",
                "run_name",
                "rel_l2",
                "reliability_raw",
                "physics_rms",
                "boundary_rms",
                "structure_error",
                "loss_std",
                "loss_ratio",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"[done] matrix_dir={output_dir}")


if __name__ == "__main__":
    main()

