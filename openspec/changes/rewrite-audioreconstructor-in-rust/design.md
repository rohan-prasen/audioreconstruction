## Context

The Python CLI in `onnx/cli/` dispatches one PyInstaller process per file. Each process decodes the track, opens the model and calls ONNX Runtime for each segment. On one Apple Silicon machine, CLI help took 62 ms median, a single packaged worker help run took 33.11 s, and opening an in-process CPU session took 49 ms. These measurements cover different operations. They motivate measuring full conversions and provide no album-level speedup estimate.

## Goals / Non-Goals

Port the user command and the shipped inference process to Rust while preserving their distinct callers. Optimize repeated startup first. Training, model export, HTTP serving, new codecs, concurrent folder processing and a Python-callable Rust API are outside this change. Keep the Python worker available as the comparison oracle during migration.

## Decisions

### Keep the wheel small and the worker independently runnable

Use the existing `onnx/cli/pyproject.toml` uv member with maturin binary bindings. Package one Rust launcher executable named `audioreconstructor`. A separate Cargo target under the ONNX subtree builds the worker, with its own inference and codec dependencies. Pin the dependency graph in a shared Cargo lock. Directory membership must keep the CLI and native workspace manifests discoverable from their current working directories. Retain the root uv lock for Python build and verification tools.

A Python extension would introduce an interpreter boundary with no agreed Python API. Bundling inference in both the wheel and the release asset would duplicate a sizable runtime. The launcher therefore uses the verified release worker for conversions. Both executable paths run without Python after installation. Keep the exported ONNX weights and config as separate assets. Root contributors building the local CLI from source will need Cargo and a linker. Document that distinction from installing prebuilt wheels.

### Keep one worker alive for a folder

The launcher handles discovery, output mapping, terminal presentation, asset installation and diagnostics. The worker owns decoding, the active provider/session, inference, encoding and tags. Preserve today's public single-file flags and line protocol. Add a private folder mode: open one subprocess with explicit model/config/provider arguments and send file requests over stdin. Frame requests and responses with a record ID and a reversible path representation on each OS. Reserve stdout for framed batch events and drain diagnostics independently. Single-file hosts keep their current stdout/stderr grammar.

Process files serially. Initialize the session lazily for the first readable track and keep it until EOF. Reset all per-track buffers, peak, frame offsets, progress and metadata. Emit a terminal result per request. Treat file errors as recoverable. After an unexpected worker exit, report the interrupted file and resume remaining files with a fresh worker; bound restarts by advancing past the failed file. On interrupt terminate and reap the child. Stage each FLAC beside its destination and replace only after successful encoding and metadata handling so existing outputs survive a failed conversion.

### Preserve the existing signal path

Use the same ONNX graph, tensor names, shapes and ORT version as the reference during parity testing. Select a Rust interface to the native ORT library and package its native dependencies. Prefer the reference codec implementation through native bindings where decoder delay, quantization or resampling differences would otherwise change the samples. Test support using the reference on each target, including its actual decode failures for discoverable extensions.

Match channel tiling/truncation, resampling ratio and polyphase filter behavior, whole-track peak normalization including silence, segment padding, final trimming and FLAC sample format. Compare mapped ID3v2 fields, ID3v1 fallback, cover selection and best-effort warnings. Exercise auto, CPU, DirectML and CoreML, including automatic CPU retry after session initialization or execution failure. Record the provider actually exercised in test evidence.

### Keep distribution contracts testable before release

Build wheels for Linux and Windows x86-64, macOS arm64 and macOS Intel. Separately map those four targets onto the six existing GitHub worker asset labels, including the Linux/Windows x86 aliases and the macOS amd64 label for arm64. Preserve Rosetta target selection. The raw worker asset must run after downloading the single executable, model and config from a matching release. Verify ORT, codecs and provider libraries on clean target machines early. Link or embed required redistributable dependencies; a worker that requires an extra manually installed native library fails this gate.

Preserve the per-version OS cache, TLS downloads, transient-error retries, manifest schema/version/tag checks, SHA-256 and byte counts, staged replacement and executable permissions. Keep valid caches usable offline. Exercise an old host with a candidate worker and the new CLI against staged release assets. Check that wheel, executable version, manifest and tag agree. Build candidates locally or on authorized runners. Publication is a separate operation.

## Risks / Trade-offs

- **Numerical differences.** Freeze fixtures and thresholds before tuning. As proposed acceptance bounds, require identical decoded samples on a deterministic, native-rate CPU golden fixture. For decoded/resampled CPU fixtures allow at most two 16-bit PCM sample steps per sample versus the baseline, with exact channels, rate and length. For accelerated providers collect repeated reference outputs first and freeze per-provider tolerances from observed variation before assessing Rust. Investigate differences at decode, resample, model and write stages separately.
- **Timing noise.** Compare installed release builds, with assets already verified, identical files and output storage, model hash, provider and thread settings. Use a full song and a fixed ten-track corpus. Record first-run measurements separately from at least five interleaved warm runs per workload. Time from command start to first actual chunk progress and to process exit. Proposed cutover gate: lower warm median ten-track elapsed time beyond observed run-to-run variation, and single-song median within 5% of baseline or faster. Report cold results and first-progress distributions separately. Keep the existing default when evidence is inconclusive.
- **Target-specific dependencies.** Capture OS version, wheel tag and actual execution provider. Verify minimum supported OS/runtime combinations and inspect dynamic linkage and redistribution terms before adopting a crate or binary. CPU fallback alone cannot qualify an accelerated path that worked on the same reference host.
- **Cross-version behavior.** Preserve previous release URLs and exercise reinstalling the prior wheel with its matching verified assets. Keep the Python CLI/import-based test harness usable as an oracle in an isolated environment while transitioning to executable-level contract tests.

## Migration Plan

1. Capture reference behavior and benchmark inputs. Prove the hardest packaging constraints with a minimal inference/self-test build on each target.
2. Port the worker and compare single-file outputs against the reference. Port launcher commands and verify staged cache and release behavior.
3. Add session reuse and test mixed-success folders and interrupts. Run parity, wheel, worker-protocol and performance gates on candidate artifacts.
4. Switch build defaults only after the evidence passes. Preserve the previous wheel and release assets for rollback. Leave tagging and publishing to a separately authorized release.
