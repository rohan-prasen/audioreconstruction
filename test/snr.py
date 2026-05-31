"""Signal-to-Noise Ratio between two audio files."""
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


def compute_snr(ref: np.ndarray, deg: np.ndarray) -> float:
    signal_power = float((ref ** 2).mean())
    noise_power = float(((ref - deg) ** 2).mean())
    return 10.0 * np.log10(signal_power / max(noise_power, 1e-12))


@click.command()
@click.argument("reference", type=click.Path(exists=True, path_type=Path))
@click.argument("degraded", type=click.Path(exists=True, path_type=Path))
@click.option("--sr", default=44100, show_default=True, help="Sample rate for comparison.")
@click.option("--verbose", "-v", is_flag=True)
def main(reference: Path, degraded: Path, sr: int, verbose: bool) -> None:
    """Signal-to-Noise Ratio (dB) between REFERENCE and DEGRADED audio.

    Higher is better. Typical range: 10–40 dB.
    A good reconstruction should be above 20 dB.
    """
    if verbose:
        click.echo(f"Reference : {reference}")
        click.echo(f"Degraded  : {degraded}")
        click.echo(f"Sample rate: {sr} Hz")

    ref = load_mono(reference, sr)
    deg = load_mono(degraded, sr)
    min_len = min(len(ref), len(deg))
    score = compute_snr(ref[:min_len], deg[:min_len])
    click.echo(f"SNR: {score:.4f} dB")


if __name__ == "__main__":
    main()
