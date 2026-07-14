"""Click command-line interface for audioreconstructor."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from . import batch, ui
from .cli import CliError, doctor as run_doctor, get_package_version, run_inference, setup_assets

PROVIDERS = ("auto", "cpu", "directml")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(get_package_version(), "-V", "--version", prog_name="audioreconstructor")
def cli() -> None:
    """Enhance audio with the Audioreconstructor ONNX model."""


@cli.command()
def setup() -> None:
    """Download and verify the native runtime and model."""
    ui.banner(get_package_version())
    try:
        setup_assets(report=ui.rich_reporter())
    except CliError as exc:
        ui.error_panel(str(exc))
        sys.exit(1)


@cli.command()
def doctor() -> None:
    """Verify cached assets and run a runtime self-test."""
    ui.banner(get_package_version())
    sys.exit(run_doctor(report=ui.rich_reporter()))


@cli.command()
@click.option("--input", "input_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Input audio file.")
@click.option("--folder", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Folder of audio files to enhance recursively.")
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), help="Output FLAC file (with --input).")
@click.option("--provider", type=click.Choice(PROVIDERS), default="auto", show_default=True, help="ONNX execution provider.")
def enhance(input_path: Path | None, folder: Path | None, output_path: Path | None, provider: str) -> None:
    """Reconstruct high-fidelity FLAC from lossy audio."""
    if bool(input_path) == bool(folder):
        raise click.UsageError("Provide exactly one of --input or --folder.")
    ui.banner(get_package_version())
    try:
        if folder is not None:
            _enhance_folder(folder, provider)
        else:
            if output_path is None:
                raise click.UsageError("--output is required with --input.")
            _enhance_single(input_path, output_path, provider)  # type: ignore[arg-type]
    except CliError as exc:
        ui.error_panel(str(exc))
        sys.exit(1)


def _enhance_single(input_path: Path, output_path: Path, provider: str) -> None:
    with ui.enhance_progress() as progress:
        task = progress.add_task(input_path.name, total=100)
        code, error = run_inference(
            input_path,
            output_path,
            provider,
            on_progress=lambda pct: progress.update(task, completed=pct),
        )
        if code == 0:
            progress.update(task, completed=100)
    if code == 0:
        ui.result_panel(str(output_path))
    else:
        ui.error_panel(error or f"enhancement failed (exit code {code})")
        sys.exit(1)


def _enhance_folder(folder: Path, provider: str) -> None:
    files = batch.discover_audio_files(folder)
    if not files:
        raise CliError(f"no audio files found in {folder}")
    ui.note(f"Enhancing {len(files)} file(s) from {folder}")

    succeeded = 0
    failures: list[tuple[str, str]] = []
    with ui.enhance_progress() as progress:
        for src in files:
            out = batch.output_path_for(src, folder)
            out.parent.mkdir(parents=True, exist_ok=True)
            name = src.relative_to(folder).as_posix()
            task = progress.add_task(name, total=100)
            code, error = run_inference(
                src,
                out,
                provider,
                on_progress=lambda pct, t=task: progress.update(t, completed=pct),
            )
            if code == 0:
                progress.update(task, completed=100)
                succeeded += 1
            else:
                failures.append((name, error or f"exit code {code}"))

    ui.summary_panel(succeeded, failures)
    if failures:
        sys.exit(1)
