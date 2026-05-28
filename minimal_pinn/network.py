from __future__ import annotations

from typing import Iterable, List

import torch
from torch import nn


class Sine(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sin(x)


def build_activation(name: str) -> nn.Module:
    table = {
        "tanh": nn.Tanh(),
        "relu": nn.ReLU(),
        "gelu": nn.GELU(),
        "silu": nn.SiLU(),
        "sin": Sine(),
    }
    if name not in table:
        raise ValueError(f"Unsupported activation: {name}")
    return table[name]


class MLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_layers: Iterable[int],
        activation: str,
    ) -> None:
        super().__init__()
        dims: List[int] = [input_dim, *hidden_layers, output_dim]
        layers = []
        act = build_activation(activation)
        for idx in range(len(dims) - 2):
            layers.append(nn.Linear(dims[idx], dims[idx + 1]))
            layers.append(act.__class__())
        layers.append(nn.Linear(dims[-2], dims[-1]))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
