from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ModelConfig:
    sample_rate: int = 44100
    segment_length: int = 131072  # ~2.97s at 44.1kHz
    in_channels: int = 2
    base_channels: int = 32
    channel_multipliers: tuple[int, ...] = (1, 2, 4, 8, 16, 16)
    bottleneck_dilations: tuple[int, ...] = (1, 2, 4, 8)
    kernel_size: int = 7
    decoder_kernel_size: int = 7

    def save(self, path: Path) -> None:
        data = asdict(self)
        data["channel_multipliers"] = list(data["channel_multipliers"])
        data["bottleneck_dilations"] = list(data["bottleneck_dilations"])
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> ModelConfig:
        data = json.loads(path.read_text())
        data["channel_multipliers"] = tuple(data["channel_multipliers"])
        data["bottleneck_dilations"] = tuple(data["bottleneck_dilations"])
        return cls(**data)


@dataclass
class TrainConfig:
    epochs: int = 200
    batch_size: int = 4
    lr_generator: float = 1e-4
    lr_discriminator: float = 1e-4
    adam_betas: tuple[float, float] = (0.5, 0.9)
    spectral_loss_weight: float = 100.0
    feature_match_weight: float = 10.0
    checkpoint_interval: int = 10
    val_interval: int = 5
    val_split: float = 0.2
    num_workers: int = 4
    seed: int = 42


@dataclass
class DataConfig:
    lossless_dir: Path = field(default_factory=lambda: Path("data/lossless"))
    lossy_dir: Path = field(default_factory=lambda: Path("data/lossy"))
    bitrates: tuple[int, ...] = (128, 256, 320)
