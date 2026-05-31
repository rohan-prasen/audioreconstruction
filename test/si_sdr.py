"""Scale-Invariant Signal-to-Distortion Ratio between two audio files."""
from __future__ import annotations

from pathlib import Path

import click
import numpy as np
import torchaudio
import torchaudio.functional as F


def load_mono(path: Path, target_sr: int) -> np.ndarray:
    waveform, sr = torchaudio.load(str(path))
    if sr != target_sr:
        waveform = F.resample(waveform, sr, target_sr)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform.squeeze().numpy().astype(np.float64)


def compute_si_sdr(ref: np.ndarray, deg: np.ndarray) -> float:
    ref = ref - ref.mean()
    deg = deg - deg.mean()

    dot = float(np.dot(deg, ref))
    ref_power = float(np.dot(ref, ref)) + 1e-8
    s_target = (dot / ref_power) * ref

    noise = deg - s_target
    target_power = float(np.dot(s_target, s_target)) + 1e-8
    noise_power = float(np.dot(noise, noise)) + 1e-8
    return 10.0 * np.log10(target_power / noise_power)


@click.command()
@click.argument("reference", type=click.Path(exists=True, path_type=Path))
@click.argument("degraded", type=click.Path(exists=True, path_type=Path))
@click.option("--sr", default=44100, show_default=True, help="Sample rate for comparison.")
@click.option("--verbose", "-v", is_flag=True)
def main(reference: Path, degraded: Path, sr: int, verbose: bool) -> None:
    """Scale-Invariant SDR (dB) between REFERENCE and DEGRADED audio.

    Better than plain SNR — robust to amplitude scaling.
    Higher is better. >20 dB = good, >30 dB = excellent.
    """
    if verbose:
        click.echo(f"Reference : {reference}")
        click.echo(f"Degraded  : {degraded}")
        click.echo(f"Sample rate: {sr} Hz")

    ref = load_mono(reference, sr)
    deg = load_mono(degraded, sr)
    min_len = min(len(ref), len(deg))
    score = compute_si_sdr(ref[:min_len], deg[:min_len])
    click.echo(f"SI-SDR: {score:.4f} dB")


if __name__ == "__main__":
    main()
