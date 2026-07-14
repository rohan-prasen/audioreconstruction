"""Install and invoke versioned Audioreconstructor GitHub Release assets."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import time
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
DOWNLOAD_RETRIES = 3  # total attempts per asset on transient network errors
DOWNLOAD_BACKOFF_SECONDS = 1.0  # base backoff, multiplied by attempt number
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
    """Download one release asset and validate it, retrying transient failures.

    Network hiccups (connection resets, timeouts, 5xx responses) are retried up to
    ``DOWNLOAD_RETRIES`` times with linear backoff. Permanent errors (4xx such as a
    missing asset) fail immediately without retrying.
    """
    request = Request(url, headers={"User-Agent": f"{PACKAGE_NAME}/{get_package_version()}"})
    digest = hashlib.sha256()
    size = 0
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        digest = hashlib.sha256()
        size = 0
        try:
            with urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, destination.open("wb") as handle:
                while data := response.read(CHUNK_SIZE):
                    handle.write(data)
                    digest.update(data)
                    size += len(data)
            break  # success
        except HTTPError as exc:
            # 4xx are permanent (e.g. asset not found); only retry 5xx.
            if exc.code < 500 or attempt == DOWNLOAD_RETRIES:
                raise CliError(f"download failed ({exc.code}) for {url}") from exc
        except URLError as exc:
            if attempt == DOWNLOAD_RETRIES:
                raise CliError(f"download failed for {url}: {exc.reason}") from exc
        except OSError as exc:
            if attempt == DOWNLOAD_RETRIES:
                raise CliError(f"could not save {destination.name}: {exc}") from exc
        time.sleep(DOWNLOAD_BACKOFF_SECONDS * attempt)

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
    on_progress: Callable[[int], None] | None = None,
    on_message: Callable[[str], None] | None = None,
) -> tuple[int, str | None]:
    """Run the native binary, translating its host protocol into callbacks.

    The binary emits a machine protocol for its host: ``PROGRESS <int>`` per chunk,
    ``DONE <path>`` on success, and ``ERROR <CODE> <message>`` / ``WARN <message>``.
    We stream that output instead of letting it leak to the terminal, forwarding
    progress to ``on_progress`` and any error/warning text to ``on_message``.

    Returns ``(returncode, error_message)`` where ``error_message`` is the last
    ``ERROR`` line seen, or ``None``.
    """
    package_version = package_version or get_package_version()
    target = target or detect_target()
    cache_root = cache_root or get_cache_root(target.system)
    paths = installation_paths(cache_root, package_version, target)
    missing = [key for key in ("manifest", "binary", "model", "config") if not paths[key].is_file()]
    if missing:
        names = ", ".join(paths[key].name for key in missing)
        raise CliError(f"setup is incomplete ({names}). Run 'audioreconstructor setup'.")
    if target.system == "Linux" and not os.access(paths["binary"], os.X_OK):
        raise CliError(f"{paths['binary']} is not executable. Run 'audioreconstructor setup'.")
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
        # stderr merged into stdout so a single ordered line stream carries
        # PROGRESS/DONE (stdout) and ERROR/WARN (stderr) without a two-pipe deadlock.
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        raise CliError(f"could not start {paths['binary']}: {exc}") from exc

    error_message: str | None = None
    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.strip()
        if not line:
            continue
        kind, _, rest = line.partition(" ")
        if kind == "PROGRESS":
            try:
                percent = int(rest)
            except ValueError:
                continue
            if on_progress is not None:
                on_progress(percent)
        elif kind == "DONE":
            continue
        elif kind == "ERROR":
            error_message = rest or line
            if on_message is not None:
                on_message(line)
        elif on_message is not None:  # WARN or anything unexpected
            on_message(line)

    return process.wait(), error_message
