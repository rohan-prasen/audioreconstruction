"""Log-Spectral Distance between two audio files."""
from __future__ import annotations

from pathlib import Path

import click
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


def compute_lsd(ref: torch.Tensor, deg: torch.Tensor) -> float:
    """Log-Spectral Distance — lower is better (0 = identical)."""
    stft = T.Spectrogram(n_fft=2048, hop_length=512, power=2)
    ref_spec = stft(ref)
    deg_spec = stft(deg)

    min_t = min(ref_spec.shape[-1], deg_spec.shape[-1])
    log_ref = torch.log10(ref_spec[:, :min_t] + 1e-8)
    log_deg = torch.log10(deg_spec[:, :min_t] + 1e-8)

    # Per-frame LSD averaged across time
    frame_lsd = torch.sqrt(((log_ref - log_deg) ** 2).mean(dim=0))
    return float(frame_lsd.mean())


@click.command()
@click.argument("reference", type=click.Path(exists=True, path_type=Path))
@click.argument("degraded", type=click.Path(exists=True, path_type=Path))
@click.option("--sr", default=44100, show_default=True, help="Sample rate for comparison.")
@click.option("--verbose", "-v", is_flag=True)
def main(reference: Path, degraded: Path, sr: int, verbose: bool) -> None:
    """Log-Spectral Distance between REFERENCE and DEGRADED audio.

    Measures frequency content fidelity (log10 scale). Lower is better (0 = identical).
    """
    if verbose:
        click.echo(f"Reference : {reference}")
        click.echo(f"Degraded  : {degraded}")
        click.echo(f"Sample rate: {sr} Hz")

    ref = load_mono(reference, sr)
    deg = load_mono(degraded, sr)
    min_len = min(len(ref), len(deg))
    score = compute_lsd(ref[:min_len], deg[:min_len])
    click.echo(f"LSD: {score:.4f}")


if __name__ == "__main__":
    main()
