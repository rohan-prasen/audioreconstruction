# Audio Reconstruction

Reconstruct high-fidelity audio from compressed MP3 sources using adversarial neural networks. The model restores lost high-frequency harmonics, spectral detail, and natural timbre — producing near-lossless FLAC output from lossy input.

**Input:** MP3 (128 / 256 / 320 kbps) | **Output:** FLAC (~800+ kbps effective bitrate)

![](/media/recordings/demo.gif)

## How It Works

A GAN (Generative Adversarial Network) learns to reverse compression artifacts:

1. **Generator** — a 1D U-Net (~28M params) that predicts high-resolution spectral content from the compressed waveform via a residual connection (learns the difference, not the full signal)
2. **Discriminator** — a multi-scale network (~25M params) that enforces perceptual realism by distinguishing real from reconstructed audio
3. **Training objective** — combines LSGAN adversarial loss, multi-scale spectral loss (STFT at 512/1024/2048), and feature matching loss

## Use Cases

- Music remastering from low-bitrate sources
- Streaming audio quality enhancement
- Archival recovery of degraded recordings

## Architecture

```
audioreconstruction/
├── backend/           # Local FastAPI inference server
├── server/            # Production server (Modal.com GPU deployment)
├── frontend/          # React 19 + Vite 8 + Tailwind CSS 4 UI
├── model/             # PyTorch model definition, training, and evaluation
├── test/              # Audio similarity evaluation scripts
├── design/            # UI design briefs and mockups
├── docs/              # Contributing, security, code of conduct
└── pyproject.toml     # Python project config (uv)
```

## Tech Stack

| Layer      | Technology                            |
|------------|---------------------------------------|
| Model      | PyTorch, torchaudio, safetensors      |
| Backend    | FastAPI, uvicorn, SlowAPI             |
| Deployment | Modal.com (GPU serverless — T4)       |
| Frontend   | React 19, Vite 8, Tailwind CSS 4     |
| Metrics    | PESQ, SNR (perceptual evaluation)     |
| Tooling    | uv (Python), Bun (JS), Ruff (lint)   |

## Getting Started

### Prerequisites

- Python >= 3.10
- Node.js >= 20
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Bun](https://bun.sh/) (JS package manager, optional — npm works too)
- [FFmpeg](https://ffmpeg.org/) (for data preparation)

### Setup

```bash
git clone git@github.com:rohan-prasen/audioreconstruction.git
cd audioreconstruction

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && bun install
```

> Model weights are hosted on HuggingFace — [download here](https://huggingface.co/rohanprasen-kedari/audioreconstruction/tree/main/checkpoints/best). Place `generator.safetensors` under `./model/checkpoints/best/`.

### Run Locally

```bash
# Start the local backend
uv run uvicorn backend.main:app --reload

# Start the frontend (in a separate terminal)
cd frontend && bun dev
```

### Deploy to Modal

```bash
# Deploy the production server to Modal.com (requires `modal` CLI auth)
cd server && modal deploy modal_app.py
```

## Development

```bash
# Lint Python
uv run ruff check .

# Lint frontend
cd frontend && bun lint

# Run tests
uv run pytest

# Prepare training data (requires FFmpeg)
uv run python -m model.prepare_data

# Train the model
uv run python -m model.train

# Evaluate / infer
uv run python -m model.evaluate --checkpoint model/checkpoints/best --input song.mp3 --output output/
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## Security

To report a vulnerability, see [SECURITY.md](docs/SECURITY.md).

## License

[MIT](LICENSE) — Rohan Prasen Kedari
