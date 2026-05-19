from __future__ import annotations

from pathlib import Path

import click
import torch
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from torch.utils.data import DataLoader

from model.config import DataConfig, ModelConfig, TrainConfig
from model.dataset import build_splits
from model.discriminator import MultiScaleDiscriminator
from model.generator import Generator
from model.losses import (
    SpectralLoss,
    discriminator_loss,
    feature_matching_loss,
    generator_adversarial_loss,
)
from model.utils import load_checkpoint, save_checkpoint, set_seed

console = Console()


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def train_one_epoch(
    generator: Generator,
    discriminator: MultiScaleDiscriminator,
    dataloader: DataLoader,
    opt_g: torch.optim.Optimizer,
    opt_d: torch.optim.Optimizer,
    spectral_loss_fn: SpectralLoss,
    scaler: torch.amp.GradScaler,
    train_cfg: TrainConfig,
    device: torch.device,
    progress: Progress,
    task_id: int,
) -> dict[str, float]:
    generator.train()
    discriminator.train()
    totals: dict[str, float] = {"g_loss": 0, "d_loss": 0, "spec": 0, "feat": 0, "adv": 0}
    steps = 0

    for lossy, lossless in dataloader:
        lossy = lossy.to(device)
        lossless = lossless.to(device)

        # --- Discriminator step ---
        opt_d.zero_grad()
        with torch.amp.autocast("cuda"):
            fake = generator(lossy)
            real_logits, real_features = discriminator(lossless)
            fake_logits, _ = discriminator(fake.detach())
            d_loss = discriminator_loss(real_logits, fake_logits)

        scaler.scale(d_loss).backward()
        scaler.step(opt_d)

        # --- Generator step ---
        opt_g.zero_grad()
        with torch.amp.autocast("cuda"):
            fake_logits_g, fake_features_g = discriminator(fake)
            adv_loss = generator_adversarial_loss(fake_logits_g)
            spec_loss = spectral_loss_fn(fake, lossless)
            feat_loss = feature_matching_loss(real_features, fake_features_g)
            g_loss = (
                adv_loss
                + train_cfg.spectral_loss_weight * spec_loss
                + train_cfg.feature_match_weight * feat_loss
            )

        scaler.scale(g_loss).backward()
        scaler.step(opt_g)
        scaler.update()

        totals["g_loss"] += g_loss.item()
        totals["d_loss"] += d_loss.item()
        totals["spec"] += spec_loss.item()
        totals["feat"] += feat_loss.item()
        totals["adv"] += adv_loss.item()
        steps += 1
        progress.advance(task_id)

    return {k: v / max(steps, 1) for k, v in totals.items()}


@torch.no_grad()
def validate(
    generator: Generator,
    spectral_loss_fn: SpectralLoss,
    dataloader: DataLoader,
    device: torch.device,
) -> float:
    generator.eval()
    total_loss = 0.0
    steps = 0
    for lossy, lossless in dataloader:
        lossy = lossy.to(device)
        lossless = lossless.to(device)
        with torch.amp.autocast("cuda"):
            fake = generator(lossy)
            loss = spectral_loss_fn(fake, lossless)
        total_loss += loss.item()
        steps += 1
    return total_loss / max(steps, 1)


@click.command()
@click.option("--epochs", default=200, type=int)
@click.option("--batch-size", default=4, type=int)
@click.option("--lr", default=1e-4, type=float)
@click.option("--resume", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--checkpoint-dir", type=click.Path(path_type=Path), default=Path("model/checkpoints"))
@click.option("--data-lossless", type=click.Path(exists=True, path_type=Path), default=Path("data/lossless"))
@click.option("--data-lossy", type=click.Path(exists=True, path_type=Path), default=Path("data/lossy"))
def main(
    epochs: int,
    batch_size: int,
    lr: float,
    resume: Path | None,
    checkpoint_dir: Path,
    data_lossless: Path,
    data_lossy: Path,
) -> None:
    model_cfg = ModelConfig()
    train_cfg = TrainConfig(epochs=epochs, batch_size=batch_size, lr_generator=lr, lr_discriminator=lr)
    data_cfg = DataConfig(lossless_dir=data_lossless, lossy_dir=data_lossy)

    set_seed(train_cfg.seed)
    device = get_device()
    console.print(f"Device: [bold]{device}[/bold]")

    train_ds, val_ds = build_splits(model_cfg, data_cfg, train_cfg.val_split, train_cfg.seed)
    console.print(f"Train: {len(train_ds)} files, Val: {len(val_ds)} files")

    train_loader = DataLoader(
        train_ds, batch_size=train_cfg.batch_size, shuffle=True,
        num_workers=train_cfg.num_workers, pin_memory=True, drop_last=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=train_cfg.batch_size, shuffle=False,
        num_workers=train_cfg.num_workers, pin_memory=True,
    )

    generator = Generator(model_cfg).to(device)
    discriminator = MultiScaleDiscriminator(model_cfg.in_channels).to(device)

    g_params = sum(p.numel() for p in generator.parameters())
    d_params = sum(p.numel() for p in discriminator.parameters())
    console.print(f"Generator: {g_params / 1e6:.1f}M params, Discriminator: {d_params / 1e6:.1f}M params")

    opt_g = torch.optim.Adam(generator.parameters(), lr=train_cfg.lr_generator, betas=train_cfg.adam_betas)
    opt_d = torch.optim.Adam(discriminator.parameters(), lr=train_cfg.lr_discriminator, betas=train_cfg.adam_betas)
    scaler = torch.amp.GradScaler("cuda")
    spectral_loss_fn = SpectralLoss().to(device)

    start_epoch = 0
    if resume is not None:
        start_epoch = load_checkpoint(resume, generator, discriminator, opt_g, opt_d)
        console.print(f"Resumed from epoch {start_epoch}")

    best_val_loss = float("inf")

    for epoch in range(start_epoch, train_cfg.epochs):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(f"Epoch {epoch + 1}/{train_cfg.epochs}", total=len(train_loader))
            metrics = train_one_epoch(
                generator, discriminator, train_loader,
                opt_g, opt_d, spectral_loss_fn, scaler,
                train_cfg, device, progress, task_id,
            )

        line = (
            f"Epoch {epoch + 1:>4d} | "
            f"G: {metrics['g_loss']:.4f} D: {metrics['d_loss']:.4f} | "
            f"Spec: {metrics['spec']:.4f} Feat: {metrics['feat']:.4f} Adv: {metrics['adv']:.4f}"
        )

        if (epoch + 1) % train_cfg.val_interval == 0:
            val_loss = validate(generator, spectral_loss_fn, val_loader, device)
            line += f" | Val: {val_loss:.4f}"
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                save_checkpoint(generator, discriminator, opt_g, opt_d, epoch + 1, checkpoint_dir / "best")
                line += " [green]*best*[/green]"

        console.print(line)

        if (epoch + 1) % train_cfg.checkpoint_interval == 0:
            save_checkpoint(generator, discriminator, opt_g, opt_d, epoch + 1, checkpoint_dir / f"epoch_{epoch + 1}")

    save_checkpoint(generator, discriminator, opt_g, opt_d, train_cfg.epochs, checkpoint_dir / "final")
    model_cfg.save(checkpoint_dir / "config.json")
    console.print("[bold green]Training complete.[/bold green]")


if __name__ == "__main__":
    main()
