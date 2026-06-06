from __future__ import annotations

import math
from typing import Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class KdVDoubleSolitonCase(BaseCase):
    """KdV two-soliton: u_t + 6*u*u_x + u_xxx = 0.

    Hirota bilinear two-soliton solution:
      u(x,t) = 2 * d^2/dx^2 [ln(tau)]
      tau = 1 + exp(eta1) + exp(eta2) + A12 * exp(eta1 + eta2)
      eta_i = kappa_i * (x - kappa_i^2 * t) + delta_i
      A12 = ((k1 - k2) / (k1 + k2))^2

    Default: k1=1.5, k2=0.8, delta1=6.0, delta2=-6.0
    Domain: x in [-15, 15], t in [0, 5]
    """

    name = "kdv_double_soliton"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(
        self,
        k1: float = 1.5,
        k2: float = 0.8,
        delta1: float = 6.0,
        delta2: float = -6.0,
    ) -> None:
        self.k1 = k1
        self.k2 = k2
        self.delta1 = delta1
        self.delta2 = delta2
        self.A12 = ((k1 - k2) / (k1 + k2)) ** 2
        self.x_min = -15.0
        self.x_max = 15.0
        self.t_max = 5.0

    def _sample_xt(self, num_points: int, seed: int, device: torch.device) -> torch.Tensor:
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
            gen = torch.Generator(device=device).manual_seed(seed + 23)
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
            self.x_min * torch.ones_like(t_bc),
            self.x_max * torch.ones_like(t_bc),
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

    def _tau_and_derivs(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return (tau, tau_x, tau_xx) for the two-soliton tau function."""
        xx = x[:, 0:1]
        tt = x[:, 1:2]
        eta1 = self.k1 * (xx - self.k1 ** 2 * tt) + self.delta1
        eta2 = self.k2 * (xx - self.k2 ** 2 * tt) + self.delta2
        e1 = torch.exp(eta1)
        e2 = torch.exp(eta2)
        e12 = e1 * e2
        A = self.A12

        tau = 1.0 + e1 + e2 + A * e12
        tau_x = self.k1 * e1 + self.k2 * e2 + (self.k1 + self.k2) * A * e12
        tau_xx = (self.k1 ** 2) * e1 + (self.k2 ** 2) * e2 + ((self.k1 + self.k2) ** 2) * A * e12
        return tau, tau_x, tau_xx

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        tau, tau_x, tau_xx = self._tau_and_derivs(x)
        return 2.0 * (tau * tau_xx - tau_x ** 2) / (tau ** 2)

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        grad_u = gradients(u, x)
        u_t = grad_u[:, 1:2]
        u_x = grad_u[:, 0:1]
        u_xx = second_derivative(u, x, dim=0)
        u_xxx = gradients(u_xx, x)[:, 0:1]
        return u_t + 6.0 * u * u_x + u_xxx

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(self.x_min, self.x_max, 256, device=device).unsqueeze(1)
        t = torch.ones_like(x) * (self.t_max * 0.5)
        pts = torch.cat([x, t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
