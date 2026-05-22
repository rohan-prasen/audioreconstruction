from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from torchaudio.functional import resample


def load_audio_sf(path: Path, target_sr: int, channels: int) -> torch.Tensor:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)
    if waveform.shape[0] > channels:
        waveform = waveform[:channels]
    elif waveform.shape[0] < channels:
        waveform = waveform.repeat(channels, 1)[:channels]
    if sr != target_sr:
        waveform = resample(waveform, sr, target_sr)
    return waveform


def write_flac(waveform: torch.Tensor, path: Path, sample_rate: int) -> None:
    audio_out = waveform.squeeze(0).T.numpy()
    sf.write(str(path), audio_out, sample_rate)
