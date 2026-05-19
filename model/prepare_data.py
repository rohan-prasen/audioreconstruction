from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

BITRATES = (128, 256, 320)
console = Console()


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        console.print("[red]FFmpeg not found.[/red] Install it:")
        console.print("  Ubuntu/Debian: sudo apt install ffmpeg")
        console.print("  macOS: brew install ffmpeg")
        console.print("  Fedora: sudo dnf install ffmpeg")
        raise SystemExit(1)


def transcode_file(src: Path, dst: Path, bitrate: int) -> bool:
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src),
            "-codec:a", "libmp3lame", "-b:a", f"{bitrate}k",
            "-ar", "44100",
            str(dst),
        ],
        capture_output=True,
        check=True,
    )
    return True


@click.command()
@click.option("--input", "input_dir", type=click.Path(exists=True, path_type=Path), default=Path("data/lossless"))
@click.option("--output", "output_dir", type=click.Path(path_type=Path), default=Path("data/lossy"))
def main(input_dir: Path, output_dir: Path) -> None:
    check_ffmpeg()

    flac_files = sorted(input_dir.glob("*.flac"))
    if not flac_files:
        console.print(f"[yellow]No .flac files found in {input_dir}[/yellow]")
        return

    total = len(flac_files) * len(BITRATES)
    created = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Transcoding", total=total)

        for flac_path in flac_files:
            stem = flac_path.stem
            for bitrate in BITRATES:
                dst = output_dir / str(bitrate) / f"{stem}.mp3"
                progress.update(task, description=f"{stem} → {bitrate}k")
                if transcode_file(flac_path, dst, bitrate):
                    created += 1
                else:
                    skipped += 1
                progress.advance(task)

    console.print(f"[green]Done.[/green] Created: {created}, Skipped (existing): {skipped}")


if __name__ == "__main__":
    main()
