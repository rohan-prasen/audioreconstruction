## Context

The root manifest owns the development environment and references a registry build of the CLI. The second Python lock is in `onnx/cli/`. Native release jobs install `onnx/requirements.txt` on Python 3.12. Modal builds a Python 3.10 image from an inline dependency list and copies the server directory and checkpoints. PyPI publishing builds the Hatch project in `onnx/cli/`. Each boundary has a different consumer.

## Goals / Non-Goals

Make dependency ownership explicit and builds reproducible while retaining the existing paths and supported interpreters. A source-tree reorganization would require compatibility wrappers for training commands, release scripts and deployment paths without improving resolution. Rust implementation, algorithm selection and wheel distribution for a fork belong to a later change.

## Decisions

| Owner | Responsibility | Installation boundary |
| --- | --- | --- |
| Root project | Training, evaluation, local backend, PyTorch export and existing aggregate development commands | Keep the root project and its default workflow. Declare explicit workspace members and map the existing CLI dev dependency to its workspace source. |
| `onnx/cli/` | Published CLI | Keep Hatch metadata, version and script. Own CLI test and lint tools locally. Check a scoped sync in a fresh environment. |
| `onnx/runtime/` | Torch-free inference and PyInstaller build | Add a private, non-packaged uv member with a distinct distribution name. Keep the manifest beside the CLI member so both discover the root. Retain the existing script and spec paths. Keep the PyTorch exporter in the root environment. |
| `server/` | Production inference | Add a private, non-packaged member for image dependencies. Keep local deployment tooling available at root. Build the remote environment from a portable server-scoped export including mutagen and excluding workspace paths. Preserve image mounts, secrets and system packages. |
| `frontend/` | Browser application | Keep its Bun manifest, lockfile, build and deployment working directory. CI checks it alongside Python. |

Retain consumed pip requirements paths as generated, scoped exports. Audit existing consumers before changing each file, including dependencies used only by local server tools. Compare the actual Modal image inputs separately from the server requirements file. Keep root defaults compatible wherever a member takes ownership of a dependency. The private apps run from source and must not publish wheels. In particular the local `onnx` directory must not become a distribution that shadows the upstream ONNX dependency.

For a future fork, add a separately named Python workspace member with a maturin build backend and a Cargo manifest when the first measured hotspot warrants it. Bind a narrow operation behind its existing Python caller, keeping the current implementation as a reference and fallback. Before enabling a binding, compare both implementations on the same stereo 44.1 kHz inputs, including a short final segment, for output shape, numerical tolerance and timings. The PyInstaller subprocess contract and public CLI stay above that boundary.

## Risks / Trade-offs

- Workspace resolution spans members and Python versions. The native requirements currently specify SciPy >=1.16, while the root lock selects 1.15.x on Python 3.10. Scope native-build-only requirements to their existing 3.12 target using markers or a Python-specific dependency group. Verify the 3.10 root and service environments independently before retiring either lock. Never raise the workspace-wide minimum to fix a build-only conflict.
- A shared developer environment can hide missing dependencies. Exercise each scoped install in a fresh environment and run the wheel outside the checkout.
- Updating a lock can change inference through binary dependency upgrades. Preserve working versions where compatible, inspect resolution changes and compare representative outputs against the baseline.
- A workspace build can write distributions to a different output directory. Set the CLI build output explicitly to the location consumed by the publish workflow and inspect that directory before publication.

## Migration Plan

Capture baseline command, dependency and artifact behavior. Introduce the members, resolve from the existing lock and verify clean scoped installs. Switch CI and deployment inputs together with generated exports, then retire the nested lock. Land the migration as one reversible change. Roll back the manifests, locks, exports and workflows together if compatibility checks regress. No checkpoint, cache or data migration is required.
