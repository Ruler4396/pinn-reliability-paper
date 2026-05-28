from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import torch

from .base import BaseCase, cosine_error, gradients, second_derivative


class StokesPoiseuilleCase(BaseCase):
    name = "stokes_poiseuille"
    input_dim = 2
    output_dim = 3
    output_names: Tuple[str, ...] = ("u", "v", "p")

    def _sample_xy(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = torch.rand((num_points, 1), generator=gen, device=device)
        y = -1.0 + 2.0 * torch.rand((num_points, 1), generator=gen, device=device)
        return torch.cat([x, y], dim=1)

    def _sample_y_from_bands(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        y_bands: Sequence[Sequence[float]],
        band_weights: Sequence[float] | None = None,
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        if band_weights is None:
            probs = torch.ones(len(y_bands), device=device) / max(len(y_bands), 1)
        else:
            probs = torch.tensor(list(band_weights), dtype=torch.float32, device=device)
            probs = probs / torch.sum(probs)
        band_ids = torch.multinomial(probs, num_samples=num_points, replacement=True, generator=gen)
        y = torch.zeros((num_points, 1), device=device)
        for idx, band in enumerate(y_bands):
            mask = (band_ids == idx).unsqueeze(1)
            count = int(mask.sum().item())
            if count == 0:
                continue
            low, high = float(band[0]), float(band[1])
            values = low + (high - low) * torch.rand((count, 1), generator=gen, device=device)
            y[mask] = values.reshape(-1)
        return y

    def _sample_xy_focus(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        y_bands: Sequence[Sequence[float]],
        band_weights: Sequence[float] | None,
    ) -> torch.Tensor:
        gen = torch.Generator(device=device).manual_seed(seed)
        x = torch.rand((num_points, 1), generator=gen, device=device)
        y = self._sample_y_from_bands(
            num_points=num_points,
            seed=seed + 701,
            device=device,
            y_bands=y_bands,
            band_weights=band_weights,
        )
        return torch.cat([x, y], dim=1)

    def _sample_mixed_xy(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None,
        ratio_key: str,
    ) -> torch.Tensor:
        cfg = region_cfg or {}
        if not cfg.get("enabled", False):
            return self._sample_xy(num_points, seed, device)

        focus_ratio = float(cfg.get(ratio_key, 0.0))
        focus_ratio = max(0.0, min(1.0, focus_ratio))
        focus_points = int(round(num_points * focus_ratio))
        global_points = max(0, num_points - focus_points)

        y_bands = cfg.get("y_bands", [[-1.0, -0.6], [-0.2, 0.2], [0.6, 1.0]])
        band_weights = cfg.get("band_weights", [0.4, 0.2, 0.4])

        parts: List[torch.Tensor] = []
        if global_points > 0:
            parts.append(self._sample_xy(global_points, seed, device))
        if focus_points > 0:
            parts.append(
                self._sample_xy_focus(
                    focus_points,
                    seed + 1207,
                    device=device,
                    y_bands=y_bands,
                    band_weights=band_weights,
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
        x = self._sample_xy(num_points, seed, device)
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 31)
            scale = torch.std(y, dim=0, keepdim=True)
            y = y + noise_std * scale * torch.randn(
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
        x = self._sample_mixed_xy(
            num_points=num_points,
            seed=seed,
            device=device,
            region_cfg=region_cfg,
            ratio_key="observation_focus_ratio",
        )
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 31)
            scale = torch.std(y, dim=0, keepdim=True)
            y = y + noise_std * scale * torch.randn(
                y.shape, generator=gen, device=device
            )
        return x, y

    def sample_collocation(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        return self._sample_xy(num_points, seed, device)

    def sample_collocation_with_region(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
        region_cfg: Dict[str, Any] | None = None,
    ) -> torch.Tensor:
        return self._sample_mixed_xy(
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
        side = torch.randint(0, 4, (num_points, 1), generator=gen, device=device)
        coord = torch.rand((num_points, 1), generator=gen, device=device)
        x = torch.zeros((num_points, 2), device=device)
        x[:, 0:1] = torch.where(side == 0, torch.zeros_like(coord), coord)
        x[:, 0:1] = torch.where(side == 1, torch.ones_like(coord), x[:, 0:1])
        x[:, 1:2] = torch.where(side == 2, -torch.ones_like(coord), -1.0 + 2.0 * coord)
        x[:, 1:2] = torch.where(side == 3, torch.ones_like(coord), x[:, 1:2])
        return x, self.truth(x)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        x = torch.linspace(0.0, 1.0, num_eval, device=device)
        y = torch.linspace(-1.0, 1.0, num_eval, device=device)
        xx, yy = torch.meshgrid(x, y, indexing="ij")
        return torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        xx = x[:, 0:1]
        yy = x[:, 1:2]
        u = 1.0 - yy**2
        v = torch.zeros_like(u)
        p = -2.0 * xx
        return torch.cat([u, v, p], dim=1)

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        v = pred[:, 1:2]
        p = pred[:, 2:3]

        grad_u = gradients(u, x)
        grad_v = gradients(v, x)
        grad_p = gradients(p, x)

        u_x = grad_u[:, 0:1]
        v_y = grad_v[:, 1:2]
        p_x = grad_p[:, 0:1]
        p_y = grad_p[:, 1:2]

        u_xx = second_derivative(u, x, dim=0)
        u_yy = second_derivative(u, x, dim=1)
        v_xx = second_derivative(v, x, dim=0)
        v_yy = second_derivative(v, x, dim=1)

        mom_x = u_xx + u_yy - p_x
        mom_y = v_xx + v_yy - p_y
        continuity = u_x + v_y
        return torch.cat([mom_x, mom_y, continuity], dim=1)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        y = torch.linspace(-1.0, 1.0, 256, device=device).unsqueeze(1)
        x = 0.5 * torch.ones_like(y)
        pts = torch.cat([x, y], dim=1)
        with torch.no_grad():
            pred = model(pts)[:, 0:1]
            truth = self.truth(pts)[:, 0:1]
        return cosine_error(pred, truth)
