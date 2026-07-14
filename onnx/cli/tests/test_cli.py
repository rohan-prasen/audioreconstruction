from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audioreconstructor import app, batch, cli
from click.testing import CliRunner


TARGET = cli.Target("Linux", "x86_64", "audioreconstructor-linux-x86_64", "audioreconstructor")


class FakeProcess:
    """Stand-in for subprocess.Popen that replays the native binary's protocol."""

    def __init__(self, lines: list[str], returncode: int) -> None:
        self.stdout = iter(lines)
        self._returncode = returncode

    def wait(self) -> int:
        return self._returncode


class _FakeResponse:
    """Minimal urlopen() context-manager stand-in yielding fixed bytes once."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, _size: int = -1) -> bytes:
        data, self._data = self._data, b""
        return data

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


def description(data: bytes) -> dict[str, int | str]:
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


class ReleaseFixture:
    version = "1.0.0"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.assets = {
            TARGET.asset_name: b"linux executable\n",
            "audioreconstructor-windows-x86_64.exe": b"windows executable\r\n",
            cli.MODEL_NAME: b"model data",
            cli.CONFIG_NAME: b'{"sample_rate": 44100}',
        }
        self.sources: dict[str, Path] = {}
        for name, data in self.assets.items():
            source = root / name
            source.write_bytes(data)
            self.sources[f"test://{name}"] = source
        manifest = {
            "schemaVersion": 1,
            "version": self.version,
            "releaseTag": cli.release_tag(self.version),
            "files": {name: description(data) for name, data in self.assets.items()},
        }
        manifest_path = root / cli.MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.sources[f"test://{cli.MANIFEST_NAME}"] = manifest_path
        self.downloaded: list[str] = []

    def download(self, url: str, destination: Path, expected: cli.Artifact | None = None) -> None:
        self.downloaded.append(url)
        shutil.copyfile(self.sources[url], destination)
        if expected is not None:
            valid, detail = cli.artifact_is_valid(destination, expected)
            if not valid:
                raise AssertionError(detail)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.cache = self.root / "cache"
        (self.root / "release").mkdir(exist_ok=True)
        self.release = ReleaseFixture(self.root / "release")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def install(self) -> tuple[dict[str, Path], list[str]]:
        messages: list[str] = []
        with mock.patch.object(cli, "release_url", side_effect=lambda _version, name: f"test://{name}"), mock.patch.object(
            cli, "download", side_effect=self.release.download
        ):
            paths = cli.setup_assets(
                package_version=self.release.version,
                target=TARGET,
                cache_root=self.cache,
                report=messages.append,
            )
        return paths, messages

    def test_setup_downloads_validates_and_reuses_assets(self) -> None:
        old_cache = self.cache / "0.9.0"
        old_cache.mkdir(parents=True)
        (old_cache / "unused").write_text("old", encoding="utf-8")

        paths, messages = self.install()

        self.assertTrue(paths["binary"].is_file())
        self.assertTrue(os.access(paths["binary"], os.X_OK))
        self.assertEqual(paths["model"].read_bytes(), self.release.assets[cli.MODEL_NAME])
        self.assertFalse(old_cache.exists())
        self.assertIn("Setup complete.", messages)
        self.assertEqual(len(self.release.downloaded), 4)

        self.release.downloaded.clear()
        _, messages = self.install()
        self.assertEqual(self.release.downloaded, [])
        self.assertIn(f"Using cached {TARGET.asset_name}", messages)

    def test_setup_replaces_a_corrupt_asset(self) -> None:
        paths, _ = self.install()
        paths["model"].write_bytes(b"corrupt")
        self.release.downloaded.clear()

        self.install()

        self.assertEqual(paths["model"].read_bytes(), self.release.assets[cli.MODEL_NAME])
        self.assertEqual(self.release.downloaded, [f"test://{cli.MODEL_NAME}"])

    def test_doctor_runs_self_test_after_integrity_checks(self) -> None:
        self.install()
        messages: list[str] = []
        with mock.patch.object(cli, "_self_test", return_value=(True, "passed")) as self_test:
            result = cli.doctor(
                package_version=self.release.version,
                target=TARGET,
                cache_root=self.cache,
                report=messages.append,
            )

        self.assertEqual(result, 0)
        self_test.assert_called_once()
        self.assertIn("[PASS] Runtime self-test: passed", messages)
        self.assertEqual(messages[-1], "Status: HEALTHY")

    def test_doctor_fails_without_a_required_asset(self) -> None:
        paths, _ = self.install()
        paths["config"].unlink()
        messages: list[str] = []

        result = cli.doctor(
            package_version=self.release.version,
            target=TARGET,
            cache_root=self.cache,
            report=messages.append,
        )

        self.assertEqual(result, 1)
        self.assertIn("[FAIL] config.json: missing", messages)
        self.assertEqual(messages[-1], "Status: UNHEALTHY")

    def test_inference_streams_progress_and_injects_cached_paths(self) -> None:
        paths, _ = self.install()
        lines = ["PROGRESS 50\n", "WARN metadata copy skipped\n", "PROGRESS 100\n", "DONE result.flac\n"]
        progress: list[int] = []
        with mock.patch.object(cli.subprocess, "Popen", return_value=FakeProcess(lines, 0)) as popen:
            code, error = cli.run_inference(
                Path("source song.mp3"),
                Path("result.flac"),
                "cpu",
                package_version=self.release.version,
                target=TARGET,
                cache_root=self.cache,
                on_progress=progress.append,
            )

        self.assertEqual(code, 0)
        self.assertIsNone(error)
        self.assertEqual(progress, [50, 100])
        command = popen.call_args.args[0]
        self.assertEqual(command[0], str(paths["binary"]))
        self.assertEqual(command[command.index("--model") + 1], str(paths["model"]))
        self.assertEqual(command[command.index("--config") + 1], str(paths["config"]))
        self.assertEqual(command[command.index("--input") + 1], "source song.mp3")

    def test_inference_captures_error_line_and_exit_code(self) -> None:
        self.install()
        lines = ["PROGRESS 10\n", "ERROR INPUT_READ_FAILED could not read file\n"]
        with mock.patch.object(cli.subprocess, "Popen", return_value=FakeProcess(lines, 2)):
            code, error = cli.run_inference(
                Path("x.mp3"),
                Path("y.flac"),
                "auto",
                package_version=self.release.version,
                target=TARGET,
                cache_root=self.cache,
            )

        self.assertEqual(code, 2)
        self.assertIn("INPUT_READ_FAILED", error)

    def test_discover_audio_files_recurses_and_filters(self) -> None:
        folder = self.root / "songs"
        (folder / "rock").mkdir(parents=True)
        (folder / "a.mp3").write_bytes(b"x")
        (folder / "rock" / "b.WAV").write_bytes(b"x")
        (folder / "notes.txt").write_bytes(b"x")
        (folder / ".hidden.mp3").write_bytes(b"x")
        (folder / "enhanced").mkdir()
        (folder / "enhanced" / "old.flac").write_bytes(b"x")

        found = batch.discover_audio_files(folder)
        names = sorted(p.relative_to(folder).as_posix() for p in found)
        self.assertEqual(names, ["a.mp3", "rock/b.WAV"])

    def test_output_path_for_mirrors_tree(self) -> None:
        folder = Path("/songs")
        out = batch.output_path_for(Path("/songs/rock/track.wav"), folder)
        self.assertEqual(out, Path("/songs/enhanced/rock/track.flac"))

    def test_enhance_requires_exactly_one_source(self) -> None:
        result = CliRunner().invoke(app.cli, ["enhance"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("exactly one", result.output)

    def test_download_retries_transient_failures(self) -> None:
        dest = self.root / "asset.bin"
        payload = b"payload bytes"
        calls = {"n": 0}

        def flaky_urlopen(_request, timeout=None):
            calls["n"] += 1
            if calls["n"] < cli.DOWNLOAD_RETRIES:
                raise cli.URLError("temporary network error")
            return _FakeResponse(payload)

        with mock.patch.object(cli, "urlopen", side_effect=flaky_urlopen), mock.patch.object(cli.time, "sleep"):
            cli.download("https://example/asset", dest)

        self.assertEqual(calls["n"], cli.DOWNLOAD_RETRIES)
        self.assertEqual(dest.read_bytes(), payload)

    def test_download_does_not_retry_client_errors(self) -> None:
        dest = self.root / "asset.bin"

        def not_found(_request, timeout=None):
            raise cli.HTTPError("https://example/asset", 404, "Not Found", {}, None)

        with mock.patch.object(cli, "urlopen", side_effect=not_found), mock.patch.object(cli.time, "sleep") as slept:
            with self.assertRaises(cli.CliError):
                cli.download("https://example/asset", dest)

        slept.assert_not_called()

    def test_platform_and_cache_resolution(self) -> None:
        linux = cli.get_cache_root("Linux", {"XDG_CACHE_HOME": "/tmp/xdg"}, Path("/home/test"))
        windows = cli.get_cache_root("Windows", {"LOCALAPPDATA": "C:/Users/test/AppData/Local"}, Path("/home/test"))
        self.assertEqual(linux, Path("/tmp/xdg") / cli.PACKAGE_NAME)
        self.assertEqual(windows, Path("C:/Users/test/AppData/Local") / cli.PACKAGE_NAME / "Cache")
        with self.assertRaises(cli.CliError):
            cli.detect_target("Darwin", "arm64")

    def test_release_manifest_generator_records_each_asset(self) -> None:
        assets_dir = self.root / "release-assets"
        assets_dir.mkdir()
        for name, data in self.release.assets.items():
            (assets_dir / name).write_bytes(data)
        generator = Path(__file__).resolve().parents[1] / "tools" / "generate_manifest.py"

        result = subprocess.run(
            [sys.executable, str(generator), "--version", self.release.version, "--assets-dir", str(assets_dir)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((assets_dir / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertEqual(manifest["releaseTag"], "audioreconstructor-v1.0.0")
        self.assertEqual(manifest["files"][cli.MODEL_NAME], description(self.release.assets[cli.MODEL_NAME]))


if __name__ == "__main__":
    unittest.main()
