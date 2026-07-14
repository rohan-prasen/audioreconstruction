"""Folder discovery and output mapping for batch (``--folder``) enhancement."""
from __future__ import annotations

from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".opus"}
ENHANCED_DIR = "enhanced"


def discover_audio_files(folder: Path) -> list[Path]:
    """Recursively list audio files under ``folder``.

    Skips the ``enhanced/`` output directory (so re-runs don't reprocess results)
    and any hidden files or directories. Extension matching is case-insensitive.
    """
    files: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(folder).parts
        if ENHANCED_DIR in parts:
            continue
        if any(part.startswith(".") for part in parts):
            continue
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(path)
    return files


def output_path_for(src: Path, folder: Path) -> Path:
    """Map a source file to ``folder/enhanced/<relative>.flac``, mirroring the tree."""
    relative = src.relative_to(folder).with_suffix(".flac")
    return folder / ENHANCED_DIR / relative
