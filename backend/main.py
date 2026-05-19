from __future__ import annotations

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from model.evaluate import load_generator, reconstruct

load_dotenv()

CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", "model/checkpoints/best/"))
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        generator = load_generator(CHECKPOINT_DIR, device)
        app.state.generator = generator
        app.state.device = device
        app.state.model_loaded = True
    except Exception as exc:
        logger.warning("Could not load model from %s: %s", CHECKPOINT_DIR, exc)
        app.state.generator = None
        app.state.device = device
        app.state.model_loaded = False
    yield


app = FastAPI(title="Audio Reconstruction", lifespan=lifespan)

@app.get("/")
async def hello():
    return {"Hello" : "Welcome to Audio Reconstruction API"}

@app.get("/health-check")
async def health_check():
    return {
        "status": "ok",
        "model_loaded": app.state.model_loaded,
        "device": str(app.state.device),
    }


@app.post("/model-serve")
async def model_serve(file: UploadFile):
    if not app.state.model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded. Place a checkpoint in the configured directory.")

    if file.content_type and "audio" not in file.content_type and "octet-stream" not in file.content_type:
        raise HTTPException(status_code=415, detail="Expected an audio file (MP3).")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")

    input_tmp = None
    output_tmp = None
    try:
        input_tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        input_tmp.write(content)
        input_tmp.close()

        generator = app.state.generator
        device = app.state.device
        result = reconstruct(generator, Path(input_tmp.name), device)

        output_tmp = tempfile.NamedTemporaryFile(suffix=".flac", delete=False)
        output_tmp.close()
        audio_out = result.squeeze(0).T.numpy()
        sf.write(output_tmp.name, audio_out, generator.cfg.sample_rate)

        flac_bytes = Path(output_tmp.name).read_bytes()

        stem = Path(file.filename).stem if file.filename else "output"
        return StreamingResponse(
            iter([flac_bytes]),
            media_type="audio/flac",
            headers={"Content-Disposition": f'attachment; filename="{stem}.flac"'},
        )
    finally:
        if input_tmp is not None:
            Path(input_tmp.name).unlink(missing_ok=True)
        if output_tmp is not None:
            Path(output_tmp.name).unlink(missing_ok=True)
