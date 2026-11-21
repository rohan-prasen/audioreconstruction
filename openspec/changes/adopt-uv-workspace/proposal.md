## Why

The root project and published CLI resolve dependencies separately, and the root development environment can import a released CLI while the checkout contains newer code. A shared workspace gives contributors a reproducible way to test local components together and gives a future native implementation a defined integration point.

## What Changes

- Register the Python projects in one uv workspace, resolve local member dependencies from the checkout and commit one Python lockfile.
- Give each independently built or deployed component an explicit dependency owner and a scoped check. Preserve existing source paths, default root commands and public artifacts.
- Document where a future maturin-built PyO3 package can plug in while keeping the current Python and native-binary installation paths working.

## Capabilities

### New Capabilities

- `repository-workspace` covers shared Python resolution, component-specific environments and compatibility checks across the monorepo.

### Modified Capabilities

## Impact

Root development, CLI packaging, native builds, Modal image assembly, frontend checks and contributor documentation. The migration requires no release, model retraining, data conversion or change to the web API.
