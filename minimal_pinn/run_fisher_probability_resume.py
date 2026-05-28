"""
Quick wrapper to run the Stokes probability boundary matrix with resume support.
Skips runs that already have output directories.
"""

import sys
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

def main():
    sys.path.insert(0, str(PROJECT_DIR))
    from minimal_pinn.run_multiseed_boundary_matrix import (
        load_matrix_spec, build_run_config, make_tag, load_case_thresholds,
    )
    from minimal_pinn.reliability import build_reliability_summary
    from minimal_pinn.trainer import run_training
    
    import csv
    
    spec_path = PROJECT_DIR / "minimal_pinn" / "configs" / "fisher_kpp_probability_boundary_v1.json"
    spec = load_matrix_spec(spec_path)
    
    base_dir = PROJECT_DIR / "minimal_pinn"
    output_dir = base_dir / "results" / "probability_matrices" / str(spec["matrix_name"])
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    
    case_name = str(spec["case"])
    observation_counts = [int(v) for v in spec["observation_counts"]]
    noise_levels = [float(v) for v in spec["noise_levels"]]
    seeds = [int(v) for v in spec["seeds"]]
    overrides = spec.get("overrides", {})
    threshold_rel_l2 = float(spec["threshold_rel_l2"])
    recalibration_path = spec["recalibration_path"]
    thresholds = load_case_thresholds(recalibration_path, case_name)
    
    total = len(noise_levels) * len(observation_counts) * len(seeds)
    done = 0
    skipped = 0
    
    for noise_std in noise_levels:
        for num_observation in observation_counts:
            for seed in seeds:
                config = build_run_config(
                    case_name=case_name,
                    num_observation=num_observation,
                    noise_std=noise_std,
                    overrides=overrides,
                )
                config["seed"] = seed
                run_name = f"{case_name}_{spec['matrix_name']}_{make_tag(num_observation, noise_std, seed)}"
                config["run_name"] = run_name
                
                run_dir = runs_dir / run_name
                if (run_dir / "metrics.json").exists():
                    skipped += 1
                    continue
                
                print(
                    f"[run {done+skipped+1}/{total}] matrix={spec['matrix_name']} case={case_name} "
                    f"obs={num_observation} noise={noise_std} seed={seed}",
                    flush=True,
                )
                run_training(config=config, output_dir=run_dir)
                done += 1
    
    if done > 0:
        print(f"\nCompleted {done} new runs ({skipped} already existed).")
        print(f"Output: {output_dir}")
    else:
        print(f"\nAll {skipped} runs already exist. Nothing to do.")
        print(f"Output: {output_dir}")

if __name__ == "__main__":
    main()
