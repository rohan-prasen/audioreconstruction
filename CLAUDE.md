# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GAN-based audio super-resolution: reconstructs high-fidelity FLAC from lossy MP3 (128/256/320 kbps). Uses a 1D U-Net generator (~28M params) with a multi-scale discriminator (~25M params), trained with mixed-precision on CUDA.

## Commands

```bash
# Install all Python dependencies
uv sync

# Lint
uv run ruff check .

# Run tests
uv run pytest

# Prepare training data (requires FFmpeg; transcodes FLAC→MP3 at 128/256/320k)
uv run python -m model.prepare_data

# Train
uv run python -m model.train              # defaults: 200 epochs, batch 4, lr 1e-4
uv run python -m model.train --resume model/checkpoints/epoch_50

# Evaluate / infer (single file or directory)
uv run python -m model.evaluate --checkpoint model/checkpoints/best --input song.mp3 --output output/
uv run python -m model.evaluate --checkpoint model/checkpoints/best --input data/lossy/128/ --output output/ --reference data/lossless/

# Export generator weights for HuggingFace
uv run python -m model.export --checkpoint model/checkpoints/best

# Frontend
cd frontend && bun install && bun dev     # dev server
cd frontend && bun lint                   # lint
cd frontend && bun run build              # production build
```

## Architecture

### Model pipeline (`model/`)

All modules are run as `python -m model.<module>`. The pipeline flows:

1. **prepare_data.py** — FFmpeg batch transcoder. Creates `data/lossy/{128,256,320}/*.mp3` from `data/lossless/*.flac`. Files paired by stem name.
2. **dataset.py** — `AudioPairDataset` loads (lossy, lossless) pairs, randomly sampling one bitrate per item. `build_splits()` creates train/val sets (80/20).
3. **train.py** — Full GAN training loop with mixed-precision (`torch.amp`), gradient checkpointing, and Rich progress bars. Saves best checkpoint by validation spectral loss.
4. **evaluate.py** — Loads only the generator from a checkpoint. Processes audio in `segment_length` chunks (131072 samples ≈ 3s). Computes PESQ and SNR when reference FLACs provided.
5. **export.py** — Strips discriminator, saves generator-only weights as `model.safetensors` + `config.json`.

Key design: the generator uses a **residual connection** — output = generator(input) + input — so it learns to predict the *difference* between lossy and lossless, not the full waveform.

### Config system (`model/config.py`)

Three dataclasses: `ModelConfig` (architecture), `TrainConfig` (hyperparameters), `DataConfig` (paths). `ModelConfig` serializes to/from JSON for checkpoint portability.

### Checkpoint format

Each checkpoint directory contains:
- `generator.safetensors` / `discriminator.safetensors` — model weights
- `training_state.pt` — epoch counter + optimizer states
- `config.json` — model architecture config (saved at end of training)

### Loss components

| Loss | Weight | Module |
|------|--------|--------|
| LSGAN adversarial | 1.0 | `losses.py` |
| Multi-scale spectral (STFT at 512/1024/2048) | 100.0 | `losses.py` — L1 on magnitude + log-magnitude |
| Feature matching | 10.0 | `losses.py` — L1 on discriminator intermediate features |

### Frontend (`frontend/`)

React 19 + Vite 8 + Tailwind CSS 4. Scaffolded but minimal — no backend API exists yet.

### Data layout

```
data/
├── lossless/          # source FLAC files (user-provided)
└── lossy/
    ├── 128/           # auto-generated MP3
    ├── 256/
    └── 320/
```

## Key Constraints

- Python 3.10 (pinned in `.python-version`), managed by `uv`
- CUDA required for training (mixed-precision assumes CUDA)
- Evaluation/inference falls back to CPU but is slow
- FFmpeg must be installed for data preparation
- Audio is always stereo (`in_channels=2`), 44.1kHz
- Model weights use safetensors format exclusively (not `.pt`)
