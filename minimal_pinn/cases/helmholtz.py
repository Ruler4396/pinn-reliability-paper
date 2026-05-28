from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, second_derivative


class HelmholtzCase(BaseCase):
    name = "helmholtz"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(self, mode: int = 3, kappa: float | None = None) -> None:
        self.mode = int(mode)
        self.mode_y = self.mode + 1
        laplace_coeff = (self.mode * math.pi) ** 2 + (self.mode_y * math.pi) ** 2
        if kappa is None:
            self.kappa = math.sqrt(max(laplace_coeff - 5.0, 1.0))
        else:
            self.kappa = float(kappa)

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
            gen = torch.Generator(device=device).manual_seed(seed + 31)
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
        return torch.cos(self.mode * math.pi * x[:, 0:1]) * torch.sin(
            self.mode_y * math.pi * x[:, 1:2]
        )

    def forcing(self, x: torch.Tensor) -> torch.Tensor:
        truth = self.truth(x)
        laplace_coeff = (self.mode * math.pi) ** 2 + (self.mode_y * math.pi) ** 2
        return (self.kappa**2 - laplace_coeff) * truth

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        u_xx = second_derivative(u, x, dim=0)
        u_yy = second_derivative(u, x, dim=1)
        return u_xx + u_yy + (self.kappa**2) * u - self.forcing(x)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(0.0, 1.0, 256, device=device).unsqueeze(1)
        y = 0.5 * torch.ones_like(x)
        pts = torch.cat([x, y], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
