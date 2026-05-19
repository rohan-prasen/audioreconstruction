from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from safetensors.torch import load_file, save_file

from model.config import ModelConfig

console = Console()


@click.command()
@click.option("--checkpoint", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--output", "output_dir", type=click.Path(path_type=Path), default=Path("exported"))
def main(checkpoint: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = checkpoint / "config.json"
    if config_path.exists():
        cfg = ModelConfig.load(config_path)
    else:
        cfg = ModelConfig()
        console.print("[yellow]No config.json in checkpoint, using defaults[/yellow]")

    weights = load_file(str(checkpoint / "generator.safetensors"))
    save_file(weights, str(output_dir / "model.safetensors"))
    cfg.save(output_dir / "config.json")

    console.print(f"[green]Exported to {output_dir}/[/green]")
    console.print(f"  model.safetensors  ({sum(v.numel() for v in weights.values()) / 1e6:.1f}M params)")
    console.print("  config.json")
    console.print()
    console.print("Push to HuggingFace:")
    console.print(f"  huggingface-cli upload <your-username>/audio-super-resolution {output_dir}/")


if __name__ == "__main__":
    main()
