from __future__ import annotations

import logging
from pathlib import Path

import soundfile as sf
import torch
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from torchaudio.functional import resample

logger = logging.getLogger("audioreconstruction")

_ID3_TO_VORBIS = {
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


def copy_metadata(src_mp3: Path, dst_flac: Path) -> None:
    try:
        id3 = ID3(str(src_mp3))
    except Exception:
        return

    flac = FLAC(str(dst_flac))

    has_tags = False
    for id3_key, vorbis_key in _ID3_TO_VORBIS.items():
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
        logger.info("Copied metadata from %s to %s", src_mp3.name, dst_flac.name)
