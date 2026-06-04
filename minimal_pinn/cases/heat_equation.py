from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class HeatEquationCase(BaseCase):
    """Pure heat equation u_t = nu * u_xx (linear parabolic).

    Exact solution: u(x,t) = exp(-nu * pi^2 * t) * sin(pi * x)
    Domain: x in [-1, 1], t in [0, 1]
    """

    name = "heat_equation"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(self, nu: float = 0.1) -> None:
        self.nu = nu

    def _sample_xt(self, num_points: int, seed: int, device: torch.device) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = -1.0 + 2.0 * torch.rand((num_points, 1), generator=gen, device=device)
        t = torch.rand((num_points, 1), generator=gen, device=device)
        return torch.cat([x, t], dim=1)

    def sample_observations(self, num_points: int, noise_std: float, seed: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self._sample_xt(num_points, seed, device)
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 23)
            y = y + noise_std * torch.std(y, dim=0, keepdim=True) * torch.randn(y.shape, generator=gen, device=device)
        return x, y

    def sample_collocation(self, num_points: int, seed: int, device: torch.device) -> torch.Tensor:
        return self._sample_xt(num_points, seed, device)

    def sample_boundary(self, num_points: int, seed: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        gen = torch.Generator(device=device).manual_seed(seed)
        half = num_points // 2
        t_bc = torch.rand((half, 1), generator=gen, device=device)
        side = torch.randint(0, 2, (half, 1), generator=gen, device=device)
        x_bc = torch.where(side == 0, -torch.ones_like(t_bc), torch.ones_like(t_bc))
        spatial_bc = torch.cat([x_bc, t_bc], dim=1)
        x_ic = -1.0 + 2.0 * torch.rand((num_points - half, 1), generator=gen, device=device)
        t_ic = torch.zeros_like(x_ic)
        initial_bc = torch.cat([x_ic, t_ic], dim=1)
        pts = torch.cat([spatial_bc, initial_bc], dim=0)
        return pts, self.truth(pts)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        x = torch.linspace(-1.0, 1.0, num_eval, device=device)
        t = torch.linspace(0.0, 1.0, num_eval, device=device)
        xx, tt = torch.meshgrid(x, t, indexing="ij")
        return torch.stack([xx.reshape(-1), tt.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        xx = x[:, 0:1]
        tt = x[:, 1:2]
        return torch.exp(-self.nu * (math.pi ** 2) * tt) * torch.sin(math.pi * xx)

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        u_t = gradients(u, x)[:, 1:2]
        u_xx = second_derivative(u, x, dim=0)
        return u_t - self.nu * u_xx

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(-1.0, 1.0, 256, device=device).unsqueeze(1)
        t = torch.ones_like(x)
        pts = torch.cat([x, t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
