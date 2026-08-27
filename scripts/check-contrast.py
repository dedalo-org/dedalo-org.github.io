#!/usr/bin/env python3
"""Measure every colour in the page against the background it sits on.

A palette is easy to admire and hard to read. This computes the WCAG relative
luminance of each token and the contrast ratio against its own theme's
background, so "the dim grey is fine" is a number somebody checked rather than
a thing somebody thought.

Three thresholds, and the distinction between them is the whole point:

- **4.5:1** for anything that is text. Every `--fg*` and every accent, because
  accents are used as text on this page.
- **3:1** for `--line-hot`, which draws the boundary of a control. WCAG 1.4.11
  covers components that carry information.
- **nothing** for `--line`, a decorative hairline between sections. Holding a
  divider to a contrast floor makes it stop being a hairline, and 1.4.11
  exempts purely decorative graphics — so it is exempted here *by name*,
  rather than by being quietly skipped.

    scripts/check-contrast.py            # measure and report
    scripts/check-contrast.py --quiet    # only complain
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "index.html"

TEXT_MINIMUM = 4.5
COMPONENT_MINIMUM = 3.0

# Decorative, and named here so the exemption is a decision rather than an
# omission. Anything not in this set is held to a threshold.
DECORATIVE = {"line"}

# Tokens that are backgrounds or sit on an accent rather than on the page.
NOT_FOREGROUND = {"bg", "bg-alt", "bg-raised", "on-accent"}


def luminance(colour: str) -> float:
    """WCAG relative luminance of an `#rrggbb` colour."""
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    """Contrast ratio between two colours, lighter over darker."""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


BLOCK = re.compile(r"([^{}]*)\{([^{}]*)\}")
TOKEN = re.compile(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})")


def palettes(css: str) -> dict[str, dict[str, str]]:
    """Every rule that defines a `--bg`, keyed by its selector.

    A block without a background of its own is not a theme — it is a partial
    override, and measuring its colours against somebody else's background
    would produce a number that means nothing.
    """
    found: dict[str, dict[str, str]] = {}
    for selector, body in BLOCK.findall(css):
        tokens = dict(TOKEN.findall(body))
        if "bg" in tokens and len(tokens) > 1:
            found[" ".join(selector.split())] = tokens
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="only report failures")
    args = parser.parse_args()

    page = PAGE.read_text()
    # Only the stylesheet: the surrounding HTML has braces of its own, and a
    # greedy block match over the whole file reports the `<head>` as a theme.
    style = re.search(r"<style>(.*?)</style>", page, re.S)
    if not style:
        print("error: the page has no <style> block", file=sys.stderr)
        return 1
    themes = palettes(style.group(1))
    if not themes:
        print("error: no theme block with a --bg was found", file=sys.stderr)
        return 1

    failures = 0
    for selector, tokens in themes.items():
        background = tokens["bg"]
        if not args.quiet:
            print(f"\n{selector}  (bg {background})")

        for name, colour in sorted(tokens.items()):
            if name in NOT_FOREGROUND:
                continue
            if name in DECORATIVE:
                if not args.quiet:
                    print(f"  ---  {name:<10} {colour}  decorative, exempt by name")
                continue

            needed = COMPONENT_MINIMUM if name.startswith("line") else TEXT_MINIMUM
            ratio = contrast(colour, background)
            passed = ratio >= needed
            failures += not passed
            if not passed:
                print(
                    f"error: {selector}: --{name} ({colour}) is {ratio:.2f}:1 on "
                    f"{background}, and needs {needed}:1",
                    file=sys.stderr,
                )
            elif not args.quiet:
                print(f"  ok   {name:<10} {colour}  {ratio:5.2f}:1  (needs {needed})")

    measured = sum(
        1 for t in themes.values() for n in t if n not in NOT_FOREGROUND and n not in DECORATIVE
    )
    if failures:
        print(f"\n{failures} of {measured} colours are below their threshold", file=sys.stderr)
        return 1
    print(f"\n{measured} colours checked across {len(themes)} themes, all above threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
