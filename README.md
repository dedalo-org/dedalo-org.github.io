# dedalo-org.github.io

The organisation's site, served at **<https://dedalo-org.github.io/>**.

One HTML page, no build step and no JavaScript: the Content-Security-Policy in
the document forbids scripts and remote resources, and
`scripts/check-site.py` fails the build if a script tag or an external `src`
ever appears. That is the whole architecture.

## What lives where

| URL | Repository | What it is |
| --- | --- | --- |
| `/` | this one | The pitch, the guarantees, install, project status |
| `/dedalo/` | [`dedalo`](https://github.com/dedalo-org/dedalo) | The handbook — mdBook, the narrative documentation |
| `/dedalo/api/` | [`dedalo`](https://github.com/dedalo-org/dedalo) | A redirect. The API reference is on [docs.rs](https://docs.rs/dedalo), versioned per release |

The reference is not published here on purpose: docs.rs builds it from the
crate that was uploaded, so what a reader sees matches the version they
installed rather than whatever `main` looked like that morning.

`/dedalo/` is a separate GitHub Pages deployment on the same domain, so links
to it are declared with `--external-prefix` rather than resolved against this
tree — a typo inside one is still caught, but the files are not here to check.

Only the `robots.txt` at the domain root is ever fetched, so this one names
both sitemaps.

## One convention for diagrams

The page had ASCII diagrams drawn with box-drawing characters inside `<pre>`.
A screen reader reads those literally — `─ ─ ─ ▶` and so on — which is a
hundred characters of noise where a sentence should be. They are gone; the
pipeline, the split and the funding ladder are SVG.

The rule, so the page does not end up with two conventions:

**A picture gets `role="img"` and an `aria-label` that carries the whole
content.** One announcement instead of a hundred characters. The label says
what the diagram *shows*, in order, and never describes the drawing — "82.5
percent to contributors, 15 percent to the project treasury, 2.5 percent
protocol fee to the network", not "a doughnut chart with three arcs".

`aria-hidden` plus a separate text equivalent was the alternative. It was not
taken: it makes the diagram decoration for sighted readers only, and the
equivalent drifts because nothing ties it to the picture.

**Text stays text.** A terminal transcript, an install command and a list of
links are content, not pictures, and hiding them behind a label would take
away something a screen reader user can otherwise read line by line. They get
a `<figcaption class="sr-only">` that says what the block shows *before* the
literal characters, so the columns arrive with context rather than instead of
it.

**Decoration is `aria-hidden="true"`.** The window-chrome dots, the theme
toggle's icon, and the scrolling tickers. The tickers are the case worth
naming: they are announced by nothing, and every fact in them — the
pre-release status, that on-chain broadcast is not live, that Dedalo holds no
signing key — is stated in readable prose further down the page. Hiding a
duplicate is fine; hiding the only copy of something would not be.

## Working on it

```sh
scripts/check-site.py --root site --built site --base-path "" --external-prefix /dedalo/
```

Then open `site/index.html`. There is nothing to compile.

Pushing to `main` runs the same check and publishes. The check is not a
formality: it verifies the CSP is present, that no script or remote resource
crept in, that the CSS braces balance, that every `#anchor` points at an
element that exists, and that every internal link resolves in the tree about
to go live.
