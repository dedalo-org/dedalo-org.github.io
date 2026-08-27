#!/usr/bin/env python3
"""Generate the labyrinth favicon, and write it into the page.

Dedalo is Daedalus, who built the labyrinth. The mark is one, drawn rather
than drawn *by hand*: concentric square rings with alternating gaps, which is
the square form of the classical labyrinth and is mirror-symmetric about its
vertical axis by construction.

Why a generator instead of a committed asset:

- the geometry is a handful of numbers, and changing the ring count or the
  stroke weight should be an edit to a parameter rather than to path data
  somebody has to re-derive;
- symmetry is *asserted* below rather than eyeballed, so a change that breaks
  it fails here instead of looking slightly wrong in a tab;
- the page stays entirely self-contained. The icon is inlined as a data URI,
  which is what keeps the site's Content-Security-Policy able to say
  `default-src 'none'` and mean it.

The SVG carries its own `prefers-color-scheme` rule, so the icon follows the
*browser's* theme rather than the page's — a tab strip is not the page, and an
icon tuned for one is invisible against the other.

    scripts/make-favicon.py            # print the SVG
    scripts/make-favicon.py --check    # is the page's icon current?
    scripts/make-favicon.py --write    # regenerate it in site/index.html
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "index.html"

# The drawing. Everything about the mark's shape is these six numbers, and
# they are chosen for **sixteen pixels** rather than for the poster.
#
# A favicon lives in a tab strip. At 16px one viewBox unit is half a device
# pixel, so a wall thinner than four units and a corridor narrower than four
# more both dissolve into grey — which is what three thin rings did, and it
# looked like a smudge. Two thick rings and a solid centre survive the size the
# mark is actually seen at, and being chunky at 160px is the cheaper failure.
SIZE = 32  # viewBox is square and this wide
RINGS = 2  # concentric rings, outermost first
STROKE = 3.6  # wall thickness
MARGIN = 2.4  # space from the viewBox edge to the outer ring
GAP = 4.4  # width of the opening in each ring
HEART = 3.6  # the solid square at the centre

# Chosen to hold their own against a browser's tab strip, which is neither the
# page's background nor reliably either of the two the page offers.
INK_LIGHT = "#14170f"
INK_DARK = "#7dff9b"


def ring(index: int) -> str:
    """One ring: a square with a centred gap in its top or bottom edge.

    Drawn as a single open path starting at one side of the gap and running
    the whole way round to the other, so a ring is one stroke and the gap is
    the absence of one — rather than four lines with a hole arranged between
    them.
    """
    inset = MARGIN + index * (SIZE - 2 * MARGIN - STROKE) / (2 * RINGS - 1)
    lo, hi = inset, SIZE - inset
    mid = SIZE / 2
    left, right = mid - GAP / 2, mid + GAP / 2

    if index % 2 == 0:
        # Gap at the top: right of it, clockwise, back to left of it.
        return (
            f"M{right:.2f} {lo:.2f}H{hi:.2f}V{hi:.2f}H{lo:.2f}V{lo:.2f}H{left:.2f}"
        )
    # Gap at the bottom, mirrored vertically so the path alternates.
    return f"M{right:.2f} {hi:.2f}H{hi:.2f}V{lo:.2f}H{lo:.2f}V{hi:.2f}H{left:.2f}"


def svg() -> str:
    """The complete icon, as a single line of SVG."""
    paths = "".join(f'<path d="{ring(i)}"/>' for i in range(RINGS))
    # A filled centre: the thing at the middle of a labyrinth, and the one
    # element that keeps the mark from reading as a plain spiral at 16px.
    heart = SIZE / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}">'
        f"<style>"
        f"path,rect{{stroke:{INK_LIGHT};fill:none;"
        f"stroke-width:{STROKE};stroke-linecap:square}}"
        f"rect{{fill:{INK_LIGHT};stroke:none}}"
        f"@media(prefers-color-scheme:dark){{"
        f"path{{stroke:{INK_DARK}}}rect{{fill:{INK_DARK}}}}}"
        f"</style>"
        f"{paths}"
        f'<rect x="{heart - HEART / 2:.2f}" y="{heart - HEART / 2:.2f}" '
        f'width="{HEART:.2f}" height="{HEART:.2f}"/>'
        f"</svg>"
    )


def data_uri() -> str:
    """The icon as a `data:` URI, ready for `<link rel="icon">`.

    Percent-encoded rather than base64: an SVG is text, and text that survives
    as text can be read in a diff by whoever reviews the next change to it.
    """
    return "data:image/svg+xml," + quote(svg(), safe="")


def is_symmetric() -> bool:
    """Whether every ring is mirror-symmetric about the vertical axis.

    Checked rather than assumed. The gap is centred and the square is centred,
    so this holds by construction — which is exactly the kind of claim that
    stops being true when somebody adjusts a number.
    """
    mid = SIZE / 2
    for index in range(RINGS):
        xs = [float(v) for v in re.findall(r"[MH](-?\d+\.\d+)", ring(index))]
        reflected = sorted(round(2 * mid - x, 2) for x in xs)
        if sorted(round(x, 2) for x in xs) != reflected:
            return False
    return True


ICON_LINE = re.compile(r'<link rel="icon" href="[^"]*">')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="update site/index.html")
    parser.add_argument("--check", action="store_true", help="is the page current?")
    args = parser.parse_args()

    if not is_symmetric():
        print("error: the generated rings are not mirror-symmetric", file=sys.stderr)
        return 1

    line = f'<link rel="icon" href="{data_uri()}">'

    if not (args.write or args.check):
        print(svg())
        return 0

    page = PAGE.read_text()
    if not ICON_LINE.search(page):
        print(f"error: no <link rel=\"icon\"> in {PAGE}", file=sys.stderr)
        return 1

    if args.check:
        current = ICON_LINE.search(page).group(0)
        if current != line:
            print(
                "error: the favicon in the page is not what the generator "
                "produces; run scripts/make-favicon.py --write",
                file=sys.stderr,
            )
            return 1
        print("favicon is current")
        return 0

    PAGE.write_text(ICON_LINE.sub(lambda _: line, page, count=1))
    print(f"favicon written into {PAGE.relative_to(ROOT)} ({len(line)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
