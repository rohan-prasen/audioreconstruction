# Model

GAN-based audio super-resolution. Takes any MP3 (unknown bitrate) and reconstructs a high-fidelity stereo FLAC.

**Architecture:** 1D U-Net generator (28.2M params) + multi-scale discriminator (25.1M params)
**Training:** Mixed-precision, gradient checkpointing | **Peak VRAM:** ~3 GB on RTX 4070

---

## Prerequisites

- Python >= 3.10
- NVIDIA GPU with CUDA (tested on RTX 4070, 12 GB)
- [FFmpeg](https://ffmpeg.org/) (for data preparation)
- [uv](https://docs.astral.sh/uv/) (Python package manager)

```bash
# Install all dependencies from the project root
uv sync
```

---

## Quick Start

### 1. Prepare your data

Place your lossless FLAC files in root `data/lossless/`, then generate the lossy training pairs:

```bash
uv run python -m model.prepare_data
```

This transcodes every FLAC to MP3 at 128, 256, and 320 kbps into root `data/lossy/{128,256,320}/`. Existing files are skipped on re-runs.

**Custom paths:**

```bash
uv run python -m model.prepare_data --input /path/to/flacs --output /path/to/lossy
```

### 2. Train

```bash
uv run python -m model.train
```

| Flag | Default | Description |
|------|---------|-------------|
| `--epochs` | 200 | Total training epochs |
| `--batch-size` | 4 | Batch size (safe up to ~16 on 12 GB) |
| `--lr` | 1e-4 | Learning rate for both G and D |
| `--resume` | — | Path to a checkpoint dir to resume from |
| `--checkpoint-dir` | `model/checkpoints` | Where to save checkpoints |
| `--data-lossless` | `data/lossless` | Lossless FLAC directory |
| `--data-lossy` | `data/lossy` | Lossy MP3 directory |

Training automatically:
- Mixes all three bitrates so the model generalizes to unknown compression
- Splits files 80/20 into train/val sets
- Saves the best checkpoint (lowest val spectral loss) to `checkpoints/best/`
- Saves periodic checkpoints every 10 epochs
- Logs per-epoch metrics: G loss, D loss, spectral loss, feature matching loss, adversarial loss

**Resume from a checkpoint:**

```bash
uv run python -m model.train --resume model/checkpoints/epoch_50
```

### 3. Evaluate / Infer

Reconstruct a single MP3 to FLAC:

```bash
uv run python -m model.evaluate \
  --checkpoint model/checkpoints/best \
  --input song.mp3 \
  --output output/
```

Reconstruct an entire directory:

```bash
uv run python -m model.evaluate \
  --checkpoint model/checkpoints/best \
  --input /path/to/mp3s/ \
  --output /path/to/output/
```

Evaluate against reference FLACs (computes PESQ and SNR):

```bash
uv run python -m model.evaluate \
  --checkpoint model/checkpoints/best \
  --input data/lossy/128/ \
  --output output/ \
  --reference data/lossless/
```

### 4. Export for HuggingFace

```bash
uv run python -m model.export --checkpoint model/checkpoints/best
```

Produces `exported/model.safetensors` and `exported/config.json` — only the generator weights (discriminator is not needed at inference).

**Push to HuggingFace Hub:**

```bash
huggingface-cli upload your-username/audio-super-resolution exported/
```

---

## File Reference

| File | Purpose |
|------|---------|
| `config.py` | `ModelConfig`, `TrainConfig`, `DataConfig` dataclasses |
| `generator.py` | 1D U-Net with skip connections and gradient checkpointing |
| `discriminator.py` | Multi-scale discriminator (3 scales) |
| `losses.py` | LSGAN + multi-scale spectral + feature matching losses |
| `dataset.py` | Stereo audio pair dataset with random bitrate sampling |
| `train.py` | Training loop with mixed precision and rich progress |
| `evaluate.py` | Inference (MP3 to FLAC) and metrics (PESQ, SNR) |
| `export.py` | Export generator weights as safetensors for HuggingFace |
| `prepare_data.py` | FFmpeg batch transcoder (FLAC to MP3 at 128/256/320) |
| `utils.py` | Audio I/O, normalization, checkpoint save/load |

## Training Loss Components

| Loss | Weight | Purpose |
|------|--------|---------|
| Adversarial (LSGAN) | 1.0 | Perceptual realism |
| Multi-scale spectral | 100.0 | Frequency accuracy (STFT at 512, 1024, 2048) |
| Feature matching | 10.0 | Stability via discriminator feature alignment |

## Data Layout

```
data/
├── lossless/          # Your original FLAC files
└── lossy/
    ├── 128/           # Generated: 128 kbps MP3
    ├── 256/           # Generated: 256 kbps MP3
    └── 320/           # Generated: 320 kbps MP3
```

Files are paired by filename: `data/lossless/track.flac` matches `data/lossy/128/track.mp3`.
