from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

import torch


def gradients(y: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    return torch.autograd.grad(
        y,
        x,
        grad_outputs=torch.ones_like(y),
        create_graph=True,
        retain_graph=True,
    )[0]


def second_derivative(
    y: torch.Tensor,
    x: torch.Tensor,
    dim: int,
) -> torch.Tensor:
    first = gradients(y, x)[:, dim : dim + 1]
    return gradients(first, x)[:, dim : dim + 1]


def relative_l2(pred: torch.Tensor, truth: torch.Tensor) -> float:
    num = torch.linalg.norm(pred - truth)
    den = torch.linalg.norm(truth) + 1e-12
    return float((num / den).detach().cpu())


def abs_rmse(pred: torch.Tensor, truth: torch.Tensor) -> float:
    return float(torch.sqrt(torch.mean((pred - truth) ** 2)).detach().cpu())


def cosine_error(pred: torch.Tensor, truth: torch.Tensor) -> float:
    pred_flat = pred.reshape(-1)
    truth_flat = truth.reshape(-1)
    score = torch.nn.functional.cosine_similarity(
        pred_flat.unsqueeze(0),
        truth_flat.unsqueeze(0),
    )[0]
    return float((1.0 - score).detach().cpu())


class BaseCase(ABC):
    name: str
    input_dim: int
    output_dim: int
    output_names: Tuple[str, ...]

    @abstractmethod
    def sample_observations(
        self,
        num_points: int,
        noise_std: float,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        raise NotImplementedError

    @abstractmethod
    def sample_collocation(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        raise NotImplementedError

    @abstractmethod
    def sample_boundary(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        raise NotImplementedError

    @abstractmethod
    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        raise NotImplementedError

    def sample_observations_with_region(
        self,
        num_points: int,
        noise_std: float,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        del region_cfg
        return self.sample_observations(
            num_points=num_points,
            noise_std=noise_std,
            seed=seed,
            device=device,
        )

    def sample_collocation_with_region(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None = None,
    ) -> torch.Tensor:
        del region_cfg
        return self.sample_collocation(
            num_points=num_points,
            seed=seed,
            device=device,
        )

    def observable_prediction(
        self,
        x: torch.Tensor,
        pred: torch.Tensor,
    ) -> torch.Tensor:
        del x
        return pred

    def observation_residual(
        self,
        x_observation: torch.Tensor,
        pred_observation: torch.Tensor,
        truth_observation: torch.Tensor,
    ) -> torch.Tensor:
        del x_observation
        return pred_observation - truth_observation

    @abstractmethod
    def truth(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

    @abstractmethod
    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

    def boundary_residual(
        self,
        x_boundary: torch.Tensor,
        pred_boundary: torch.Tensor,
        truth_boundary: torch.Tensor,
    ) -> torch.Tensor:
        del x_boundary
        return pred_boundary - truth_boundary

    @abstractmethod
    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        raise NotImplementedError

    def named_error_metrics(
        self,
        pred: torch.Tensor,
        truth: torch.Tensor,
    ) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        for idx, name in enumerate(self.output_names):
            pred_i = pred[:, idx : idx + 1]
            truth_i = truth[:, idx : idx + 1]
            truth_norm = float(torch.linalg.norm(truth_i).detach().cpu())
            if truth_norm > 1e-8:
                metrics[f"rel_l2_{name}"] = relative_l2(pred_i, truth_i)
            else:
                metrics[f"abs_rmse_{name}"] = abs_rmse(pred_i, truth_i)
        return metrics
