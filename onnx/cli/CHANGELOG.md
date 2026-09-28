# Changelog

## 1.2.1

**Reliable HTTPS downloads.** `setup` now verifies release downloads against the bundled
certifi CA store instead of the interpreter's system trust store. This fixes
`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` on macOS and other
environments that lack a configured CA store — the platform-independent trust set pip uses.

**Clearer self-test failures.** When `doctor`'s runtime self-test fails, it now surfaces the
native binary's real error output instead of PyInstaller's generic "Failed to execute
script" banner, so the actual cause is visible.

**Fixes.** The reported package version is now derived from installed metadata (it can no
longer drift from the release version), and unused launcher code was removed.

## 1.2.0

**macOS support.** The CLI now runs on macOS, on both Apple Silicon (arm64) and Intel
(x86_64). `setup` downloads the matching native binary
(`audioreconstructor-macos-amd64` / `audioreconstructor-macos-intel`) and caches it
under `~/Library/Caches/audioreconstructor/<version>`. When Python runs under Rosetta 2
on an Apple Silicon machine, the CLI detects the translation and still installs the
native arm64 binary.

**Core ML provider.** `enhance --provider coreml` is now accepted; on macOS the default
`auto` provider tries Core ML first and falls back to CPU.

Note: releases 1.1.0 and earlier ship no macOS assets — macOS requires version 1.2.0 or
later.

## 1.1.0

**New UI.** The CLI has been restyled around a clean, Spotify-inspired design system —
a single green accent (`#1DB954`) over a calm white/grey palette, with red reserved for
errors. The header, per-file progress bars, and result/summary panels now read as one
consistent, low-noise interface.

**Added retry logic.** Asset downloads during `audioreconstructor setup` now retry
automatically on transient network failures (connection resets, timeouts, and 5xx
responses) with linear backoff. Permanent errors such as a missing asset (4xx) still fail
fast without wasted retries, so a flaky connection no longer means starting setup over.

## 1.0.1

- Rebuilt the CLI with Click subcommands (`setup`, `doctor`, `enhance`) and a Rich TUI.
- Added `enhance --folder` for recursive batch reconstruction into a mirrored
  `<folder>/enhanced/` tree.
- Fixed the native runtime's progress protocol leaking raw `PROGRESS`/`DONE` lines to the
  terminal; it now drives a live progress bar.
