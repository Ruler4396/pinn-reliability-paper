from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class AdvectionDiffusionCase(BaseCase):
    name = "advection_diffusion"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(
        self,
        nu: float = 0.02,
        beta_x: float = 4.0,
        beta_y: float = 2.0,
    ) -> None:
        self.nu = float(nu)
        self.beta_x = float(beta_x)
        self.beta_y = float(beta_y)

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
            gen = torch.Generator(device=device).manual_seed(seed + 37)
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
        xx = x[:, 0:1]
        yy = x[:, 1:2]
        return torch.exp(xx + yy) * torch.sin(math.pi * xx) * torch.sin(math.pi * yy)

    def forcing(self, x: torch.Tensor) -> torch.Tensor:
        x_req = x.detach().clone().requires_grad_(True)
        u_true = self.truth(x_req)
        grad_u = gradients(u_true, x_req)
        u_x = grad_u[:, 0:1]
        u_y = grad_u[:, 1:2]
        u_xx = second_derivative(u_true, x_req, dim=0)
        u_yy = second_derivative(u_true, x_req, dim=1)
        return (self.beta_x * u_x + self.beta_y * u_y - self.nu * (u_xx + u_yy)).detach()

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        grad_u = gradients(u, x)
        u_x = grad_u[:, 0:1]
        u_y = grad_u[:, 1:2]
        u_xx = second_derivative(u, x, dim=0)
        u_yy = second_derivative(u, x, dim=1)
        return self.beta_x * u_x + self.beta_y * u_y - self.nu * (u_xx + u_yy) - self.forcing(x)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(0.0, 1.0, 256, device=device).unsqueeze(1)
        y = 0.5 * torch.ones_like(x)
        pts = torch.cat([x, y], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
