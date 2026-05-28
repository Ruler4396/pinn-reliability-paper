from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def ensure_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    config = dict(config)
    config.setdefault("seed", 42)
    config.setdefault("run_name", "unnamed_run")
    config.setdefault("network", {})
    config.setdefault("training", {})
    config.setdefault("data", {})
    config.setdefault("reliability", {})

    config["network"].setdefault("hidden_layers", [64, 64, 64])
    config["network"].setdefault("activation", "tanh")

    config["training"].setdefault("epochs", 500)
    config["training"].setdefault("lr", 1e-3)
    config["training"].setdefault("print_every", 50)
    config["training"].setdefault(
        "weights",
        {"data": 1.0, "physics": 1.0, "boundary": 1.0},
    )
    config["training"].setdefault("adaptive_sampling", {})
    config["training"]["adaptive_sampling"].setdefault("enabled", False)
    config["training"]["adaptive_sampling"].setdefault("method", "rar_topk_v1")
    config["training"]["adaptive_sampling"].setdefault("warmup_epochs", 100)
    config["training"]["adaptive_sampling"].setdefault("refresh_every", 50)
    config["training"]["adaptive_sampling"].setdefault("candidate_factor", 4.0)
    config["training"]["adaptive_sampling"].setdefault("replace_ratio", 0.25)
    config["training"].setdefault("adaptive_weighting", {})
    config["training"]["adaptive_weighting"].setdefault("enabled", False)
    config["training"]["adaptive_weighting"].setdefault("method", "uncertainty_v1")
    config["training"]["adaptive_weighting"].setdefault("lr", 1e-2)
    config["training"]["adaptive_weighting"].setdefault("warmup_epochs", 0)
    config["training"]["adaptive_weighting"].setdefault("regularizer_scale", 1.0)
    config["training"]["adaptive_weighting"].setdefault("clamp_min", -4.0)
    config["training"]["adaptive_weighting"].setdefault("clamp_max", 4.0)
    config["training"]["adaptive_weighting"].setdefault(
        "log_var_init",
        {"data": 0.0, "physics": 0.0, "boundary": 0.0},
    )

    config["data"].setdefault("num_observation", 128)
    config["data"].setdefault("num_collocation", 512)
    config["data"].setdefault("num_boundary", 128)
    config["data"].setdefault("num_eval", 41)
    config["data"].setdefault("noise_std", 0.0)

    config["reliability"].setdefault(
        "thresholds",
        {
            "physics_rms": {"good": 1e-3, "fail": 1e-1, "mode": "smaller_better"},
            "boundary_rms": {"good": 1e-3, "fail": 1e-1, "mode": "smaller_better"},
            "rel_l2": {"good": 1e-2, "fail": 2e-1, "mode": "smaller_better"},
            "structure_error": {
                "good": 1e-2,
                "fail": 2e-1,
                "mode": "smaller_better",
            },
            "loss_std": {"good": 1e-4, "fail": 1e-2, "mode": "smaller_better"},
            "loss_ratio": {"good": 0.1, "fail": 0.9, "mode": "smaller_better"},
        },
    )
    return config
