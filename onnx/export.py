from __future__ import annotations

from pathlib import Path

import click
import numpy as np
import onnxruntime as ort
import torch
from rich.console import Console

from model.evaluate import load_generator

console = Console()

DUMMY_SHAPE = (1, 2, 131072)  # matches ModelConfig.segment_length; chunking happens outside forward()


@click.command()
@click.option("--checkpoint", type=click.Path(exists=True, path_type=Path), default=Path("model/checkpoints/best"))
@click.option("--output", "output_dir", type=click.Path(path_type=Path), default=Path("onnx/exported"))
@click.option("--opset", default=18, type=int)
@click.option("--skip-verify", is_flag=True)
def main(checkpoint: Path, output_dir: Path, opset: int, skip_verify: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")

    gen = load_generator(checkpoint, device)
    cfg = gen.cfg
    dummy = torch.randn(*DUMMY_SHAPE)

    onnx_path = output_dir / "model.onnx"
    torch.onnx.export(
        gen,
        dummy,
        str(onnx_path),
        input_names=["audio"],
        output_names=["audio_out"],
        opset_version=opset,
        dynamo=False,  # legacy TorchScript exporter — avoids the onnxscript dependency the dynamo path requires
    )
    cfg.save(output_dir / "config.json")

    size_mb = onnx_path.stat().st_size / 1e6
    console.print(f"[green]Exported {onnx_path} ({size_mb:.1f} MB)[/green]")
    console.print(f"[green]Exported {output_dir / 'config.json'}[/green]")

    if skip_verify:
        return

    with torch.no_grad():
        pt_out = gen(dummy).numpy()

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_out = session.run(["audio_out"], {"audio": dummy.numpy()})[0]

    max_diff = float(np.abs(pt_out - ort_out).max())
    if max_diff < 1e-3:
        console.print(f"[green]PASS[/green] max abs diff vs PyTorch: {max_diff:.6f}")
    else:
        console.print(f"[red]FAIL[/red] max abs diff vs PyTorch: {max_diff:.6f} (threshold 1e-3)")
        raise SystemExit(1)

    console.print()
    console.print("Commit the updated model (tracked via git-lfs, see .gitattributes):")
    console.print(f"  git add {output_dir}/model.onnx {output_dir}/config.json onnx/manifest.json")
    console.print("  git commit -m 'chore: update exported onnx model'")


if __name__ == "__main__":
    main()
