from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class TaylorGreenCase(BaseCase):
    """Taylor-Green vortex decay (2D Navier-Stokes).

    u = -cos(pi*x)*sin(pi*y)*exp(-2*nu*pi^2*t)
    v =  sin(pi*x)*cos(pi*y)*exp(-2*nu*pi^2*t)
    Domain: [0,1]x[0,1], t in [0, 0.5]
    """

    name = "taylor_green"
    input_dim = 3
    output_dim = 2
    output_names: Tuple[str, ...] = ("u", "v")

    def __init__(self, nu: float = 1.0) -> None:
        self.nu = nu
        self._decay = 2.0 * nu * (math.pi ** 2)

    def _sample_xyt(self, num_points: int, seed: int, device: torch.device) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = torch.rand((num_points, 1), generator=gen, device=device)
        y = torch.rand((num_points, 1), generator=gen, device=device)
        t = 0.5 * torch.rand((num_points, 1), generator=gen, device=device)
        return torch.cat([x, y, t], dim=1)

    def sample_observations(self, num_points: int, noise_std: float, seed: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self._sample_xyt(num_points, seed, device)
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 23)
            y = y + noise_std * torch.std(y, dim=0, keepdim=True) * torch.randn(y.shape, generator=gen, device=device)
        return x, y

    def sample_collocation(self, num_points: int, seed: int, device: torch.device) -> torch.Tensor:
        return self._sample_xyt(num_points, seed, device)

    def sample_boundary(self, num_points: int, seed: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        gen = torch.Generator(device=device).manual_seed(seed)
        side = torch.randint(0, 4, (num_points, 1), generator=gen, device=device)
        coord = torch.rand((num_points, 1), generator=gen, device=device)
        t = 0.5 * torch.rand((num_points, 1), generator=gen, device=device)
        x = torch.zeros((num_points, 3), device=device)
        x[:, 0:1] = torch.where(side == 0, torch.zeros_like(coord), coord)
        x[:, 0:1] = torch.where(side == 1, torch.ones_like(coord), x[:, 0:1])
        x[:, 1:2] = torch.where(side == 2, torch.zeros_like(coord), coord)
        x[:, 1:2] = torch.where(side == 3, torch.ones_like(coord), x[:, 1:2])
        x[:, 2:3] = t
        return x, self.truth(x)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        grid = torch.linspace(0.0, 1.0, num_eval, device=device)
        t = torch.linspace(0.0, 0.5, num_eval, device=device)
        xx, yy, tt = torch.meshgrid(grid, grid, t, indexing="ij")
        return torch.stack([xx.reshape(-1), yy.reshape(-1), tt.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        xx = x[:, 0:1]
        yy = x[:, 1:2]
        tt = x[:, 2:3]
        decay = torch.exp(-self._decay * tt)
        u = -torch.cos(math.pi * xx) * torch.sin(math.pi * yy) * decay
        v = torch.sin(math.pi * xx) * torch.cos(math.pi * yy) * decay
        return torch.cat([u, v], dim=1)

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        v = pred[:, 1:2]
        u_t = gradients(u, x)[:, 2:3]
        v_t = gradients(v, x)[:, 2:3]
        u_x = gradients(u, x)[:, 0:1]
        u_y = gradients(u, x)[:, 1:2]
        v_x = gradients(v, x)[:, 0:1]
        v_y = gradients(v, x)[:, 1:2]
        u_xx = second_derivative(u, x, dim=0)
        u_yy = second_derivative(u, x, dim=1)
        v_xx = second_derivative(v, x, dim=0)
        v_yy = second_derivative(v, x, dim=1)
        continuity = u_x + v_y
        mom_u = u_t + u * u_x + v * u_y - self.nu * (u_xx + u_yy)
        mom_v = v_t + u * v_x + v * v_y - self.nu * (v_xx + v_yy)
        return torch.cat([continuity, mom_u, mom_v], dim=1)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        grid = torch.linspace(0.0, 1.0, 50, device=device)
        xx, yy = torch.meshgrid(grid, grid, indexing="ij")
        t = 0.25 * torch.ones_like(xx.reshape(-1, 1))
        pts = torch.cat([xx.reshape(-1, 1), yy.reshape(-1, 1), t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
