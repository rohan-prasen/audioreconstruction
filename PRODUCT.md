# Product

## Register

product

## Users

Audiophile hobbyists with libraries of old, lossy MP3s (128/256/320 kbps) who
care about fidelity and want lossless-quality restoration for personal
listening. They arrive with a specific file and a specific want: make this
sound better. They are comfortable judging audio quality by ear but are **not**
here to operate a DAW or read a research paper. Context is a quick, one-off
task — drop a file, wait, download a FLAC.

## Product Purpose

A single-purpose tool that reconstructs high-fidelity FLAC from lossy MP3 using
a GAN audio super-resolution model. It exists to make an expert-grade ML result
accessible to someone who just has a file and a pair of good ears. Success is:
a user drops an MP3, trusts the wait, and downloads output they can hear is
better — with zero confusion about what's happening, especially during the
cold-start/retry window while the model wakes up.

## Brand Personality

Warm, crafted, confident. The voice is human and lightly playful ("Give me old
and rusty audio. I will make them as good as new") without tipping into hype.
It should feel like a well-made instrument handed over by someone who knows
exactly what they're doing — inviting, tactile, quietly expert. Emotional goal:
reassurance and delight, not spectacle.

## Anti-references

- **Generic SaaS template.** No Vercel/Linear-clone dark gradients, hero-metric
  stat blocks, identical feature-card grids, or tiny tracked uppercase eyebrows
  above every section. This is not a startup landing page.
- **Cluttered audio-tool UI.** No DAW/Audacity-style dense panels, knobs,
  meters, waveform scrubbers, or toolbar overload. One task, one surface. Resist
  the urge to add controls that imply the user is an engineer.

## Design Principles

- **The tool disappears into the task.** Earned familiarity over novelty. Every
  affordance (upload, queue, start, download) behaves the way a user already
  expects; surprise is spent on warmth, never on how standard actions work.
- **Confidence without jargon.** Deliver an expert ML result in plain,
  human language. No bitrates-as-brag, no model-architecture flexing in the
  primary flow. Speak to ears, not to engineers.
- **Warmth is the differentiator.** Personality lives in voice, typography, and
  the warm palette — not in decoration bolted on top. When in doubt, remove the
  ornament and let the copy and materials carry the feel.
- **One thing, done beautifully.** Single-purpose is the strength. Refuse
  feature creep that would turn a focused tool into a cluttered console.
- **Honest about the machine.** The model cold-starts and retries; the wait is
  real. Surface waking/processing/retry/error states truthfully and calmly so
  the user always trusts what's happening rather than wondering if it broke.

## Accessibility & Inclusion

Target WCAG 2.1 AA. Body text and status labels must clear 4.5:1 against their
tinted backgrounds in **both** light and dark themes (watch the muted grays on
sand — the most likely failure). Status changes are already announced via
`aria-live`; keep every async state (waking, processing, done, error) reachable
to screen readers. Full `prefers-reduced-motion` support is required — the
animated mesh blobs, shimmer, and card entrances must have a calm/instant
fallback (already scaffolded; keep it). Interactive controls need visible
focus states and full keyboard operation, including the theme menu.
