---
name: AudioReconstruction
description: Warm, crafted GAN audio super-resolution tool — restore lossy MP3 to lossless FLAC.
colors:
  terracotta-ember: "oklch(57% 0.125 58)"
  terracotta-ember-dark: "oklch(70% 0.13 68)"
  warm-sand-bg: "oklch(92.8% 0.012 78)"
  surface: "oklch(97.2% 0.006 82)"
  ink: "oklch(19% 0.018 66)"
  muted: "oklch(43% 0.014 72)"
  border: "oklch(81.5% 0.014 78)"
  success-amber: "oklch(67% 0.13 72)"
  warning: "#d97706"
  danger: "#dc2626"
typography:
  display:
    fontFamily: "Iowan Old Style, Charter, Georgia, serif"
    fontSize: "clamp(48px, 9vw, 116px)"
    fontWeight: 400
    lineHeight: 0.92
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Avenir Next, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(18px, 2.15vw, 24px)"
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: "0"
  title:
    fontFamily: "Iowan Old Style, Charter, Georgia, serif"
    fontSize: "19px"
    fontWeight: 500
    lineHeight: 1.12
    letterSpacing: "-0.006em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0"
  label:
    fontFamily: "Optima, Avenir Next, Gill Sans, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.07em"
rounded:
  sm: "14px"
  md: "18px"
  lg: "24px"
  xl: "28px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "18px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.warm-sand-bg}"
    rounded: "{rounded.pill}"
    padding: "0 30px"
    height: "56px"
    typography: "{typography.body}"
  button-primary-disabled:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    height: "56px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "34px"
    padding: "0 13px"
  button-ghost:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "40px"
    padding: "0 13px 0 15px"
  chip-badge:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "28px"
    padding: "0 10px"
    typography: "{typography.label}"
  card-queue:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "14px 18px"
  dropzone:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "24px"
---

# Design System: AudioReconstruction

## 1. Overview

**Creative North Star: "The Warm Listening Room"**

A hi-fi mastering room at golden hour. Warm lamplight falls on sand-toned walls;
brass-warm accents catch the eye; a few floating glass panels glow as if lit from
within. The interface is not a lab, not a startup dashboard, and not a cluttered
DAW — it is a calm, expert space where a good file gets handed back better. Every
material choice serves reassurance: you are in capable hands, the work is
happening, the wait is honest.

The system is warm-neutral by default and spends its one saturated color —
Terracotta Ember — sparingly, on the moments that matter (primary action, focus,
progress, the wordmark's glow). Depth comes from **warm glass**: backdrop-blurred
floating surfaces with a warm ambient shadow beneath and a bright inset highlight
along the top edge, as if catching room light. Typography pairs a warm literary
serif (Iowan Old Style) for display and titles against a clean system sans for
body and a humanist sans (Optima/Avenir Next) for labels and controls — contrast
by axis, never two sans that almost match.

This system explicitly rejects two things, carried straight from PRODUCT.md.
First, the **generic SaaS template**: no dark hero gradients, no hero-metric stat
blocks, no identical feature-card grids, no tiny tracked uppercase eyebrows above
every section. Second, the **cluttered audio-tool UI**: no knobs, meters,
waveform scrubbers, or toolbar overload. One task, one warm surface.

**Key Characteristics:**
- Warm-neutral sand canvas; one saturated accent (Terracotta Ember) used on ≤10% of any screen.
- Signature warm-glass elevation: backdrop-blur + warm ambient shadow + inset top-highlight.
- Serif-display / system-sans / humanist-label three-voice type system.
- Generous pill geometry (999px) on all interactive controls.
- Light and dark themes, both warm-tinted; identical component grammar across them.
- Motion is calm and honest: state feedback, not choreography.

## 2. Colors

A warm-neutral palette — sand and near-white surfaces under near-black ink —
lit by a single fired-clay accent. Warmth lives in the hue of every neutral
(all tinted toward the same 58–82 hue band), never in loud color.

### Primary
- **Terracotta Ember** (`oklch(57% 0.125 58)`, dark theme `oklch(70% 0.13 68)`): The one saturated voice. Primary emphasis, focus rings, progress fill, the soft radial glow behind the wordmark and dropzone, and the emphasized word in the subhead. It is a glow color as much as a fill color — used at low opacity as ambient light, at full strength only on the thing the eye should land on.

### Neutral
- **Warm Sand** (`oklch(92.8% 0.012 78)`, dark `oklch(12% 0.018 58)`): The body background. Panels sit *on* sand; it is never a surface for text directly.
- **Surface** (`oklch(97.2% 0.006 82)`, dark `oklch(18% 0.02 56)`): Near-white raised panels — dropzone, cards, nav, toast. Almost always shown at partial opacity over the sand so the glass reads.
- **Ink** (`oklch(19% 0.018 66)`, dark `oklch(96% 0.009 82)`): Primary text, and the fill of primary buttons and download/action controls (ink-on-sand inversion).
- **Muted** (`oklch(43% 0.014 72)`, dark `oklch(74% 0.026 76)`): Secondary text, captions, meta. **This is the palette's danger zone** — see the Legible Muted Rule.
- **Border** (`oklch(81.5% 0.014 78)`, dark `oklch(34% 0.032 62)`): Hairline dividers and the resting stroke on glass surfaces, usually mixed a few percent toward accent or ink.

### Tertiary (status)
- **Success Amber** (`oklch(67% 0.13 72)`): Done state — a warm gold, deliberately *not* the conventional green, to stay inside the room's warmth.
- **Warning** (`#d97706`) / **Danger** (`#dc2626`): Reserved strictly for validation errors, rejected files, and failed jobs. The only cool-adjacent reds in the system; they appear as thin lines and low-opacity row tints, never as fills.

### Named Rules
**The One Ember Rule.** Terracotta Ember covers ≤10% of any screen. Its rarity is what makes the primary action and the active state read instantly. If two things on screen are ember, one of them is wrong.

**The Legible Muted Rule.** `--muted` on `--bg`/`--surface` is the single most likely contrast failure. Body and status text must clear **4.5:1**; placeholder and tertiary captions are held to the same bar, not excused as "elegant." When in doubt, push the text toward Ink, never toward the sand. Light-gray-for-elegance is forbidden.

## 3. Typography

**Display Font:** Iowan Old Style (with Charter, Georgia, serif)
**Body Font:** System sans (`-apple-system`, `BlinkMacSystemFont`, Segoe UI, system-ui)
**Label / Control Font:** Optima (with Avenir Next, Gill Sans) — a humanist sans

**Character:** A warm literary serif carries the personality; a neutral system
sans carries the work; a humanist sans gives buttons and labels a soft, tactile
confidence. Contrast is on the serif↔sans axis — never two near-identical sans
paired together. The subhead is the one italic voice, and it is set in Avenir
Next italic to feel spoken, not printed.

### Hierarchy
- **Display** (400, `clamp(48px, 9vw, 116px)`, lh 0.92, ls -0.04em): The hero headline only. `text-wrap: balance`. One per page.
- **Headline / Subhead** (500 italic, `clamp(18px, 2.15vw, 24px)`, lh 1.45): The spoken tagline under the hero. `text-wrap: pretty`; the emphasized word flips to upright Ember weight 800.
- **Title** (500, 19px, lh 1.12, ls -0.006em): Serif section/panel titles — the dropzone's "Audio upload", the wakeup toast title. Small serif, not display.
- **Body** (400, 13–16px, lh 1.45): All working copy, captions, status. Cap prose at 65–75ch.
- **Label** (500, 11–12px, ls 0.07em, UPPERCASE): Badges and format tags only ("FLAC OUTPUT", "28M GAN"). The humanist sans, tracked.

### Named Rules
**The Serif-Speaks Rule.** The serif is for identity and headings — display, titles, the wordmark, the drag overlay. It never sets body copy, form controls, or data. Those are sans, always.

**The Quiet Kicker Rule.** Uppercase tracked labels are permitted **only** as file-format badges where the letterform-as-spec reading is the point. They are forbidden as section eyebrows above headings — that is the SaaS scaffold this brand rejects.

## 4. Elevation

Depth is carried by **warm glass**, not flat shadows and not tonal-only layering.
A floating surface is a translucent near-white panel over sand: `backdrop-filter:
blur(18–26px) saturate(1.1–1.35)`, a diffuse **warm-brown** ambient shadow beneath
(`rgb(82 58 30 / …)`, not neutral black), and a bright inset highlight along the
top edge (`inset 0 1px 0 rgb(255 255 255 / .4)`) so the panel looks like it is
catching room light. This is the signature material and it is intentional — but
it is reserved for surfaces that genuinely float.

### Shadow Vocabulary
- **Ambient float** (`box-shadow: 0 18px 54px rgb(82 58 30 / 0.13)`): Resting elevation for cards, dropzone, nav.
- **Ambient lift** (`box-shadow: 0 26px 90px rgb(82 58 30 / 0.18)`): `--shadow-soft` — the deepest, for drag-active and modal-like moments.
- **Inset highlight** (`inset 0 1px 0 rgb(255 255 255 / 0.42)`): The top-edge catch-light. Pairs with every glass surface; it is what sells the material.
- **Accent halo** (`0 0 0 8px color-mix(in oklch, var(--accent) 16%, transparent)`): The soft Ember ring on drag-accept and focus.

### Named Rules
**The Warm-Shadow Rule.** Shadows are warm brown (`rgb(82 58 30)`), never neutral `rgb(0 0 0)` in the light theme. A cool black shadow instantly breaks the golden-hour room. (Dark theme shadows may go to true black.)

**The Floating-Glass Rule.** Glass (backdrop-blur) is for surfaces that float over content: nav, dropzone, cards, toast, menu. It is forbidden as decoration on inline or full-width blocks. If a surface doesn't float, it doesn't blur.

## 5. Components

Every interactive control is a **pill** (999px). Every floating surface is **warm
glass**. States are stated, not implied: default, hover, focus-visible, active,
disabled, loading, and — for jobs — waiting/done/error.

### Buttons
- **Shape:** Full pill (999px). No square or slightly-rounded buttons anywhere.
- **Primary** (`.start-button`): Ink fill, sand text (inversion), min-height 56px, padding `0 30px`, weight 750, ls -0.01em, soft ink shadow.
- **Hover / Focus:** `transform: scale(1.02)` + `filter: brightness(1.04)`; ease `cubic-bezier(0.2, 0.8, 0.2, 1)` ~160ms. Focus-visible must show a ring (do not rely on the scale alone).
- **Disabled:** Muted-over-surface fill, muted text, no shadow, `cursor: not-allowed`. Used for the loading "Reconstructing…" state with an inline spinner.
- **Secondary** (`.mini-action.secondary`): Surface-tint fill, ink text, 34px pill — the Cancel affordance.
- **Ghost** (`.github-link`): Transparent-over-surface, hairline border, ink text; on hover the border shifts toward Ember and a small ↗ badge fades in.
- **Icon button** (`.download-btn`): 34px circle, ink fill / sand icon, `scale(1.05)` on hover.

### Chips / Badges
- **Style:** Surface-tint fill, hairline border, pill. Uppercase tracked label type.
- **Use:** Format/spec tags only ("FLAC output", "28M GAN"). Never as interactive filters — they are read-only spec.

### Cards / Containers
- **Corner Style:** `md` (18px) for the queue card; `lg` (24px) for the dropzone.
- **Background:** Surface at ~80% over sand, warm glass.
- **Shadow Strategy:** Ambient float (see Elevation).
- **Border:** Hairline `--border` mixed a few percent toward accent.
- **Internal Padding:** Rows at `14px 18px`; dropzone at `clamp(18px, 4vw, 24px)`.
- **Signature detail:** The queue card enters with a 260ms `cardIn` (translateY + scale); rows carry an inline progress track that shimmers Ember while processing.

### Inputs / Fields
- **Dropzone well** (`.upload-well`): Dashed hairline border, sand-tint fill, 17px radius. The primary input is a full-panel file affordance, not a text field.
- **Focus / Drag-accept:** Border goes solid Ember, fill tints Ember ~9%, panel `scale(1.02)` with an Ember halo ring. Drag-reject swaps Ember for Danger.
- **Error:** Inline message in Danger under the panel; `aria-live="polite"`.

### Navigation
- **Style:** A single floating pill bar, centered, `min(100% - gutters, 820px)`, fixed at top. Warm glass; on scroll it tightens (more opaque, deeper blur).
- **Contents:** Serif wordmark with a glowing Ember dot, a theme menu (light/dark/system popover), and a ghost "Star" link.
- **Mobile:** Bar narrows; label text truncates; the Star link collapses to icon-only under 430px.

### Theme Menu (signature)
Popover docked under a pill trigger, `20px` radius glass, radio-style options with
an Ember-tinted selected state. Closes on outside-click and Escape; full keyboard
and `role="menu"` semantics. This is the one dropdown — keep it warm glass and
keep it accessible.

### Wakeup Toast (signature)
A fixed bottom-center warm-glass pill that appears while the model cold-starts,
with an Ember spinner and honest copy ("Waking up the model… First request takes
~30–60 s"). It embodies the "honest about the machine" principle — it is a
first-class component, not an afterthought.

## 6. Do's and Don'ts

### Do:
- **Do** spend Terracotta Ember on ≤10% of the screen — primary action, focus, progress, and glow only. The One Ember Rule.
- **Do** keep body and status text at ≥4.5:1 against sand/surface in **both** themes; push toward Ink, never toward sand. The Legible Muted Rule.
- **Do** use warm-brown ambient shadows (`rgb(82 58 30 / …)`) with a white inset top-highlight on every glass surface. The Warm-Shadow Rule.
- **Do** set the serif (Iowan Old Style) for display, titles, and the wordmark; system sans for body; humanist sans for labels/controls. The Serif-Speaks Rule.
- **Do** make every interactive control a full pill (999px) and give it default/hover/focus-visible/disabled states.
- **Do** surface the machine honestly — waking, processing, retrying, done, error — with `aria-live` and calm motion.
- **Do** honor `prefers-reduced-motion`: the mesh blobs, shimmer, and card entrance must have an instant/calm fallback (already scaffolded — keep it).

### Don't:
- **Don't** build a **generic SaaS template** — no dark hero gradients, no hero-metric stat blocks, no identical feature-card grids, no tiny uppercase tracked eyebrows above sections. (PRODUCT.md anti-reference.)
- **Don't** build a **cluttered audio-tool UI** — no knobs, meters, waveform scrubbers, or toolbar overload. One task, one surface. (PRODUCT.md anti-reference.)
- **Don't** use `--muted` gray for anything that must be read comfortably; if it looks elegant and faint, it's failing contrast.
- **Don't** apply glassmorphism to inline or full-width blocks. Glass is for floating surfaces only. The Floating-Glass Rule.
- **Don't** use neutral black (`rgb(0 0 0)`) shadows in the light theme — they break the golden-hour warmth.
- **Don't** pair the system sans with another near-identical sans, or set body copy in the serif. Contrast on the serif↔sans axis only.
- **Don't** push the display headline past its `116px` ceiling or tighten letter-spacing below `-0.04em`; larger is shouting, tighter is touching.
- **Don't** use a conventional green for success — success is Warm Amber, to stay inside the room.
- **Don't** add numbered section markers (01/02/03) or eyebrow kickers as scaffolding; uppercase tracked type is for format badges only.
