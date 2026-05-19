from __future__ import annotations

import torch
import torch.nn as nn


class DiscriminatorBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, stride: int) -> None:
        super().__init__()
        padding = (kernel_size - 1) // 2
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, stride=stride, padding=padding)
        self.norm = nn.BatchNorm1d(out_ch)
        self.act = nn.LeakyReLU(0.2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.norm(self.conv(x)))


class ScaleDiscriminator(nn.Module):
    def __init__(self, in_channels: int = 1) -> None:
        super().__init__()
        self.layers = nn.ModuleList([
            DiscriminatorBlock(in_channels, 64, kernel_size=15, stride=1),
            DiscriminatorBlock(64, 128, kernel_size=41, stride=4),
            DiscriminatorBlock(128, 256, kernel_size=41, stride=4),
            DiscriminatorBlock(256, 512, kernel_size=41, stride=4),
            DiscriminatorBlock(512, 512, kernel_size=5, stride=1),
        ])
        self.head = nn.Conv1d(512, 1, kernel_size=3, padding=1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor]]:
        features = []
        for layer in self.layers:
            x = layer(x)
            features.append(x)
        logit = self.head(x)
        return logit, features


class MultiScaleDiscriminator(nn.Module):
    def __init__(self, in_channels: int = 1, num_scales: int = 3) -> None:
        super().__init__()
        self.discriminators = nn.ModuleList(
            ScaleDiscriminator(in_channels) for _ in range(num_scales)
        )
        self.downsamplers = nn.ModuleList(
            nn.AvgPool1d(kernel_size=4, stride=2, padding=1)
            for _ in range(num_scales - 1)
        )

    def forward(
        self, x: torch.Tensor
    ) -> tuple[list[torch.Tensor], list[list[torch.Tensor]]]:
        logits = []
        all_features = []
        for i, disc in enumerate(self.discriminators):
            if i > 0:
                x = self.downsamplers[i - 1](x)
            logit, features = disc(x)
            logits.append(logit)
            all_features.append(features)
        return logits, all_features
