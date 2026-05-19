# Audio Super-Resolution

Reconstruct high-fidelity audio from compressed MP3 sources using adversarial neural networks. The model restores lost high-frequency harmonics, spectral detail, and natural timbre — producing near-lossless FLAC output from lossy input.

**Input:** MP3 (128 / 256 / 320 kbps) | **Output:** FLAC (~800+ kbps effective bitrate)

---

## How It Works

A GAN (Generative Adversarial Network) learns to reverse compression artifacts:

1. **Generator** — predicts high-resolution spectral content from the compressed waveform
2. **Discriminator** — enforces perceptual realism by distinguishing real from reconstructed audio
3. **Training objective** — combines adversarial loss, multi-scale spectral loss, and perceptual loss

## Use Cases

- Music remastering from low-bitrate sources
- Streaming audio quality enhancement
- Archival recovery of degraded recordings

---

## Architecture

```
audioreconstruction/
├── backend/           # FastAPI inference server
├── frontend/          # React + Vite + Tailwind UI
├── model/             # PyTorch model weights and configs
├── docker/            # Container definitions
├── docs/              # Contributing, security, code of conduct
└── pyproject.toml     # Python project config (uv)
```

## Tech Stack

| Layer    | Technology                            |
|----------|---------------------------------------|
| Model    | PyTorch, torchaudio, safetensors      |
| Backend  | FastAPI, uvicorn                      |
| Frontend | React 19, Vite 8, Tailwind CSS 4     |
| Metrics  | PESQ (perceptual evaluation)          |
| Tooling  | uv (Python), Bun (JS), Ruff (lint)   |

---

## Getting Started

### Prerequisites

- Python >= 3.10
- Node.js >= 20
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Bun](https://bun.sh/) (JS package manager, optional — npm works too)

### Setup

```bash
git clone git@github.com:rohan-prasen/audioreconstruction.git
cd audioreconstruction

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && bun install
```

### Run

```bash
# Start the backend
uv run uvicorn backend.main:app --reload

# Start the frontend (in a separate terminal)
cd frontend && bun dev
```

---

## Development

```bash
# Lint Python
uv run ruff check .

# Lint frontend
cd frontend && bun lint

# Run tests
uv run pytest
```

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## Security

To report a vulnerability, see [docs/SECURITY.md](docs/SECURITY.md).

## License

[MIT](LICENSE) — Rohan Prasen Kedari