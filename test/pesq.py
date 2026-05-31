"""PESQ score calculation between two audio files (FLAC/MP3/WAV)."""
from __future__ import annotations

from pathlib import Path

import click
import numpy as np
import torchaudio
import torchaudio.functional as F
from pesq import pesq as _pesq


_PESQ_SR = {
    "nb": 8000,
    "wb": 16000,
}

# PESQ C library crashes on long audio; process in 10-second chunks
_CHUNK_SECONDS = 10


def load_mono(path: Path, target_sr: int) -> np.ndarray:
    waveform, sr = torchaudio.load(str(path))
    if sr != target_sr:
        waveform = F.resample(waveform, sr, target_sr)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    # PESQ requires contiguous float32
    return np.ascontiguousarray(waveform.squeeze().numpy(), dtype=np.float32)


def compute_pesq(ref_path: Path, deg_path: Path, mode: str) -> float:
    target_sr = _PESQ_SR[mode]
    ref = load_mono(ref_path, target_sr)
    deg = load_mono(deg_path, target_sr)

    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]

    # Normalize together so amplitude difference doesn't affect score
    peak = max(float(np.abs(ref).max()), float(np.abs(deg).max()), 1e-8)
    ref = ref / peak
    deg = deg / peak

    chunk_size = _CHUNK_SECONDS * target_sr
    scores = []
    for start in range(0, min_len, chunk_size):
        end = start + chunk_size
        ref_chunk = np.ascontiguousarray(ref[start:end])
        deg_chunk = np.ascontiguousarray(deg[start:end])
        # Skip chunks shorter than 0.25 s — PESQ needs minimum signal length
        if len(ref_chunk) < target_sr // 4:
            continue
        try:
            scores.append(_pesq(target_sr, ref_chunk, deg_chunk, mode))
        except Exception as e:
            click.echo(f"[warn] chunk {start//target_sr}s skipped: {e}", err=True)

    if not scores:
        raise RuntimeError("No valid chunks produced a PESQ score.")

    return float(np.mean(scores))


@click.command()
@click.argument("reference", type=click.Path(exists=True, path_type=Path))
@click.argument("degraded", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--mode",
    type=click.Choice(["nb", "wb"]),
    default="wb",
    show_default=True,
    help="nb=narrowband@8kHz, wb=wideband@16kHz",
)
@click.option("--verbose", "-v", is_flag=True, help="Print per-file details.")
def main(reference: Path, degraded: Path, mode: str, verbose: bool) -> None:
    """Calculate PESQ score between REFERENCE and DEGRADED audio files.

    REFERENCE is typically the lossless FLAC; DEGRADED is the lossy MP3
    or reconstructed output. PESQ range: -0.5 (worst) to 4.5 (best).
    """
    if verbose:
        click.echo(f"Reference : {reference}")
        click.echo(f"Degraded  : {degraded}")
        click.echo(f"Mode      : {mode} ({_PESQ_SR[mode]} Hz)")

    score = compute_pesq(reference, degraded, mode)
    click.echo(f"PESQ ({mode}): {score:.4f}")


if __name__ == "__main__":
    main()
