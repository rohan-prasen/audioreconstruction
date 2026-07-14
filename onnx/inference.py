"""Torch-free CLI: enhance an MP3 into a FLAC using an exported ONNX generator.

Shipped standalone (see requirements-onnx.txt) and spawned as a subprocess by the
host Electron app, one process per file. Stdout/stderr contract:
  PROGRESS <0-100>\\n      (stdout, one per chunk)
  DONE <output_path>\\n    (stdout, exit 0)
  ERROR <CODE> <message>\\n (stderr, exit non-zero)
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
import onnxruntime as ort
import scipy.signal
import soundfile as sf
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3

ID3_TO_VORBIS = {
    "TPE1": "ARTIST",
    "TIT2": "TITLE",
    "TALB": "ALBUM",
    "TDRC": "DATE",
    "TRCK": "TRACKNUMBER",
    "TPOS": "DISCNUMBER",
    "TCON": "GENRE",
    "TPE2": "ALBUMARTIST",
    "TCOM": "COMPOSER",
    "TCOP": "COPYRIGHT",
    "COMM": "COMMENT",
}


class ModelNotFoundError(Exception):
    pass


class InputReadError(Exception):
    pass


class OrtInitError(Exception):
    pass


def resolve_providers(preference: str) -> list[str]:
    if preference == "cpu":
        return ["CPUExecutionProvider"]
    if preference == "directml":
        return ["DmlExecutionProvider", "CPUExecutionProvider"]
    if preference == "coreml":
        return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    system = platform.system()
    if system == "Windows":
        return ["DmlExecutionProvider", "CPUExecutionProvider"]
    if system == "Darwin":
        return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def load_audio(path: Path, target_sr: int, channels: int) -> np.ndarray:
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception as exc:
        raise InputReadError(f"could not read {path}: {exc}") from exc

    waveform = data.T  # (channels, samples)
    if waveform.shape[0] != channels:
        waveform = np.tile(waveform, (channels, 1))[:channels]

    if sr != target_sr:
        frac = Fraction(target_sr, sr).limit_denominator(1000)
        waveform = scipy.signal.resample_poly(waveform, frac.numerator, frac.denominator, axis=-1)

    return waveform.astype(np.float32)


def normalize_audio(waveform: np.ndarray) -> np.ndarray:
    peak = np.abs(waveform).max()
    if peak > 0:
        waveform = waveform / peak
    return waveform


def read_id3v1(path: Path) -> dict[str, str] | None:
    """Minimal ID3v1/1.1 trailer reader — mutagen's ID3 class only parses ID3v2."""
    try:
        with open(path, "rb") as f:
            f.seek(-128, 2)
            tag = f.read(128)
    except OSError:
        return None
    if tag[:3] != b"TAG":
        return None

    def field(data: bytes) -> str:
        return data.split(b"\x00")[0].decode("latin-1").strip()

    values = {
        "TITLE": field(tag[3:33]),
        "ARTIST": field(tag[33:63]),
        "ALBUM": field(tag[63:93]),
        "DATE": field(tag[93:97]),
        "COMMENT": field(tag[97:127]),
    }
    return {k: v for k, v in values.items() if v} or None


def copy_metadata(src_mp3: Path, dst_flac: Path) -> None:
    flac = FLAC(str(dst_flac))
    has_tags = False
    id3 = None
    try:
        id3 = ID3(str(src_mp3))
    except Exception as exc:
        v1_tags = read_id3v1(src_mp3)
        if v1_tags:
            for vorbis_key, text in v1_tags.items():
                flac[vorbis_key] = [text]
                has_tags = True
        else:
            print(f"WARN metadata copy skipped for {src_mp3.name}: {exc}", file=sys.stderr)

    if id3 is not None:
        for id3_key, vorbis_key in ID3_TO_VORBIS.items():
            frame = id3.get(id3_key)
            if frame is None:
                continue
            text = frame.text[0] if id3_key == "COMM" and frame.text else str(frame)
            if text:
                flac[vorbis_key] = [text]
                has_tags = True

        pictures = [id3[key] for key in id3 if key.startswith("APIC") and id3[key].data]
        cover = next((p for p in pictures if p.type == 3), pictures[0] if pictures else None)
        if cover:
            pic = Picture()
            pic.type = cover.type
            pic.mime = cover.mime
            pic.desc = cover.desc
            pic.data = cover.data
            flac.add_picture(pic)
            has_tags = True

    if has_tags:
        flac.save()


def create_session(model_path: Path, providers: list[str]) -> ort.InferenceSession:
    try:
        return ort.InferenceSession(str(model_path), providers=providers)
    except Exception as exc:
        if providers == ["CPUExecutionProvider"]:
            raise OrtInitError(f"onnxruntime failed to initialize even CPUExecutionProvider: {exc}") from exc
        try:
            return ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        except Exception as cpu_exc:
            raise OrtInitError(f"onnxruntime failed to initialize even CPUExecutionProvider: {cpu_exc}") from cpu_exc


def run_session(session: ort.InferenceSession, model_path: Path, chunk: np.ndarray) -> tuple[ort.InferenceSession, np.ndarray]:
    try:
        out = session.run(["audio_out"], {"audio": chunk})[0]
        return session, out
    except Exception:
        if session.get_providers() == ["CPUExecutionProvider"]:
            raise
        session = create_session(model_path, ["CPUExecutionProvider"])
        out = session.run(["audio_out"], {"audio": chunk})[0]
        return session, out


def convert(model_path: Path, config_path: Path, input_path: Path, output_path: Path, provider: str) -> None:
    if not model_path.exists() or not config_path.exists():
        raise ModelNotFoundError(f"missing model.onnx or config.json under {model_path.parent}")

    cfg = json.loads(config_path.read_text())
    sample_rate = cfg["sample_rate"]
    seg_len = cfg["segment_length"]
    channels = cfg["in_channels"]

    waveform = load_audio(input_path, sample_rate, channels)
    waveform = normalize_audio(waveform)
    length = waveform.shape[-1]

    session = create_session(model_path, resolve_providers(provider))

    total_chunks = max(1, -(-length // seg_len))  # ceil div
    chunks_out = []
    for i, start in enumerate(range(0, length, seg_len)):
        end = min(start + seg_len, length)
        chunk = waveform[:, start:end]
        actual_len = chunk.shape[-1]
        if actual_len < seg_len:
            chunk = np.pad(chunk, ((0, 0), (0, seg_len - actual_len)))
        inp = chunk[np.newaxis, ...].astype(np.float32)
        session, out = run_session(session, model_path, inp)
        chunks_out.append(out[0][:, :actual_len])
        print(f"PROGRESS {int((i + 1) / total_chunks * 100)}", flush=True)

    result = np.concatenate(chunks_out, axis=-1)
    sf.write(str(output_path), result.T, sample_rate, format="FLAC")
    copy_metadata(input_path, output_path)
    print(f"DONE {output_path}", flush=True)


def run_self_test(model_path: Path, config_path: Path, provider: str) -> None:
    cfg = json.loads(config_path.read_text())
    sample_rate = cfg["sample_rate"]
    channels = cfg["in_channels"]
    noise = np.random.uniform(-0.5, 0.5, size=(sample_rate, channels)).astype(np.float32)

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "self_test_in.wav"
        out_path = Path(tmp) / "self_test_out.flac"
        sf.write(str(in_path), noise, sample_rate)

        convert(model_path, config_path, in_path, out_path, provider)

        out_data, out_sr = sf.read(str(out_path), dtype="float32", always_2d=True)
        assert out_sr == sample_rate, f"sample rate mismatch: {out_sr} != {sample_rate}"
        assert abs(out_data.shape[0] - noise.shape[0]) < cfg["segment_length"], "output length diverged by more than one chunk"
        assert np.isfinite(out_data).all(), "output contains NaN/Inf"

    print("SELF-TEST PASS", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--provider", choices=["auto", "cpu", "directml", "coreml"], default="auto")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test and (args.input is None or args.output is None):
        parser.error("--input and --output are required unless --self-test is passed")
    return args


def main() -> None:
    args = parse_args()
    try:
        if args.self_test:
            run_self_test(args.model, args.config, args.provider)
        else:
            convert(args.model, args.config, args.input, args.output, args.provider)
    except ModelNotFoundError as exc:
        print(f"ERROR MODEL_NOT_FOUND {exc}", file=sys.stderr)
        sys.exit(3)
    except InputReadError as exc:
        print(f"ERROR INPUT_READ_FAILED {exc}", file=sys.stderr)
        sys.exit(2)
    except OrtInitError as exc:
        print(f"ERROR ORT_INIT_FAILED {exc}", file=sys.stderr)
        sys.exit(4)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary, must report every failure mode
        print(f"ERROR GENERIC {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
