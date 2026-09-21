from __future__ import annotations

import asyncio
import datetime as dt
import gc
import logging
import os
import re
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
import torch
from audio_io import copy_metadata, load_audio_sf, write_flac
from batcher import InferenceBatcher
from blob_storage import (
    BlobStorageError,
    blob_size,
    delete_blob,
    download_to_path,
    make_download_sas,
    make_upload_sas,
    new_blob_name,
    upload_flac,
)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from model.evaluate import load_generator

torch.set_num_threads(2)

_IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


class _ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return dt.datetime.fromtimestamp(record.created, tz=_IST).strftime(
            datefmt or "%Y-%m-%d %H:%M:%S"
        )


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    _ISTFormatter(
        fmt="%(asctime)s IST | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logging.root.handlers.clear()
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("audioreconstruction")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_CHUNK = 1024 * 1024
MODEL_CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", "/checkpoints/best/"))
TEMP_DIR = Path(tempfile.gettempdir()) / "audioreconstruction"
INFERENCE_TIMEOUT = 180

# Comma-separated. Defaults to production only; set in dev to add localhost.
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "https://audioreconstruction.vercel.app"
    ).split(",")
    if o.strip()
]

# Exactly what new_blob_name() produces. Nothing else is accepted.
_BLOB_NAME_RE = re.compile(r"^[0-9a-f]{32}\.mp3$")
_UNSAFE_STEM_RE = re.compile(r'[^\w\-. ]')


class ServeRequest(BaseModel):
    blobName: str
    filename: str | None = None


def _preprocess_audio(
    input_path: Path,
    cfg,
) -> list[tuple[torch.Tensor, int]]:
    info = sf.info(str(input_path))
    duration = info.frames / info.samplerate
    if duration > 360:
        raise ValueError("Audio exceeds 6 minute limit.")

    waveform = load_audio_sf(
        input_path, target_sr=cfg.sample_rate, channels=cfg.in_channels
    )

    peak = waveform.abs().max()
    if peak > 0:
        waveform = waveform / peak

    seg_len = cfg.segment_length
    length = waveform.shape[-1]
    segments: list[tuple[torch.Tensor, int]] = []

    if length <= seg_len:
        padded = torch.nn.functional.pad(waveform, (0, seg_len - length))
        segments.append((padded, length))
    else:
        for start in range(0, length, seg_len):
            chunk = waveform[:, start : start + seg_len]
            actual_len = chunk.shape[-1]
            if actual_len < seg_len:
                chunk = torch.nn.functional.pad(chunk, (0, seg_len - actual_len))
            segments.append((chunk, min(seg_len, length - start)))

    del waveform
    return segments


def _encode_flac(
    result: torch.Tensor,
    sample_rate: int,
    output_path: Path,
    src_mp3: Path | None = None,
) -> None:
    write_flac(result, output_path, sample_rate)
    if src_mp3 is not None:
        copy_metadata(src_mp3, output_path)


def _get_model_cfg(generator):
    if hasattr(generator, "cfg"):
        return generator.cfg
    if hasattr(generator, "_orig_mod") and hasattr(generator._orig_mod, "cfg"):
        return generator._orig_mod.cfg
    from model.config import ModelConfig
    return ModelConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    for f in TEMP_DIR.glob("*"):
        f.unlink(missing_ok=True)

    logger.info("===== Startup | PID=%d =====", os.getpid())

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    try:
        t0 = time.monotonic()
        generator = load_generator(MODEL_CHECKPOINT_DIR, device)
        logger.info("Model loaded in %.1fs", time.monotonic() - t0)

        cfg = _get_model_cfg(generator)

        batcher = InferenceBatcher(generator=generator, device=device)
        t0 = time.monotonic()
        await batcher.warmup(cfg)
        logger.info("Warmup done in %.1fs", time.monotonic() - t0)
        await batcher.start()

        app.state.generator = generator
        app.state.device = device
        app.state.batcher = batcher
        app.state.cfg = cfg
        app.state.ready = True
    except Exception as exc:  # noqa: BLE001 - keep app alive but not-ready if startup/warmup fails
        logger.error("Startup failed: %s", exc)
        app.state.ready = False
        app.state.batcher = None

    yield

    if getattr(app.state, "batcher", None) is not None:
        await app.state.batcher.stop()

    for f in TEMP_DIR.glob("*"):
        f.unlink(missing_ok=True)
    logger.info("===== Shutdown =====")


app = FastAPI(title="Audio Reconstruction", version="1.0.0", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "POST"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    return {"message": "Welcome to Audio Reconstruction API"}


@app.get("/health-check")
@limiter.limit("10/minute")
async def health_check(request: Request):
    return {
        "status": "ok" if app.state.ready else "degraded",
        "model_loaded": app.state.ready,
    }


@app.post("/model-serve")
@limiter.limit("40/minute")
async def model_serve(request: Request, body: ServeRequest):
    if not app.state.ready:
        raise HTTPException(503, "Model not loaded.")

    blob_name = body.blobName
    if not _BLOB_NAME_RE.match(blob_name):
        raise HTTPException(400, "Invalid blob name.")

    loop = asyncio.get_running_loop()
    batcher: InferenceBatcher = app.state.batcher
    cfg = app.state.cfg

    # Size is checked against Azure before any GPU work happens.
    try:
        size = await loop.run_in_executor(None, blob_size, blob_name)
    except BlobStorageError:
        raise HTTPException(404, "Upload not found or expired.")

    if size > MAX_UPLOAD_BYTES:
        await loop.run_in_executor(None, delete_blob, blob_name)
        raise HTTPException(
            413, f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    mp3_path = TEMP_DIR / blob_name
    flac_path: Path | None = None

    try:
        await loop.run_in_executor(None, download_to_path, blob_name, mp3_path)

        try:
            segments = await loop.run_in_executor(
                None, _preprocess_audio, mp3_path, cfg
            )
        except ValueError as exc:
            raise HTTPException(413, str(exc))

        futures = [batcher.submit(seg) for seg, _ in segments]
        results = await asyncio.wait_for(
            asyncio.gather(*futures),
            timeout=INFERENCE_TIMEOUT,
        )

        trimmed = [
            result[:, :actual_len]
            for result, (_, actual_len) in zip(results, segments)
        ]
        del segments, results

        combined = torch.cat(trimmed, dim=-1) if len(trimmed) > 1 else trimmed[0]
        del trimmed

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        out_blob = new_blob_name(".flac")
        flac_path = TEMP_DIR / out_blob
        await loop.run_in_executor(
            None, _encode_flac, combined, cfg.sample_rate, flac_path, mp3_path
        )
        del combined

        await loop.run_in_executor(None, upload_flac, flac_path, out_blob)

        stem = Path(body.filename).stem if body.filename else "output"
        stem = _UNSAFE_STEM_RE.sub("_", stem)[:100] or "output"
        download_name = f"{stem}_reconstructed.flac"

        return {
            "downloadUrl": make_download_sas(out_blob, download_name),
            "filename": download_name,
            "size": flac_path.stat().st_size,
        }
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(504, "Inference timed out — file may be too big.")
    except BlobStorageError as exc:
        logger.error("Storage failure: %s", exc)
        raise HTTPException(502, "Storage unavailable.")
    except Exception:
        logger.exception("Inference failed")
        raise HTTPException(500, "Inference failed.")
    finally:
        mp3_path.unlink(missing_ok=True)
        if flac_path is not None:
            flac_path.unlink(missing_ok=True)
        await loop.run_in_executor(None, delete_blob, blob_name)
        gc.collect()


@app.post("/upload-url")
@limiter.limit("20/minute")
async def upload_url(request: Request):
    """Hand the browser a short-lived, write-only key for one new blob."""
    blob_name = new_blob_name(".mp3")
    try:
        upload_url = make_upload_sas(blob_name)
    except BlobStorageError as exc:
        logger.error("Could not mint upload SAS: %s", exc)
        raise HTTPException(503, "Storage unavailable.")

    return {"uploadUrl": upload_url, "blobName": blob_name}
