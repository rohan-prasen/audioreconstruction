from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ModelConfig:
    sample_rate: int = 44100
    segment_length: int = 131072
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
