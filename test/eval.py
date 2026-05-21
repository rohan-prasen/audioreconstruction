from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from torchaudio.functional import resample

console = Console()

SAMPLE_RATE = 44100
STFT_SIZES = (512, 1024, 2048)


def load_flac(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data.T, sr


def align_pair(
    ref: np.ndarray, rec: np.ndarray, sr_ref: int, sr_rec: int
) -> tuple[np.ndarray, np.ndarray, int]:
    target_sr = SAMPLE_RATE

    if sr_ref != target_sr:
        ref = resample(torch.from_numpy(ref), sr_ref, target_sr).numpy()
    if sr_rec != target_sr:
        rec = resample(torch.from_numpy(rec), sr_rec, target_sr).numpy()

    channels = min(ref.shape[0], rec.shape[0])
    ref = ref[:channels]
    rec = rec[:channels]

    length = min(ref.shape[-1], rec.shape[-1])
    return ref[:, :length], rec[:, :length], target_sr


def compute_snr(ref: np.ndarray, rec: np.ndarray) -> float:
    signal_power = float((ref**2).mean())
    noise_power = float(((ref - rec) ** 2).mean())
    return float(10 * np.log10(signal_power / max(noise_power, 1e-10)))


def compute_spectrogram_similarity(ref: np.ndarray, rec: np.ndarray) -> float:
    ref_flat = ref.reshape(-1)
    rec_flat = rec.reshape(-1)

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
        rec_spec = torch.stft(
            torch.from_numpy(rec_flat),
            n_fft=n_fft,
            hop_length=hop,
            window=window,
            return_complex=True,
        ).abs()

        ref_vec = ref_spec.flatten().double()
        rec_vec = rec_spec.flatten().double()

        dot = torch.dot(ref_vec, rec_vec)
        norm_ref = torch.linalg.norm(ref_vec)
        norm_rec = torch.linalg.norm(rec_vec)
        cosine = float(dot / (norm_ref * norm_rec + 1e-10))
        similarities.append(max(0.0, cosine) * 100.0)

    return float(np.mean(similarities))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare an original FLAC against a reconstructed FLAC"
    )
    parser.add_argument("original", type=Path, help="Path to the original (reference) FLAC")
    parser.add_argument("reconstructed", type=Path, help="Path to the reconstructed FLAC")
    args = parser.parse_args()

    if not args.original.exists():
        console.print(f"[red]Original file not found: {args.original}[/red]")
        sys.exit(1)
    if not args.reconstructed.exists():
        console.print(f"[red]Reconstructed file not found: {args.reconstructed}[/red]")
        sys.exit(1)

    console.print(f"Original:      [cyan]{args.original}[/cyan]")
    console.print(f"Reconstructed: [cyan]{args.reconstructed}[/cyan]")
    console.print()

    ref_data, sr_ref = load_flac(args.original)
    rec_data, sr_rec = load_flac(args.reconstructed)

    ref, rec, sr = align_pair(ref_data, rec_data, sr_ref, sr_rec)

    snr = compute_snr(ref, rec)
    similarity = compute_spectrogram_similarity(ref, rec)

    table = Table(title="Comparison Results", show_header=True, header_style="bold")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Interpretation")

    if snr >= 25:
        snr_style = "[green]"
        snr_label = "Excellent"
    elif snr >= 15:
        snr_style = "[yellow]"
        snr_label = "Good"
    elif snr >= 10:
        snr_style = "[bright_yellow]"
        snr_label = "Moderate"
    else:
        snr_style = "[red]"
        snr_label = "Poor"

    table.add_row("SNR", f"{snr_style}{snr:.2f} dB[/]", snr_label)

    if similarity >= 95:
        sim_style = "[green]"
        sim_label = "Near-identical"
    elif similarity >= 85:
        sim_style = "[yellow]"
        sim_label = "Very similar"
    elif similarity >= 70:
        sim_style = "[bright_yellow]"
        sim_label = "Similar"
    else:
        sim_style = "[red]"
        sim_label = "Divergent"

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
        console.print(Panel("[green bold]HIGH FIDELITY[/] — reconstruction closely matches the original", border_style="green"))
    elif similarity >= 80 and snr >= 10:
        console.print(Panel("[yellow bold]ACCEPTABLE[/] — audible differences but structurally intact", border_style="yellow"))
    else:
        console.print(Panel("[red bold]LOW FIDELITY[/] — significant divergence from original", border_style="red"))


if __name__ == "__main__":
    main()
