## 1. Establish the baseline

- [x] 1.1 Inventory all Python and Bun entry points, working directories, manifest consumers, workflow outputs and deployment inputs. Compare against MONOREPO.md and capture the working commands and pre-existing failures.
- [x] 1.2 Record CLI wheel metadata, release asset names, both FastAPI route schemas, and native inference output for a short tagged input from the existing build. Retain the decoded samples, tags and process output for comparison.

## 2. Introduce the Python workspace

- [x] 2.1 Register the CLI, native inference and production server directories as explicit members. Give the latter two private, distinct project names. Verify uv discovers all three from the root and each member directory.
- [x] 2.2 Assign direct dependencies and development tools to their owners, scope build-only interpreter requirements, and resolve the root CLI dependency locally. Verify the root default commands still have their dependencies and the imported CLI points to the checkout.
- [x] 2.3 Generate the root lock, review version changes against both previous locks, and verify locked syncs in fresh environments for root development on 3.12, root compatibility and Modal on 3.10, native builds on 3.12 and the CLI across 3.10–3.13. After these pass, remove the nested lock and repeat locked sync from the CLI directory.
- [x] 2.4 Generate portable root, server and native requirements exports for existing consumers. Use the server-scoped image inputs in Modal. Check regeneration produces no diff and each consumer can install its export without local workspace paths.

## 3. Exercise delivery and release contracts

- [x] 3.1 Update PR checks to reject stale locks and exports. Run root Ruff and pytest, CLI tests from its directory and the existing frozen Bun install, lint and build. Verify clean environments expose missing member dependencies.
- [x] 3.2 Exercise documented model, evaluation and export entry points using existing data and checkpoint paths. Compare both FastAPI schemas to baseline and smoke-test the isolated Modal app import and health route using its image layout.
- [x] 3.3 Build the CLI sdist and wheel from its member into the publish job’s expected directory. Compare metadata, install the wheel outside the checkout, and exercise setup, doctor and enhance against controlled release fixtures without Torch, ONNX Runtime or Rust installed.
- [ ] 3.4 Dry-run the native release matrix with its existing six asset labels, build directory and model assets. Verify the tag/version guard, manifest sizes and SHA-256 values. Compare the binary protocol, decoded output and tags on the baseline fixture and its exit status on invalid input. Exercise build and packaging without publishing a release.

## 4. Document the contributor workflow

- [x] 4.1 Update MONOREPO.md, affected setup instructions and mirrored agent guidance. Verify the documented root, member and Bun commands from clean environments and confirm both guidance files match.
- [x] 4.2 Document the future maturin/PyO3 member boundary, Python fallback and parity and performance checks for a candidate operation. Verify this migration adds no native build prerequisite to the current CLI or developer setup.

## Baseline evidence

Before manifest changes, root Ruff passed, pytest collected 19 passing tests, and frontend lint and build passed with an existing effect-cleanup warning in App.jsx. MONOREPO.md incorrectly describes an onnx/uv.lock and an empty root test suite. The root pre-commit export consumes the root manifest, the six native jobs install onnx/requirements.txt from the root and build under onnx/, and PyPI publishes onnx/cli/dist/*. Modal currently supplies inline image requirements and two directory mounts. The frontend runs Bun from frontend/. Training, evaluation, export and local serving run from the root. The CLI builds from onnx/cli/.

## Workspace verification

- All four project directories report the same four members. Locked syncs passed for the root on 3.10 and 3.12, the production server on 3.10, the native build on 3.12, and the CLI on 3.10 through 3.13. All original root package versions were retained. The former CLI lock's certifi 2026.10.19 resolves to the root's 2026.10.23.
- Root pytest passed 19 tests. All four CLI interpreters passed 17 tests. The isolated wheel matched the baseline wheel contents, including metadata, and passed the CLI fixture suite outside the checkout. Both API schemas matched. The isolated production app loaded its checkpoint and returned healthy on CPU.
- All three requirements exports regenerated identically and installed successfully. A clean frozen Bun install, lint and build passed with the baseline lint warning.
- The rebuilt Apple Silicon binary produced identical decoded PCM and preserved the title tag, progress protocol and invalid-argument exit code. Binary dependency resolution succeeded for Linux x86-64, Windows x86-64, macOS arm64 and macOS x86-64. Hosted builds were left unrun at the user’s request to keep the refactor local.
- PyTorch evaluation and generator-weight export succeeded. Running the separate ONNX exporter from the root fails in both the original and workspace environments because the local onnx module shadows the installed ONNX library.
