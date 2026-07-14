"""Install and invoke versioned Audioreconstructor GitHub Release assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as installed_version
from pathlib import Path
from typing import Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import __version__

PACKAGE_NAME = "audioreconstructor"
REPOSITORY = "rohan-prasen/audioreconstruction"
MANIFEST_NAME = "manifest.json"
MODEL_NAME = "model.onnx"
CONFIG_NAME = "config.json"
DOWNLOAD_TIMEOUT_SECONDS = 30
SELF_TEST_TIMEOUT_SECONDS = 600
CHUNK_SIZE = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_DIR_RE = re.compile(r"^\d+(?:\.\d+)+(?:[a-zA-Z0-9._-]+)?$")


class CliError(Exception):
    """An expected CLI failure that should be rendered without a traceback."""


@dataclass(frozen=True)
class Target:
    system: str
    architecture: str
    asset_name: str
    executable_name: str


@dataclass(frozen=True)
class Artifact:
    name: str
    sha256: str
    size: int


def get_package_version() -> str:
    try:
        return installed_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return __version__


def release_tag(version: str) -> str:
    return f"audioreconstructor-v{version}"


def release_url(version: str, asset_name: str) -> str:
    tag = quote(release_tag(version), safe="")
    asset = quote(asset_name, safe="")
    return f"https://github.com/{REPOSITORY}/releases/download/{tag}/{asset}"


def detect_target(system: str | None = None, machine: str | None = None) -> Target:
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if machine not in {"x86_64", "amd64"}:
        raise CliError(f"unsupported architecture: {machine}. Only x86-64 is supported.")
    if system == "Linux":
        return Target(system, "x86_64", "audioreconstructor-linux-x86_64", "audioreconstructor")
    if system == "Windows":
        return Target(system, "x86_64", "audioreconstructor-windows-x86_64.exe", "audioreconstructor.exe")
    raise CliError(f"unsupported operating system: {system}. Only Linux and Windows are supported.")


def get_cache_root(
    system: str,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    if system == "Linux":
        return Path(environ["XDG_CACHE_HOME"]) / PACKAGE_NAME if environ.get("XDG_CACHE_HOME") else home / ".cache" / PACKAGE_NAME
    if system == "Windows":
        local_app_data = environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
        return base / PACKAGE_NAME / "Cache"
    raise CliError(f"unsupported operating system: {system}")


def installation_paths(cache_root: Path, version: str, target: Target) -> dict[str, Path]:
    directory = cache_root / version
    return {
        "directory": directory,
        "manifest": directory / MANIFEST_NAME,
        "binary": directory / target.executable_name,
        "model": directory / MODEL_NAME,
        "config": directory / CONFIG_NAME,
    }


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while data := handle.read(CHUNK_SIZE):
            digest.update(data)
            size += len(data)
    return digest.hexdigest(), size


def artifact_is_valid(path: Path, artifact: Artifact) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    try:
        digest, size = _hash_file(path)
    except OSError as exc:
        return False, str(exc)
    if size != artifact.size:
        return False, f"size is {size} bytes; expected {artifact.size}"
    if digest != artifact.sha256:
        return False, "SHA-256 mismatch"
    return True, "valid"


def _read_manifest(path: Path, package_version: str, required_assets: Sequence[str]) -> dict[str, Artifact]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"could not read {MANIFEST_NAME}: {exc}") from exc

    if raw.get("schemaVersion") != 1:
        raise CliError(f"{MANIFEST_NAME} has an unsupported schema version")
    if raw.get("version") != package_version:
        raise CliError(f"{MANIFEST_NAME} is for version {raw.get('version')!r}, expected {package_version!r}")
    if raw.get("releaseTag") != release_tag(package_version):
        raise CliError(f"{MANIFEST_NAME} does not match release {release_tag(package_version)}")
    files = raw.get("files")
    if not isinstance(files, dict):
        raise CliError(f"{MANIFEST_NAME} has no files mapping")

    artifacts: dict[str, Artifact] = {}
    for name in required_assets:
        item = files.get(name)
        if not isinstance(item, dict):
            raise CliError(f"{MANIFEST_NAME} is missing metadata for {name}")
        digest = item.get("sha256")
        size = item.get("bytes")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise CliError(f"{MANIFEST_NAME} has an invalid SHA-256 for {name}")
        if not isinstance(size, int) or size <= 0:
            raise CliError(f"{MANIFEST_NAME} has an invalid byte count for {name}")
        artifacts[name] = Artifact(name=name, sha256=digest, size=size)
    return artifacts


def _temporary_path(directory: Path, filename: str) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix=f".{filename}.", suffix=".part", dir=directory, delete=False)
    handle.close()
    return Path(handle.name)


def download(url: str, destination: Path, expected: Artifact | None = None) -> None:
    """Download one release asset and validate it before returning."""
    request = Request(url, headers={"User-Agent": f"{PACKAGE_NAME}/{get_package_version()}"})
    try:
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, destination.open("wb") as handle:
            digest = hashlib.sha256()
            size = 0
            while data := response.read(CHUNK_SIZE):
                handle.write(data)
                digest.update(data)
                size += len(data)
    except HTTPError as exc:
        raise CliError(f"download failed ({exc.code}) for {url}") from exc
    except URLError as exc:
        raise CliError(f"download failed for {url}: {exc.reason}") from exc
    except OSError as exc:
        raise CliError(f"could not save {destination.name}: {exc}") from exc

    if expected is not None:
        if size != expected.size:
            raise CliError(f"downloaded {expected.name} has {size} bytes; expected {expected.size}")
        if digest.hexdigest() != expected.sha256:
            raise CliError(f"downloaded {expected.name} failed SHA-256 verification")


def _make_executable(path: Path, target: Target) -> None:
    if target.system != "Linux":
        return
    try:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as exc:
        raise CliError(f"could not make {path.name} executable: {exc}") from exc


def _load_or_download_manifest(paths: Mapping[str, Path], version: str, required_assets: Sequence[str]) -> dict[str, Artifact]:
    manifest = paths["manifest"]
    try:
        return _read_manifest(manifest, version, required_assets)
    except CliError:
        pass

    temporary = _temporary_path(paths["directory"], MANIFEST_NAME)
    try:
        download(release_url(version, MANIFEST_NAME), temporary)
        artifacts = _read_manifest(temporary, version, required_assets)
        os.replace(temporary, manifest)
        return artifacts
    finally:
        temporary.unlink(missing_ok=True)


def _prune_old_versions(cache_root: Path, current_version: str, report: Callable[[str], None]) -> None:
    try:
        children = list(cache_root.iterdir())
    except OSError:
        return
    for child in children:
        if child.name == current_version or not VERSION_DIR_RE.fullmatch(child.name):
            continue
        try:
            if child.is_symlink():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
        except OSError as exc:
            report(f"Warning: could not remove old cache {child}: {exc}")


def setup_assets(
    *,
    package_version: str | None = None,
    target: Target | None = None,
    cache_root: Path | None = None,
    report: Callable[[str], None] = print,
) -> dict[str, Path]:
    """Install the current package version's native assets into the user cache."""
    package_version = package_version or get_package_version()
    target = target or detect_target()
    cache_root = cache_root or get_cache_root(target.system)
    paths = installation_paths(cache_root, package_version, target)
    paths["directory"].mkdir(parents=True, exist_ok=True)

    required_assets = (target.asset_name, MODEL_NAME, CONFIG_NAME)
    artifacts = _load_or_download_manifest(paths, package_version, required_assets)
    path_by_asset = {
        target.asset_name: paths["binary"],
        MODEL_NAME: paths["model"],
        CONFIG_NAME: paths["config"],
    }

    for asset_name in required_assets:
        destination = path_by_asset[asset_name]
        valid, _ = artifact_is_valid(destination, artifacts[asset_name])
        if valid:
            report(f"Using cached {asset_name}")
        else:
            report(f"Downloading {asset_name}")
            temporary = _temporary_path(paths["directory"], asset_name)
            try:
                download(release_url(package_version, asset_name), temporary, artifacts[asset_name])
                if asset_name == target.asset_name:
                    _make_executable(temporary, target)
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        if asset_name == target.asset_name:
            _make_executable(destination, target)

    _prune_old_versions(cache_root, package_version, report)
    report("Setup complete.")
    report(f"Cache:  {paths['directory']}")
    report(f"Binary: {paths['binary']}")
    report(f"Model:  {paths['model']}")
    report(f"Config: {paths['config']}")
    return paths


def _self_test(paths: Mapping[str, Path]) -> tuple[bool, str]:
    command = [
        str(paths["binary"]),
        "--model",
        str(paths["model"]),
        "--config",
        str(paths["config"]),
        "--provider",
        "auto",
        "--self-test",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=SELF_TEST_TIMEOUT_SECONDS, check=False)
    except OSError as exc:
        return False, str(exc)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {SELF_TEST_TIMEOUT_SECONDS} seconds"
    if result.returncode == 0 and "SELF-TEST PASS" in result.stdout:
        return True, "passed"
    detail = (result.stderr or result.stdout).strip().splitlines()
    return False, detail[-1] if detail else f"exited with code {result.returncode}"


def doctor(
    *,
    package_version: str | None = None,
    target: Target | None = None,
    cache_root: Path | None = None,
    report: Callable[[str], None] = print,
) -> int:
    package_version = package_version or get_package_version()
    try:
        target = target or detect_target()
    except CliError as exc:
        report(f"[FAIL] Platform: {exc}")
        report("Status: UNHEALTHY")
        return 1
    cache_root = cache_root or get_cache_root(target.system)
    paths = installation_paths(cache_root, package_version, target)
    required_assets = (target.asset_name, MODEL_NAME, CONFIG_NAME)
    report(f"Version: {package_version}")
    report(f"Platform: {target.system} {target.architecture}")
    report(f"Cache: {paths['directory']}")

    try:
        artifacts = _read_manifest(paths["manifest"], package_version, required_assets)
    except CliError as exc:
        report(f"[FAIL] Manifest: {exc}")
        report("Status: UNHEALTHY")
        return 1
    report("[PASS] Manifest")

    path_by_asset = {
        target.asset_name: paths["binary"],
        MODEL_NAME: paths["model"],
        CONFIG_NAME: paths["config"],
    }
    healthy = True
    for asset_name in required_assets:
        valid, detail = artifact_is_valid(path_by_asset[asset_name], artifacts[asset_name])
        label = "PASS" if valid else "FAIL"
        report(f"[{label}] {asset_name}: {detail}")
        healthy = healthy and valid

    if target.system == "Linux":
        executable = paths["binary"].is_file() and os.access(paths["binary"], os.X_OK)
        report(f"[{'PASS' if executable else 'FAIL'}] Binary execute permission")
        healthy = healthy and executable

    if healthy:
        report("[PASS] Bundled runtime dependencies")
        passed, detail = _self_test(paths)
        report(f"[{'PASS' if passed else 'FAIL'}] Runtime self-test: {detail}")
        healthy = healthy and passed
    else:
        report("[SKIP] Runtime self-test: setup is incomplete")

    report(f"Status: {'HEALTHY' if healthy else 'UNHEALTHY'}")
    return 0 if healthy else 1


def run_inference(
    input_path: Path,
    output_path: Path,
    provider: str,
    *,
    package_version: str | None = None,
    target: Target | None = None,
    cache_root: Path | None = None,
) -> int:
    package_version = package_version or get_package_version()
    target = target or detect_target()
    cache_root = cache_root or get_cache_root(target.system)
    paths = installation_paths(cache_root, package_version, target)
    missing = [key for key in ("manifest", "binary", "model", "config") if not paths[key].is_file()]
    if missing:
        names = ", ".join(paths[key].name for key in missing)
        raise CliError(f"setup is incomplete ({names}). Run '{PACKAGE_NAME} --setup'.")
    if target.system == "Linux" and not os.access(paths["binary"], os.X_OK):
        raise CliError(f"{paths['binary']} is not executable. Run '{PACKAGE_NAME} --setup'.")
    command = [
        str(paths["binary"]),
        "--model",
        str(paths["model"]),
        "--config",
        str(paths["config"]),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--provider",
        provider,
    ]
    try:
        return subprocess.run(command, check=False).returncode
    except OSError as exc:
        raise CliError(f"could not start {paths['binary']}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enhance audio with the Audioreconstructor ONNX model.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--setup", action="store_true", help="download and verify the native runtime and model")
    actions.add_argument("--doctor", action="store_true", help="verify cached assets and run a runtime self-test")
    parser.add_argument("--version", action="version", version=get_package_version())
    parser.add_argument("--input", type=Path, help="input audio file")
    parser.add_argument("--output", type=Path, help="output FLAC file")
    parser.add_argument("--provider", choices=("auto", "cpu", "directml"), default="auto", help="ONNX provider (default: auto)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.setup:
            setup_assets()
            return 0
        if args.doctor:
            return doctor()
        if args.input is None and args.output is None:
            parser.print_help()
            return 0
        if args.input is None or args.output is None:
            parser.error("--input and --output must be used together")
        return run_inference(args.input, args.output, args.provider)
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
