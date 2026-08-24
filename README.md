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
