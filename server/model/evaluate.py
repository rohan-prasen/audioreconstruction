from __future__ import annotations

from pathlib import Path

import torch
from safetensors.torch import load_file

from model.config import ModelConfig
from model.generator import Generator


def load_generator(checkpoint_dir: Path, device: torch.device) -> Generator:
    config_path = checkpoint_dir / "config.json"
    if not config_path.exists():
        config_path = checkpoint_dir.parent / "config.json"
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
