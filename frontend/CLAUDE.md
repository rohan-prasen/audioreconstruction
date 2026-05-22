# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
bun install           # install dependencies
bun dev               # dev server at http://localhost:5173
bun run build         # production build to dist/
bun lint              # ESLint (js/jsx only, no TypeScript)
bun preview           # preview production build
```

## Backend proxy

`vite.config.js` proxies all `/api/*` requests to the backend, stripping the `/api` prefix before forwarding. The backend URL defaults to `http://localhost:8000` and can be overridden with `VITE_BACKEND_URL` in a `.env` file.

In `App.jsx`, `API_BASE` is set from `import.meta.env.VITE_BACKEND_URL || ""`, so fetch calls to `/model-serve` and `/health-check` go through the Vite proxy in dev and hit the backend directly in production (where `VITE_BACKEND_URL` is set to the Modal-deployed URL).

## Architecture

The entire frontend is a single React component tree in `src/App.jsx` (~695 lines). There is no routing, no state management library, and no component directory — everything lives in one file.

### State model

`App` owns all state:
- `files` — array of `File` objects in the reconstruction queue
- `jobMap` — `{ [fileKey]: { status, result?, error? } }` tracking each file's backend job state (`"processing" | "waiting" | "done" | "error"`)
- `serverStatus` — `"unknown" | "online" | "degraded" | "offline"` from health-check polling
- `themeChoice` — `"light" | "dark" | "system"` persisted in `localStorage`

`fileKey(file)` produces a stable string key from `name-size-lastModified`.

### Backend integration

`reconstructAll()` iterates the pending queue sequentially (one file at a time), posting each to `POST /model-serve` as `multipart/form-data`. It implements exponential back-off with jitter (up to 5 retries) on 429/503/504 responses. The response is a binary FLAC blob; a temporary object URL is created for the download link and revoked on queue clear or component unmount.

Health checks poll `GET /health-check` every 30 seconds; the Start button is disabled when `serverStatus === "offline"`.

### Styling

All styles are in `src/index.css` — no Tailwind utilities are used directly in JSX (Tailwind is imported but the design uses hand-written CSS classes). The design system uses CSS custom properties (`--bg`, `--fg`, `--accent`, etc.) with a `[data-theme="dark"]` override block. Theme is applied by setting `document.documentElement.dataset.theme`.

The animated background uses four `.blob` divs with CSS keyframe animations and `mix-blend-mode`; the `prefers-reduced-motion` media query disables all animations.

### Design reference

`design.html` in the frontend root is the static HTML mockup the React app was built from. Consult it when making visual changes.
