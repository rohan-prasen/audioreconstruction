from __future__ import annotations

import torch
import torch.nn as nn
from torch.utils.checkpoint import checkpoint

from model.config import ModelConfig


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, stride: int = 1, dilation: int = 1) -> None:
        super().__init__()
        padding = (kernel_size * dilation - dilation) // 2
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, stride=stride, padding=padding, dilation=dilation)
        self.norm = nn.BatchNorm1d(out_ch)
        self.act = nn.LeakyReLU(0.2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.norm(self.conv(x)))


class EncoderBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int) -> None:
        super().__init__()
        self.conv1 = ConvBlock(in_ch, out_ch, kernel_size)
        self.conv2 = ConvBlock(out_ch, out_ch, kernel_size)
        self.downsample = nn.Conv1d(out_ch, out_ch, kernel_size=4, stride=2, padding=1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.conv1(x)
        skip = self.conv2(x)
        down = self.downsample(skip)
        return down, skip


class DecoderBlock(nn.Module):
    def __init__(self, in_ch: int, skip_ch: int, out_ch: int, kernel_size: int) -> None:
        super().__init__()
        self.upsample = nn.ConvTranspose1d(in_ch, in_ch, kernel_size=4, stride=2, padding=1)
        self.conv1 = ConvBlock(in_ch + skip_ch, out_ch, kernel_size)
        self.conv2 = ConvBlock(out_ch, out_ch, kernel_size)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.upsample(x)
        diff = skip.shape[-1] - x.shape[-1]
        if diff > 0:
            x = nn.functional.pad(x, (0, diff))
        elif diff < 0:
            skip = nn.functional.pad(skip, (0, -diff))
        x = torch.cat([x, skip], dim=1)
        x = self.conv1(x)
        x = self.conv2(x)
        return x


class Bottleneck(nn.Module):
    def __init__(self, channels: int, kernel_size: int, dilations: tuple[int, ...]) -> None:
        super().__init__()
        self.layers = nn.ModuleList(
            ConvBlock(channels, channels, kernel_size, dilation=d) for d in dilations
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for layer in self.layers:
            x = x + layer(x)
        return x


class Generator(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        mults = cfg.channel_multipliers
        base = cfg.base_channels
        ks = cfg.kernel_size
        dks = cfg.decoder_kernel_size

        channels = [cfg.in_channels] + [base * m for m in mults]

        self.encoders = nn.ModuleList(
            EncoderBlock(channels[i], channels[i + 1], ks)
            for i in range(len(mults))
        )

        self.bottleneck = Bottleneck(channels[-1], ks, cfg.bottleneck_dilations)

        dec_channels = list(reversed(channels[1:]))
        self.decoders = nn.ModuleList(
            DecoderBlock(dec_channels[i], dec_channels[i], dec_channels[i + 1], dks)
            for i in range(len(mults) - 1)
        )
        self.final_decoder = DecoderBlock(dec_channels[-1], dec_channels[-1], base, dks)

        self.head = nn.Sequential(
            nn.Conv1d(base, cfg.in_channels, kernel_size=7, padding=3),
            nn.Tanh(),
        )

        self.use_checkpointing = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        skips: list[torch.Tensor] = []

        for encoder in self.encoders:
            if self.use_checkpointing and self.training:
                x, skip = checkpoint(encoder, x, use_reentrant=False)
            else:
                x, skip = encoder(x)
            skips.append(skip)

        x = self.bottleneck(x)

        skips = list(reversed(skips))
        for i, decoder in enumerate(self.decoders):
            x = decoder(x, skips[i])

        x = self.final_decoder(x, skips[-1])
        x = self.head(x)

        diff = residual.shape[-1] - x.shape[-1]
        if diff > 0:
            x = nn.functional.pad(x, (0, diff))
        elif diff < 0:
            x = x[:, :, : residual.shape[-1]]

        return x + residual
