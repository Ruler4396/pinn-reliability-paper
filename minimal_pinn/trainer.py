from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
from torch import nn

from .cases import build_case
from .cases.base import relative_l2
from .config import ensure_defaults
from .network import MLP
from .reliability import build_reliability_summary


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def mse_mean(x: torch.Tensor) -> torch.Tensor:
    return torch.mean(x**2)


def pointwise_residual_norm(residual: torch.Tensor) -> torch.Tensor:
    if residual.ndim == 1:
        residual = residual.unsqueeze(1)
    return torch.sqrt(torch.mean(residual**2, dim=1))


def maybe_refresh_collocation(
    *,
    case,
    model: nn.Module,
    x_col: torch.Tensor,
    config: Dict[str, Any],
    epoch: int,
    device: torch.device,
) -> torch.Tensor:
    adaptive_cfg = config["training"]["adaptive_sampling"]
    if not bool(adaptive_cfg.get("enabled", False)):
        return x_col
    if str(adaptive_cfg.get("method", "rar_topk_v1")) != "rar_topk_v1":
        return x_col

    warmup_epochs = int(adaptive_cfg.get("warmup_epochs", 100))
    refresh_every = int(adaptive_cfg.get("refresh_every", 50))
    if epoch < warmup_epochs or refresh_every <= 0 or epoch % refresh_every != 0:
        return x_col

    num_collocation = int(config["data"]["num_collocation"])
    candidate_factor = max(float(adaptive_cfg.get("candidate_factor", 4.0)), 1.0)
    replace_ratio = min(max(float(adaptive_cfg.get("replace_ratio", 0.25)), 0.0), 1.0)
    replace_count = max(1, min(num_collocation - 1, int(round(num_collocation * replace_ratio))))
    keep_count = num_collocation - replace_count
    candidate_count = max(replace_count, int(round(num_collocation * candidate_factor)))
    seed_base = int(config["seed"]) + 100000 + epoch * 17

    was_training = model.training
    model.eval()
    with torch.enable_grad():
        candidate_x = case.sample_collocation(
            num_points=candidate_count,
            seed=seed_base,
            device=device,
        )
        candidate_req = candidate_x.detach().clone().requires_grad_(True)
        candidate_pred = model(candidate_req)
        candidate_residual = case.physics_residual(candidate_req, candidate_pred)
        residual_score = pointwise_residual_norm(candidate_residual).detach()
        topk_idx = torch.topk(residual_score, k=replace_count, largest=True).indices
        topk_points = candidate_x[topk_idx].detach()

    gen = torch.Generator(device=device).manual_seed(seed_base + 1)
    keep_idx = torch.randperm(x_col.shape[0], generator=gen, device=device)[:keep_count]
    kept_points = x_col[keep_idx].detach()
    refreshed = torch.cat([kept_points, topk_points], dim=0)
    if was_training:
        model.train()
    return refreshed


def build_adaptive_weighting(
    config: Dict[str, Any],
    device: torch.device,
) -> Dict[str, Any] | None:
    adaptive_cfg = config["training"]["adaptive_weighting"]
    if not bool(adaptive_cfg.get("enabled", False)):
        return None
    if str(adaptive_cfg.get("method", "uncertainty_v1")) != "uncertainty_v1":
        return None

    init_cfg = adaptive_cfg.get("log_var_init", {})
    log_vars = {
        name: nn.Parameter(
            torch.tensor(float(init_cfg.get(name, 0.0)), device=device),
        )
        for name in ("data", "physics", "boundary")
    }
    optimizer = torch.optim.Adam(
        list(log_vars.values()),
        lr=float(adaptive_cfg.get("lr", 1e-2)),
    )
    return {"log_vars": log_vars, "optimizer": optimizer}


def compute_weighted_objective(
    *,
    loss_data: torch.Tensor,
    loss_phys: torch.Tensor,
    loss_bc: torch.Tensor,
    base_weights: Dict[str, float],
    adaptive_weighting: Dict[str, Any] | None,
    config: Dict[str, Any],
    epoch: int,
) -> tuple[torch.Tensor, torch.Tensor, Dict[str, float]]:
    core_total = (
        float(base_weights["data"]) * loss_data
        + float(base_weights["physics"]) * loss_phys
        + float(base_weights["boundary"]) * loss_bc
    )
    if adaptive_weighting is None:
        effective_weights = {
            "data": float(base_weights["data"]),
            "physics": float(base_weights["physics"]),
            "boundary": float(base_weights["boundary"]),
        }
        return core_total, core_total, effective_weights

    adaptive_cfg = config["training"]["adaptive_weighting"]
    warmup_epochs = int(adaptive_cfg.get("warmup_epochs", 0))
    if epoch <= warmup_epochs:
        effective_weights = {
            "data": float(base_weights["data"]),
            "physics": float(base_weights["physics"]),
            "boundary": float(base_weights["boundary"]),
        }
        return core_total, core_total, effective_weights

    reg_scale = float(adaptive_cfg.get("regularizer_scale", 1.0))
    log_vars = adaptive_weighting["log_vars"]

    effective_data = float(base_weights["data"]) * torch.exp(-log_vars["data"])
    effective_phys = float(base_weights["physics"]) * torch.exp(-log_vars["physics"])
    effective_bc = float(base_weights["boundary"]) * torch.exp(-log_vars["boundary"])

    objective_total = (
        effective_data * loss_data
        + effective_phys * loss_phys
        + effective_bc * loss_bc
        + reg_scale * (log_vars["data"] + log_vars["physics"] + log_vars["boundary"])
    )
    effective_weights = {
        "data": float(effective_data.detach().cpu()),
        "physics": float(effective_phys.detach().cpu()),
        "boundary": float(effective_bc.detach().cpu()),
    }
    return core_total, objective_total, effective_weights


def run_training(config: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    config = ensure_defaults(config)
    set_seed(int(config["seed"]))

    device = torch.device("cpu")
    case = build_case(config["case"])
    model = MLP(
        input_dim=case.input_dim,
        output_dim=case.output_dim,
        hidden_layers=config["network"]["hidden_layers"],
        activation=config["network"]["activation"],
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(config["training"]["lr"]))
    weights = config["training"]["weights"]
    adaptive_weighting = build_adaptive_weighting(config=config, device=device)

    lr_schedule_cfg = config["training"].get("lr_schedule", {})
    scheduler = None
    if lr_schedule_cfg.get("type") == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=epochs,
            eta_min=float(lr_schedule_cfg.get("eta_min", 1e-5)),
        )

    region_cfg = config["data"].get("region_aware")

    x_obs, y_obs = case.sample_observations_with_region(
        num_points=int(config["data"]["num_observation"]),
        noise_std=float(config["data"]["noise_std"]),
        seed=int(config["seed"]),
        device=device,
        region_cfg=region_cfg,
    )
    x_col = case.sample_collocation_with_region(
        num_points=int(config["data"]["num_collocation"]),
        seed=int(config["seed"]) + 1,
        device=device,
        region_cfg=region_cfg,
    )
    x_bc, y_bc = case.sample_boundary(
        num_points=int(config["data"]["num_boundary"]),
        seed=int(config["seed"]) + 2,
        device=device,
    )
    x_eval = case.sample_eval(num_eval=int(config["data"]["num_eval"]), device=device)
    y_eval = case.truth(x_eval)

    history: list[Dict[str, float]] = []
    epochs = int(config["training"]["epochs"])
    print_every = int(config["training"]["print_every"])

    for epoch in range(1, epochs + 1):
        x_col = maybe_refresh_collocation(
            case=case,
            model=model,
            x_col=x_col,
            config=config,
            epoch=epoch,
            device=device,
        )
        optimizer.zero_grad()
        if adaptive_weighting is not None:
            adaptive_weighting["optimizer"].zero_grad()

        pred_obs_raw = model(x_obs)
        obs_residual = case.observation_residual(x_obs, pred_obs_raw, y_obs)
        loss_data = mse_mean(obs_residual)

        x_col_req = x_col.detach().clone().requires_grad_(True)
        pred_col = model(x_col_req)
        physics_residual = case.physics_residual(x_col_req, pred_col)
        loss_phys = mse_mean(physics_residual)

        pred_bc = model(x_bc)
        bc_residual = case.boundary_residual(x_bc, pred_bc, y_bc)
        loss_bc = mse_mean(bc_residual)

        core_total, objective_total, effective_weights = compute_weighted_objective(
            loss_data=loss_data,
            loss_phys=loss_phys,
            loss_bc=loss_bc,
            base_weights=weights,
            adaptive_weighting=adaptive_weighting,
            config=config,
            epoch=epoch,
        )
        objective_total.backward()
        optimizer.step()
        if adaptive_weighting is not None:
            adaptive_weighting["optimizer"].step()
            adaptive_cfg = config["training"]["adaptive_weighting"]
            clamp_min = float(adaptive_cfg.get("clamp_min", -4.0))
            clamp_max = float(adaptive_cfg.get("clamp_max", 4.0))
            for param in adaptive_weighting["log_vars"].values():
                param.data.clamp_(clamp_min, clamp_max)
        if scheduler is not None:
            scheduler.step()

        record = {
            "epoch": float(epoch),
            "loss_total": float(core_total.detach().cpu()),
            "objective_total": float(objective_total.detach().cpu()),
            "loss_data": float(loss_data.detach().cpu()),
            "loss_physics": float(loss_phys.detach().cpu()),
            "loss_boundary": float(loss_bc.detach().cpu()),
            "weight_data": float(effective_weights["data"]),
            "weight_physics": float(effective_weights["physics"]),
            "weight_boundary": float(effective_weights["boundary"]),
        }
        history.append(record)

        if epoch == 1 or epoch % print_every == 0 or epoch == epochs:
            with torch.no_grad():
                pred_eval_raw = model(x_eval)
                pred_eval = case.observable_prediction(x_eval, pred_eval_raw)
                rel_l2 = relative_l2(pred_eval, y_eval)
            print(
                f"[epoch {epoch}] total={record['loss_total']:.4e} "
                f"data={record['loss_data']:.4e} phys={record['loss_physics']:.4e} "
                f"bc={record['loss_boundary']:.4e} rel_l2={rel_l2:.4e} "
                f"w=({record['weight_data']:.2f},{record['weight_physics']:.2f},{record['weight_boundary']:.2f})",
                flush=True,
            )

    metrics = evaluate_model(
        model=model,
        case=case,
        x_eval=x_eval,
        y_eval=y_eval,
        x_bc=x_bc,
        y_bc=y_bc,
        history=history,
        thresholds=config["reliability"]["thresholds"],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "config.json").open("w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)

    with (output_dir / "history.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "epoch",
                "loss_total",
                "objective_total",
                "loss_data",
                "loss_physics",
                "loss_boundary",
                "weight_data",
                "weight_physics",
                "weight_boundary",
            ],
        )
        writer.writeheader()
        writer.writerows(history)

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)

    torch.save({"model_state_dict": model.state_dict()}, output_dir / "best.ckpt")
    return metrics


def evaluate_model(
    model: torch.nn.Module,
    case,
    x_eval: torch.Tensor,
    y_eval: torch.Tensor,
    x_bc: torch.Tensor,
    y_bc: torch.Tensor,
    history: list[Dict[str, float]],
    thresholds: Dict[str, Dict[str, float | str]],
) -> Dict[str, Any]:
    model.eval()
    with torch.no_grad():
        pred_eval_raw = model(x_eval)
        pred_bc = model(x_bc)
        pred_eval = case.observable_prediction(x_eval, pred_eval_raw)

    x_eval_req = x_eval.detach().clone().requires_grad_(True)
    pred_eval_req = model(x_eval_req)
    physics_rms = float(
        torch.sqrt(torch.mean(case.physics_residual(x_eval_req, pred_eval_req) ** 2))
        .detach()
        .cpu()
    )
    boundary_rms = float(
        torch.sqrt(torch.mean(case.boundary_residual(x_bc, pred_bc, y_bc) ** 2))
        .detach()
        .cpu()
    )
    rel_l2 = relative_l2(pred_eval, y_eval)
    structure_error = case.structure_error(model, device=torch.device("cpu"))

    loss_values = np.array([row["loss_total"] for row in history], dtype=float)
    tail = loss_values[-min(10, len(loss_values)) :]
    loss_std = float(np.std(tail))
    loss_ratio = float(loss_values[-1] / max(loss_values[0], 1e-12))

    scalar_metrics = {
        "physics_rms": physics_rms,
        "boundary_rms": boundary_rms,
        "rel_l2": rel_l2,
        "structure_error": structure_error,
        "loss_std": loss_std,
        "loss_ratio": loss_ratio,
    }
    reliability = build_reliability_summary(scalar_metrics, thresholds)

    return {
        "case": case.name,
        "scalar_metrics": scalar_metrics,
        "per_output_metrics": case.named_error_metrics(pred_eval, y_eval),
        "reliability": reliability,
    }
