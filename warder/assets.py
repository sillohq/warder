"""The built interface, and the document that loads it.

``pip install warder`` must not require Node, a build step, or a network call.
Someone installing an admin panel is not signing up to run Vite. So the wheel
carries the built assets under ``warder/static/`` and the React sources stay in
``ui/`` in the repository, excluded from the wheel by the build.

Nothing is fetched from a CDN. Everything is served by the framework's own
static layer under the admin's prefix, with content-hashed filenames and
immutable cache headers — so the admin works on an air-gapped network and under
a Content-Security-Policy that forbids third-party script, which are the same
conditions the people who most want an admin panel are usually working under.

The manifest's hash is also the Inertia asset version: when a deploy changes
the bundle, an open tab is told to reload rather than being handed new props to
render with old JavaScript, which produces a blank screen and no error.
"""

from __future__ import annotations

import hashlib
import json as jsonlib
import pathlib
import typing

__all__ = ["STATIC", "Assets"]

#: Where the built bundle lives inside the installed package.
STATIC = pathlib.Path(__file__).parent / "static"


class Assets:
    """The built bundle: what to load, and which version it is."""

    __slots__ = ("directory", "manifest", "version")

    def __init__(self, directory: pathlib.Path | None = None) -> None:
        self.directory = directory or STATIC
        self.manifest = self._read()
        self.version = self._version()

    @property
    def built(self) -> bool:
        """Whether there is a bundle to serve.

        False in a source checkout that has never run the build. The admin
        still answers — with a page that says so — rather than serving a blank
        document, because "nothing rendered" is the hardest failure to diagnose.
        """
        return bool(self.manifest)

    def _read(self) -> dict[str, typing.Any]:
        path = self.directory / "manifest.json"
        try:
            return typing.cast(dict, jsonlib.loads(path.read_text()))
        except (OSError, ValueError):
            return {}

    def _version(self) -> str:
        """A short hash of the manifest, which changes when the bundle does."""
        if not self.manifest:
            return "dev"
        payload = jsonlib.dumps(self.manifest, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:12]

    def entry(self) -> dict[str, typing.Any]:
        """The manifest entry for the interface's entry point."""
        for name, entry in self.manifest.items():
            if entry.get("isEntry") or name.endswith("main.tsx"):
                return typing.cast(dict, entry)
        return {}

    def tags(self, base: str) -> str:
        """The ``<link>`` and ``<script>`` tags that load the bundle."""
        entry = self.entry()
        if not entry:
            return ""
        base = base.rstrip("/")
        parts = [
            f'<link rel="stylesheet" href="{base}/{css}">'
            for css in entry.get("css", ())
        ]
        parts.append(f'<script type="module" src="{base}/{entry["file"]}"></script>')
        return "".join(parts)

    def document(self, admin: typing.Any, payload: str) -> str:
        """The full HTML document, with the page object embedded.

        Server-rendered only in the sense that the *first* response is a
        document; every visit after it is a page object over the same URL.
        """
        base = f"{admin.prefix}/assets"
        favicon = f'<link rel="icon" href="{admin.favicon}">' if admin.favicon else ""
        theme = admin.theme.stylesheet()
        body = (
            f'<div id="app" data-page="{payload}"></div>' if self.built else _unbuilt()
        )
        return (
            "<!doctype html>"
            f'<html lang="en" class="wd">'
            "<head>"
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow">'
            f"<title>{_escape(admin.title)}</title>"
            f"{favicon}"
            f"<style>{theme}</style>"
            f"{self.tags(base)}"
            "</head>"
            f'<body class="wd-body">{body}</body>'
            "</html>"
        )


def _unbuilt() -> str:
    """What a source checkout sees instead of a blank page."""
    return (
        '<div style="font:14px ui-sans-serif,system-ui;max-width:34rem;'
        'margin:12vh auto;padding:0 1.5rem;color:#16181d">'
        "<h1 style='font-size:1.1rem;margin:0 0 .75rem'>The interface is not built"
        "</h1>"
        "<p style='margin:0 0 .75rem;color:#6b7280'>Warder is installed from a "
        "source checkout and <code>warder/static/</code> is empty. A wheel always "
        "carries the built bundle; a checkout has to build it once:</p>"
        "<pre style='background:#f4f4f3;padding:.75rem;border-radius:6px;"
        "overflow:auto'>cd ui &amp;&amp; npm install &amp;&amp; npm run build</pre>"
        "</div>"
    )


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
