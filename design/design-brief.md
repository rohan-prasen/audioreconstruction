# Design Brief — Audio Reconstruction SPA

A single-page React app that restores lossy MP3 audio to lossless FLAC using a 28M-parameter GAN model. Users drop up to 3 MP3 files, the app reconstructs each one server-side, and they download the resulting FLACs. One screen. No login. No history. No playback.

This brief is the source of truth for visual design generated in Open Design. Color palette and exact font choices are intentionally left Open — pick them in Open Design.

---

## Product summary

**One-liner:** Restore your lossy music to lossless.

**Primary action:** Drop MP3 → wait → download FLAC.

**Hard constraints (must be visible in UI):**
- Max **3 files** per session/queue
- Max **25 MB** per file
- Max **6 minutes** duration per file
- Output format: **FLAC**

**Out of scope (do not design):**
- Audio playback / preview / A/B compare
- Waveform visualizations of user audio
- Account system, history, persistence across reloads
- Multi-language / i18n
- Mobile-app native shell

---

## The single screen — layout

One viewport-height hero composition. Everything important is above the fold on desktop. The queue grows downward inside the same screen — the page scrolls only when the queue is populated.

**Vertical order, top to bottom:**

1. **Floating navbar** (fixed, top, full-width, frosted glass)
2. **Hero visual** — animated waveform / abstract music-themed art (decorative, not interactive)
3. **Headline + subhead**
4. **Dropzone** (frosted-glass panel, Stripe-narrow, centered)
5. **Queue** (appears only when files are added — stacks vertically below dropzone)
6. **Footer** (single line, minimal)

Generous whitespace between sections. Apple.com-grade breathing room.

---

## Components

### 1. Floating navbar

Fixed to top of viewport with a small inset from the edges (not edge-to-edge). Pill or rounded-rectangle shape, frosted-glass background, subtle border, soft shadow. Floats above the hero.

**Contents (left to right):**
- **Wordmark** — left-aligned. Plain text or simple monogram. No logomark required.
- *(spacer / flex)*
- **Theme toggle** — three-state segmented control: **Light · Dark · System**. Defaults to System. Persist choice in `localStorage`.
- **GitHub icon link** — Opens `https://github.com/rohan-prasen/audioreconstruction` in a new tab (`target="_blank" rel="noOpener noreferrer"`). Show a small "external link" affordance on hover.

**Behavior:**
- Sticky at top, never scrolls away.
- On page scroll: slightly increase background opacity / blur strength for legibility.
- No nav links beyond the GitHub icon and theme toggle.

### 2. Hero visual — gradient mesh

A slow, continuously-animated **gradient mesh**. Multiple soft, blurred color blobs drifting and morphing across a wide canvas behind the headline. Think: Stripe homepage mesh, Apple WWDC backdrops, Linear's ambient gradients.

**Look:**
- 3–5 large radial color stops, heavily blurred, overlapping.
- Smooth, slow drift — each blob has its own slow orbit / breathing motion (10–20s cycles).
- Subtle saturation, not neon. Should fade gently to the page background at the edges.
- No hard lines, no shapes, no particles. Pure soft color motion.

**Placement:**
- Sits **behind** the headline + subhead, **never** behind the dropzone.
- Either occupies the top ~50–60% of the viewport, or feathers softly into the rest of the page.
- The headline must remain perfectly legible against it — add a faint background "scrim" gradient under the headline if needed.

**Implementation hint (designer-facing):**
- CSS-only is fine: stack of `radial-gradient`s on absolutely-positioned divs, each animated with `transform: translate()` keyframes.
- WebGL/canvas is acceptable if performance is verified.
- Light and dark modes need separate color stops — same composition, different hues.

**Constraints:**
- Must not jank scrolling or input.
- Pauses entirely when `prefers-reduced-motion: reduce` — replace with a static snapshot.

### 3. Headline + subhead

**Headline (H1):** Restore your lossy music to lossless.
**Subhead:** Drop up to 3 MP3s. Our 28M-parameter audio reconstruction model rebuilds them as studio-quality FLAC.

Large, confident typography. Centered. Tight tracking. The headline is the loudest element on the page after the hero visual.

### 4. Dropzone

A **soft frosted-glass panel**, centered, **narrow** (Stripe-style — roughly 480–560px wide on desktop, never full-bleed). Generous internal padding. Rounded corners (large radius, Apple-feel).

**Inside the dropzone:**
- Icon (upload / cloud-up / music-note — pick one)
- Primary line: "Drop your MP3s here"
- Secondary line: "or click to browse"
- Tertiary line (small, muted): "MP3 only · up to 25 MB · 6 minutes · 3 files max"

**States — must be visually distinct:**

| State | Trigger | Visual treatment |
|---|---|---|
| **Idle** | Default | Soft frosted panel, subtle border |
| **Hover** | Mouse over panel | Slightly increased blur / brighter border |
| **Drag-over** | File dragged into window | **Noticeable** — border becomes solid + colored accent, panel scales up slightly (~1.02), brief inner glow. Should feel alive. |
| **Drag-reject** | Non-MP3 dragged over | Same scale, but warning treatment (red-ish border + "MP3 only" inline message) |
| **Disabled** | Queue at 3 files | Panel dims to ~60% opacity. Inside copy changes to "Queue full — remove a file to add more." Cursor not-allowed. |

**Interaction rules:**
- Click anywhere inside the dropzone Opens native file picker.
- Drag-and-drop supported from desktop file system.
- Multiple files can be dropped at once; if dropping N would exceed 3, accept the first (3 − current) and toast the rest as "Queue limit reached."
- Reject non-MP3 files with an inline error message that auto-dismisses after 4s.
- Reject files >25 MB or >6 minutes client-side with the same inline error pattern. Duration is read via `<audio>` metadata before upload.

### 5. Queue — stacked card list

Appears below the dropzone **only when files exist**. Vertically stacked cards, one per file, max 3. Smooth entry animation (slide down + fade, ~250ms Apple spring) when a card is added.

**Card anatomy (single file):**

```
┌────────────────────────────────────────────────────────┐
│  [filename.mp3]                            [status]  X │
│  ────────────────────────────────────────────────────  │  ← progress bar
└────────────────────────────────────────────────────────┘
```

- **Filename** — truncated with ellipsis if long, full name in tooltip on hover. File extension preserved.
- **Status label** — small, right-aligned next to the X. One of: `Ready` / `Uploading` / `Processing` / `Done` / `Failed` / `Cancelled`. Status changes are crossfaded (~150ms).
- **Remove (X) button** — small, circular, ghost style. Beautiful — not a harsh red X. On hover: subtle background fill + scale 1.05. On `Ready` state: removes the file. On `Uploading`/`Processing` state: triggers cancel-and-remove confirmation pattern (see below). On `Done` state: removes the card and discards the FLAC.
- **Progress bar** — full-width linear bar at the bottom of the card. Hairline-thin (2–3px). Animated stripe / shimmer during indeterminate states (cold start). Fills 0→100% during deterministic states.

**Card states — visual treatment:**

| State | Card look | Progress bar |
|---|---|---|
| `Ready` | Default — neutral | Empty / hidden |
| `Uploading` | Subtle pulse on filename | 0% → ~20% (determinate, based on XHR upload progress) |
| `Processing` | Slight animation cue (very subtle) | Shimmer / indeterminate stripe — server doesn't stream progress |
| `Done` | Card brightens slightly | 100% filled, settles into a static accent line |
| `Failed` | Card border tints warning | Empty + error message line replaces status |
| `Cancelled` | Card dims | Empty |

**Per-card actions during `Processing`:**
- Show a **Cancel** button (replaces the X temporarily, or sits beside the status label — designer's call). Clicking it aborts the in-flight request, transitions card to `Cancelled` state. The user can still hit X to remove the cancelled card afterward, or it auto-collapses after 3s.

**Per-card actions when `Done`:**
- The cancel button is replaced by a **Download** button — primary style, clear affordance. Clicking triggers FLAC download. Button remains usable until the card is removed.

**Per-card actions when `Failed`:**
- Show a **Retry** button next to the error message. Single click re-submits that file only.

### 6. Start button

A single primary action button positioned **below the queue**, centered, large, primary style. The clearest call-to-action on the page once files are queued.

**Label:** `Start reconstruction` (alternate short form acceptable: `Start`).

**Visibility & enabled rules:**

| Queue state | Button visible? | Enabled? |
|---|---|---|
| Queue empty | Hidden | — |
| At least one file is `Ready` (not yet started) | Visible | Enabled |
| All files are `Uploading` / `Processing` | Visible | Disabled — label changes to `Reconstructing…` with a small spinner |
| All files are `Done` / `Failed` / `Cancelled` (no `Ready` remaining) | Hidden | — |
| Mixed: some `Ready`, some in-flight | Visible | Enabled — pressing it starts the remaining `Ready` files |

**Behavior:**
- Click → every `Ready` card transitions to `Uploading` → `Processing`.
- If the user adds a new file while others are still processing, the new file lands as `Ready` and the Start button re-enables to kick it off.
- The Start button is **separate from** per-card Cancel — Cancel still lives inside each card during its own processing.

**Visual treatment:**
- Solid primary fill, generous horizontal padding, full pill radius (Apple-feel).
- Sized larger than the in-card Download buttons — this is the page's hero action.
- Disabled state: muted fill, no shadow.
- Hover/active: subtle scale (1.02) + brightness shift, snappy spring.

**No "Download all" button.** Per-card Download buttons are the only download path.

### 7. Footer

Single horizontal line, low-contrast, centered or left-aligned. Text: **28M GAN Audio Reconstruction**. No links. No social icons. Just the line, with appropriate top spacing.

---

## State machine — the page as a whole

```
[Empty]
   │
   │  add file(s)
   ▼
[Has Files] ──────────── click Start ────────────▶ [Working]
   │                                                  │
   │ remove all files                                 │ all done / all failed / cancelled
   ▼                                                  ▼
[Empty] ◀───────── remove all ─────────────────── [Settled]
                                                      │
                                                      │ add more files
                                                      ▼
                                                 [Has Files]
```

**Processing does NOT auto-start.** Files added to the queue land in `Ready` state and stay there until the user clicks the **Start reconstruction** button below the queue. This gives users a clear "review-then-go" moment, consistent with the Apple/Stripe pattern of explicit confirmation for non-trivial actions.

---

## Error / edge-case copy (verbatim)

Keep tone calm, terse, useful. No exclamation points. No tech jargon in user-facing text.

| Situation | Message |
|---|---|
| Wrong file type | "MP3 only — that file isn't supported." |
| File > 25 MB | "That file is over 25 MB. Try a smaller one." |
| File > 6 min | "That file is longer than 6 minutes. Try a shorter clip." |
| Queue full | "Queue is full. Remove a file to add another." |
| Network error | "Connection lost. Tap retry when you're back online." |
| Server busy / rate limited | "Slow down a moment — too many requests. Try again in a minute." |
| Server timeout | "That took too long. The file might be too complex — try a shorter clip." |
| Server unavailable | A page-level banner above the dropzone: "Service is warming up. Hang tight." |
| Generic failure | "Something went wrong. Tap retry." |

---

## Visual language

**Aesthetic:** Apple minimalism, modern frosted-glass surfaces, generous whitespace, soft shadows, micro-shadows on cards. No skeuomorphism. No gradients on text. No neon.

**Surfaces:**
- Page background: clean and quiet — let the hero visual carry the personality.
- Frosted glass: used for navbar and dropzone. Backdrop-blur (~20–40px) + low-opacity fill + 1px subtle border.
- Cards (queue items): solid surface, hairline border, soft shadow on hover.

**Corners:**
- Large radius on the dropzone (~24px).
- Medium radius on queue cards (~16px).
- Full pill radius on navbar and buttons.

**Shadows:**
- One ambient shadow on elevated surfaces.
- No multi-layer dramatic shadows. Apple-feel = quiet shadow + crisp edges.

**Iconography:**
- Stroke-based, 1.5–2px weight, rounded line caps.
- Lucide / Heroicons-style is fine.

**Typography:** *(pick in Open Design — these are guardrails, not prescriptions)*
- Sans-serif. System stack or a clean modern grotesque (Inter / Geist / SF Pro).
- Headline: large, tight-tracked, semibold or bold.
- Body: regular weight, comfortable line-height (~1.5).
- Filenames + status: monospace optional, otherwise body sans.

**Color:** *(pick in Open Design)*
- Whatever palette is chosen: enforce strong contrast (WCAG AA minimum) in both light and dark modes.
- One accent color drives primary buttons (Download, Retry), the drag-over highlight, and the progress bar fill.
- Reserve a warning hue for `Failed` states only.

---

## Motion principles

**Personality:** snappy Apple springs. Things move with intent, settle quickly, never feel sluggish.

**Defaults:**
- Standard transition: 150–250ms.
- Easing: spring with low overshoot, or `cubic-bezier(0.22, 1, 0.36, 1)`.
- Card entry: slide-down 12px + fade, ~250ms.
- Card removal: fade + slight scale 0.97, ~180ms.
- Drag-over: scale 1.02 + border color tween, ~120ms.
- Status crossfade: 150ms.
- Theme toggle transition: 200ms color tween across all surfaces.

**Reduced motion:**
- Honor `prefers-reduced-motion: reduce`.
- Replace springs with simple opacity transitions.
- Pause hero visual animation entirely.

---

## Responsive behavior

**Desktop-first** layout. The 3-card vertical queue works equally well on all sizes — no responsive reshuffling needed beyond standard reflow.

**Breakpoints (suggested):**
- Desktop (≥1024px): max content width ~640px, centered.
- Tablet (768–1023px): content width 90vw, max 560px.
- Mobile (<768px): content width 92vw, dropzone scales down, navbar contents stay (theme toggle compresses to icon-only segmented control), footer stays single-line.

**Touch:**
- Tap targets ≥ 44×44px (X button, theme toggle segments, GitHub icon, Download/Retry/Cancel buttons).
- Drag-and-drop gracefully degrades to tap-to-browse on touch devices.

---

## Accessibility

- Full keyboard navigation. Tab order: navbar → dropzone → each queue card's controls in order → footer.
- Visible focus rings on every interactive element. Use the accent color, not native browser default.
- Dropzone is a proper `<button>` or has `role="button"` + `tabindex="0"` + keyboard activation (Enter / Space).
- Status changes announced via `aria-live="polite"` region.
- All icons have accessible labels (`aria-label`).
- Color is never the only signal — `Failed` state uses an icon + text, not just hue.
- Theme toggle is a proper segmented control with `role="radiogroup"`.

---

## Copy library

**Headline:** Restore your lossy music to lossless.
**Subhead:** Drop up to 3 MP3s. Our 28M-parameter audio reconstruction model rebuilds them as studio-quality FLAC.
**Dropzone primary:** Drop your MP3s here
**Dropzone secondary:** or click to browse
**Dropzone tertiary:** MP3 only · up to 25 MB · 6 minutes · 3 files max
**Dropzone — queue full:** Queue full — remove a file to add more.
**Start button (idle):** Start reconstruction
**Start button (working):** Reconstructing…
**Download button:** Download
**Cancel button:** Cancel
**Retry button:** Retry
**Footer:** 28M GAN Audio Reconstruction

---

## Acceptance criteria

A mockup is "done" when:

1. The single screen idle state shows the floating navbar, animated gradient mesh hero, headline, dropzone, and footer all visible without scrolling on a 1440×900 desktop.
2. There is a clear visual delta between idle / hover / drag-over / drag-reject / disabled states on the dropzone.
3. Queue cards show all five important states: `Ready` (with Start button visible below), `Processing` (with shimmer + in-card Cancel), `Done` (with Download), `Failed` (with Retry), `Cancelled` (dimmed).
4. The **Start reconstruction** button below the queue is the loudest action on the page when any `Ready` files exist, and disappears when none remain.
5. The navbar is a floating frosted pill containing wordmark + theme toggle (Light/Dark/System segmented control) + GitHub icon.
6. The hero is a soft, slowly-animated gradient mesh that does not compete with the headline.
7. Light and dark modes both present cleanly. System mode visibly defers to OS preference.
8. Motion respects `prefers-reduced-motion` — gradient mesh freezes to a static snapshot.
9. Layout holds at 1440px, 1024px, 768px, and 375px widths.

---

## Decisions locked

- **Start button required** — processing does not auto-start.
- **Per-card downloads only** — no "Download all" button.
- **Hero is a gradient mesh** — soft animated color blobs, no waveform, no particles.
- **Color palette and typeface** — to be chosen in Open Design within the guardrails above.
