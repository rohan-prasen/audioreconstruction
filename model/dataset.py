from __future__ import annotations

import random

import torch
from torch.utils.data import Dataset

from model.config import DataConfig, ModelConfig
from model.utils import load_audio, normalize_audio


class AudioPairDataset(Dataset):
    def __init__(
        self,
        model_cfg: ModelConfig,
        data_cfg: DataConfig,
        file_stems: list[str],
    ) -> None:
        self.model_cfg = model_cfg
        self.data_cfg = data_cfg
        self.file_stems = file_stems
        self._validate_pairs()

    def _validate_pairs(self) -> None:
        missing = []
        for stem in self.file_stems:
            lossless = self.data_cfg.lossless_dir / f"{stem}.flac"
            if not lossless.exists():
                missing.append(str(lossless))
            for br in self.data_cfg.bitrates:
                lossy = self.data_cfg.lossy_dir / str(br) / f"{stem}.mp3"
                if not lossy.exists():
                    missing.append(str(lossy))
        if missing:
            raise FileNotFoundError(
                f"Missing {len(missing)} files. First 5: {missing[:5]}"
            )

    def __len__(self) -> int:
        return len(self.file_stems)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        stem = self.file_stems[idx]
        sr = self.model_cfg.sample_rate
        seg_len = self.model_cfg.segment_length

        ch = self.model_cfg.in_channels
        lossless = load_audio(
            self.data_cfg.lossless_dir / f"{stem}.flac", target_sr=sr, channels=ch
        )

        bitrate = random.choice(self.data_cfg.bitrates)
        lossy = load_audio(
            self.data_cfg.lossy_dir / str(bitrate) / f"{stem}.mp3", target_sr=sr, channels=ch
        )

        min_len = min(lossless.shape[-1], lossy.shape[-1])
        if min_len < seg_len:
            lossless = torch.nn.functional.pad(lossless, (0, seg_len - min_len))
            lossy = torch.nn.functional.pad(lossy, (0, seg_len - min_len))
            min_len = seg_len

        start = random.randint(0, min_len - seg_len)
        lossless = lossless[:, start : start + seg_len]
        lossy = lossy[:, start : start + seg_len]

        lossless = normalize_audio(lossless)
        lossy = normalize_audio(lossy)

        return lossy, lossless


def build_splits(
    model_cfg: ModelConfig,
    data_cfg: DataConfig,
    val_split: float = 0.2,
    seed: int = 42,
) -> tuple[AudioPairDataset, AudioPairDataset]:
    stems = sorted(
        p.stem for p in data_cfg.lossless_dir.glob("*.flac")
    )
    if not stems:
        raise FileNotFoundError(f"No .flac files in {data_cfg.lossless_dir}")

    rng = random.Random(seed)
    rng.shuffle(stems)
    split_idx = max(1, int(len(stems) * (1 - val_split)))
    train_stems = stems[:split_idx]
    val_stems = stems[split_idx:] if split_idx < len(stems) else stems[-1:]

    train_ds = AudioPairDataset(model_cfg, data_cfg, train_stems)
    val_ds = AudioPairDataset(model_cfg, data_cfg, val_stems)
    return train_ds, val_ds
