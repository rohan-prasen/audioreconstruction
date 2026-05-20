# Electron Desktop Application — Migration Plan

> **Project:** Audio Reconstruction (GAN-based MP3 → FLAC super-resolution)
> **Created:** 2026-05-20
> **Estimated Duration:** 8 weeks
> **Target Platforms:** Linux, macOS, Windows

---

## Current Architecture

```
┌─────────────────┐        /api proxy        ┌─────────────────────┐
│  React 19 SPA   │ ────────────────────────► │  FastAPI Backend    │
│  Vite 8 + TW 4  │      localhost:8000       │  PyTorch Generator  │
│  framer-motion  │                           │  (~28M params)      │
└─────────────────┘                           └─────────────────────┘
     frontend/                                     backend/
```

## Target Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Electron Shell                          │
│  ┌──────────────────────┐   IPC Bridge   ┌──────────────┐ │
│  │  BrowserWindow       │ ◄────────────► │  Main Process│ │
│  │  (React 19 renderer) │                │  (Node.js)   │ │
│  └──────────────────────┘                └──────┬───────┘ │
│                                                 │         │
│                                    child_process.spawn()  │
│                                                 │         │
│                                          ┌──────▼───────┐ │
│                                          │ Python Sidecar│ │
│                                          │ (FastAPI +    │ │
│                                          │  PyTorch GAN) │ │
│                                          └──────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**Key Decision — Python Sidecar vs ONNX Runtime:**

| Approach | Pros | Cons |
|----------|------|------|
| **Python sidecar** (recommended) | Zero model conversion, exact parity with current inference, reuse backend/main.py as-is | Larger bundle (~200-400 MB with Python + PyTorch), slower cold start |
| **ONNX Runtime in Node.js** | Smaller bundle (~50 MB), faster startup, no Python dependency | Requires model export to ONNX, potential numerical drift, `torch.amp.autocast` not directly supported, ongoing conversion maintenance |

**Recommendation:** Start with the Python sidecar. It's lower risk and preserves your existing inference pipeline exactly. ONNX conversion can be a future optimization (Week 7-8 stretch goal).

---

## Week 1 — Scaffold Electron + Vite Integration

### Goals
- Get Electron loading the existing React frontend in a BrowserWindow
- Establish the mono-repo structure (electron lives alongside frontend/)

### Tasks

- [ ] Initialize Electron in a new `desktop/` folder
  ```
  desktop/
  ├── package.json
  ├── electron.vite.config.js
  ├── src/
  │   ├── main/           # Electron main process
  │   │   └── index.js
  │   ├── preload/         # Context bridge
  │   │   └── index.js
  │   └── renderer/        # Symlink or import from frontend/
  └── resources/           # App icons
  ```
- [ ] Evaluate build tooling — **electron-vite** (recommended, native Vite integration) vs electron-forge + Vite plugin vs electron-builder standalone
- [ ] Configure electron-vite to use the existing `frontend/src` as the renderer source
- [ ] Get the React app rendering in Electron's BrowserWindow with hot-reload working in dev mode
- [ ] Set up basic window config: title, min size (1024x720), dark title bar, frameless option evaluation
- [ ] Verify Tailwind 4, framer-motion, and all existing animations work inside Electron's Chromium

### Deliverable
The existing React UI opens in an Electron window with full hot-reload during development.

---

## Week 2 — Python Sidecar Lifecycle Management

### Goals
- Electron spawns and manages the FastAPI backend as a child process
- Clean startup and shutdown, with health-check polling

### Tasks

- [ ] Create a `PythonSidecar` module in `desktop/src/main/` that:
  - Locates the Python environment (bundled or system `uv`/`python`)
  - Spawns `uvicorn backend.main:app --host 127.0.0.1 --port 0` (port 0 = OS picks a free port)
  - Captures stdout to extract the assigned port number
  - Polls `/health-check` until the backend responds
  - Emits a "backend-ready" event to the renderer via IPC
- [ ] Handle lifecycle:
  - On app `ready` → spawn sidecar
  - On `before-quit` → send SIGTERM, wait 3s, then SIGKILL if still alive
  - On unexpected crash → show error dialog, offer restart
- [ ] Add a loading/splash screen in the renderer that shows while the backend starts (the model load can take 5-15s)
- [ ] Wire the renderer's API calls to use `http://127.0.0.1:{dynamic_port}` instead of the Vite proxy `/api`

### Deliverable
App boots, shows a loading screen, backend starts, model loads, health-check turns green, UI becomes interactive.

---

## Week 3 — IPC Bridge + Native File System Access

### Goals
- Replace browser-based file upload with native file dialogs
- Expose safe Node.js APIs to the renderer via contextBridge

### Tasks

- [ ] Define the preload API surface:
  ```js
  // preload/index.js — exposed via contextBridge
  {
    selectFile: () => Promise<{ path, name, size }>,  // native open dialog
    getBackendUrl: () => string,                       // dynamic port
    onBackendReady: (callback) => void,                // IPC listener
    onModelProgress: (callback) => void,               // future: progress events
    platform: string,                                  // 'darwin' | 'linux' | 'win32'
    appVersion: string,
  }
  ```
- [ ] Implement native file picker via `dialog.showOpenDialog` with MP3 filter (`{ name: 'MP3 Audio', extensions: ['mp3'] }`)
- [ ] Update `App.jsx` to detect Electron environment (`window.electronAPI`) and:
  - Use native dialog instead of `<input type="file">`
  - Show file path in the UI (desktop users expect this)
  - Support drag-and-drop from the OS file manager (Electron handles this natively)
- [ ] Add "Save As" dialog for the reconstructed FLAC output instead of browser download
- [ ] Implement a native "Open output folder" button after reconstruction

### Deliverable
Users pick MP3s via native OS dialog, get the FLAC saved to a chosen location, and can open the output folder.

---

## Week 4 — Native Menus, Tray, and Window Chrome

### Goals
- The app feels native on each platform
- System tray for background processing

### Tasks

- [ ] Build a native application menu:
  ```
  File
  ├── Open MP3...          (Ctrl/Cmd+O)
  ├── Open Recent         ►
  ├── ─────────────
  └── Quit                 (Ctrl/Cmd+Q)

  View
  ├── Toggle Full Screen   (F11)
  └── Toggle DevTools      (Ctrl/Cmd+Shift+I, dev only)

  Help
  ├── About Audio Reconstruction
  └── Check for Updates
  ```
- [ ] Add system tray icon with context menu (Reconstruct, Show Window, Quit)
- [ ] Evaluate custom title bar vs native — recommendation: use **native** title bar on macOS/Windows, skip custom chrome unless you have a strong design reason
- [ ] Add `nativeTheme.themeSource = 'dark'` to match the app's dark UI
- [ ] Implement "recent files" tracking using `electron-store` or a simple JSON file in `app.getPath('userData')`
- [ ] Add global keyboard shortcuts for power users (Ctrl+O to open, Ctrl+Shift+R to reconstruct)

### Deliverable
Native menus, keyboard shortcuts, tray icon, and recent files — the app feels like a real desktop tool.

---

## Week 5 — Packaging and Distribution

### Goals
- Produce installable packages for Linux, macOS, and Windows
- Bundle Python + model weights inside the distributable

### Tasks

- [ ] Choose packaging strategy for the Python sidecar:

  | Strategy | Bundle Size | Complexity |
  |----------|-------------|------------|
  | **PyInstaller one-dir** | ~300 MB (with PyTorch CPU) | Medium — proven tooling |
  | **uv + vendored venv** | ~400 MB | Low — just zip the venv |
  | **conda-pack** | ~350 MB | Medium |
  | **Nuitka** | ~250 MB | High — full Python→C compile |

  **Recommendation:** PyInstaller `--onedir` mode. It's the most battle-tested for shipping Python with native deps.

- [ ] Create a build script that:
  1. Runs PyInstaller on `backend/main.py` (includes model/, PyTorch, soundfile, etc.)
  2. Copies the frozen Python bundle into `desktop/resources/backend/`
  3. Copies model checkpoint into `desktop/resources/model/`
  4. Runs `electron-builder` to produce the platform installer
- [ ] Configure electron-builder for each platform:
  - **Linux:** AppImage + .deb
  - **macOS:** .dmg (signed if you have an Apple Developer cert)
  - **Windows:** NSIS installer + portable .exe
- [ ] Set app metadata: name, icons (1024px PNG source → icns/ico), bundle ID, file associations (`.mp3`)
- [ ] Test the packaged app on all three platforms (use VMs or CI runners for cross-platform)

### Deliverable
Installable packages (.AppImage, .dmg, .exe) that include the entire Python inference stack.

---

## Week 6 — UX Polish for Desktop

### Goals
- Desktop-specific UX improvements the web version can't offer
- Progress reporting, notifications, batch processing

### Tasks

- [ ] **Real-time progress:** Modify the backend to emit Server-Sent Events (SSE) or WebSocket messages with chunk-by-chunk progress during reconstruction. Update the UI's `ProcessingCard` to show actual progress (chunk 3/17) instead of just a spinner.
- [ ] **OS notifications:** When reconstruction finishes while the window is minimized, show a native OS notification via `Notification` API
- [ ] **Batch processing mode:** Add a "Batch Reconstruct" option that accepts a folder of MP3s and processes them sequentially, showing a queue with per-file progress
- [ ] **Drag-and-drop zone enhancement:** Support dragging multiple files from the OS file manager
- [ ] **Output preferences:** Let users configure a default output directory via a settings panel (persisted with `electron-store`)
- [ ] **Taskbar progress:** On Windows/Linux, show a progress bar in the taskbar icon during reconstruction (`win.setProgressBar()`)

### Deliverable
The desktop app offers a meaningfully better experience than the web version.

---

## Week 7 — Auto-Updates and CI/CD

### Goals
- Users get updates automatically
- CI builds and publishes releases

### Tasks

- [ ] Integrate `electron-updater` (part of electron-builder):
  - Configure update server: GitHub Releases (free, simplest) or a custom static host
  - Add update check on app launch + periodic check every 24h
  - Show "Update available" dialog with release notes
  - Download + install on next restart
- [ ] Set up GitHub Actions CI pipeline:
  ```yaml
  # .github/workflows/desktop-release.yml
  on:
    push:
      tags: ['v*']
  jobs:
    build-linux:    # ubuntu-latest, PyInstaller + electron-builder
    build-macos:    # macos-latest, universal binary
    build-windows:  # windows-latest, NSIS installer
  ```
  - Each job: install uv, install deps, run PyInstaller, run electron-builder, upload artifacts to GitHub Release
- [ ] Code sign:
  - **macOS:** Apple Developer ID + notarization (required for Gatekeeper)
  - **Windows:** Optional but recommended — EV code signing cert reduces SmartScreen warnings
  - **Linux:** No signing needed (AppImage/deb)
- [ ] Add a version bump script that updates `package.json`, `pyproject.toml`, and creates a git tag

### Deliverable
Push a tag → CI builds all platforms → GitHub Release with auto-update support.

---

## Week 8 — Testing, Hardening, and Stretch Goals

### Goals
- Stability and edge case handling
- Optional: ONNX conversion for a lighter build

### Tasks

- [ ] **E2E tests with Playwright:** Test the Electron app using `@playwright/test` with Electron support:
  - App launches successfully
  - Backend health-check passes
  - File open → reconstruction → FLAC saved
  - Menu items work
  - Graceful shutdown
- [ ] **Error hardening:**
  - Backend crashes mid-inference → show error, allow retry
  - No GPU available → show "CPU mode (slower)" indicator
  - Corrupt MP3 → clear error message
  - Disk full → catch write error, alert user
  - Model checkpoint missing → guide user to download
- [ ] **Memory management:** Monitor Python subprocess memory usage, warn if above 2 GB
- [ ] **Crash reporting:** Integrate `electron-log` for structured logging + optional Sentry integration
- [ ] **Stretch — ONNX conversion:**
  - Export the generator to ONNX: `torch.onnx.export(generator, dummy_input, "generator.onnx")`
  - Run inference via `onnxruntime-node` directly in the Electron main process
  - Eliminates the Python sidecar entirely → bundle drops from ~350 MB to ~80 MB
  - Validate output quality matches PyTorch inference (compare spectrograms, PESQ scores)

### Deliverable
A stable, tested desktop application ready for public release.

---

## Architecture Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Build tool | electron-vite | Native Vite integration, reuses existing frontend config |
| Python bundling | PyInstaller --onedir | Battle-tested, handles PyTorch + native deps well |
| Backend communication | HTTP (localhost) | Reuses existing FastAPI, no protocol changes needed |
| IPC | contextBridge + preload | Security best practice, no nodeIntegration in renderer |
| Installer format | AppImage / DMG / NSIS | Standard per-platform, electron-builder supports all three |
| Auto-update | electron-updater + GitHub Releases | Free hosting, built-in to electron-builder |
| State persistence | electron-store | Simple key-value, JSON-backed, no DB needed |

## Dependency Overview

### New Dependencies (desktop/)

| Package | Purpose |
|---------|---------|
| `electron` | Desktop shell |
| `electron-vite` | Build tooling for Electron + Vite |
| `electron-builder` | Packaging and distribution |
| `electron-updater` | Auto-update mechanism |
| `electron-store` | Persistent settings (output dir, recent files) |
| `electron-log` | Structured logging |

### Python Build Tool

| Package | Purpose |
|---------|---------|
| `pyinstaller` | Freeze Python + PyTorch into a standalone binary |

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyTorch bundle size (~300 MB) | Large download, slow install | Use CPU-only PyTorch build (saves ~1 GB vs CUDA); consider ONNX long-term |
| Python sidecar cold start (5-15s) | Poor first impression | Splash screen with progress; preload model weights on install |
| macOS Gatekeeper rejection | Users can't open unsigned app | Apple Developer ID ($99/yr) + notarization required for distribution |
| Windows SmartScreen warning | Users scared off | EV code signing cert (~$200-400/yr) or build reputation over time |
| Cross-platform audio codec differences | soundfile/FFmpeg behavior varies | Pin FFmpeg version in PyInstaller bundle; test on all platforms |
| Electron security (nodeIntegration) | XSS → full system access | contextBridge + preload only, never enable nodeIntegration |

## Final File Structure

```
audioreconstruction/
├── backend/               # Existing — unchanged
├── frontend/              # Existing — minor changes (detect Electron env)
├── model/                 # Existing — unchanged
├── desktop/               # NEW
│   ├── package.json
│   ├── electron.vite.config.js
│   ├── electron-builder.yml
│   ├── src/
│   │   ├── main/
│   │   │   ├── index.js           # App entry, window management
│   │   │   ├── sidecar.js         # Python process lifecycle
│   │   │   ├── menu.js            # Native menus
│   │   │   └── updater.js         # Auto-update logic
│   │   └── preload/
│   │       └── index.js           # contextBridge API
│   ├── resources/
│   │   ├── icon.png               # 1024x1024 source icon
│   │   └── backend/               # PyInstaller output (gitignored)
│   └── scripts/
│       ├── build-backend.sh       # PyInstaller wrapper
│       └── package-all.sh         # Full build pipeline
├── plan/                  # This document
├── pyproject.toml
└── README.md
```
