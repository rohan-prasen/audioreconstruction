# Frontend

React 19 single-page application for uploading MP3 files and downloading reconstructed FLAC output. Built with Vite 8 and Tailwind CSS 4.

## Setup

```bash
bun install       # install dependencies
bun dev           # dev server at http://localhost:5173
bun run build     # production build to dist/
bun lint          # ESLint
bun preview       # preview production build
```

## Backend Proxy

`vite.config.js` proxies `/api/*` requests to the backend, stripping the `/api` prefix. The backend URL defaults to `http://localhost:8000` and can be overridden with `VITE_BACKEND_URL` in a `.env` file.

In production, `VITE_BACKEND_URL` points to the Modal-deployed server URL.

## Architecture

The entire UI lives in a single React component tree in `src/App.jsx`. There is no routing or external state management library.

### Key State

| State | Type | Purpose |
|-------|------|---------|
| `files` | `File[]` | Files queued for reconstruction |
| `jobMap` | `{ [key]: { status, result?, error? } }` | Per-file job tracking (`processing`, `waiting`, `done`, `error`) |
| `serverStatus` | `string` | Backend health (`unknown`, `online`, `degraded`, `offline`) |
| `themeChoice` | `string` | Light/dark/system theme, persisted in `localStorage` |

### Backend Integration

- **Reconstruct:** `POST /model-serve` (multipart/form-data) — returns a binary FLAC blob
- **Health:** `GET /health-check` — polled every 30 seconds
- Implements exponential back-off with jitter (up to 5 retries) on 429/503/504

### Styling

All styles are in `src/index.css` using CSS custom properties (`--bg`, `--fg`, `--accent`, etc.) with a `[data-theme="dark"]` override block. Animated background blobs use CSS keyframes with `prefers-reduced-motion` support.

### Dependencies

| Package | Purpose |
|---------|---------|
| react / react-dom | UI framework |
| framer-motion | Animations |
| ogl | WebGL background effects |
| tailwindcss | Utility CSS |
| @tailwindcss/vite | Vite integration |
