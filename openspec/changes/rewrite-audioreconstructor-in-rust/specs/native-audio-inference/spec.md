## Purpose

Reconstruct audio with the existing ONNX generator and preserve the observable behavior of native worker integrations while reducing repeated startup in folder runs.

## ADDED Requirements

### Requirement: Compatible native worker interface

The release worker SHALL accept existing model, config, input, output, provider and self-test arguments, retaining the stdout progress/completion protocol, stderr warning/error protocol and exit codes.

#### Scenario: Existing host launches the replacement worker

- **WHEN** the worker receives valid single-file arguments from the previous host
- **THEN** it emits flushed `PROGRESS <percent>` records and `DONE <path>` on stdout and exits zero after writing the file.

#### Scenario: Worker reports a classified failure

- **WHEN** input decoding fails, model assets are missing, or runtime initialization fails
- **THEN** it emits the matching `ERROR INPUT_READ_FAILED`, `ERROR MODEL_NOT_FOUND` or `ERROR ORT_INIT_FAILED` record on stderr and exits 2, 3 or 4 respectively.

### Requirement: Audio and metadata parity

For the same assets and execution provider, the worker SHALL reproduce the reference output sample rate, channel order, frame count and decoded waveform within the predeclared numerical bounds in the design. It SHALL preserve the reference metadata and embedded picture semantics.

#### Scenario: Process a non-native sample rate and partial final chunk

- **WHEN** an input requires resampling and its final chunk requires padding
- **THEN** decoded output matches the reference length and sample comparison passes through the final frame.

#### Scenario: Carry tags and artwork into FLAC

- **WHEN** an input contains mapped ID3 fields and multiple embedded pictures
- **THEN** the output matches the reference Vorbis fields and selected cover image, including its bytes and picture attributes.

### Requirement: Reuse one inference session per healthy batch

A normal folder run SHALL share one initialized model session across its files. File-local failures SHALL allow later files to complete. The worker SHALL retain the reference CPU fallback on provider initialization or execution failure.

#### Scenario: Run ten tracks

- **WHEN** ten readable tracks use the same model and healthy provider
- **THEN** one worker starts, one session initializes, and each track produces its own progress and output.

#### Scenario: Recover from a provider failure mid-track

- **WHEN** a non-CPU provider fails on a chunk and CPU execution succeeds
- **THEN** the worker retries that chunk on CPU, preserves frame order and reuses the working CPU session for subsequent chunks and tracks.

### Requirement: Demonstrate end-to-end improvement

The implementation SHALL qualify the packaged Rust CLI and worker together on fixed single-song and ten-track workloads before becoming the default.

#### Scenario: Compare the release candidates

- **WHEN** the reference and candidate are timed with preinstalled assets on the same machine, provider and inputs
- **THEN** a report gives cold and warm time to first progress and total wall time, checks the design’s performance criteria, and identifies regressions before cutover.
