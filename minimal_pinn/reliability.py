from __future__ import annotations

import math
from typing import Dict


def logistic_score(value: float, good: float, fail: float, mode: str) -> float:
    if mode == "smaller_better":
        k = math.log(19.0) / (good - fail)
        x0 = fail
    elif mode == "larger_better":
        k = -math.log(19.0) / (good - fail)
        x0 = fail
    else:
        raise ValueError(f"Unsupported threshold mode: {mode}")
    z = max(-60.0, min(60.0, -k * (value - x0)))
    score = 1.0 / (1.0 + math.exp(z))
    return max(0.0, min(1.0, score))


def geometric_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    product = 1.0
    for value in values:
        product *= max(value, 1e-12)
    return product ** (1.0 / len(values))


def build_reliability_summary(
    metrics: Dict[str, float],
    thresholds: Dict[str, Dict[str, float | str]],
) -> Dict[str, float | Dict[str, float]]:
    scores = {
        name: logistic_score(
            value=metrics[name],
            good=float(spec["good"]),
            fail=float(spec["fail"]),
            mode=str(spec["mode"]),
        )
        for name, spec in thresholds.items()
        if name in metrics
    }

    dim_scores = {
        "physics_consistency": geometric_mean(
            [scores["physics_rms"], scores["boundary_rms"]]
        ),
        "training_stability": geometric_mean(
            [scores["loss_std"], scores["loss_ratio"]]
        ),
        "numerical_accuracy": geometric_mean([scores["rel_l2"]]),
        "structural_stability": geometric_mean([scores["structure_error"]]),
    }

    overall = sum(dim_scores.values()) / len(dim_scores)
    return {
        "indicator_scores": scores,
        "dimension_scores": dim_scores,
        "reliability_raw": overall,
    }
