<div align="center">

# Audio Reconstruction

Reconstruct MP3 audio with a trained neural network.

[![Publish audioreconstructor to PyPI](https://github.com/rohan-prasen/audioreconstruction/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/rohan-prasen/audioreconstruction/actions/workflows/publish-pypi.yml)
[![PyPI version](https://img.shields.io/pypi/v/audioreconstructor?logo=python&logoColor=white&label=PyPI&color=3776AB)](https://pypi.org/project/audioreconstructor/)
[![GitHub stars](https://img.shields.io/github/stars/rohan-prasen/audioreconstruction?logo=github&color=yellow)](https://github.com/rohan-prasen/audioreconstruction/stargazers)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-model-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/rohanprasen-kedari/audioreconstruction)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10--3.13-3776AB?logo=python&logoColor=white)

</div>

Audio Reconstruction is a free, open-source tool that turns MP3s into FLACs using a trained neural network. The model aims to reduce compression artifacts and reconstruct detail lost during MP3 encoding.

**[Try the web app](https://audioreconstruction.vercel.app)**: upload an MP3, let the model process it, and download a FLAC to listen for yourself. You don't need a GPU.

The model estimates missing detail; it cannot guarantee a match to the original recording. See the [evaluation notes](test/README.md) for comparison tools and sample output.

**Input:** MP3 (128 / 256 / 320 kbps) &nbsp;|&nbsp; **Output:** FLAC (~800+ kbps effective bitrate) &nbsp;|&nbsp; **Audio:** stereo, 44.1 kHz

---

## Contents

- [Pick your path](#pick-your-path)
- [Quick start (CLI)](#quick-start-cli)
- [Reconstruction quality](#reconstruction-quality)
- [How it works](#how-it-works)
- [Repository map](#repository-map)
- [Getting started (developers)](#getting-started-developers)
- [Training your own model](#training-your-own-model)
- [Evaluation & audio metrics](#evaluation--audio-metrics)
- [Deployment](#deployment)
- [Development commands](#development-commands)
- [Tech stack](#tech-stack)
- [Key constraints](#key-constraints)
- [Project docs](#project-docs)
- [Contributing](#contributing) / [Security](#security) / [License](#license)

---

## Pick your path

| Option | How you use it | Do you need a GPU? |
| ------ | -------------- | ------------------ |
| [Web app](https://audioreconstruction.vercel.app) | Drop an MP3 in your browser and download the reconstructed FLAC | No, processing runs on the hosted GPU |
| [CLI](#quick-start-cli) | Install with pip and process files or folders locally | No, the ONNX model runs on CPU |
| [Self-host / develop](#getting-started-developers) | Clone the repo to run the FastAPI server and React frontend, or train a model | Required for training; optional for inference |

The web app uses a React frontend on Vercel and the production server on Modal.com. Uploads are limited to 25 MB and 6 minutes per file.

## Quick start (CLI)

The [`audioreconstructor`](https://pypi.org/project/audioreconstructor/) package runs
the trained model locally through ONNX. You can process a single file or a whole
folder without installing PyTorch, cloning this repository, or training a model.

```bash
pip install audioreconstructor
audioreconstructor setup                                       # downloads + verifies model
audioreconstructor enhance --input song.mp3 --output song.flac # single file
audioreconstructor enhance --folder ./songs                    # whole folder (recursive)
audioreconstructor doctor                                      # diagnose environment / cache
```

![CLI demo showing audio reconstruction in the terminal](/media/recordings/cli-demo.gif)

`setup` downloads the native executable, `model.onnx`, and `config.json` from the
matching GitHub Release, verifies each against a SHA-256 manifest, and caches them
per version. The CLI supports 64-bit Linux and Windows, plus macOS Apple Silicon and Intel.
See [`onnx/cli/README.md`](onnx/cli/README.md) for execution providers and cache locations.

## Reconstruction quality

These measurements come from one 30-second demo track. A lossless FLAC was encoded
as MP3 at each bitrate, reconstructed by the model, and compared with the original
using [`test/eval_flac.py`](test/eval_flac.py).

| Source MP3 | SNR vs. original | Spectrogram similarity |
| ---------- | ---------------: | ---------------------: |
| 128 kbps   | 16.78 dB         | 99.56 %                |
| 256 kbps   | 22.62 dB         | 99.96 %                |
| 320 kbps   | 20.46 dB         | 99.98 %                |

These results describe that demo track, not performance across a music library.
The table compares reconstructed audio with the original FLAC; it does not include
an MP3 baseline showing whether reconstruction improved on the input.

To run the comparison on your own audio, transcode a lossless FLAC to MP3,
reconstruct it, then run
`uv run python -m test.eval_flac original.flac reconstructed.flac`.
See [`test/README.md`](test/README.md) for the comparison commands and another sample output.

### Hear it (before / after)

Listen to the MP3 inputs alongside their reconstructed FLACs. These short clips are from the demo track:

<table>
  <tr><th>Before — MP3 input</th><th>After — reconstructed FLAC</th></tr>
  <tr>
    <td><audio controls src="media/samples/clips/sample1_before.mp3"></audio></td>
    <td><audio controls src="media/samples/clips/sample1_after.flac"></audio></td>
  </tr>
  <tr>
    <td><audio controls src="media/samples/clips/sample2_before.mp3"></audio></td>
    <td><audio controls src="media/samples/clips/sample2_after.flac"></audio></td>
  </tr>
  <tr>
    <td><audio controls src="media/samples/clips/sample3_before.mp3"></audio></td>
    <td><audio controls src="media/samples/clips/sample3_after.flac"></audio></td>
  </tr>
</table>

> If GitHub doesn't display the audio players, download the clips from [`media/samples/clips/`](media/samples/clips/) and play them locally.

## How it works

The model is a generative adversarial network (GAN) trained to reconstruct audio from compressed input.

The generator is a 1D U-Net (~28M parameters) that predicts missing detail from the compressed waveform. A residual connection (`output = generator(input) + input`) lets it learn the difference between lossy and lossless audio rather than regenerate the whole signal.

During training, a multi-scale discriminator (~25M parameters) learns to distinguish real audio from the generator's output. Training uses a weighted sum of three losses:

| Loss | Weight | What it does |
| ---- | -----: | ------------ |
| LSGAN adversarial | 1.0 | Encourages output that the discriminator classifies as real audio |
| Multi-scale spectral (STFT @ 512 / 1024 / 2048) | 100.0 | L1 on magnitude + log-magnitude; the main fidelity signal |
| Feature matching | 10.0 | L1 on the discriminator's intermediate features; stabilizes training |

Inference processes audio in `segment_length` chunks (131072 samples ≈ 3 s). Training uses mixed precision (`torch.amp`) and gradient checkpointing on CUDA.

### Use cases

You can experiment with reconstruction for music remastering from low-bitrate sources, audio intended for streaming, or compressed recordings in an archive. Compare the output with your source before deciding whether to keep it.

## Repository map

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

`backend/` is a local dev server. It imports `model/` directly, handles one request at a time, and uses permissive CORS. It reads the checkpoint path from `CHECKPOINT_DIR` (default `model/checkpoints/best/`) and is not deployed.

`server/` runs in production on Modal.com. It keeps its own copy of the inference-only model code in `server/model/` because Modal packages `server/` as an isolated container image. It adds dynamic batching, rate limiting, strict CORS, structured logging, and pre-signed uploads.

When changing inference behavior for production, edit `server/`.

### Pre-signed uploads (production only)

The browser uploads straight to Azure Blob Storage instead of sending the upload through the GPU container:

1. `POST /upload-url` → `{uploadUrl, blobName}` — a write-only SAS scoped to one blob, 15 min.
2. Browser `PUT`s the MP3 directly to Azure (header `x-ms-blob-type: BlockBlob`).
3. `POST /model-serve` with `{blobName, filename}` → `{downloadUrl, filename, size}` — a read-only SAS, 1 hour, that saves as `<stem>_reconstructed.flac`.

The server generates `blobName` and validates it again on arrival because it is used as a temporary file path. It deletes the input blob after processing.

## Getting started (developers)

### Prerequisites

- Python 3.12 (pinned in `.python-version`; root project requires `>=3.10`)
- Node.js >= 20
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

> [Download the model weights from Hugging Face](https://huggingface.co/rohanprasen-kedari/audioreconstruction/tree/main/checkpoints/best) and place `generator.safetensors` under `./model/checkpoints/best/`. Training saves checkpoints there; inference loads only the generator.

### Run locally

```bash
# Terminal 1 — local backend (loads model/ directly)
uv run uvicorn backend.main:app --reload       # http://localhost:8000

# Terminal 2 — frontend (proxies /api/* to the backend in dev)
cd frontend && bun dev                          # http://localhost:5173
```

See [`frontend/CLAUDE.md`](frontend/CLAUDE.md) for the frontend state model, retry and backoff logic, and styling.

## Training your own model

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

Training data follows this layout:

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
Model weights use safetensors exclusively; the `.pt` file holds training state.

## Evaluation & audio metrics

```bash
# Reconstruct and (optionally) score against reference FLACs — single file or directory
uv run python -m model.evaluate --checkpoint model/checkpoints/best --input song.mp3 --output output/
uv run python -m model.evaluate --checkpoint model/checkpoints/best \
  --input data/lossy/128/ --output output/ --reference data/lossless/
```

`evaluate` computes PESQ and SNR when references are supplied. The `test/`
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

The server runs on a T4 GPU (`min_containers=0`, `max_containers=2`) and scales to zero
when idle. It uses `slowapi` for rate limiting and restricts CORS to the frontend origin.

### Azure Blob Storage

The production server needs these environment variables (supplied on Modal via the `azure-blob` secret):
`AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY`, `AZURE_UPLOAD_CONTAINER`, `AZURE_OUTPUT_CONTAINER`
(and `AZURE_BLOB_ENDPOINT` to point at Azurite locally).

> The storage account must have a CORS rule allowing `PUT`/`GET` from the frontend origin, or the browser's direct upload is blocked.

### ONNX CLI release flow

Build the native binary with PyInstaller, then generate the SHA-256 `manifest.json`.
Upload the binary, `model.onnx`, `config.json`, and `manifest.json` to a GitHub Release
tagged `audioreconstructor-v<version>`, and bump `onnx/cli/pyproject.toml` to match.
The package version and release tag must match. See [`onnx/cli/README.md`](onnx/cli/README.md).

## Development commands

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

## Tech stack

| Layer      | Technology                                      |
| ---------- | ----------------------------------------------- |
| Model      | PyTorch, torchaudio, safetensors                |
| Backend    | FastAPI, uvicorn, SlowAPI                        |
| Deployment | Modal.com (serverless GPU — T4), Azure Blob      |
| Frontend   | React 19, Vite 8, Tailwind CSS 4, Framer Motion |
| CLI        | ONNX Runtime, Click, Rich, PyInstaller          |
| Metrics    | PESQ, SNR, LSD, SI-SDR, Mel-SSIM                 |
| Tooling    | uv (Python), Bun (JS), Ruff (lint)              |

## Key constraints

- Python 3.12 is pinned in `.python-version`; the root project requires `>=3.10`, and the CLI package supports 3.10–3.13
- Training requires CUDA for mixed precision; inference falls back to CPU but is slow
- Data preparation requires FFmpeg
- Audio is always stereo (`in_channels=2`), 44.1 kHz
- Model weights use safetensors exclusively, not `.pt`
- Both inference servers limit uploads to 25 MB / 6 minutes

## Project docs

| Doc | What's in it |
| --- | ------------ |
| [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) | Full architecture guide for agents (mirrors of each other) |
| [`PRODUCT.md`](PRODUCT.md) | Product purpose and target user |
| [`DESIGN.md`](DESIGN.md) | Design system: color tokens and typography |
| [`frontend/CLAUDE.md`](frontend/CLAUDE.md) | Frontend state model, retry logic, styling |
| [`onnx/cli/README.md`](onnx/cli/README.md) | CLI usage, execution providers, cache locations |
| [`test/README.md`](test/README.md) | Audio-similarity evaluation scripts and a sample comparison |
| [`openspec/changes/`](openspec/changes/) | Planned / in-flight change proposals |

## Contributing

Read the [contribution guidelines](docs/CONTRIBUTING.md) and [code of conduct](docs/CODE_OF_CONDUCT.md) before contributing.

## Security

To report a vulnerability, see [SECURITY.md](docs/SECURITY.md).

## License

[MIT](LICENSE) — Rohan Prasen Kedari

---

Found this useful? A star helps other people find it — and nudges me to keep improving the model.
