from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class NLSSolitonCase(BaseCase):
    """NLS soliton: i*psi_t + psi_xx + 2*|psi|^2*psi = 0.

    Soliton solution (eta=1, xi=0): psi(x,t) = sech(x) * exp(it)
    Real: u = sech(x)*cos(t), Imag: v = sech(x)*sin(t)
    Domain: x in [-10, 10], t in [0, 2]
    """

    name = "nls_soliton"
    input_dim = 2
    output_dim = 2
    output_names: Tuple[str, ...] = ("u", "v")

    def __init__(self, eta: float = 1.0, xi: float = 0.0) -> None:
        self.eta = eta
        self.xi = xi

    def _sample_xt(self, num_points: int, seed: int, device: torch.device) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = -10.0 + 20.0 * torch.rand((num_points, 1), generator=gen, device=device)
        t = 2.0 * torch.rand((num_points, 1), generator=gen, device=device)
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
        t_bc = 2.0 * torch.rand((half, 1), generator=gen, device=device)
        side = torch.randint(0, 2, (half, 1), generator=gen, device=device)
        x_bc = torch.where(side == 0, -10.0 * torch.ones_like(t_bc), 10.0 * torch.ones_like(t_bc))
        spatial_bc = torch.cat([x_bc, t_bc], dim=1)
        x_ic = -10.0 + 20.0 * torch.rand((num_points - half, 1), generator=gen, device=device)
        t_ic = torch.zeros_like(x_ic)
        initial_bc = torch.cat([x_ic, t_ic], dim=1)
        pts = torch.cat([spatial_bc, initial_bc], dim=0)
        return pts, self.truth(pts)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        x = torch.linspace(-10.0, 10.0, num_eval, device=device)
        t = torch.linspace(0.0, 2.0, num_eval, device=device)
        xx, tt = torch.meshgrid(x, t, indexing="ij")
        return torch.stack([xx.reshape(-1), tt.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        xx = x[:, 0:1]
        tt = x[:, 1:2]
        sech = 1.0 / torch.cosh(self.eta * (xx - 2.0 * self.xi * tt))
        phase = self.xi * xx - (self.xi ** 2 - self.eta ** 2) * tt
        u = self.eta * sech * torch.cos(phase)
        v = self.eta * sech * torch.sin(phase)
        return torch.cat([u, v], dim=1)

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        v = pred[:, 1:2]
        u_t = gradients(u, x)[:, 1:2]
        v_t = gradients(v, x)[:, 1:2]
        u_xx = second_derivative(u, x, dim=0)
        v_xx = second_derivative(v, x, dim=0)
        mod_sq = u ** 2 + v ** 2
        res_real = -v_t + u_xx + 2.0 * mod_sq * u
        res_imag = u_t + v_xx + 2.0 * mod_sq * v
        return torch.cat([res_real, res_imag], dim=1)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(-10.0, 10.0, 256, device=device).unsqueeze(1)
        t = torch.ones_like(x)
        pts = torch.cat([x, t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
