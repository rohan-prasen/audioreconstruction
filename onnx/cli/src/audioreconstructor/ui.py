"""Rich rendering helpers — Spotify-inspired: green accent, otherwise mono."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Column, Table
from rich.text import Text

console = Console()

# Spotify (Encore) palette: green is the only accent; everything else is
# white/grey. Red appears solely for errors.
GREEN = "#1DB954"  # essential green — the single accent
WHITE = "#FFFFFF"  # primary text
MUTED = "#B3B3B3"  # subdued / secondary text
FAINT = "#727272"  # borders, separators, de-emphasised text
TRACK = "#404040"  # unfilled progress track
RED = "#E22134"    # errors only

# Prefix -> style for the reporter fed into setup_assets()/doctor().
_LINE_STYLES = {
    "[PASS]": GREEN,
    "[FAIL]": RED,
    "[SKIP]": FAINT,
    "Downloading": WHITE,
    "Using cached": FAINT,
    "Warning": MUTED,
}


def banner(version: str) -> None:
    """Render the app header as a clean, mono panel with a green mark."""
    title = Text.assemble(("● ", GREEN), ("Audioreconstructor", f"bold {WHITE}"))
    subtitle = Text.assemble(
        ("ONNX audio super-resolution", MUTED),
        ("   v", FAINT),
        (version, FAINT),
    )
    console.print()
    console.print(
        Panel(Group(title, subtitle), box=ROUNDED, border_style=FAINT, padding=(0, 2), expand=False)
    )
    console.print()


def section(label: str) -> None:
    """A small left-aligned section heading."""
    console.print(Text.assemble(("● ", GREEN), (label, f"bold {WHITE}")))
    console.print()


def rich_reporter() -> Callable[[str], None]:
    """Return a ``report(str)`` callable that colorizes launcher status lines."""

    def report(message: str) -> None:
        if message == "Status: HEALTHY":
            style: str | None = GREEN
        elif message == "Status: UNHEALTHY":
            style = RED
        else:
            style = next((s for prefix, s in _LINE_STYLES.items() if message.startswith(prefix)), MUTED)
        console.print(Padding(Text(message, style=style), (0, 0, 0, 2)))

    return report


@contextmanager
def enhance_progress() -> Iterator[Progress]:
    """Live per-file progress: green spinner, green fill, muted percent."""
    progress = Progress(
        SpinnerColumn(style=GREEN),
        TextColumn(
            "{task.description}",
            style=WHITE,
            table_column=Column(min_width=18, max_width=42, no_wrap=True, overflow="ellipsis"),
        ),
        BarColumn(bar_width=None, style=TRACK, complete_style=GREEN, finished_style=GREEN),
        TextColumn("{task.percentage:>3.0f}%", style=MUTED),
        console=console,
        expand=True,
    )
    with progress:
        yield progress


def summary_panel(succeeded: int, failures: list[tuple[str, str]]) -> None:
    """Render a compact result summary panel for batch runs."""
    grid = Table.grid(padding=(0, 1))
    grid.add_row(Text("✓", style=GREEN), Text(f"{succeeded} succeeded", style=WHITE))
    grid.add_row(Text("✗", style=RED if failures else FAINT), Text(f"{len(failures)} failed", style=RED if failures else FAINT))
    if failures:
        grid.add_row("", "")
        for name, err in failures:
            grid.add_row(Text("•", style=RED), Text(f"{name} — {err}", style=MUTED))
    console.print()
    console.print(Panel(grid, title="Summary", title_align="left", box=ROUNDED, border_style=FAINT, padding=(0, 2), expand=False))


def result_panel(output_path: str) -> None:
    """Render the single-file success panel."""
    body = Text.assemble(("✓ ", GREEN), ("Saved  ", f"bold {WHITE}"), (output_path, MUTED))
    console.print()
    console.print(Panel(body, box=ROUNDED, border_style=FAINT, padding=(0, 2), expand=False))


def note(message: str) -> None:
    console.print(Padding(Text(message, style=MUTED), (0, 0, 1, 2)))


def error_panel(message: str) -> None:
    console.print()
    console.print(Panel(Text(message, style=RED), title="Error", title_align="left", box=ROUNDED, border_style=RED, padding=(0, 2), expand=False))
