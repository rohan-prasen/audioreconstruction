# Audio Reconstruction

[![Publish audioreconstructor to PyPi](https://github.com/rohan-prasen/audioreconstruction/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/rohan-prasen/audioreconstruction/actions/workflows/publish-pypi.yml)
[![PyPI Version](https://img.shields.io/pypi/v/audioreconstructor?logo=python&logoColor=white&label=PyPI&color=3776AB)](https://pypi.org/project/audioreconstructor/)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10--3.13-3776AB?logo=python&logoColor=white)

Reconstruct high-fidelity audio from compressed MP3 sources using adversarial neural networks. The model restores lost high-frequency harmonics, spectral detail, and natural timbre — producing near-lossless FLAC output from lossy input.

**Input:** MP3 (128 / 256 / 320 kbps) &nbsp;|&nbsp; **Output:** FLAC (~800+ kbps effective bitrate) &nbsp;|&nbsp; **Audio:** stereo, 44.1 kHz

![](/media/recordings/cli-demo.gif)

---

## Contents

- [Pick your path](#pick-your-path) — three ways to use the project
- [Quick Start (CLI)](#quick-start-cli) — reconstruct a file in 3 commands
- [How It Works](#how-it-works) — the GAN model, in brief
- [Repository Map](#repository-map) — what lives where
- [Getting Started (Developers)](#getting-started-developers) — clone, install, run locally
- [Training Your Own Model](#training-your-own-model) — data → train → evaluate → export
- [Evaluation & Audio Metrics](#evaluation--audio-metrics)
- [Deployment](#deployment) — Modal GPU + Azure Blob Storage
- [Development Commands](#development-commands)
- [Key Constraints](#key-constraints)
- [Project Docs](#project-docs) — deeper reading
- [Contributing / Security / License](#contributing)

---

## Pick your path

There are **three independent ways** to use this project. Choose by how much you want to run yourself:

| Path | For whom | What you run | Needs a GPU? |
| ---- | -------- | ------------ | ------------ |
| **1. CLI (pip)** | Anyone who just wants better audio | `pip install audioreconstructor` → runs an ONNX model on CPU | No |
| **2. Hosted web app** | Non-technical users | Open the site, drop an MP3, download the FLAC | No (runs on our GPU) |
| **3. Self-host / develop** | Contributors & tinkerers | Clone the repo, run the FastAPI server + React frontend, or train the model | Training: yes. Inference: optional |

- **Path 1** ships a standalone [`audioreconstructor`](https://pypi.org/project/audioreconstructor/) PyPI package — no PyTorch, no repo clone, no GPU. See [Quick Start](#quick-start-cli).
- **Path 2** is the React frontend deployed to Vercel (`https://audioreconstruction.vercel.app`), backed by the production server on Modal.com.
- **Path 3** is the full repository. See [Getting Started](#getting-started-developers).

## Quick Start (CLI)

The fastest way to reconstruct audio — no training, no GPU, no repo clone. The
[`audioreconstructor`](https://pypi.org/project/audioreconstructor/) package ships an
ONNX build of the trained model that runs on CPU:

```bash
pip install audioreconstructor
audioreconstructor setup                                       # downloads + verifies model
audioreconstructor enhance --input song.mp3 --output song.flac # single file
audioreconstructor enhance --folder ./songs                    # whole folder (recursive)
audioreconstructor doctor                                      # diagnose environment / cache
```

On first run, `setup` downloads the native executable, `model.onnx`, and `config.json`
from the matching GitHub Release, verifies each against a SHA-256 manifest, and caches
them per-version. Supports 64-bit Linux and Windows, plus macOS Apple Silicon and Intel.
See [`onnx/cli/README.md`](onnx/cli/README.md) for execution providers and cache locations.

## How It Works

A GAN (Generative Adversarial Network) learns to reverse compression artifacts:

1. **Generator** — a 1D U-Net (~28M params) that predicts high-resolution spectral content from the compressed waveform. It uses a **residual connection** (`output = generator(input) + input`), so it learns the *difference* between lossy and lossless rather than regenerating the whole signal.
2. **Discriminator** — a multi-scale network (~25M params) that enforces perceptual realism by distinguishing real from reconstructed audio.
3. **Training objective** — a weighted sum of three losses:

   | Loss | Weight | What it does |
   | ---- | -----: | ------------ |
   | LSGAN adversarial | 1.0 | Pushes output toward the "real audio" manifold |
   | Multi-scale spectral (STFT @ 512 / 1024 / 2048) | 100.0 | L1 on magnitude + log-magnitude; the main fidelity signal |
   | Feature matching | 10.0 | L1 on the discriminator's intermediate features; stabilizes training |

Inference processes audio in `segment_length` chunks (131072 samples ≈ 3 s). Training uses mixed precision (`torch.amp`) and gradient checkpointing on CUDA.

### Use cases

- Music remastering from low-bitrate sources
- Streaming audio quality enhancement
- Archival recovery of degraded recordings

## Repository Map

```
audioreconstruction/
├── model/             # PyTorch model: definition, training, evaluation, export
│   ├── generator.py       # 1D U-Net generator (~28M params)
│   ├── discriminator.py   # Multi-scale discriminator (~25M params)
│   ├── losses.py          # Spectral + adversarial + feature-matching losses
│   ├── config.py          # ModelConfig / TrainConfig / DataConfig dataclasses
│   ├── prepare_data.py    # FFmpeg transcoder: FLAC → MP3 @ 128/256/320k
│   ├── dataset.py         # AudioPairDataset + train/val splits
│   ├── train.py           # Full GAN training loop (mixed precision)
│   ├── evaluate.py        # load_generator + chunked inference + PESQ/SNR
│   └── export.py          # Strip discriminator → generator-only safetensors
│
├── backend/           # Local dev FastAPI server (imports model/ directly)
├── server/            # Production FastAPI server → Modal.com GPU (self-contained copy of inference code)
│   ├── app.py             # Routes, rate limiting, CORS, logging
│   ├── batcher.py         # Dynamic batching of concurrent segment requests
│   ├── blob_storage.py    # Azure Blob SAS minting + blob moves
│   ├── audio_io.py        # soundfile I/O + ID3 → Vorbis metadata copy
│   └── modal_app.py       # Modal App/image definition (T4 GPU)
│
├── onnx/              # Torch-free ONNX delivery path (own uv.lock)
│   ├── export.py          # PyTorch generator → model.onnx
│   ├── inference.py       # onnxruntime inference subprocess
│   ├── audioreconstructor.spec  # PyInstaller → native binary
│   └── cli/               # `audioreconstructor` PyPI package (Click + Rich TUI)
│
├── frontend/          # React 19 + Vite 8 + Tailwind CSS 4 single-page app
├── test/              # Standalone audio-similarity CLIs (PESQ/SNR/LSD/SI-SDR/Mel-SSIM)
├── docs/              # Contributing, security, code of conduct, agent routing
├── design/            # UI design briefs and mockups
├── openspec/          # Change proposals (planned/in-flight features)
├── media/             # Demo GIFs, sample audio, screenshots
│
├── CLAUDE.md / AGENTS.md   # Agent guide (byte-identical mirrors)
├── PRODUCT.md              # Product intent and target user
├── DESIGN.md              # Design system (color tokens, typography)
└── pyproject.toml         # Root Python project (uv)
```

### Two inference servers — why both?

- **`backend/`** is a simple dev server: imports `model/` directly, one request at a time, permissive CORS. Checkpoint path from `CHECKPOINT_DIR` (default `model/checkpoints/best/`). **Not deployed.**
- **`server/`** is the production server on Modal.com. It keeps its **own copy** of the inference-only model code (`server/model/`) because Modal packages `server/` as an isolated container image. It adds dynamic batching, rate limiting, strict CORS, structured logging, and a pre-signed-upload flow.

**When changing inference behavior for production, edit `server/`.**

### Pre-signed uploads (production only)

Audio never passes through the GPU container. The browser uploads straight to Azure Blob Storage:

1. `POST /upload-url` → `{uploadUrl, blobName}` — a write-only SAS scoped to one blob, 15 min.
2. Browser `PUT`s the MP3 directly to Azure (header `x-ms-blob-type: BlockBlob`).
3. `POST /model-serve` with `{blobName, filename}` → `{downloadUrl, filename, size}` — a read-only SAS, 1 hour, that saves as `<stem>_reconstructed.flac`.

`blobName` is server-generated and re-validated on arrival (it's used as a temp-file path). The input blob is deleted after processing.

## Getting Started (Developers)

### Prerequisites

- **Python 3.12** (pinned in `.python-version`; root project requires `>=3.10`)
- **Node.js >= 20**
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Bun](https://bun.sh/) — JS package manager (npm also works)
- [FFmpeg](https://ffmpeg.org/) — required only for training-data preparation

### Setup

```bash
git clone git@github.com:rohan-prasen/audioreconstruction.git
cd audioreconstruction

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && bun install
```

> **Model weights** are hosted on HuggingFace — [download here](https://huggingface.co/rohanprasen-kedari/audioreconstruction/tree/main/checkpoints/best). Place `generator.safetensors` under `./model/checkpoints/best/`. (Training produces checkpoints there; inference loads the generator only.)

### Run locally

```bash
# Terminal 1 — local backend (loads model/ directly)
uv run uvicorn backend.main:app --reload       # http://localhost:8000

# Terminal 2 — frontend (proxies /api/* to the backend in dev)
cd frontend && bun dev                          # http://localhost:5173
```

See [`frontend/CLAUDE.md`](frontend/CLAUDE.md) for the frontend state model, retry/back-off logic, and styling.

## Training Your Own Model

The `model/` pipeline runs as `python -m model.<module>`. CUDA is required for training.

```bash
# 1. Place source FLACs in data/lossless/, then transcode to MP3 (needs FFmpeg)
uv run python -m model.prepare_data            # → data/lossy/{128,256,320}/*.mp3

# 2. Train (defaults: 200 epochs, batch 4, lr 1e-4; saves best by val spectral loss)
uv run python -m model.train
uv run python -m model.train --resume model/checkpoints/epoch_50

# 3. Export generator-only weights (strips discriminator) for distribution
uv run python -m model.export --checkpoint model/checkpoints/best
```

**Data layout:**

```
data/
├── lossless/          # source FLAC files (you provide these)
└── lossy/
    ├── 128/           # auto-generated MP3
    ├── 256/
    └── 320/
```

Files are paired by stem name. Each checkpoint directory holds `generator.safetensors`,
`discriminator.safetensors`, `training_state.pt` (epoch + optimizer state), and `config.json`.
Weights use **safetensors exclusively** (never `.pt` for model weights).

## Evaluation & Audio Metrics

```bash
# Reconstruct and (optionally) score against reference FLACs — single file or directory
uv run python -m model.evaluate --checkpoint model/checkpoints/best --input song.mp3 --output output/
uv run python -m model.evaluate --checkpoint model/checkpoints/best \
  --input data/lossy/128/ --output output/ --reference data/lossless/
```

`evaluate` computes **PESQ** and **SNR** when references are supplied. The `test/`
directory holds standalone similarity CLIs (not a pytest suite) for comparing file pairs:

```bash
uv run python -m test.eval_flac "original.flac" "reconstructed.flac"
uv run python -m test.eval_mp3  "reference.flac" "compressed.mp3"
```

Lower-level metric modules live alongside them: `snr.py`, `pesq.py`, `lsd.py`,
`mel_ssim.py`, `si_sdr.py`. See [`test/README.md`](test/README.md).

## Deployment

### Production server → Modal.com

```bash
cd server && modal deploy modal_app.py          # requires `modal` CLI auth
```

Runs on a **T4 GPU** (`min_containers=0`, `max_containers=2`, scales to zero when idle).
Rate-limited via `slowapi`, CORS locked to the frontend origin.

### Azure Blob Storage

The production server needs these environment variables (supplied on Modal via the `azure-blob` secret):
`AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY`, `AZURE_UPLOAD_CONTAINER`, `AZURE_OUTPUT_CONTAINER`
(and `AZURE_BLOB_ENDPOINT` to point at Azurite locally).

> **The storage account must have a CORS rule** allowing `PUT`/`GET` from the frontend origin, or the browser's direct upload is blocked.

### ONNX CLI release flow

Build the native binary with PyInstaller → generate the SHA-256 `manifest.json` →
upload the binary + `model.onnx` + `config.json` + `manifest.json` to a GitHub Release
tagged `audioreconstructor-v<version>` → bump `onnx/cli/pyproject.toml` to match.
**The package version and release tag must stay in lockstep.** See [`onnx/cli/README.md`](onnx/cli/README.md).

## Development Commands

```bash
# Root Python project
uv run ruff check .                 # lint
uv run pytest                       # tests (no test_*.py in the root project yet)

# Published CLI package (onnx/cli/)
cd onnx/cli && uv run pytest        # unittest-based tests
cd onnx/cli && uv run ruff check .  # lint

# Frontend
cd frontend && bun lint             # ESLint
cd frontend && bun run build        # production build
```

## Tech Stack

| Layer      | Technology                                      |
| ---------- | ----------------------------------------------- |
| Model      | PyTorch, torchaudio, safetensors                |
| Backend    | FastAPI, uvicorn, SlowAPI                        |
| Deployment | Modal.com (serverless GPU — T4), Azure Blob      |
| Frontend   | React 19, Vite 8, Tailwind CSS 4, Framer Motion |
| CLI        | ONNX Runtime, Click, Rich, PyInstaller          |
| Metrics    | PESQ, SNR, LSD, SI-SDR, Mel-SSIM                 |
| Tooling    | uv (Python), Bun (JS), Ruff (lint)              |

## Key Constraints

- Python 3.12 pinned (`.python-version`); root project requires `>=3.10`, the CLI package supports 3.10–3.13
- CUDA required for training (mixed precision assumes CUDA); inference falls back to CPU but is slow
- FFmpeg required for data preparation
- Audio is always stereo (`in_channels=2`), 44.1 kHz
- Model weights use safetensors exclusively (not `.pt`)
- Upload limit on both inference servers: **25 MB / 6 minutes**

## Project Docs

| Doc | What's in it |
| --- | ------------ |
| [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) | Full architecture guide for agents (mirrors of each other) |
| [`PRODUCT.md`](PRODUCT.md) | Product purpose and target user |
| [`DESIGN.md`](DESIGN.md) | Design system — color tokens, typography |
| [`frontend/CLAUDE.md`](frontend/CLAUDE.md) | Frontend state model, retry logic, styling |
| [`onnx/cli/README.md`](onnx/cli/README.md) | CLI usage, execution providers, cache locations |
| [`test/README.md`](test/README.md) | Audio-similarity evaluation scripts |
| [`openspec/changes/`](openspec/changes/) | Planned / in-flight change proposals |

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines and [CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md).

## Security

To report a vulnerability, see [SECURITY.md](docs/SECURITY.md).

## License

[MIT](LICENSE) — Rohan Prasen Kedari
