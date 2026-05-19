from __future__ import annotations

from pathlib import Path

import click
import numpy as np
import soundfile as sf
import torch
from pesq import pesq
from rich.console import Console
from rich.table import Table
from safetensors.torch import load_file
from torchaudio.functional import resample

from model.config import ModelConfig
from model.generator import Generator
from model.utils import load_audio, normalize_audio

console = Console()


def load_generator(checkpoint_dir: Path, device: torch.device) -> Generator:
    config_path = checkpoint_dir / "config.json"
    if config_path.exists():
        cfg = ModelConfig.load(config_path)
    else:
        cfg = ModelConfig()
    gen = Generator(cfg)
    gen.load_state_dict(load_file(str(checkpoint_dir / "generator.safetensors")))
    gen.to(device)
    gen.eval()
    gen.use_checkpointing = False
    return gen


@torch.no_grad()
def reconstruct(generator: Generator, input_path: Path, device: torch.device) -> torch.Tensor:
    sr = generator.cfg.sample_rate
    waveform = load_audio(input_path, target_sr=sr, channels=generator.cfg.in_channels)
    waveform = normalize_audio(waveform)
    seg_len = generator.cfg.segment_length
    length = waveform.shape[-1]

    if length <= seg_len:
        padded = torch.nn.functional.pad(waveform, (0, seg_len - length))
        inp = padded.unsqueeze(0).to(device)
        with torch.amp.autocast("cuda"):
            out = generator(inp)
        return out.squeeze(0).cpu()[:, :length]

    chunks = []
    for start in range(0, length, seg_len):
        end = min(start + seg_len, length)
        chunk = waveform[:, start:end]
        if chunk.shape[-1] < seg_len:
            chunk = torch.nn.functional.pad(chunk, (0, seg_len - chunk.shape[-1]))
        inp = chunk.unsqueeze(0).to(device)
        with torch.amp.autocast("cuda"):
            out = generator(inp)
        actual_len = min(seg_len, length - start)
        chunks.append(out.squeeze(0).cpu()[:, :actual_len])

    return torch.cat(chunks, dim=-1)


def compute_metrics(
    reconstructed: torch.Tensor,
    reference: torch.Tensor,
    sample_rate: int,
) -> dict[str, float]:
    min_len = min(reconstructed.shape[-1], reference.shape[-1])
    rec = reconstructed[:, :min_len].squeeze().numpy()
    ref = reference[:, :min_len].squeeze().numpy()

    signal_power = float((ref ** 2).mean())
    noise_power = float(((ref - rec) ** 2).mean())
    snr_val = float(10 * np.log10(signal_power / max(noise_power, 1e-10)))

    eval_sr = 16000
    rec_16k = resample(torch.from_numpy(rec).unsqueeze(0), sample_rate, eval_sr).squeeze().numpy()
    ref_16k = resample(torch.from_numpy(ref).unsqueeze(0), sample_rate, eval_sr).squeeze().numpy()

    try:
        pesq_score = pesq(eval_sr, ref_16k, rec_16k, "wb")
    except Exception:
        pesq_score = float("nan")

    return {"snr_db": snr_val, "pesq": pesq_score}


@click.command()
@click.option("--checkpoint", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--input", "input_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--output", "output_path", type=click.Path(path_type=Path), default=None)
@click.option("--reference", type=click.Path(exists=True, path_type=Path), default=None)
def main(
    checkpoint: Path,
    input_path: Path,
    output_path: Path | None,
    reference: Path | None,
) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    console.print(f"Device: [bold]{device}[/bold]")

    generator = load_generator(checkpoint, device)

    if input_path.is_dir():
        files = sorted(input_path.glob("*.mp3"))
        if not files:
            console.print(f"[yellow]No .mp3 files in {input_path}[/yellow]")
            return
    else:
        files = [input_path]

    if output_path is None:
        output_path = Path("output")
    output_path.mkdir(parents=True, exist_ok=True)

    table = Table(title="Results")
    table.add_column("File")
    table.add_column("SNR (dB)", justify="right")
    table.add_column("PESQ", justify="right")

    for f in files:
        console.print(f"Processing: {f.name}")
        result = reconstruct(generator, f, device)
        out_file = output_path / f"{f.stem}.flac"
        audio_out = result.squeeze(0).T.numpy()
        sf.write(str(out_file), audio_out, generator.cfg.sample_rate)

        if reference is not None:
            ref_path = reference / f"{f.stem}.flac" if reference.is_dir() else reference
            if ref_path.exists():
                ref_audio = load_audio(ref_path, target_sr=generator.cfg.sample_rate, channels=generator.cfg.in_channels)
                ref_audio = normalize_audio(ref_audio)
                metrics = compute_metrics(result, ref_audio, generator.cfg.sample_rate)
                table.add_row(f.name, f"{metrics['snr_db']:.2f}", f"{metrics['pesq']:.3f}")
            else:
                table.add_row(f.name, "-", "-")
        else:
            table.add_row(f.name, "-", "-")

    console.print(table)
    console.print(f"[green]Output saved to {output_path}[/green]")


if __name__ == "__main__":
    main()
