from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class BurgersCase(BaseCase):
    name = "burgers"
    input_dim = 2
    output_dim = 1
    output_names: Tuple[str, ...] = ("u",)

    def __init__(self, nu: float = 0.01 / math.pi) -> None:
        self.nu = nu

    def _sample_xt(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = -1.0 + 2.0 * torch.rand((num_points, 1), generator=gen, device=device)
        t = torch.rand((num_points, 1), generator=gen, device=device)
        return torch.cat([x, t], dim=1)

    def _sample_xt_focus(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        x_range: Tuple[float, float],
        t_range: Tuple[float, float],
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x_low, x_high = x_range
        t_low, t_high = t_range
        x = x_low + (x_high - x_low) * torch.rand((num_points, 1), generator=gen, device=device)
        t = t_low + (t_high - t_low) * torch.rand((num_points, 1), generator=gen, device=device)
        return torch.cat([x, t], dim=1)

    def _sample_mixed_xt(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None,
        ratio_key: str,
    ) -> torch.Tensor:
        cfg = region_cfg or {}
        if not cfg.get("enabled", False):
            return self._sample_xt(num_points, seed, device)

        focus_ratio = float(cfg.get(ratio_key, 0.0))
        focus_ratio = max(0.0, min(1.0, focus_ratio))
        focus_points = int(round(num_points * focus_ratio))
        global_points = max(0, num_points - focus_points)

        x_range = tuple(cfg.get("x_range", [-0.4, 0.4]))
        t_range = tuple(cfg.get("t_range", [0.0, 0.5]))

        parts = []
        if global_points > 0:
            parts.append(self._sample_xt(global_points, seed, device))
        if focus_points > 0:
            parts.append(
                self._sample_xt_focus(
                    focus_points,
                    seed + 1009,
                    device,
                    x_range=x_range,
                    t_range=t_range,
                )
            )
        if len(parts) == 1:
            return parts[0]
        return torch.cat(parts, dim=0)

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

    def sample_observations_with_region(
        self,
        num_points: int,
        noise_std: float,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self._sample_mixed_xt(
            num_points=num_points,
            seed=seed,
            device=device,
            region_cfg=region_cfg,
            ratio_key="observation_focus_ratio",
        )
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

    def sample_collocation_with_region(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None = None,
    ) -> torch.Tensor:
        return self._sample_mixed_xt(
            num_points=num_points,
            seed=seed,
            device=device,
            region_cfg=region_cfg,
            ratio_key="collocation_focus_ratio",
        )

    def sample_boundary(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        gen = torch.Generator(device=device).manual_seed(seed)
        half = num_points // 2

        t_bc = torch.rand((half, 1), generator=gen, device=device)
        side = torch.randint(0, 2, (half, 1), generator=gen, device=device)
        x_bc = torch.where(side == 0, -torch.ones_like(t_bc), torch.ones_like(t_bc))
        spatial_bc = torch.cat([x_bc, t_bc], dim=1)

        x_ic = -1.0 + 2.0 * torch.rand(
            (num_points - half, 1), generator=gen, device=device
        )
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
        return -torch.exp(-tt) * torch.sin(math.pi * xx)

    def forcing(self, x: torch.Tensor) -> torch.Tensor:
        xx = x[:, 0:1]
        tt = x[:, 1:2]
        exp_t = torch.exp(-tt)
        term1 = exp_t * torch.sin(math.pi * xx)
        term2 = math.pi * torch.exp(-2.0 * tt) * torch.sin(math.pi * xx) * torch.cos(
            math.pi * xx
        )
        term3 = self.nu * (math.pi**2) * exp_t * torch.sin(math.pi * xx)
        return term1 + term2 - term3

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        grad_u = gradients(u, x)
        u_x = grad_u[:, 0:1]
        u_t = grad_u[:, 1:2]
        u_xx = second_derivative(u, x, dim=0)
        return u_t + u * u_x - self.nu * u_xx - self.forcing(x)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        x = torch.linspace(-1.0, 1.0, 256, device=device).unsqueeze(1)
        t = torch.ones_like(x)
        pts = torch.cat([x, t], dim=1)
        with torch.no_grad():
            pred = model(pts)
            truth = self.truth(pts)
        return cosine_error(pred, truth)
