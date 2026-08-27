#!/usr/bin/env python3
"""Generate the pixel-art sun and moon, and write them into the page.

The theme control is a sun and a moon drawn on a grid, one pixel per cell, in
the flat retro register the rest of the page already uses. They are generated
rather than hand-drawn for the same reason the page's other geometry is
computed: a sprite is a shape plus a rule, and the rule is easier to read and
much easier to change than sixty rectangles somebody placed by eye.

What is checked rather than eyeballed:

- **the sun is four-fold symmetric** — mirror it horizontally, vertically or
  about either diagonal and it is unchanged;
- **the moon is not**, and must not be. A crescent that came out symmetric
  would mean the bite had been taken out of the middle;
- **both fill a comparable amount of the grid**, so one does not visually jump
  when the other replaces it.

Each sprite is emitted as a single SVG `<path>` of `h`/`v` runs — one element
per row-run rather than one `<rect>` per pixel, which is what keeps the two of
them under a kilobyte inside a page that has no external requests at all.

    scripts/make-sprites.py            # print both sprites
    scripts/make-sprites.py --check    # are the page's sprites current?
    scripts/make-sprites.py --write    # regenerate them in site/index.html
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "index.html"

GRID = 15  # cells per side; odd, so the sprite has a centre cell


def sun() -> list[list[bool]]:
    """A disc with eight rays, four-fold symmetric by construction."""
    centre = (GRID - 1) / 2
    cells = [[False] * GRID for _ in range(GRID)]
    for y in range(GRID):
        for x in range(GRID):
            dx, dy = x - centre, y - centre
            distance = (dx * dx + dy * dy) ** 0.5
            body = distance <= 3.6
            # A ray sits on an axis or a diagonal, in the band outside the
            # body. Drawn from the same centre as the body, so the symmetry of
            # the whole follows from the symmetry of the test.
            on_spoke = dx == 0 or dy == 0 or abs(dx) == abs(dy)
            ray = on_spoke and 5.0 <= distance <= 6.6
            cells[y][x] = body or ray
    return cells


def moon() -> list[list[bool]]:
    """A disc with a smaller disc taken out of its upper right."""
    centre = (GRID - 1) / 2
    cells = [[False] * GRID for _ in range(GRID)]
    for y in range(GRID):
        for x in range(GRID):
            dx, dy = x - centre, y - centre
            inside = (dx * dx + dy * dy) ** 0.5 <= 6.4
            bx, by = x - (centre + 4.6), y - (centre - 1.2)
            bitten = (bx * bx + by * by) ** 0.5 <= 6.2
            cells[y][x] = inside and not bitten
    return cells


def path(cells: list[list[bool]]) -> str:
    """The grid as one SVG path: a horizontal run per group of lit cells."""
    parts = []
    for y, row in enumerate(cells):
        x = 0
        while x < GRID:
            if not row[x]:
                x += 1
                continue
            start = x
            while x < GRID and row[x]:
                x += 1
            parts.append(f"M{start} {y}h{x - start}v1h-{x - start}z")
    return "".join(parts)


def filled(cells: list[list[bool]]) -> int:
    return sum(cell for row in cells for cell in row)


def mirrored_horizontally(cells): return [row[::-1] for row in cells]
def mirrored_vertically(cells): return cells[::-1]
def transposed(cells): return [list(row) for row in zip(*cells)]


def checks() -> list[str]:
    """Everything that must be true of the two sprites. Empty means good."""
    problems = []
    s, m = sun(), moon()

    if mirrored_horizontally(s) != s:
        problems.append("the sun is not symmetric left to right")
    if mirrored_vertically(s) != s:
        problems.append("the sun is not symmetric top to bottom")
    if transposed(s) != s:
        problems.append("the sun is not symmetric about its diagonal")

    # A crescent that survived mirroring would be a ring, or a disc with a hole
    # in the middle — either way, not a moon.
    if mirrored_horizontally(m) == m:
        problems.append("the moon is symmetric, so it is not a crescent")

    # Neither sprite should visibly jump when it replaces the other.
    a, b = filled(s), filled(m)
    if not 0.6 <= a / b <= 1.6:
        problems.append(f"the sprites differ too much in weight: {a} vs {b} cells")

    return problems


SUN_PATH = re.compile(r'(<path class="sprite-sun" d=")[^"]*(")')
MOON_PATH = re.compile(r'(<path class="sprite-moon" d=")[^"]*(")')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="update site/index.html")
    parser.add_argument("--check", action="store_true", help="is the page current?")
    args = parser.parse_args()

    for problem in checks():
        print(f"error: {problem}", file=sys.stderr)
    if checks():
        return 1

    sun_d, moon_d = path(sun()), path(moon())

    if not (args.write or args.check):
        print(f"grid {GRID}x{GRID}, sun {filled(sun())} cells, moon {filled(moon())} cells\n")
        print(f'<path class="sprite-sun" d="{sun_d}"/>')
        print(f'<path class="sprite-moon" d="{moon_d}"/>')
        return 0

    page = PAGE.read_text()
    if not (SUN_PATH.search(page) and MOON_PATH.search(page)):
        print(f"error: no sprite paths found in {PAGE}", file=sys.stderr)
        return 1

    updated = SUN_PATH.sub(lambda mo: mo.group(1) + sun_d + mo.group(2), page, count=1)
    updated = MOON_PATH.sub(lambda mo: mo.group(1) + moon_d + mo.group(2), updated, count=1)

    if args.check:
        if updated != page:
            print(
                "error: the sprites in the page are not what the generator "
                "produces; run scripts/make-sprites.py --write",
                file=sys.stderr,
            )
            return 1
        print("sprites are current")
        return 0

    PAGE.write_text(updated)
    print(f"sprites written into {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
