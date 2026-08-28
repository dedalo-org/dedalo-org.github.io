#!/usr/bin/env python3
"""Generate the OpenGraph card, as SVG, from code.

The page declares `og:title`, `og:description`, `og:type` and `og:url` and no
image, so every link to it renders as a bare text card next to everybody else's
picture.

## Why this is generated rather than drawn

The obvious answer is a PNG in the repository. That is a **binary blob nobody
can review**: a diff shows "file changed" and regenerating it means finding
whatever produced it. In a project whose entire argument is that things which
decide anything should be reviewable, that is the wrong shape.

So the source is this script, the intermediate is an SVG of `<path>` elements,
and the PNG is rasterised **at deploy time and never committed**. What lives in
git is text, all the way down.

## Why the text is drawn as paths

`<text>` needs a font, and the glyphs a rasteriser picks depend on what is
installed on the machine doing the rasterising. That makes the card
non-reproducible for no benefit. The five-by-seven font below is part of the
source, so the same SVG always produces the same image — the same reasoning
that makes `make-sprites.py` draw the sun and moon from a rule rather than by
eye.

    scripts/make-og-image.py            # print the SVG
    scripts/make-og-image.py --write    # write site/og.svg
    scripts/make-og-image.py --check    # is site/og.svg current?
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARD = ROOT / "site" / "og.svg"

# The size every crawler expects. Anything else is cropped by somebody.
WIDTH, HEIGHT = 1200, 630

# The page's own palette, so a shared link looks like the page it opens.
BG = "#0a0c0a"
BG_ALT = "#0f120e"
LINE = "#232c1e"
FG = "#dbe6d0"
FG_DIM = "#93a385"
GREEN = "#7dff9b"
AMBER = "#ffcb6b"
CYAN = "#79dcf2"

# A five-by-seven bitmap font. One string per row, `#` for an inked cell.
#
# Uppercase only, plus the punctuation the card needs. Small enough to read as
# data and large enough to be legible at the size it is drawn — which is the
# whole reason for a pixel font rather than a hinted one.
GLYPHS: dict[str, tuple[str, ...]] = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#..##", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("....#", "....#", "....#", "....#", "#...#", "#...#", ".###."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "%": ("##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ">": (".....", "#....", ".#...", "..#..", ".#...", "#....", "....."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}

GLYPH_W, GLYPH_H = 5, 7


def runs(cells: list[list[bool]]) -> list[tuple[int, int, int]]:
    """Horizontal runs of inked cells, as `(x, y, length)`.

    One path command per run rather than one per pixel: the card is a few
    kilobytes instead of a few hundred, and a run is what the eye sees anyway.
    """
    out = []
    for y, row in enumerate(cells):
        x = 0
        while x < len(row):
            if not row[x]:
                x += 1
                continue
            start = x
            while x < len(row) and row[x]:
                x += 1
            out.append((start, y, x - start))
    return out


def render(text: str, x: int, y: int, scale: int, colour: str) -> str:
    """One `<path>` for a whole line of text, at `scale` pixels per cell."""
    width = GLYPH_W + 1  # one blank column between glyphs
    cells = [[False] * (width * len(text)) for _ in range(GLYPH_H)]

    for index, character in enumerate(text.upper()):
        glyph = GLYPHS.get(character)
        if glyph is None:
            raise SystemExit(f"no glyph for {character!r}; add one to GLYPHS")
        for row, bits in enumerate(glyph):
            for column, bit in enumerate(bits):
                if bit == "#":
                    cells[row][index * width + column] = True

    commands = [
        f"M{x + cx * scale} {y + cy * scale}h{length * scale}v{scale}h-{length * scale}z"
        for cx, cy, length in runs(cells)
    ]
    return f'<path fill="{colour}" d="{"".join(commands)}"/>'


def text_width(text: str, scale: int) -> int:
    """How wide a line will be, for centring it."""
    return (len(text) * (GLYPH_W + 1) - 1) * scale


def centred(text: str, y: int, scale: int, colour: str) -> str:
    return render(text, (WIDTH - text_width(text, scale)) // 2, y, scale, colour)


# The panel inset, and therefore the widest a line of text may be. A line that
# overflows it is not a style question: the card is cropped by whoever renders
# it, and the first thing lost is the end of the sentence.
PANEL_INSET = 56
PANEL_PAD = 24
MAX_TEXT_WIDTH = WIDTH - 2 * (PANEL_INSET + PANEL_PAD)

# Each line: the text, its baseline, the cell size, and the colour.
LINES: tuple[tuple[str, int, int, str], ...] = (
    ("DEDALO", 132, 13, GREEN),
    ("TURN CODE MERGES INTO", 280, 5, FG),
    ("SUSTAINABLE OPEN-SOURCE FUNDING", 330, 5, FG),
    # The pipeline, in the order the stages run. This is the one sentence that
    # says what the project is: merges in, payouts out.
    ("GIT MERGES > ATTRIBUTION > PAYOUT PLAN > SETTLEMENT", 420, 3, FG_DIM),
    # The split, which is the number people actually ask about.
    ("82.5% CONTRIBUTORS   15% TREASURY   2.5% PROTOCOL", 490, 3, AMBER),
)


def overflowing() -> list[str]:
    """Lines too wide for the panel, with how far over they are.

    Checked rather than eyeballed, because the failure is invisible in the SVG
    and only shows up once something has rasterised and cropped it.
    """
    problems = []
    for text, _y, scale, _colour in LINES:
        width = text_width(text, scale)
        if width > MAX_TEXT_WIDTH:
            problems.append(
                f"{text[:32]!r} is {width}px wide at scale {scale}, "
                f"{width - MAX_TEXT_WIDTH}px past the panel"
            )
    return problems


def card() -> str:
    """The whole card.

    What it shows is the pipeline, not a logo the project does not have.
    """
    problems = overflowing()
    if problems:
        raise SystemExit("the card does not fit:\n  " + "\n  ".join(problems))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Dedalo. Turn code merges into sustainable open-source funding. '
        f'The pipeline: git merges, attribution, payout plan, settlement. '
        f'82.5 percent to contributors, 15 percent treasury, 2.5 percent protocol fee.">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>',
        # A panel, so the card reads as the same object as the page's terminals.
        f'<rect x="{PANEL_INSET}" y="{PANEL_INSET}" '
        f'width="{WIDTH - 2 * PANEL_INSET}" height="{HEIGHT - 2 * PANEL_INSET}" '
        f'fill="{BG_ALT}" stroke="{LINE}" stroke-width="2"/>',
    ]

    for text, y, scale, colour in LINES:
        parts.append(centred(text, y, scale, colour))

    # A rule under the wordmark, clear of its baseline, in the accent the page
    # uses for the stage that is not pure.
    wordmark_bottom = LINES[0][1] + GLYPH_H * LINES[0][2]
    parts.append(
        f'<rect x="440" y="{wordmark_bottom + 18}" width="320" height="4" fill="{CYAN}"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write site/og.svg")
    parser.add_argument("--check", action="store_true", help="fail if site/og.svg is stale")
    args = parser.parse_args()

    svg = card()

    if args.check:
        if not CARD.exists():
            print(f"{CARD} does not exist; run --write", file=sys.stderr)
            return 1
        if CARD.read_text() != svg:
            print(
                f"{CARD} is not what this script produces — run --write and commit "
                "the result, or the card and its source have parted company",
                file=sys.stderr,
            )
            return 1
        print(f"og.svg is current ({len(svg)} bytes)")
        return 0

    if args.write:
        CARD.write_text(svg)
        print(f"wrote {CARD} ({len(svg)} bytes)")
        return 0

    print(svg, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
