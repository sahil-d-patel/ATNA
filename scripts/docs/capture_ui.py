"""Capture the running application to a PDF walkthrough.

Screenshots every page, drives the scenario editor through an actual airport removal
so the simulated state is captured rather than described, and assembles the result
into an annotated PDF.

The point of automating this rather than taking screenshots by hand is that the
document regenerates from the current code. A UI change that breaks a page surfaces
here as a failed capture instead of silently leaving stale images in the docs.

Usage::

    ./setupScripts/start.sh                 # in one shell
    PYTHONPATH=src python scripts/docs/capture_ui.py

Options::

    --url      application base URL (default http://localhost:8501)
    --out      output PDF path (default docs/ui/ATNA-interface.pdf)
    --keep     also keep the intermediate PNGs
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]

VIEWPORT = {"width": 1600, "height": 1200}
# Streamlit streams content in after load; these waits are generous because a missed
# render produces a blank panel in the PDF rather than an obvious error.
SETTLE_MS = 3500
CHART_SETTLE_MS = 2000


@dataclass(frozen=True)
class Capture:
    """One page of the walkthrough."""

    slug: str
    href: str
    title: str
    caption: str


CAPTURES: tuple[Capture, ...] = (
    Capture(
        "overview", "", "Overview",
        "Snapshot totals, then the projects central claim: hub score against bridge "
        "score with the diagonal drawn in. Airports above the line carry more "
        "structural load than their traffic implies.",
    ),
    Capture(
        "network-map", "render_network_map_page", "Network Map",
        "The route network over an Albers USA projection. Marker area follows hub "
        "score, color follows Leiden community, and cross-community routes are tinted "
        "separately. The regional structure is legible directly from the map.",
    ),
    Capture(
        "airport-explorer", "render_airport_explorer_page", "Airport Explorer",
        "Every airport in the snapshot, searchable by code, name, or city. Percentile "
        "scores render as bars on a fixed 0-100 domain so standing is comparable "
        "between tables.",
    ),
    Capture(
        "communities", "render_communities_page", "Communities",
        "Leiden partitions with their size, internal traffic, and density. The top "
        "hub and bridge lists stored as airport ids in the artifact are resolved to "
        "codes for display.",
    ),
    Capture(
        "route-explorer", "render_route_explorer_page", "Route Explorer",
        "Routes ranked by structural importance rather than raw traffic. A modest "
        "route that is one of few links between regions outranks a busier route "
        "buried inside one community.",
    ),
    Capture(
        "scenario-editor", "render_scenario_editor_page", "Scenario Editor",
        "The baseline network before any simulation. Any airport can be removed by "
        "clicking it, or through the quick-find control.",
    ),
    Capture(
        "methodology", "render_methodology_page", "Methodology",
        "Every formula as implemented, followed by the model's known limitations "
        "stated plainly rather than omitted.",
    ),
)

SCENARIO_CAPTURE = Capture(
    "scenario-active", "render_scenario_editor_page", "Scenario Editor — active simulation",
    "ATL removed. The removed airport is marked, airports touched by the two-hop "
    "ripple are shaded by exposure, and the impact and network-health scores update "
    "against the live graph.",
)


def _goto_page(page: Page, href: str) -> None:
    """Navigate via the sidebar so the app owns its own routing.

    Matched on href rather than link text: Streamlit prefixes each nav label with the
    name of its material icon, so the accessible name is not the visible label.
    """
    selector = (
        "section[data-testid='stSidebar'] a[href$='8501/']" if href == ""
        else f"section[data-testid='stSidebar'] a[href*='{href}']"
    )
    page.locator(selector).first.click()
    page.wait_for_timeout(SETTLE_MS)


def _dismiss_overlays(page: Page) -> None:
    """Close any toast that would otherwise sit over the captured content."""
    try:
        close_button = page.get_by_role("button", name="Close").first
        if close_button.is_visible(timeout=250):
            close_button.click()
            page.wait_for_timeout(300)
    except Exception:  # nothing to dismiss on this page
        pass


def _run_scenario(page: Page) -> bool:
    """Drive the editor through an ATL removal. Returns True when it took effect."""
    try:
        page.get_by_role("combobox", name="Quick-find airport").click()
        page.wait_for_timeout(400)
        page.keyboard.type("ATL")
        page.wait_for_timeout(700)
        page.keyboard.press("Enter")
        page.wait_for_timeout(900)
        page.get_by_role("button", name="Simulate removal").click()
        page.wait_for_timeout(SETTLE_MS)
        # The status box names the removed airport once the run lands.
        return page.get_by_text("Simulating removal of:").first.is_visible(timeout=3000)
    except Exception as exc:  # pragma: no cover - reported, not raised
        print(f"    scenario interaction failed: {exc}", file=sys.stderr)
        return False


def capture_screenshots(base_url: str, shots_dir: Path) -> list[tuple[Capture, Path]]:
    """Screenshot every page plus one active scenario."""
    shots_dir.mkdir(parents=True, exist_ok=True)
    captured: list[tuple[Capture, Path]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        page.goto(base_url, wait_until="networkidle")
        page.wait_for_timeout(SETTLE_MS)
        _dismiss_overlays(page)

        for capture in CAPTURES:
            print(f"  capturing {capture.title}")
            _goto_page(page, capture.href)
            page.wait_for_timeout(CHART_SETTLE_MS)
            _dismiss_overlays(page)
            path = shots_dir / f"{capture.slug}.png"
            page.screenshot(path=str(path), full_page=True)
            captured.append((capture, path))

        print(f"  capturing {SCENARIO_CAPTURE.title}")
        _goto_page(page, SCENARIO_CAPTURE.href)
        if _run_scenario(page):
            path = shots_dir / f"{SCENARIO_CAPTURE.slug}.png"
            page.screenshot(path=str(path), full_page=True)
            captured.append((SCENARIO_CAPTURE, path))
        else:
            print("    skipped: the simulation did not register", file=sys.stderr)

        browser.close()
    return captured


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs/ui/ATNA-interface.pdf")
    parser.add_argument("--keep", action="store_true", help="retain the intermediate PNGs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    shots_dir = args.out.parent / "screens"

    print(f"Capturing {args.url}")
    captured = capture_screenshots(args.url, shots_dir)
    if not captured:
        print("No pages captured; is the application running?", file=sys.stderr)
        return 1

    from build_pdf import build_pdf  # local module, imported after capture succeeds

    args.out.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(captured, args.out)
    print(f"\nWrote {args.out.relative_to(REPO_ROOT)} ({len(captured)} pages)")

    if not args.keep:
        for _, path in captured:
            path.unlink(missing_ok=True)
        if not any(shots_dir.iterdir()):
            shots_dir.rmdir()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
