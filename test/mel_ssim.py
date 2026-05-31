"""Mel-spectrogram SSIM between two audio files."""
from __future__ import annotations

from pathlib import Path

import click
import numpy as np
import torch
import torchaudio
import torchaudio.functional as F
import torchaudio.transforms as T


def load_mono(path: Path, target_sr: int) -> torch.Tensor:
    waveform, sr = torchaudio.load(str(path))
    if sr != target_sr:
        waveform = F.resample(waveform, sr, target_sr)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform.squeeze()


def _ssim_vectors(x: np.ndarray, y: np.ndarray, k1: float = 0.01, k2: float = 0.03, L: float = 1.0) -> float:
    c1 = (k1 * L) ** 2
    c2 = (k2 * L) ** 2
    mu_x, mu_y = x.mean(), y.mean()
    sigma_x = x.var()
    sigma_y = y.var()
    sigma_xy = float(np.cov(x, y)[0, 1])
    num = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    den = (mu_x ** 2 + mu_y ** 2 + c1) * (sigma_x + sigma_y + c2)
    return float(num / den)


def compute_mel_ssim(ref: torch.Tensor, deg: torch.Tensor, sr: int) -> float:
    mel = T.MelSpectrogram(sample_rate=sr, n_fft=2048, hop_length=512, n_mels=128, power=2.0)
    ref_mel = torch.log1p(mel(ref)).numpy()
    deg_mel = torch.log1p(mel(deg)).numpy()

    min_t = min(ref_mel.shape[1], deg_mel.shape[1])
    ref_mel = ref_mel[:, :min_t]
    deg_mel = deg_mel[:, :min_t]

    combined_max = max(float(ref_mel.max()), float(deg_mel.max()), 1e-8)
    ref_mel = ref_mel / combined_max
    deg_mel = deg_mel / combined_max

    scores = [_ssim_vectors(ref_mel[i], deg_mel[i]) for i in range(ref_mel.shape[0])]
    return float(np.mean(scores))


@click.command()
@click.argument("reference", type=click.Path(exists=True, path_type=Path))
@click.argument("degraded", type=click.Path(exists=True, path_type=Path))
@click.option("--sr", default=44100, show_default=True, help="Sample rate for comparison.")
@click.option("--verbose", "-v", is_flag=True)
def main(reference: Path, degraded: Path, sr: int, verbose: bool) -> None:
    """Mel-spectrogram SSIM between REFERENCE and DEGRADED audio.

    Structural similarity on mel spectrograms — perceptually meaningful for music.
    Range: -1 to 1. Higher is better (1 = identical).
    """
    if verbose:
        click.echo(f"Reference : {reference}")
        click.echo(f"Degraded  : {degraded}")
        click.echo(f"Sample rate: {sr} Hz")

    ref = load_mono(reference, sr)
    deg = load_mono(degraded, sr)
    min_len = min(len(ref), len(deg))
    score = compute_mel_ssim(ref[:min_len], deg[:min_len], sr)
    click.echo(f"Mel-SSIM: {score:.4f}")


if __name__ == "__main__":
    main()
