from __future__ import annotations

import logging
from pathlib import Path

import torch
import torchaudio
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from safetensors.torch import load_file, save_file

logger = logging.getLogger(__name__)

ID3_TO_VORBIS = {
    "TPE1": "ARTIST",
    "TIT2": "TITLE",
    "TALB": "ALBUM",
    "TDRC": "DATE",
    "TRCK": "TRACKNUMBER",
    "TPOS": "DISCNUMBER",
    "TCON": "GENRE",
    "TPE2": "ALBUMARTIST",
    "TCOM": "COMPOSER",
    "TCOP": "COPYRIGHT",
    "COMM": "COMMENT",
}


def load_audio(path: Path, target_sr: int = 44100, channels: int = 2) -> torch.Tensor:
    waveform, sr = torchaudio.load(str(path))
    if waveform.shape[0] > channels:
        waveform = waveform[:channels]
    elif waveform.shape[0] < channels:
        waveform = waveform.repeat(channels, 1)[:channels]
    if sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, sr, target_sr)
    return waveform


def normalize_audio(waveform: torch.Tensor) -> torch.Tensor:
    peak = waveform.abs().max()
    if peak > 0:
        waveform = waveform / peak
    return waveform


def save_checkpoint(
    generator: torch.nn.Module,
    discriminator: torch.nn.Module,
    optimizer_g: torch.optim.Optimizer,
    optimizer_d: torch.optim.Optimizer,
    epoch: int,
    path: Path,
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    save_file(generator.state_dict(), path / "generator.safetensors")
    save_file(discriminator.state_dict(), path / "discriminator.safetensors")
    torch.save(
        {
            "epoch": epoch,
            "optimizer_g": optimizer_g.state_dict(),
            "optimizer_d": optimizer_d.state_dict(),
        },
        path / "training_state.pt",
    )


def load_checkpoint(
    path: Path,
    generator: torch.nn.Module,
    discriminator: torch.nn.Module,
    optimizer_g: torch.optim.Optimizer | None = None,
    optimizer_d: torch.optim.Optimizer | None = None,
) -> int:
    generator.load_state_dict(load_file(path / "generator.safetensors"))
    discriminator.load_state_dict(load_file(path / "discriminator.safetensors"))
    epoch = 0
    training_state_path = path / "training_state.pt"
    if training_state_path.exists():
        state = torch.load(training_state_path, weights_only=True)
        epoch = state["epoch"]
        if optimizer_g is not None:
            optimizer_g.load_state_dict(state["optimizer_g"])
        if optimizer_d is not None:
            optimizer_d.load_state_dict(state["optimizer_d"])
    return epoch


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def copy_metadata(src_mp3: Path, dst_flac: Path) -> None:
    try:
        id3 = ID3(str(src_mp3))
    except Exception:
        return

    flac = FLAC(str(dst_flac))

    has_tags = False
    for id3_key, vorbis_key in ID3_TO_VORBIS.items():
        frame = id3.get(id3_key)
        if frame is None:
            continue
        if id3_key == "COMM":
            text = frame.text[0] if frame.text else str(frame)
        else:
            text = str(frame)
        if text:
            flac[vorbis_key] = [text]
            has_tags = True

    for key in id3:
        if key.startswith("APIC"):
            apic = id3[key]
            if apic.data:
                pic = Picture()
                pic.type = apic.type
                pic.mime = apic.mime
                pic.desc = apic.desc
                pic.data = apic.data
                flac.add_picture(pic)
                has_tags = True
            break

    if has_tags:
        flac.save()
