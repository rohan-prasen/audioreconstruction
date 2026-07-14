"""Rich rendering helpers — a clean, bordered TUI-style presentation layer."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Column, Table
from rich.text import Text

console = Console()

ACCENT = "#8b5cf6"  # violet accent, used for borders and the app mark

# Prefix -> style for the reporter fed into setup_assets()/doctor().
_LINE_STYLES = {
    "[PASS]": "bold green",
    "[FAIL]": "bold red",
    "[SKIP]": "yellow",
    "Downloading": ACCENT,
    "Using cached": "dim",
    "Warning": "yellow",
}


def banner(version: str) -> None:
    """Render the app header as a rounded panel."""
    title = Text.assemble(("◆ ", ACCENT), ("Audioreconstructor", "bold white"))
    subtitle = Text.assemble(
        ("ONNX audio super-resolution", "dim"),
        ("  ·  ", "grey37"),
        (f"v{version}", "dim cyan"),
    )
    console.print()
    console.print(
        Panel(Group(title, subtitle), box=ROUNDED, border_style=ACCENT, padding=(0, 2), expand=False)
    )
    console.print()


def section(label: str) -> None:
    """A small left-aligned section heading."""
    console.print(Text.assemble(("▸ ", ACCENT), (label, "bold")))
    console.print()


def rich_reporter() -> Callable[[str], None]:
    """Return a ``report(str)`` callable that colorizes launcher status lines."""

    def report(message: str) -> None:
        if message == "Status: HEALTHY":
            style: str | None = "bold green"
        elif message == "Status: UNHEALTHY":
            style = "bold red"
        else:
            style = next((s for prefix, s in _LINE_STYLES.items() if message.startswith(prefix)), None)
        console.print(Padding(Text(message, style=style), (0, 0, 0, 2)))

    return report


@contextmanager
def enhance_progress() -> Iterator[Progress]:
    """Live per-file progress display (spinner + aligned bar + percent + elapsed)."""
    progress = Progress(
        SpinnerColumn(style=ACCENT),
        TextColumn(
            "{task.description}",
            table_column=Column(min_width=18, max_width=42, no_wrap=True, overflow="ellipsis"),
        ),
        BarColumn(bar_width=None, complete_style=ACCENT, finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True,
    )
    with progress:
        yield progress


def summary_panel(succeeded: int, failures: list[tuple[str, str]]) -> None:
    """Render a compact result summary panel for batch runs."""
    grid = Table.grid(padding=(0, 1))
    grid.add_row(Text("✓", style="green"), Text(f"{succeeded} succeeded", style="green"))
    failed_style = "red" if failures else "dim"
    grid.add_row(Text("✗", style=failed_style), Text(f"{len(failures)} failed", style=failed_style))
    if failures:
        grid.add_row("", "")
        for name, err in failures:
            grid.add_row(Text("•", style="red"), Text(f"{name} — {err}", style="red"))
    border = "green" if not failures else "red"
    console.print()
    console.print(Panel(grid, title="Summary", title_align="left", box=ROUNDED, border_style=border, padding=(0, 2), expand=False))


def result_panel(output_path: str) -> None:
    """Render the single-file success panel."""
    body = Text.assemble(("✓ ", "green"), ("Saved  ", "bold"), (output_path, "cyan"))
    console.print()
    console.print(Panel(body, box=ROUNDED, border_style="green", padding=(0, 2), expand=False))


def note(message: str) -> None:
    console.print(Padding(Text(message, style="dim"), (0, 0, 1, 2)))


def error_panel(message: str) -> None:
    console.print()
    console.print(Panel(Text(message, style="red"), title="Error", title_align="left", box=ROUNDED, border_style="red", padding=(0, 2), expand=False))
