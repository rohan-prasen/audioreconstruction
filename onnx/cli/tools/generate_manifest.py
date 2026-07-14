"""Create the manifest.json required by an Audioreconstructor GitHub Release."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ASSET_NAMES = (
    "audioreconstructor-linux-x86_64",
    "audioreconstructor-windows-x86_64.exe",
    "model.onnx",
    "config.json",
)
CHUNK_SIZE = 1024 * 1024


def describe(path: Path) -> dict[str, int | str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="PyPI version, for example 1.0.0")
    parser.add_argument("--assets-dir", type=Path, required=True, help="directory containing the four release assets")
    parser.add_argument("--output", type=Path, help="manifest path (default: <assets-dir>/manifest.json)")
    args = parser.parse_args()

    missing = [name for name in ASSET_NAMES if not (args.assets_dir / name).is_file()]
    if missing:
        parser.error(f"missing release assets: {', '.join(missing)}")
    output = args.output or args.assets_dir / "manifest.json"
    manifest = {
        "schemaVersion": 1,
        "version": args.version,
        "releaseTag": f"audioreconstructor-v{args.version}",
        "files": {name: describe(args.assets_dir / name) for name in ASSET_NAMES},
    }
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
