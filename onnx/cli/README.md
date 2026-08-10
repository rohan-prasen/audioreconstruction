# audioreconstructor

`audioreconstructor` is the command-line release of Audioreconstruction's ONNX
audio enhancer. It installs a small Python launcher; the ONNX model and the native
runtime are downloaded only when you explicitly run setup.

## Install

```bash
pip install audioreconstructor
audioreconstructor setup
```

`setup` downloads the native executable, `model.onnx`, and `config.json` from the
GitHub Release matching the installed package version. It verifies SHA-256 hashes
before making them available locally.

The current release supports 64-bit Linux, 64-bit Windows, and macOS (Apple Silicon
and Intel; macOS requires version 1.2.0 or later).

## Use

Enhance a single file:

```bash
audioreconstructor enhance --input song.mp3 --output song_enhanced.flac
```

Enhance a whole folder (recurses into subfolders):

```bash
audioreconstructor enhance --folder ./songs
```

Reconstructed files are written to a mirrored tree under `<folder>/enhanced/`, e.g.
`songs/rock/track.mp3` → `songs/enhanced/rock/track.flac`.

Choose the ONNX execution provider when needed:

```bash
audioreconstructor enhance --input song.mp3 --output song_enhanced.flac --provider cpu
```

`auto` is the default. Windows first tries DirectML and falls back to CPU; macOS first
tries Core ML (`--provider coreml`) and falls back to CPU; Linux uses CPU. The native
executable reads supported audio through libsndfile and always writes FLAC output.

> **Note:** v1.0.0 used top-level flags (`audioreconstructor --setup`,
> `audioreconstructor --input ... --output ...`). These are now `setup`, `doctor`, and
> `enhance` subcommands. Run `audioreconstructor --help` for the full command list.

## Verify installation

```bash
audioreconstructor doctor
```

Doctor verifies all cached release assets and runs an actual synthetic-audio ONNX
inference test. A healthy installation exits with status `0`.

## Cache locations

Setup prints the exact locations it uses. By default they are:

- Linux: `$XDG_CACHE_HOME/audioreconstructor/<version>` or
  `~/.cache/audioreconstructor/<version>`
- Windows: `%LOCALAPPDATA%\\audioreconstructor\\Cache\\<version>`
- macOS: `~/Library/Caches/audioreconstructor/<version>`

Running setup for an upgraded package version removes older cached versions after the
new version has been fully verified.
