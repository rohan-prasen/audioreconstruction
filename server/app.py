from __future__ import annotations

import asyncio
import datetime as dt
import gc
import logging
import os
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
import torch
from audio_io import load_audio_sf, write_flac
from batcher import InferenceBatcher
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from model.evaluate import load_generator, warmup_generator

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
MODEL_CHECKPOINT_DIR = Path("/checkpoints/best/")
TEMP_DIR = Path(tempfile.gettempdir()) / "audioreconstruction"
INFERENCE_TIMEOUT = 180


def _preprocess_audio(
    content: bytes,
    cfg,
) -> list[tuple[torch.Tensor, int]]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=str(TEMP_DIR))
    tmp.write(content)
    tmp.close()
    input_path = Path(tmp.name)

    try:
        info = sf.info(str(input_path))
        duration = info.frames / info.samplerate
        if duration > 360:
            raise ValueError("Audio exceeds 6 minute limit.")

        waveform = load_audio_sf(
            input_path, target_sr=cfg.sample_rate, channels=cfg.in_channels
        )
    finally:
        input_path.unlink(missing_ok=True)

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


def _encode_flac(result: torch.Tensor, sample_rate: int) -> bytes:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".flac", delete=False, dir=str(TEMP_DIR))
    tmp.close()
    output_path = Path(tmp.name)
    try:
        write_flac(result, output_path, sample_rate)
        return output_path.read_bytes()
    finally:
        output_path.unlink(missing_ok=True)


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

        t0 = time.monotonic()
        warmup_generator(generator, device, cfg)
        logger.info("Warmup done in %.1fs", time.monotonic() - t0)

        batcher = InferenceBatcher(generator=generator, device=device)
        await batcher.start()

        app.state.generator = generator
        app.state.device = device
        app.state.batcher = batcher
        app.state.cfg = cfg
        app.state.ready = True
    except Exception as exc:
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
    allow_origins=["https://audioreconstruction.vercel.app"],
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
async def model_serve(request: Request, file: UploadFile):
    if not app.state.ready:
        raise HTTPException(503, "Model not loaded.")

    if (
        file.content_type
        and "audio" not in file.content_type
        and "octet-stream" not in file.content_type
    ):
        raise HTTPException(415, "Expected an audio file.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413, f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )

    loop = asyncio.get_running_loop()
    batcher: InferenceBatcher = app.state.batcher
    cfg = app.state.cfg

    try:
        segments = await loop.run_in_executor(
            None, _preprocess_audio, content, cfg
        )
        del content
    except ValueError as exc:
        raise HTTPException(413, str(exc))

    try:
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

        flac_bytes = await loop.run_in_executor(
            None, _encode_flac, combined, cfg.sample_rate
        )
        del combined

        stem = Path(file.filename).stem if file.filename else "output"

        return StreamingResponse(
            iter([flac_bytes]),
            media_type="audio/flac",
            headers={
                "Content-Disposition": f'attachment; filename="{stem}_reconstructed.flac"'
            },
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Inference timed out — file may be too big.")
    except Exception:
        logger.exception("Inference failed")
        raise HTTPException(500, "Inference failed.")
    finally:
        gc.collect()
