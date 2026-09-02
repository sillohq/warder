"""The Inertia protocol, implemented here rather than depended on.

Inertia is a small, published protocol: a request either wants a **page object**
(JSON) or a **document** (HTML with that page object embedded), and one header
decides which. Everything else — partial reloads, asset versioning, the redirect
rules — is four more headers.

``sillo-inertia`` exists, and Warder does not use it, for one reason: it is
written against the 0.x ``Request``/``Response`` API and this package is written
against the context API. Waiting for that port would block the entire interface
on another repository's schedule, to avoid writing two hundred lines of a stable
specification. When it is ported, this module becomes an adapter over it and the
props layer above does not change.

Three rules do most of the work.

**A redirect after a mutation must be 303.** After ``PUT``, ``PATCH`` or
``DELETE``, a 302 makes the browser repeat the *original method* against the new
URL, so "save and go back to the list" becomes "delete the list". The protocol
requires 303 and this converts it silently rather than trusting every handler to
remember.

**A version mismatch is a 409, not a page.** When the assets have changed under
a running tab, sending it new props to render with old JavaScript produces a
blank screen and no error. 409 with ``X-Inertia-Location`` tells the client to
do a full reload instead.

**A partial reload sends only what was asked for.** Re-running the row query to
refresh a flash message is the difference between a snappy admin and one that
feels like a page load.
"""

from __future__ import annotations

import json as jsonlib
import typing

from sillo import responses

if typing.TYPE_CHECKING:
    from sillo import HttpContext
    from sillo.core.http.response import BaseResponse

__all__ = ["Page", "Prop", "defer", "is_inertia", "location", "optional", "render"]

#: Methods after which a redirect has to be 303 rather than 302.
_UNSAFE = frozenset({"PUT", "PATCH", "DELETE"})

#: Characters that would end the script block a page object is embedded in.
_ESCAPES = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    # U+2028 and U+2029 are newlines to a JavaScript parser and nothing to a
    # JSON one, so they end a string literal that JSON says is still open.
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}


class Prop:
    """A prop that is not always sent.

    ``optional`` props are skipped unless a partial reload names them, which is
    how a list can carry an expensive count without paying for it on every
    keystroke in the search box. ``deferred`` props are skipped on the first
    visit and fetched immediately afterwards, so the page paints before the
    slow part arrives.
    """

    __slots__ = ("load", "mode", "group")

    def __init__(
        self, load: typing.Callable[[], typing.Any], mode: str, group: str = "default"
    ) -> None:
        self.load = load
        self.mode = mode
        self.group = group

    async def value(self) -> typing.Any:
        result = self.load()
        if hasattr(result, "__await__"):
            result = await result
        return result


def optional(load: typing.Callable[[], typing.Any]) -> Prop:
    """Send this only when a partial reload asks for it by name."""
    return Prop(load, "optional")


def defer(load: typing.Callable[[], typing.Any], *, group: str = "default") -> Prop:
    """Skip this on the first visit; the client fetches it straight after."""
    return Prop(load, "deferred", group)


class Page:
    """One Inertia page: a component, its props, the URL, and the asset version."""

    __slots__ = ("component", "props", "url", "version", "deferred")

    def __init__(
        self,
        component: str,
        props: typing.Mapping[str, typing.Any],
        url: str,
        version: str,
        deferred: typing.Mapping[str, list[str]] | None = None,
    ) -> None:
        self.component = component
        self.props = dict(props)
        self.url = url
        self.version = version
        self.deferred = dict(deferred or {})

    def as_dict(self) -> dict[str, typing.Any]:
        page: dict[str, typing.Any] = {
            "component": self.component,
            "props": self.props,
            "url": self.url,
            "version": self.version,
        }
        if self.deferred:
            page["deferredProps"] = self.deferred
        return page


def is_inertia(ctx: HttpContext) -> bool:
    """Whether this request wants a page object rather than a document."""
    return str(ctx.headers.get("x-inertia", "")).lower() == "true"


async def render(
    ctx: HttpContext,
    component: str,
    props: typing.Mapping[str, typing.Any],
    *,
    version: str = "",
    document: typing.Callable[[str, Page], str] | None = None,
) -> BaseResponse:
    """Answer *ctx* with *component* and *props*.

    JSON when the request came from the client-side router, a full document
    when someone typed the URL or hit refresh. Same props either way — which is
    the property that makes an Inertia page a normal server-rendered page that
    happens to be fast.
    """
    # Only a GET can be safely retried as a full page load. A mismatched POST
    # is told to reload and loses its body either way, but at least the person
    # sees a page rather than nothing.
    stale = ctx.headers.get("x-inertia-version", version) != version
    if is_inertia(ctx) and stale and ctx.method == "GET":
        return location(str(ctx.url))

    wanted = _partial(ctx, component)
    resolved, deferred = await _resolve(props, wanted, first_visit=not wanted)
    page = Page(component, resolved, str(ctx.url), version, deferred)

    if is_inertia(ctx):
        return responses.json(
            page.as_dict(),
            headers={"X-Inertia": "true", "Vary": "X-Inertia"},
        )
    builder = document if document is not None else _document
    return responses.html(builder(_embed(page), page), headers={"Vary": "X-Inertia"})


def redirect(ctx: HttpContext, url: str, *, status: int | None = None) -> BaseResponse:
    """Redirect, using 303 after a mutation.

    After ``PUT``, ``PATCH`` or ``DELETE`` a 302 makes the browser repeat the
    *original method* against the new location. That turns "save and return to
    the list" into "delete the list", which is a bug you find in production.
    """
    if status is None:
        status = 303 if ctx.method in _UNSAFE else 302
    return responses.redirect(url, status_code=status)


def location(url: str) -> BaseResponse:
    """Leave the Inertia app entirely — an external URL, or a hard reload.

    Sent as 409 rather than a redirect because the client-side router follows
    redirects itself and would try to render a login page as a page object.
    """
    return responses.empty(status_code=409, headers={"X-Inertia-Location": url})


def _partial(ctx: HttpContext, component: str) -> frozenset[str]:
    """The prop names a partial reload asked for, if this is one.

    Only honoured when the client is still on the same component: a partial
    reload of a page the server no longer thinks you are on is a full visit.
    """
    if not is_inertia(ctx):
        return frozenset()
    if ctx.headers.get("x-inertia-partial-component") != component:
        return frozenset()
    asked = ctx.headers.get("x-inertia-partial-data") or ""
    return frozenset(name.strip() for name in asked.split(",") if name.strip())


async def _resolve(
    props: typing.Mapping[str, typing.Any],
    wanted: frozenset[str],
    *,
    first_visit: bool,
) -> tuple[dict[str, typing.Any], dict[str, list[str]]]:
    """Evaluate the props that are being sent, and name the ones that are not."""
    resolved: dict[str, typing.Any] = {}
    deferred: dict[str, list[str]] = {}

    for name, value in props.items():
        if wanted and name not in wanted:
            continue
        if isinstance(value, Prop):
            if value.mode == "optional" and name not in wanted:
                continue
            if value.mode == "deferred" and first_visit:
                deferred.setdefault(value.group, []).append(name)
                continue
            resolved[name] = await value.value()
            continue
        if callable(value):
            result = value()
            resolved[name] = await result if hasattr(result, "__await__") else result
            continue
        resolved[name] = value
    return resolved, deferred


def _embed(page: Page) -> str:
    """The page object as JSON safe to sit inside an HTML attribute."""
    encoded = jsonlib.dumps(page.as_dict(), default=str)
    for character, escape in _ESCAPES.items():
        encoded = encoded.replace(character, escape)
    return encoded.replace('"', "&quot;")


def _document(
    payload: str, page: Page
) -> str:  # pragma: no cover - replaced by the site
    """A bare document, for a caller that supplies no template of its own."""
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{page.component}</title></head>"
        f'<body><div id="app" data-page="{payload}"></div></body></html>'
    )
