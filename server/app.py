from __future__ import annotations

import datetime as dt
import gc
import hashlib
import logging
import os
import sys
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
import torch
from audio_io import load_audio_sf, write_flac
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
MODEL_CHECKPOINT_DIR = Path("/checkpoints/best/")
TEMP_DIR = Path(tempfile.gettempdir()) / "audioreconstruction"
INFERENCE_TIMEOUT = 180
CHECKPOINT_TTL = 600


class _InferenceCancelled(Exception):
    pass


class _InferenceTimeout(Exception):
    pass


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(65536):
            h.update(block)
    return h.hexdigest()[:16]


def _save_checkpoint(ckpt_path: Path, chunks: list, next_start: int, length: int):
    torch.save(
        {"chunks": chunks, "next_start": next_start, "length": length},
        ckpt_path,
    )


def _clean_stale_checkpoints():
    now = time.time()
    for f in TEMP_DIR.glob("*_ckpt.pt"):
        try:
            if now - f.stat().st_mtime > CHECKPOINT_TTL:
                f.unlink(missing_ok=True)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    for f in TEMP_DIR.glob("*"):
        if not f.name.endswith("_ckpt.pt"):
            f.unlink(missing_ok=True)
    _clean_stale_checkpoints()

    logger.info("===== Startup | PID=%d =====", os.getpid())

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    try:
        t0 = time.monotonic()
        generator = load_generator(MODEL_CHECKPOINT_DIR, device)
        logger.info("Model loaded in %.1fs", time.monotonic() - t0)
        app.state.generator = generator
        app.state.device = device
        app.state.ready = True
    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        app.state.ready = False

    app.state.cancel = threading.Event()

    yield

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


@torch.inference_mode()
def _run_inference(
    generator,
    device: torch.device,
    input_path: Path,
    cancel: threading.Event,
    deadline: float,
) -> torch.Tensor:
    cfg = generator.cfg
    waveform = load_audio_sf(
        input_path, target_sr=cfg.sample_rate, channels=cfg.in_channels
    )
    peak = waveform.abs().max()
    if peak > 0:
        waveform = waveform / peak

    seg_len = cfg.segment_length
    length = waveform.shape[-1]

    file_hash = _file_hash(input_path)
    ckpt_path = TEMP_DIR / f"{file_hash}_ckpt.pt"

    if length <= seg_len:
        padded = torch.nn.functional.pad(waveform, (0, seg_len - length))
        inp = padded.unsqueeze(0).to(device)
        out = generator(inp)
        result = out.squeeze(0).cpu()[:, :length]
        del inp, out, padded, waveform
        ckpt_path.unlink(missing_ok=True)
        return result

    chunks: list[torch.Tensor] = []
    start_idx = 0

    if ckpt_path.exists():
        try:
            ckpt = torch.load(ckpt_path, weights_only=True)
            if ckpt.get("length") == length:
                chunks = ckpt["chunks"]
                start_idx = ckpt["next_start"]
                logger.info(
                    "Resuming from segment %d/%d",
                    start_idx // seg_len,
                    (length + seg_len - 1) // seg_len,
                )
        except Exception:
            pass

    for start in range(start_idx, length, seg_len):
        if cancel.is_set():
            _save_checkpoint(ckpt_path, chunks, start, length)
            del waveform, chunks
            gc.collect()
            raise _InferenceCancelled()

        if time.monotonic() > deadline:
            _save_checkpoint(ckpt_path, chunks, start, length)
            logger.info(
                "Deadline hit at segment %d/%d — checkpoint saved",
                start // seg_len,
                (length + seg_len - 1) // seg_len,
            )
            del waveform, chunks
            gc.collect()
            raise _InferenceTimeout()

        chunk = waveform[:, start : start + seg_len]
        actual_len = chunk.shape[-1]
        if actual_len < seg_len:
            chunk = torch.nn.functional.pad(chunk, (0, seg_len - actual_len))
        inp = chunk.unsqueeze(0).to(device)
        out = generator(inp)
        chunks.append(out.squeeze(0).cpu()[:, : min(seg_len, length - start)])
        del inp, out, chunk

    del waveform
    result = torch.cat(chunks, dim=-1)
    del chunks
    ckpt_path.unlink(missing_ok=True)
    return result


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
@limiter.limit("10/minute")
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

    input_tmp = None
    output_tmp = None
    try:
        input_tmp = tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False, dir=str(TEMP_DIR)
        )
        input_tmp.write(content)
        input_tmp.close()
        del content

        input_path = Path(input_tmp.name)

        info = sf.info(str(input_path))
        duration = info.frames / info.samplerate
        if duration > 360:
            raise HTTPException(413, "Audio exceeds 6 minute limit.")

        generator = app.state.generator
        device = app.state.device

        app.state.cancel.clear()
        result = _run_inference(
            generator,
            device,
            input_path,
            app.state.cancel,
            time.monotonic() + INFERENCE_TIMEOUT,
        )

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        output_tmp = tempfile.NamedTemporaryFile(
            suffix=".flac", delete=False, dir=str(TEMP_DIR)
        )
        output_tmp.close()

        write_flac(result, Path(output_tmp.name), generator.cfg.sample_rate)
        del result

        flac_bytes = Path(output_tmp.name).read_bytes()
        stem = Path(file.filename).stem if file.filename else "output"

        return StreamingResponse(
            iter([flac_bytes]),
            media_type="audio/flac",
            headers={
                "Content-Disposition": f'attachment; filename="{stem}_reconstructed.flac"'
            },
        )
    except _InferenceCancelled:
        raise HTTPException(503, "Inference cancelled.")
    except _InferenceTimeout:
        raise HTTPException(504, "Inference timed out — file may be too big.")
    finally:
        if input_tmp is not None:
            Path(input_tmp.name).unlink(missing_ok=True)
        if output_tmp is not None:
            Path(output_tmp.name).unlink(missing_ok=True)
        gc.collect()
