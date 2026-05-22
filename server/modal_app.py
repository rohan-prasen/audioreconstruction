from pathlib import Path

import modal

_SERVER_DIR = Path(__file__).parent

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "fastapi",
        "uvicorn",
        "python-multipart",
        "slowapi",
        "soundfile",
        "numpy",
        "safetensors",
        "torch",
        "torchaudio",
    )
    .add_local_dir(
        _SERVER_DIR,
        remote_path="/root/server",
        ignore=lambda p: p.is_relative_to("model/checkpoints")
        or p.name == "modal_app.py"
        or p.is_relative_to("__pycache__"),
    )
    .add_local_dir(
        _SERVER_DIR / "model" / "checkpoints",
        remote_path="/checkpoints",
    )
)

app = modal.App("audioreconstruction")


@app.function(
    image=image,
    gpu="T4",
    timeout=1800,
    scaledown_window=300,
    min_containers=0,
    max_containers=1,
    memory=8192,
)
@modal.asgi_app()
def fastapi_app():
    import sys
    sys.path.insert(0, "/root")
    sys.path.insert(0, "/root/server")
    from app import app
    return app
