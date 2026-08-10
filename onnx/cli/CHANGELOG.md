# Changelog

## 1.2.0

**macOS support.** The CLI now runs on macOS, on both Apple Silicon (arm64) and Intel
(x86_64). `setup` downloads the matching native binary
(`audioreconstructor-macos-arm64` / `audioreconstructor-macos-x86_64`) and caches it
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
