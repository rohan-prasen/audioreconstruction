# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GAN-based audio super-resolution: reconstructs high-fidelity FLAC from lossy MP3 (128/256/320 kbps). Uses a 1D U-Net generator (~28M params) with a multi-scale discriminator (~25M params), trained with mixed-precision on CUDA. Two FastAPI servers wrap the trained generator for inference — a local dev server (`backend/`) and a production server (`server/`) deployed to Modal.com GPU containers.

## Commands

```bash
# Install all Python dependencies
uv sync

# Lint
uv run ruff check .

# Run tests (currently no test_*.py files — nothing to collect yet)
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

# Audio similarity evaluation (standalone CLIs, not pytest)
uv run python -m test.eval_FLAC "original.flac" "reconstructed.flac"
uv run python -m test.eval_mp3 "reference.flac" "compressed.mp3"

# Local dev backend (loads model/ package directly)
uv run uvicorn backend.main:app --reload

# Deploy production server to Modal.com (requires `modal` CLI auth)
cd server && modal deploy modal_app.py

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
4. **evaluate.py** — Loads only the generator from a checkpoint (`load_generator`). Processes audio in `segment_length` chunks (131072 samples ≈ 3s). Computes PESQ and SNR when reference FLACs provided. Both `backend/` and `server/` rely on `load_generator` (or a bundled copy — see below).
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

### Two inference servers — `backend/` vs `server/`

Both expose the same three routes (`GET /`, `GET /health-check`, `POST /model-serve`) but differ in maturity and deployment target:

- **`backend/main.py`** — simple local dev server. Imports `model/` directly (`from model.evaluate import load_generator`), processes one request at a time with no batching or rate limiting, permissive CORS (`*`). Checkpoint path from `CHECKPOINT_DIR` env var (see `backend/.env.example`), default `model/checkpoints/best/`.
- **`server/`** — production server deployed to Modal.com. Has its own **self-contained copy** of the inference-only model code (`server/model/{config,evaluate,generator}.py` — no training/dataset/loss modules) because `modal_app.py` packages `server/` as an isolated container image via `add_local_dir`. Adds:
  - `batcher.py` — `InferenceBatcher` dynamically batches concurrent segment requests (up to `MAX_BATCH_SIZE=8`, `MAX_WAIT_S=0.25`) on a dedicated single-thread executor so GPU inference isn't serialized per-request.
  - `audio_io.py` — soundfile-based audio load/write + ID3→Vorbis metadata copying (FLAC tags carried over from the source MP3).
  - `modal_app.py` — defines the Modal `App`/image (T4 GPU, `min_containers=0`, `max_containers=2`, `scaledown_window=60`) and wraps `app.py`'s FastAPI instance via `@modal.asgi_app()`.
  - Rate limiting via `slowapi` (`10/minute` on GET routes, `40/minute` on `/model-serve`), strict CORS locked to `https://audioreconstruction.vercel.app`, IST-formatted structured logging.

When changing inference behavior that should apply in production, edit `server/` — `backend/` is dev-only and not deployed.

### Frontend (`frontend/`)

React 19 + Vite 8 + Tailwind CSS 4 — a single-file app in `src/App.jsx` that uploads MP3s to `POST /model-serve` and downloads the reconstructed FLAC. See `frontend/CLAUDE.md` for the detailed state model, retry/back-off logic, and styling approach; it proxies `/api/*` to the backend in dev via `vite.config.js`.

### Audio similarity evaluation (`test/`)

Standalone CLI scripts (not a pytest suite) for comparing signal similarity between file pairs — `eval_FLAC.py`, `eval_mp3.py`, plus lower-level metric modules (`snr.py`, `pesq.py`, `lsd.py`, `mel_ssim.py`, `si_sdr.py`). Run via `python -m test.<script>`.

### Change proposals (`openspec/`)

This repo tracks planned/in-flight changes as OpenSpec proposals under `openspec/changes/` (e.g. `add-concurrency-dynamic-batching`, `add-frontend-input-limits`), driven by the `opsx-*` skills/commands in `.claude/`, `.codex/`, `.opencode/`. Check here for context on why a partially-implemented feature looks the way it does.

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
- Upload limit on both inference servers: 25 MB / 6 minutes duration
