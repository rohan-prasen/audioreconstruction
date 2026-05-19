from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SpectralLoss(nn.Module):
    def __init__(self, fft_sizes: tuple[int, ...] = (512, 1024, 2048)) -> None:
        super().__init__()
        self.fft_sizes = fft_sizes

    def forward(self, predicted: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        b, c, t = predicted.shape
        pred_flat = predicted.reshape(b * c, t)
        targ_flat = target.reshape(b * c, t)

        loss = torch.tensor(0.0, device=predicted.device)
        for n_fft in self.fft_sizes:
            hop = n_fft // 4
            window = torch.hann_window(n_fft, device=predicted.device)
            pred_spec = torch.stft(pred_flat, n_fft=n_fft, hop_length=hop, window=window, return_complex=True).abs()
            targ_spec = torch.stft(targ_flat, n_fft=n_fft, hop_length=hop, window=window, return_complex=True).abs()
            loss = loss + F.l1_loss(pred_spec, targ_spec)
            loss = loss + F.l1_loss(pred_spec.log1p(), targ_spec.log1p())
        return loss / len(self.fft_sizes)


def generator_adversarial_loss(disc_fake_logits: list[torch.Tensor]) -> torch.Tensor:
    loss = torch.tensor(0.0, device=disc_fake_logits[0].device)
    for logit in disc_fake_logits:
        loss = loss + torch.mean((logit - 1.0) ** 2)
    return loss / len(disc_fake_logits)


def discriminator_loss(
    disc_real_logits: list[torch.Tensor],
    disc_fake_logits: list[torch.Tensor],
) -> torch.Tensor:
    loss = torch.tensor(0.0, device=disc_real_logits[0].device)
    for real_logit, fake_logit in zip(disc_real_logits, disc_fake_logits):
        loss = loss + torch.mean((real_logit - 1.0) ** 2)
        loss = loss + torch.mean(fake_logit ** 2)
    return loss / len(disc_real_logits)


def feature_matching_loss(
    real_features: list[list[torch.Tensor]],
    fake_features: list[list[torch.Tensor]],
) -> torch.Tensor:
    loss = torch.tensor(0.0, device=real_features[0][0].device)
    count = 0
    for real_feats, fake_feats in zip(real_features, fake_features):
        for real_f, fake_f in zip(real_feats, fake_feats):
            loss = loss + F.l1_loss(fake_f, real_f.detach())
            count += 1
    return loss / max(count, 1)
