# onnx_export

Exports the generator to ONNX and runs inference on it without PyTorch — built so the
audio-enhancement model can be embedded in third-party apps (e.g. an Electron music
player) without shipping a ~200MB+ PyTorch install to every end user.

**Why ONNX instead of PyTorch/safetensors:** the generator (28.2M params, pure
`Conv1d`/`ConvTranspose1d`/`BatchNorm1d`/`LeakyReLU`/`Tanh` + one residual add) has no
export blockers, and ONNX Runtime's CPU wheel is ~15-30MB versus PyTorch's ~200MB+ —
that's what makes a "download and run" UX viable for end users who don't have Python.

---

## Two scripts, two audiences

| Script | Who runs it | Needs PyTorch? |
|---|---|---|
| `export.py` | You, once per model version, in this repo's dev environment | Yes |
| `inference.py` | The end-user-facing app (or you, to test) | **No** — only `requirements-onnx.txt` |

`export.py` converts a trained PyTorch checkpoint into `model.onnx` +
`config.json`. `inference.py` is what actually ships — a standalone CLI that
takes an MP3 and produces an enhanced FLAC using only `onnxruntime` + a few small
pure-Python libraries.

---

## 1. Export a checkpoint to ONNX

From the repo root, with the dev environment installed:

```bash
uv sync --group onnx
uv run python -m onnx_export.export --checkpoint model/checkpoints/best
```

| Flag | Default | Description |
|------|---------|-------------|
| `--checkpoint` | `model/checkpoints/best` | Directory containing `generator.safetensors` + `config.json` |
| `--output` | `onnx_export/exported` | Where to write `model.onnx` + `config.json` |
| `--opset` | 18 | ONNX opset version |
| `--skip-verify` | off | Skip the PyTorch-vs-ONNX parity check |

This:
1. Loads the generator the same way `model/evaluate.py` does.
2. Exports it with a **fixed input shape** `(1, 2, 131072)` — the model is only ever
   called on 131072-sample (~2.97s) chunks; chunking happens outside the model, not
   inside `forward()`, so there's no need for dynamic axes.
3. Runs one sample through both the PyTorch model and the exported ONNX model and
   compares outputs (`PASS`/`FAIL` printed, non-zero exit on failure — this is the
   parity check `--skip-verify` disables).
4. Prints a `huggingface-cli upload` command for publishing the result.

Expect a `model.onnx` of ~112.6 MB (fp32, same 28.2M params as the safetensors
checkpoint — ONNX export doesn't quantize or shrink weights on its own) and a
`PASS` with `max abs diff` at or near `0.000000`.

---

## 2. Run inference (the shipped script)

This is the one that matters for embedding — it never imports `torch`.

**Install its own, much smaller, dependency set** (do this in whatever environment
will actually run it — a fresh venv, a bundled Python, etc., not necessarily this
repo's main `.venv`):

```bash
pip install -r onnx_export/requirements-onnx.txt
```

**Convert a file:**

```bash
python -m onnx_export.inference \
  --model onnx_export/exported/model.onnx \
  --config onnx_export/exported/config.json \
  --input song.mp3 \
  --output song_enhanced.flac
```

**Self-test** (no real audio file needed — generates synthetic noise, runs the full
pipeline end-to-end, and asserts the output is sane):

```bash
python -m onnx_export.inference \
  --model onnx_export/exported/model.onnx \
  --config onnx_export/exported/config.json \
  --self-test
```

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | *(required)* | Path to `model.onnx` |
| `--config` | *(required)* | Path to the matching `config.json` |
| `--input` | — | Source audio file (required unless `--self-test`) |
| `--output` | — | Destination `.flac` path (required unless `--self-test`) |
| `--provider` | `auto` | `auto` \| `cpu` \| `directml` \| `coreml` — see below |
| `--self-test` | off | Round-trip a synthetic sample instead of a real file |

What it does, matching `model/evaluate.py`'s pipeline exactly:
1. Reads the input with `soundfile` (libsndfile decodes MP3 directly — no ffmpeg needed).
2. Coerces to the model's channel count (mono → stereo duplication, extra channels dropped).
3. Resamples to 44100 Hz with `scipy.signal.resample_poly` if needed (most MP3s are
   already 44100 Hz, so this path rarely triggers).
4. Peak-normalizes (divides by max absolute sample).
5. Splits into non-overlapping 131072-sample chunks (last chunk zero-padded), runs each
   through the ONNX session, truncates padding, concatenates — **no overlap-add/crossfade**,
   same as the reference PyTorch implementation.
6. Writes the result as FLAC via `soundfile`.
7. Copies ID3 tags (title/artist/album/genre/etc.) and cover art from the source MP3
   onto the output FLAC's Vorbis comments via `mutagen` — without this step every
   enhanced track would lose its metadata in a music player's library view.

### Execution providers (`--provider`)

`auto` (the default) picks the best zero-install option per platform:

| Platform | Provider tried first | Falls back to |
|---|---|---|
| Windows | `DmlExecutionProvider` (DirectML — any DX12 GPU, no CUDA install needed) | CPU |
| macOS | `CoreMLExecutionProvider` | CPU |
| Linux | CPU only | — |

Linux has no zero-install GPU option here (CUDA on Linux requires the user to already
have matching CUDA/cuDNN runtime libraries, which can't be bundled blind) — this is a
deliberate v1 scoping decision, not an oversight. If session creation or the first
inference call fails on a non-CPU provider, the script automatically rebuilds the
session with `CPUExecutionProvider` and continues — no crash, no manual fallback needed.

### stdout / stderr contract

This is the interface a calling application (e.g. an Electron main process spawning
this as a subprocess) should parse:

| Stream | Format | Meaning |
|---|---|---|
| stdout | `PROGRESS <0-100>` | Emitted once per chunk processed |
| stdout | `DONE <output_path>` | Success, followed by exit code `0` |
| stderr | `ERROR <CODE> <message>` | Failure, followed by a non-zero exit code |

Error codes:

| Code | Exit | Meaning |
|---|---|---|
| `MODEL_NOT_FOUND` | 3 | `--model` or `--config` path doesn't exist |
| `INPUT_READ_FAILED` | 2 | Input file missing, corrupt, or an unsupported format |
| `ORT_INIT_FAILED` | 4 | onnxruntime couldn't initialize even the CPU provider |
| `GENERIC` | 1 | Anything else |

---

## Files in this directory

| File | Purpose |
|------|---------|
| `export.py` | Dev-only: PyTorch checkpoint → `model.onnx` + `config.json`, with parity verification |
| `inference.py` | Shipped, torch-free: MP3 → enhanced FLAC using onnxruntime |
| `requirements-onnx.txt` | Pinned dependencies for `inference.py` only (not this repo's main install) |
| `manifest.json` | Version/hash pins for the exported model, used by a downstream downloader to verify integrity before trusting a fetched `model.onnx` |
| `exported/` | Default output directory for `export.py` (gitignored — regenerate locally, don't commit) |

### Publishing a new model version

After exporting and verifying (`export.py`'s `PASS`):

```bash
huggingface-cli upload rohanprasen-kedari/audioreconstruction onnx_export/exported/ checkpoints/best-onnx/
sha256sum onnx_export/exported/model.onnx onnx_export/exported/config.json
```

Update `manifest.json`'s `modelVersion` and the `sha256`/`bytes` fields for both files
to match — this is what a downstream downloader pins against instead of trusting an
unversioned "latest" fetch.
