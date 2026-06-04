from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .config import ensure_defaults


BASE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "poisson": {
        "case": {"name": "poisson"},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
    "fisher_kpp": {
        "case": {"name": "fisher_kpp"},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
            "epochs": 500,
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
    "helmholtz": {
        "case": {"name": "helmholtz", "mode": 3},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
    "advection_diffusion": {
        "case": {"name": "advection_diffusion", "nu": 0.02, "beta_x": 4.0, "beta_y": 2.0},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
    "variable_coefficient_diffusion": {
        "case": {"name": "variable_coefficient_diffusion", "coeff_amp": 0.35},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
            "epochs": 500,
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
    "lid_driven_cavity": {
        "case": {"name": "lid_driven_cavity"},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
            "lr": 0.001,
            "print_every": 100,
            "weights": {"data": 10.0, "physics": 1.0, "boundary": 10.0},
        },
        "data": {
            "num_observation": 256,
            "num_collocation": 2048,
            "num_boundary": 256,
            "num_eval": 41,
            "noise_std": 0.0,
        },
    },
    "heat_equation": {
        "case": {"name": "heat_equation", "nu": 0.1},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
    "allen_cahn": {
        "case": {"name": "allen_cahn", "eps": 0.1},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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
    "allen_cahn_circular": {
        "case": {"name": "allen_cahn_circular", "eps": 0.1, "radius": 0.3},
        "seed": 42,
        "network": {"hidden_layers": [64, 64, 64], "activation": "tanh"},
        "training": {
            "epochs": 500,
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


def load_matrix_spec(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_run_config(
    case_name: str,
    num_observation: int,
    noise_std: float,
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    config = json.loads(json.dumps(BASE_CONFIGS[case_name]))
    config["data"]["num_observation"] = int(num_observation)
    config["data"]["noise_std"] = float(noise_std)
    if overrides:
        merge_dict(config, overrides)
    return ensure_defaults(config)


def merge_dict(target: Dict[str, Any], updates: Dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_dict(target[key], value)
        else:
            target[key] = value
