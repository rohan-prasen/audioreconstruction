from __future__ import annotations

import logging
from pathlib import Path

import torch
from safetensors.torch import load_file

from model.config import ModelConfig
from model.generator import Generator

logger = logging.getLogger("audioreconstruction")


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
    if device.type == "cuda":
        gen = torch.compile(gen, mode="reduce-overhead")
        logger.info("torch.compile applied (mode=reduce-overhead)")
    return gen


def warmup_generator(generator: torch.nn.Module, device: torch.device, cfg: ModelConfig) -> None:
    logger.info("Warming up model (batch=%d, seg=%d)...", 8, cfg.segment_length)
    dummy = torch.randn(8, cfg.in_channels, cfg.segment_length, device=device)
    with torch.inference_mode(), torch.amp.autocast("cuda", enabled=device.type == "cuda"):
        generator(dummy)
    del dummy
    if device.type == "cuda":
        torch.cuda.empty_cache()
    logger.info("Warmup complete")
