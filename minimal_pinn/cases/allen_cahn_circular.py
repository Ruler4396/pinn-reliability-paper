from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, second_derivative


class AllenCahnCircularCase(BaseCase):
    """2D steady Allen-Cahn with circular interface: -eps^2*(u_xx+u_yy) - u + u^3 = 0.

    Exact solution: u(x,y) = tanh((r - R) / (sqrt(2)*eps))
    where r = sqrt((x - cx)^2 + (y - cy)^2)
    Domain: x,y in [0,1], center=(0.5,0.5), R=0.3, eps=0.1
    """

    name = "allen_cahn_circular"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(
        self,
        eps: float = 0.1,
        radius: float = 0.3,
        cx: float = 0.5,
        cy: float = 0.5,
    ) -> None:
        self.eps = eps
        self.radius = radius
        self.cx = cx
        self.cy = cy
        self._inv_sqrt2_eps = 1.0 / (math.sqrt(2.0) * eps)

    def _r(self, x: torch.Tensor) -> torch.Tensor:
        dx = x[:, 0:1] - self.cx
        dy = x[:, 1:2] - self.cy
        return torch.sqrt(dx ** 2 + dy ** 2 + 1e-30)

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
        r = self._r(x)
        return torch.tanh(self._inv_sqrt2_eps * (r - self.radius))

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        u_xx = second_derivative(u, x, dim=0)
        u_yy = second_derivative(u, x, dim=1)
        return - (self.eps ** 2) * (u_xx + u_yy) - u + u ** 3

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        t = torch.linspace(0.0, 1.0, 200, device=device)
        cx = self.cx * torch.ones_like(t)
        pts = torch.stack([cx, t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
