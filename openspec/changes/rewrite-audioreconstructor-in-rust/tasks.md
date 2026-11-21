## 1. Capture reference behavior and prove distribution feasibility

- [ ] 1.1 Run the current CLI suite in the local uv workspace and capture executable-level fixtures for help, version, invocation errors, setup, doctor, enhance and the raw worker. Verify fixture replay against the current release.
- [ ] 1.2 Freeze model/config hashes and audio fixtures spanning silence, stereo/mono/multichannel, non-native sample rates, exact/partial chunks, supported formats, damaged input, tags and pictures. Record decoded reference PCM, format, metadata, provider and exit status. Freeze per-provider tolerances before testing candidate outputs.
- [ ] 1.3 Record cold and warm reference timings for one full song and a fixed ten-track folder using the design protocol. Save machine, provider, thread settings, input durations, per-run timings and observed variance.
- [ ] 1.4 Build a minimal native ONNX self-test against the same graph for each supported OS/architecture. Verify the raw executable runs on a clean host with only model/config assets, inspect native dependencies and record baseline-equivalent provider availability and redistribution terms.

## 2. Port the single-file worker

- [ ] 2.1 Introduce the Rust build targets and shared Cargo lock alongside the existing uv members. Check reproducible builds and root/member discovery, and keep the Python reference runnable.
- [ ] 2.2 Port decoding, channel handling, resampling, normalization, chunk inference, FLAC writing and metadata transfer. Compare intermediate buffers where needed and pass the frozen PCM and metadata fixtures.
- [ ] 2.3 Implement provider choice, initialization and execution fallback. Force each failure path, verify one CPU retry for the affected chunk and check real acceleration on reference-supported hardware.
- [ ] 2.4 Implement legacy flags, progress, warnings, errors and self-test. Run the previous host against the new worker and compare outputs, streams and exit codes for valid input, usage errors, missing assets, decode failure, runtime failure and generic errors.

## 3. Port the CLI and folder runtime

- [ ] 3.1 Build the Rust launcher through maturin binary wheels. Verify command name, version, help, argument validation, workspace source build and a wheel installation outside the checkout without Cargo or PyTorch.
- [ ] 3.2 Port setup and doctor. Exercise staged releases, old cache layouts, target aliases/Rosetta, cached offline operation, transient retries, corrupt assets, interrupted or concurrent replacement and executable permissions. Require doctor to detect checksum and self-test failures.
- [ ] 3.3 Port single-file and recursive enhancement. Verify extension filtering, directory exclusions, output mirroring, result summaries and paths containing spaces, Unicode or record delimiters against current public behavior.
- [ ] 3.4 Implement the private persistent batch protocol and reuse the session across files. Count process starts and successful session initializations during a healthy ten-track run. Exercise a corrupt middle track, provider fallback, worker termination and cancellation; verify surviving outputs, bounded recovery, diagnostics and final status.

## 4. Qualify the build and prepare cutover

- [ ] 4.1 Stage four platform wheel targets and the six existing worker asset labels, model, config and manifest. Verify wheel tags, SHA-256, byte counts, version/tag matching and rejection of incomplete or mismatched candidate sets. Exercise pip installation on Python 3.10–3.13 within the supported matrix.
- [ ] 4.2 Run both packaged implementations with identical inputs and settings. Publish timing results in the implementation report, including first progress, total duration, variance and session counts. Compare against both design gates and rerun audio/metadata parity on the benchmark outputs.
- [ ] 4.3 After qualification, update the build defaults and contributor instructions. Verify root uv sync/tests, scoped CLI builds, raw worker integration and reinstall of the previous release. Finish with staged artifacts and a rollback record; a public release requires a separate request.
