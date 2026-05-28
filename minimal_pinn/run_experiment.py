from __future__ import annotations

import argparse
from pathlib import Path

from .config import ensure_defaults, load_config
from .trainer import run_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal PINN experiment.")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to minimal_pinn/results/<run_name>.",
    )
    args = parser.parse_args()

    config = ensure_defaults(load_config(args.config))
    base_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else base_dir / "results" / str(config["run_name"])
    )
    metrics = run_training(config=config, output_dir=output_dir)
    print(f"[done] output_dir={output_dir}")
    print(metrics)


if __name__ == "__main__":
    main()

