"""Build the interface before packaging, and refuse to ship a wheel without it.

``pip install warder`` must not require Node. The wheel therefore carries the
built bundle under ``warder/static/`` while the React sources stay in ``ui/``,
excluded from it — so a consumer gets one directory of hashed assets and no
``package.json``, no ``node_modules`` and no ``postinstall``.

This hook is what keeps those two facts in step. It runs ``npm ci && npm run
build`` in ``ui/`` and then checks that a manifest came out the other side. A
wheel whose interface failed to build would install cleanly and render a blank
page, which is the worst of both outcomes, so the build fails instead.

It is skipped when ``warder/static/manifest.json`` is already newer than every
source file, because rebuilding an unchanged bundle on every ``pip install -e``
is thirty seconds nobody asked for.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import typing

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = pathlib.Path(__file__).parent
UI = ROOT / "ui"
STATIC = ROOT / "warder" / "static"
MANIFEST = STATIC / "manifest.json"


class BuildUI(BuildHookInterface):
    """Runs Vite, then proves it worked."""

    PLUGIN_NAME = "build-ui"

    def initialize(self, version: str, build_data: dict[str, typing.Any]) -> None:
        if os.environ.get("WARDER_SKIP_UI_BUILD"):
            self._require_manifest("WARDER_SKIP_UI_BUILD is set")
            return
        if not UI.exists():
            # An sdist unpacked without ui/ can still build a wheel, as long as
            # the assets it carries are already there.
            self._require_manifest("ui/ is not in this tree")
            return
        if self._current():
            return
        self._build()
        self._require_manifest("the build produced no manifest")

    def _current(self) -> bool:
        """Whether the built bundle is newer than every source that feeds it."""
        if not MANIFEST.exists():
            return False
        built = MANIFEST.stat().st_mtime
        for path in (UI / "src").rglob("*"):
            if path.is_file() and path.stat().st_mtime > built:
                return False
        for name in ("package.json", "vite.config.ts"):
            candidate = UI / name
            if candidate.exists() and candidate.stat().st_mtime > built:
                return False
        return True

    def _build(self) -> None:
        npm = shutil.which("npm")
        if npm is None:
            raise RuntimeError(
                "Building a Warder wheel needs npm, because the interface is "
                "compiled into the wheel. Install Node, or set "
                "WARDER_SKIP_UI_BUILD=1 to package assets that are already built."
            )
        install = "ci" if (UI / "package-lock.json").exists() else "install"
        for command in ([npm, install], [npm, "run", "build"]):
            subprocess.run(command, cwd=UI, check=True)

    def _require_manifest(self, why: str) -> None:
        if MANIFEST.exists():
            return
        raise RuntimeError(
            f"warder/static/manifest.json is missing and {why}. A wheel without "
            "the built interface installs cleanly and renders a blank page, so "
            "the build stops here instead. Run: cd ui && npm install && npm run build"
        )
