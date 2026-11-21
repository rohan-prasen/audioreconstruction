## Purpose

Allow existing users and scripts to install, diagnose and run the native audio reconstruction command with their current inputs and cached release assets.

## ADDED Requirements

### Requirement: Installable command

The distribution SHALL provide the `audioreconstructor` executable through pip on its supported Python 3.10–3.13 and OS/architecture combinations. A supported wheel installation SHALL require neither compilation nor a separate ONNX Runtime installation.

#### Scenario: Clean wheel installation

- **WHEN** a user installs the platform wheel outside the repository without Cargo or model files
- **THEN** help and version work offline, and list the existing setup, doctor and enhance commands.

### Requirement: Versioned setup and diagnostics

Setup SHALL use the existing OS-specific cache, release tag, target mapping, manifest schema, byte counts and SHA-256 checks. Doctor SHALL report the outcome of asset verification and a real worker self-test.

#### Scenario: Reuse or repair a cache

- **WHEN** all current-version assets validate
- **THEN** setup succeeds offline and reuses them.
- **WHEN** an asset needs replacement and the new download fails verification
- **THEN** setup fails without installing the partial or corrupt replacement.

#### Scenario: Detect a runtime failure

- **WHEN** assets validate but the worker self-test fails
- **THEN** doctor reports an unhealthy installation, includes the failure detail and exits nonzero.

### Requirement: Compatible enhancement commands

The CLI SHALL preserve existing flags, defaults, provider names, file progress, output paths, failure summaries and public exit behavior.

#### Scenario: Enhance an individual file

- **WHEN** a user runs `enhance --input SOURCE --output DEST` after setup
- **THEN** the CLI writes the reconstructed FLAC to DEST and reports completion. Invalid option combinations produce a usage error.

#### Scenario: Enhance a mixed folder

- **WHEN** a user supplies a folder with nested audio, hidden entries, an enhanced output tree and one unreadable audio file
- **THEN** the CLI visits eligible paths in the reference order, skips hidden entries and enhanced directories, mirrors successful results under `enhanced/`, continues after the unreadable file and exits nonzero with that failure identified.
