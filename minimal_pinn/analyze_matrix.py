from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for row in reader:
            rows.append(
                {
                    "matrix_name": row["matrix_name"],
                    "case": row["case"],
                    "num_observation": int(row["num_observation"]),
                    "noise_std": float(row["noise_std"]),
                    "observation_ratio": float(row["observation_ratio"]),
                    "run_name": row["run_name"],
                    "rel_l2": float(row["rel_l2"]),
                    "reliability_raw": float(row["reliability_raw"]),
                    "physics_rms": float(row["physics_rms"]),
                    "boundary_rms": float(row["boundary_rms"]),
                    "structure_error": float(row["structure_error"]),
                    "loss_std": float(row["loss_std"]),
                    "loss_ratio": float(row["loss_ratio"]),
                }
            )
    return rows


def pivot(rows: List[Dict[str, Any]], metric: str) -> Dict[str, Dict[str, float]]:
    table: Dict[str, Dict[str, float]] = {}
    for row in rows:
        noise_key = f"{row['noise_std']:.3f}"
        obs_key = f"{row['num_observation']}"
        table.setdefault(noise_key, {})[obs_key] = row[metric]
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze matrix workflow results.")
    parser.add_argument(
        "--input-csv",
        required=True,
        help="Path to matrix_summary.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save analysis outputs. Defaults next to the input CSV.",
    )
    parser.add_argument(
        "--degradation-factor",
        type=float,
        default=1.5,
        help="Boundary threshold factor relative to clean baseline rel_l2.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(input_path)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["case"]].append(row)

    analysis: Dict[str, Any] = {}
    for case_name, case_rows in grouped.items():
        max_obs = max(row["num_observation"] for row in case_rows)
        baseline = next(
            row
            for row in case_rows
            if row["num_observation"] == max_obs and abs(row["noise_std"]) < 1e-12
        )
        threshold = baseline["rel_l2"] * args.degradation_factor
        candidates = sorted(
            [
                row
                for row in case_rows
                if not (
                    row["num_observation"] == max_obs and abs(row["noise_std"]) < 1e-12
                )
                and row["rel_l2"] >= threshold
            ],
            key=lambda row: (row["noise_std"], row["num_observation"]),
        )
        ordered = sorted(case_rows, key=lambda row: (row["noise_std"], -row["num_observation"]))
        analysis[case_name] = {
            "baseline": baseline,
            "degradation_factor": args.degradation_factor,
            "threshold_rel_l2": threshold,
            "boundary_candidate": candidates[0] if candidates else None,
            "all_rows": ordered,
            "pivot_rel_l2": pivot(case_rows, "rel_l2"),
            "pivot_reliability_raw": pivot(case_rows, "reliability_raw"),
            "pivot_physics_rms": pivot(case_rows, "physics_rms"),
            "pivot_structure_error": pivot(case_rows, "structure_error"),
        }

    with (output_dir / "matrix_analysis.json").open("w", encoding="utf-8") as fh:
        json.dump(analysis, fh, ensure_ascii=False, indent=2)

    for case_name, case_data in analysis.items():
        with (output_dir / f"{case_name}_rel_l2_matrix.json").open("w", encoding="utf-8") as fh:
            json.dump(case_data["pivot_rel_l2"], fh, ensure_ascii=False, indent=2)
        with (output_dir / f"{case_name}_reliability_matrix.json").open("w", encoding="utf-8") as fh:
            json.dump(case_data["pivot_reliability_raw"], fh, ensure_ascii=False, indent=2)

    print(f"[done] analysis_dir={output_dir}")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

