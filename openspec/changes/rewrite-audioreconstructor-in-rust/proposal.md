## Why

Enhancing a folder currently starts the packaged inference program and opens the ONNX model for every track. A native Rust CLI and worker can remove the PyInstaller startup path and reuse one session across the folder while continuing to run the existing trained model.

## What Changes

- Deliver the Rust command-line application through maturin platform wheels under the existing `audioreconstructor` distribution and command name. Keep `setup`, `doctor`, single-file and recursive folder enhancement.
- Replace the PyInstaller inference worker with a Rust executable. Preserve the published single-file subprocess interface and add a private batch interface between the matching CLI and worker.
- Load the model once per healthy folder run, keep per-file progress and errors, and verify audio samples, tags and artwork against the Python reference.
- Compare packaged binaries on a full song and a ten-track folder before switching the default build. Prepare local release candidates and leave publication to a separate decision.

## Capabilities

### New Capabilities

- `audioreconstructor-cli` defines installation, verified assets, diagnostics and the interactive command contract.
- `native-audio-inference` defines audio reconstruction, worker compatibility, session reuse and the benchmark that qualifies the replacement.

### Modified Capabilities

## Impact

The CLI workspace member, native build, package tests and release workflows change together. Existing releases, model and config formats, Python training and export, both HTTP services and the frontend stay compatible. Wheels become platform-specific. Source builds of the Rust package require a Rust toolchain. Supported wheel users continue to install with pip without a compiler.
