from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torchaudio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

SAMPLE_RATE = 44100
STFT_SIZES = (512, 1024, 2048)


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    waveform, sr = torchaudio.load(str(path))
    return waveform.numpy(), sr


def align_pair(
    ref: np.ndarray, test: np.ndarray, sr_ref: int, sr_test: int
) -> tuple[np.ndarray, np.ndarray, int]:
    target_sr = SAMPLE_RATE

    if sr_ref != target_sr:
        ref = torchaudio.functional.resample(
            torch.from_numpy(ref), sr_ref, target_sr
        ).numpy()
    if sr_test != target_sr:
        test = torchaudio.functional.resample(
            torch.from_numpy(test), sr_test, target_sr
        ).numpy()

    channels = min(ref.shape[0], test.shape[0])
    ref = ref[:channels]
    test = test[:channels]

    length = min(ref.shape[-1], test.shape[-1])
    return ref[:, :length], test[:, :length], target_sr


def compute_snr(ref: np.ndarray, test: np.ndarray) -> float:
    signal_power = float((ref**2).mean())
    noise_power = float(((ref - test) ** 2).mean())
    return float(10 * np.log10(signal_power / max(noise_power, 1e-10)))


def compute_spectrogram_similarity(ref: np.ndarray, test: np.ndarray) -> float:
    ref_flat = ref.reshape(-1)
    test_flat = test.reshape(-1)

    similarities = []
    for n_fft in STFT_SIZES:
        hop = n_fft // 4
        window = torch.hann_window(n_fft)

        ref_spec = torch.stft(
            torch.from_numpy(ref_flat),
            n_fft=n_fft,
            hop_length=hop,
            window=window,
            return_complex=True,
        ).abs()
        test_spec = torch.stft(
            torch.from_numpy(test_flat),
            n_fft=n_fft,
            hop_length=hop,
            window=window,
            return_complex=True,
        ).abs()

        ref_vec = ref_spec.flatten().double()
        test_vec = test_spec.flatten().double()

        dot = torch.dot(ref_vec, test_vec)
        norm_ref = torch.linalg.norm(ref_vec)
        norm_test = torch.linalg.norm(test_vec)
        cosine = float(dot / (norm_ref * norm_test + 1e-10))
        similarities.append(max(0.0, cosine) * 100.0)

    return float(np.mean(similarities))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a reference FLAC against a lossy MP3 — measures how much quality the MP3 encoding lost"
    )
    parser.add_argument("flac", type=Path, help="Path to the reference (lossless) FLAC file")
    parser.add_argument("mp3", type=Path, help="Path to the MP3 file being tested")
    args = parser.parse_args()

    if not args.flac.exists():
        console.print(f"[red]FLAC file not found: {args.flac}[/red]")
        sys.exit(1)
    if not args.mp3.exists():
        console.print(f"[red]MP3 file not found: {args.mp3}[/red]")
        sys.exit(1)

    console.print(f"Reference (FLAC): [cyan]{args.flac}[/cyan]")
    console.print(f"Test (MP3):       [cyan]{args.mp3}[/cyan]")
    console.print()

    ref_data, sr_ref = load_audio(args.flac)
    test_data, sr_test = load_audio(args.mp3)

    ref, test, sr = align_pair(ref_data, test_data, sr_ref, sr_test)

    snr = compute_snr(ref, test)
    similarity = compute_spectrogram_similarity(ref, test)

    table = Table(title="FLAC vs MP3 — Lossy Encoding Quality", show_header=True, header_style="bold")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Interpretation")

    if snr >= 25:
        snr_style, snr_label = "[green]", "Excellent"
    elif snr >= 15:
        snr_style, snr_label = "[yellow]", "Good"
    elif snr >= 10:
        snr_style, snr_label = "[bright_yellow]", "Moderate"
    else:
        snr_style, snr_label = "[red]", "Poor"

    table.add_row("SNR", f"{snr_style}{snr:.2f} dB[/]", snr_label)

    if similarity >= 99:
        sim_style, sim_label = "[green]", "Transparent (no audible loss)"
    elif similarity >= 95:
        sim_style, sim_label = "[green]", "Near-transparent"
    elif similarity >= 85:
        sim_style, sim_label = "[yellow]", "Mild loss"
    elif similarity >= 70:
        sim_style, sim_label = "[bright_yellow]", "Noticeable loss"
    else:
        sim_style, sim_label = "[red]", "Severe loss"

    table.add_row(
        "Spectrogram Similarity",
        f"{sim_style}{similarity:.2f}%[/]",
        sim_label,
    )

    duration = ref.shape[-1] / sr
    table.add_row("Duration", f"{duration:.1f}s", f"{ref.shape[0]}ch @ {sr} Hz")

    console.print(table)

    console.print()
    if similarity >= 95 and snr >= 20:
        console.print(Panel(
            "[green bold]TRANSPARENT[/] — MP3 is perceptually close to the lossless source",
            border_style="green",
        ))
    elif similarity >= 80 and snr >= 10:
        console.print(Panel(
            "[yellow bold]ACCEPTABLE[/] — some quality lost but structurally intact",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            "[red bold]SIGNIFICANT LOSS[/] — MP3 encoding degraded the audio substantially",
            border_style="red",
        ))


if __name__ == "__main__":
    main()
