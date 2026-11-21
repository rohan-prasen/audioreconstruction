## Purpose

Let contributors resolve Python dependencies across the repository and exercise each delivery path in the environment its users receive.

## ADDED Requirements

### Requirement: Reproducible workspace development

The repository SHALL resolve its Python workspace through one committed root uv lockfile. Development commands that depend on another member SHALL use its checked-out source.

#### Scenario: Contributor works from the CLI directory

- **WHEN** a contributor syncs the CLI from its directory and runs its tests
- **THEN** uv uses the root lock and tests exercise the checked-out CLI.

#### Scenario: A manifest drifts from the lock

- **WHEN** a dependency edit requires a lock update and CI checks the lock
- **THEN** the check fails without silently updating the lock.

### Requirement: Independently usable delivery paths

The workspace SHALL preserve current Python support, documented entry points, artifact identities and runtime dependencies for each delivery path.

#### Scenario: A user installs the CLI in a clean environment

- **WHEN** a user installs the built wheel on a supported Python version outside the checkout
- **THEN** the existing console commands work without a Rust toolchain, Torch, ONNX Runtime or a workspace checkout and resolve the same versioned release assets.

#### Scenario: Existing automation builds and runs native inference

- **WHEN** release automation builds each supported native binary and runs it with existing assets
- **THEN** asset names, manifest checksums for the produced assets, progress and error protocol, output audio format and metadata handling remain compatible with the existing CLI.

#### Scenario: A contributor uses the existing repository commands

- **WHEN** contributors use the documented working directories for model, evaluation, backend, frontend and deployment commands
- **THEN** existing imports, data and checkpoint locations, HTTP routes and responses, Bun builds and Modal image entry point continue to work.
