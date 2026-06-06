from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients


class VariableCoefficientDiffusionCase(BaseCase):
    name = "variable_coefficient_diffusion"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(self, coeff_amp: float = 0.35) -> None:
        self.coeff_amp = float(coeff_amp)

    def _sample_interior(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        return torch.rand((num_points, 2), generator=gen, device=device)

    def sample_observations(
        self,
        num_points: int,
        noise_std: float,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self._sample_interior(num_points, seed, device)
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 17)
            y = y + noise_std * torch.std(y, dim=0, keepdim=True) * torch.randn(
                y.shape, generator=gen, device=device
            )
        return x, y

    def sample_collocation(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        return self._sample_interior(num_points, seed, device)

    def sample_boundary(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        gen = torch.Generator(device=device).manual_seed(seed)
        side = torch.randint(0, 4, (num_points, 1), generator=gen, device=device)
        coord = torch.rand((num_points, 1), generator=gen, device=device)
        x = torch.zeros((num_points, 2), device=device)
        x[:, 0:1] = torch.where(side == 0, torch.zeros_like(coord), coord)
        x[:, 0:1] = torch.where(side == 1, torch.ones_like(coord), x[:, 0:1])
        x[:, 1:2] = torch.where(side == 2, torch.zeros_like(coord), coord)
        x[:, 1:2] = torch.where(side == 3, torch.ones_like(coord), x[:, 1:2])
        return x, self.truth(x)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        grid = torch.linspace(0.0, 1.0, num_eval, device=device)
        xx, yy = torch.meshgrid(grid, grid, indexing="ij")
        return torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sin(math.pi * x[:, 0:1]) * torch.sin(math.pi * x[:, 1:2])

    def coefficient(self, x: torch.Tensor) -> torch.Tensor:
        return 1.0 + self.coeff_amp * (
            0.5 * torch.sin(2.0 * math.pi * x[:, 0:1]) * torch.sin(2.0 * math.pi * x[:, 1:2])
            + 0.5 * x[:, 0:1]
        )

    def _operator(self, x: torch.Tensor, field: torch.Tensor) -> torch.Tensor:
        grad_u = gradients(field, x)
        coeff = self.coefficient(x)
        flux_x = coeff * grad_u[:, 0:1]
        flux_y = coeff * grad_u[:, 1:2]
        div_x = gradients(flux_x, x)[:, 0:1]
        div_y = gradients(flux_y, x)[:, 1:2]
        return -(div_x + div_y)

    def forcing(self, x: torch.Tensor) -> torch.Tensor:
        x_req = x.detach().clone().requires_grad_(True)
        u_true = self.truth(x_req)
        return self._operator(x_req, u_true).detach()

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        return self._operator(x, pred[:, 0:1]) - self.forcing(x)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(0.0, 1.0, 200, device=device).unsqueeze(1)
        y = 0.5 * torch.ones_like(x)
        pts = torch.cat([x, y], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
