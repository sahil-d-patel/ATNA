"""Assemble captured screenshots into an annotated PDF.

Uses Matplotlib rather than a dedicated PDF library because Matplotlib is already a
dependency for the static map checks, and the layout needed here is simple: a title
page, then one page per screenshot with a caption above it.

Screenshots are full-page captures of a tall viewport, so each is scaled to fit the
printable area while preserving aspect ratio and pinned to the top of the frame.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

if TYPE_CHECKING:  # pragma: no cover - typing only
    from capture_ui import Capture

PAGE_SIZE = (11.0, 8.5)  # US Letter, landscape: the UI is wider than it is tall
INK = "#1C1917"
INK_MUTED = "#57534E"
ACCENT = "#0F766E"
HAIRLINE = "#E7E5E4"
CANVAS = "#FAFAF9"


def _title_page(pdf: PdfPages, snapshot_id: str, page_count: int) -> None:
    figure = plt.figure(figsize=PAGE_SIZE, facecolor=CANVAS)
    figure.text(0.08, 0.74, "ATNA", fontsize=54, color=INK, weight="bold", va="top")
    figure.text(
        0.08, 0.645, "Air Traffic Network Analysis", fontsize=19, color=ACCENT, va="top"
    )
    figure.text(
        0.08, 0.585, "Interface walkthrough", fontsize=13, color=INK_MUTED, va="top"
    )
    figure.add_artist(
        plt.Line2D([0.08, 0.92], [0.545, 0.545], color=HAIRLINE, linewidth=1.2)
    )
    figure.text(
        0.08, 0.49,
        "Structural criticality and scenario modelling for the U.S. domestic\n"
        "flight network. Every panel is a live capture of the running application.",
        fontsize=12, color=INK, va="top", linespacing=1.6,
    )
    figure.text(
        0.08, 0.30,
        f"Snapshot   {snapshot_id}\n"
        f"Pages      {page_count}\n"
        f"Generated  {date.today().isoformat()}",
        fontsize=10.5, color=INK_MUTED, va="top", linespacing=1.9,
        family="monospace",
    )
    pdf.savefig(figure)
    plt.close(figure)


def _screenshot_page(pdf: PdfPages, capture: Capture, image_path: Path) -> None:
    image = mpimg.imread(image_path)
    figure = plt.figure(figsize=PAGE_SIZE, facecolor=CANVAS)

    figure.text(0.06, 0.955, capture.title, fontsize=17, color=INK,
                weight="bold", va="top")
    figure.text(0.06, 0.905, capture.caption, fontsize=9.5, color=INK_MUTED,
                va="top", wrap=True, linespacing=1.5)
    figure.add_artist(
        plt.Line2D([0.06, 0.94], [0.845, 0.845], color=HAIRLINE, linewidth=1.0)
    )

    # Fit the capture into the remaining area, preserving aspect ratio and anchoring
    # to the top so long pages crop at the bottom rather than shrinking to illegible.
    frame_left, frame_bottom, frame_width, frame_height = 0.06, 0.04, 0.88, 0.78
    image_aspect = image.shape[0] / image.shape[1]
    frame_aspect = (frame_height * PAGE_SIZE[1]) / (frame_width * PAGE_SIZE[0])

    if image_aspect > frame_aspect:
        draw_height = frame_height
        draw_width = frame_height * PAGE_SIZE[1] / (image_aspect * PAGE_SIZE[0])
    else:
        draw_width = frame_width
        draw_height = frame_width * image_aspect * PAGE_SIZE[0] / PAGE_SIZE[1]

    left = frame_left + (frame_width - draw_width) / 2
    bottom = frame_bottom + (frame_height - draw_height)

    axes = figure.add_axes((left, bottom, draw_width, draw_height))
    axes.imshow(image)
    axes.axis("off")
    for spine in axes.spines.values():
        spine.set_visible(True)
        spine.set_color(HAIRLINE)

    pdf.savefig(figure)
    plt.close(figure)


def build_pdf(
    captured: list[tuple[Capture, Path]],
    output: Path,
    snapshot_id: str = "2025-12",
) -> Path:
    """Write the walkthrough PDF and return its path."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output) as pdf:
        _title_page(pdf, snapshot_id, len(captured))
        for capture, image_path in captured:
            _screenshot_page(pdf, capture, image_path)

        info = pdf.infodict()
        info["Title"] = "ATNA — Interface Walkthrough"
        info["Subject"] = "Air Traffic Network Analysis application interface"
    return output
