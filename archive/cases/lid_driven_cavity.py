from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import torch
import torch.nn.functional as F

from .base import BaseCase, cosine_error, gradients, second_derivative


def solve_lid_driven_cavity(
    grid_size: int = 41,
    reynolds: float = 100.0,
    max_steps: int = 5000,
    poisson_sweeps: int = 60,
    dt: float = 1e-3,
    tol: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray]:
    nu = 1.0 / reynolds
    n = grid_size
    h = 1.0 / (n - 1)

    psi = np.zeros((n, n), dtype=np.float64)
    omega = np.zeros((n, n), dtype=np.float64)
    u = np.zeros((n, n), dtype=np.float64)
    v = np.zeros((n, n), dtype=np.float64)

    for _ in range(max_steps):
        for _ in range(poisson_sweeps):
            psi[1:-1, 1:-1] = 0.25 * (
                psi[2:, 1:-1]
                + psi[:-2, 1:-1]
                + psi[1:-1, 2:]
                + psi[1:-1, :-2]
                + (h * h) * omega[1:-1, 1:-1]
            )
            psi[:, 0] = 0.0
            psi[:, -1] = 0.0
            psi[0, :] = 0.0
            psi[-1, :] = 0.0

        u.fill(0.0)
        v.fill(0.0)
        u[1:-1, 1:-1] = (psi[1:-1, 2:] - psi[1:-1, :-2]) / (2.0 * h)
        v[1:-1, 1:-1] = -(psi[2:, 1:-1] - psi[:-2, 1:-1]) / (2.0 * h)
        u[:, -1] = 1.0

        omega[:, 0] = -2.0 * psi[:, 1] / (h * h)
        omega[:, -1] = -2.0 * psi[:, -2] / (h * h) - 2.0 * u[:, -1] / h
        omega[0, :] = -2.0 * psi[1, :] / (h * h)
        omega[-1, :] = -2.0 * psi[-2, :] / (h * h)

        omega_old = omega.copy()
        omega_x = (omega_old[2:, 1:-1] - omega_old[:-2, 1:-1]) / (2.0 * h)
        omega_y = (omega_old[1:-1, 2:] - omega_old[1:-1, :-2]) / (2.0 * h)
        lap_omega = (
            omega_old[2:, 1:-1]
            + omega_old[:-2, 1:-1]
            + omega_old[1:-1, 2:]
            + omega_old[1:-1, :-2]
            - 4.0 * omega_old[1:-1, 1:-1]
        ) / (h * h)

        convection = u[1:-1, 1:-1] * omega_x + v[1:-1, 1:-1] * omega_y
        omega[1:-1, 1:-1] = omega_old[1:-1, 1:-1] + dt * (-convection + nu * lap_omega)

        if np.max(np.abs(omega - omega_old)) < tol:
            break

    return u.astype(np.float32), v.astype(np.float32)


class LidDrivenCavityCase(BaseCase):
    name = "lid_driven_cavity"
    input_dim = 2
    output_dim = 3
    output_names: Tuple[str, ...] = ("u", "v")

    def __init__(self, reynolds: float = 100.0, grid_size: int = 41) -> None:
        self.reynolds = reynolds
        self.nu = 1.0 / reynolds
        self.grid_size = grid_size
        self._field_cache: dict[str, torch.Tensor] = {}
        self._u_ref, self._v_ref = self._load_or_build_reference()

    def _cache_path(self) -> Path:
        root = Path(__file__).resolve().parents[1]
        cache_dir = root / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"lid_driven_cavity_re{int(self.reynolds)}_n{self.grid_size}.npz"

    def _load_or_build_reference(self) -> tuple[np.ndarray, np.ndarray]:
        cache_path = self._cache_path()
        if cache_path.exists():
            data = np.load(cache_path)
            return data["u"], data["v"]
        u, v = solve_lid_driven_cavity(grid_size=self.grid_size, reynolds=self.reynolds)
        np.savez_compressed(cache_path, u=u, v=v)
        return u, v

    def _field_tensor(self, device: torch.device) -> torch.Tensor:
        key = str(device)
        if key not in self._field_cache:
            field = np.stack([self._u_ref.T, self._v_ref.T], axis=0)
            self._field_cache[key] = torch.tensor(field, dtype=torch.float32, device=device).unsqueeze(0)
        return self._field_cache[key]

    def _sample_xy(
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
        x = self._sample_xy(num_points, seed, device)
        y = self.truth(x)
        if noise_std > 0:
            gen = torch.Generator(device=device).manual_seed(seed + 53)
            scale = torch.std(y, dim=0, keepdim=True)
            y = y + noise_std * scale * torch.randn(y.shape, generator=gen, device=device)
        return x, y

    def sample_collocation(
        self,
        num_points: int,
        seed: int,
        device: torch.device,
    ) -> torch.Tensor:
        return self._sample_xy(num_points, seed, device)

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
        x[:, 0:1] = torch.where(side == 0, coord, x[:, 0:1])
        x[:, 0:1] = torch.where(side == 1, coord, x[:, 0:1])
        x[:, 0:1] = torch.where(side == 2, torch.zeros_like(coord), x[:, 0:1])
        x[:, 0:1] = torch.where(side == 3, torch.ones_like(coord), x[:, 0:1])
        x[:, 1:2] = torch.where(side == 0, torch.zeros_like(coord), x[:, 1:2])
        x[:, 1:2] = torch.where(side == 1, torch.ones_like(coord), x[:, 1:2])
        x[:, 1:2] = torch.where(side == 2, coord, x[:, 1:2])
        x[:, 1:2] = torch.where(side == 3, coord, x[:, 1:2])
        return x, self.truth(x)

    def sample_eval(self, num_eval: int, device: torch.device) -> torch.Tensor:
        grid = torch.linspace(0.0, 1.0, num_eval, device=device)
        xx, yy = torch.meshgrid(grid, grid, indexing="ij")
        return torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=1)

    def truth(self, x: torch.Tensor) -> torch.Tensor:
        field = self._field_tensor(x.device)
        grid = torch.stack([2.0 * x[:, 0] - 1.0, 2.0 * x[:, 1] - 1.0], dim=1)
        grid = grid.view(1, -1, 1, 2)
        sampled = F.grid_sample(field, grid, mode="bilinear", align_corners=True)
        uv = sampled.squeeze(0).squeeze(-1).transpose(0, 1)
        return uv

    def observable_prediction(
        self,
        x: torch.Tensor,
        pred: torch.Tensor,
    ) -> torch.Tensor:
        del x
        return pred[:, :2]

    def observation_residual(
        self,
        x_observation: torch.Tensor,
        pred_observation: torch.Tensor,
        truth_observation: torch.Tensor,
    ) -> torch.Tensor:
        del x_observation
        return pred_observation[:, :2] - truth_observation

    def boundary_residual(
        self,
        x_boundary: torch.Tensor,
        pred_boundary: torch.Tensor,
        truth_boundary: torch.Tensor,
    ) -> torch.Tensor:
        del x_boundary
        return pred_boundary[:, :2] - truth_boundary

    def physics_residual(self, x: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
        u = pred[:, 0:1]
        v = pred[:, 1:2]
        p = pred[:, 2:3]

        grad_u = gradients(u, x)
        grad_v = gradients(v, x)
        grad_p = gradients(p, x)

        u_x = grad_u[:, 0:1]
        u_y = grad_u[:, 1:2]
        v_x = grad_v[:, 0:1]
        v_y = grad_v[:, 1:2]
        p_x = grad_p[:, 0:1]
        p_y = grad_p[:, 1:2]

        u_xx = second_derivative(u, x, dim=0)
        u_yy = second_derivative(u, x, dim=1)
        v_xx = second_derivative(v, x, dim=0)
        v_yy = second_derivative(v, x, dim=1)

        mom_x = u * u_x + v * u_y + p_x - self.nu * (u_xx + u_yy)
        mom_y = u * v_x + v * v_y + p_y - self.nu * (v_xx + v_yy)
        continuity = u_x + v_y
        return torch.cat([mom_x, mom_y, continuity], dim=1)

    def structure_error(self, model: torch.nn.Module, device: torch.device) -> float:
        line = torch.linspace(0.0, 1.0, 200, device=device).unsqueeze(1)
        pts_u = torch.cat([0.5 * torch.ones_like(line), line], dim=1)
        pts_v = torch.cat([line, 0.5 * torch.ones_like(line)], dim=1)
        with torch.no_grad():
            pred_u = self.observable_prediction(pts_u, model(pts_u))[:, 0:1]
            truth_u = self.truth(pts_u)[:, 0:1]
            pred_v = self.observable_prediction(pts_v, model(pts_v))[:, 1:2]
            truth_v = self.truth(pts_v)[:, 1:2]
        return 0.5 * (cosine_error(pred_u, truth_u) + cosine_error(pred_v, truth_v))
