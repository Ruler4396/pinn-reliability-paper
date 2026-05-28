from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class FisherKPPCase(BaseCase):
    name = "fisher_kpp"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(
        self,
        x_min: float = -1.0,
        x_max: float = 1.0,
        t_max: float = 1.0,
        diffusivity: float = 0.01,
        reaction: float = 1.0,
    ) -> None:
        self.x_min = x_min
        self.x_max = x_max
        self.t_max = t_max
        self.diffusivity = diffusivity
        self.reaction = reaction
        self.wave_speed = 5.0 * math.sqrt(self.diffusivity * self.reaction / 6.0)
        self.wave_width = math.sqrt(6.0 * self.diffusivity / self.reaction)

    def _sample_xt(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = self.x_min + (self.x_max - self.x_min) * torch.rand(
            (num_points, 1), generator=gen, device=device
        )
        t = self.t_max * torch.rand((num_points, 1), generator=gen, device=device)
        return torch.cat([x, t], dim=1)

    def sample_observations(
        self,
        num_points: int,
        noise_std: float,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self._sample_xt(num_points, seed, device)
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 29)
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
        return self._sample_xt(num_points, seed, device)

    def sample_boundary(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        gen = torch.Generator(device=device).manual_seed(seed)
        half = num_points // 2

        t_bc = self.t_max * torch.rand((half, 1), generator=gen, device=device)
        side = torch.randint(0, 2, (half, 1), generator=gen, device=device)
        x_bc = torch.where(
            side == 0,
            torch.full_like(t_bc, self.x_min),
            torch.full_like(t_bc, self.x_max),
        )
        spatial_bc = torch.cat([x_bc, t_bc], dim=1)

        x_ic = self.x_min + (self.x_max - self.x_min) * torch.rand(
            (num_points - half, 1), generator=gen, device=device
        )
        t_ic = torch.zeros_like(x_ic)
        initial_bc = torch.cat([x_ic, t_ic], dim=1)

        pts = torch.cat([spatial_bc, initial_bc], dim=0)
        return pts, self.truth(pts)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        x = torch.linspace(self.x_min, self.x_max, num_eval, device=device)
        t = torch.linspace(0.0, self.t_max, num_eval, device=device)
        xx, tt = torch.meshgrid(x, t, indexing="ij")
        return torch.stack([xx.reshape(-1), tt.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        xx = x[:, 0:1]
        tt = x[:, 1:2]
        z = (xx - self.wave_speed * tt) / self.wave_width
        return torch.pow(1.0 + torch.exp(z), -2.0)

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        grad_u = gradients(u, x)
        u_t = grad_u[:, 1:2]
        u_xx = second_derivative(u, x, dim=0)
        return u_t - self.diffusivity * u_xx - self.reaction * u + self.reaction * u * u

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(self.x_min, self.x_max, 256, device=device).unsqueeze(1)
        t = torch.full_like(x, self.t_max)
        pts = torch.cat([x, t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
