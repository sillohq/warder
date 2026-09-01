"""What an action hands back.

Free builders, the way ``json()`` and ``text()`` are free builders elsewhere in
Sillo — an action returns a value rather than reaching for a response object::

    async def publish(ctx, rows):
        count = await rows.filter(status="draft").update(status="live")
        return notice(f"Published {count} posts")

Returning ``None`` means "it worked, reload the list", which is what most
actions want and what happens if you write no return at all. Every other
outcome has a name.
"""

from __future__ import annotations

import typing

from warder.base import Declaration

__all__ = [
    "Outcome",
    "download",
    "go",
    "modal",
    "nothing",
    "notice",
    "problem",
    "refresh",
    "warning",
]


class Outcome(Declaration):
    """The result of an action, as a value the route layer turns into a response."""

    __slots__ = ("kind", "message", "options")
    _fields = ("kind", "message", "options")

    KINDS = ("notice", "warning", "problem", "go", "refresh", "download",
             "modal", "nothing")

    def __init__(self, kind: str, message: str = "", **options: typing.Any) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"Outcome kind {kind!r} is not one of {self.KINDS}.")
        self._init(kind=kind, message=message, options=options)

    @property
    def tone(self) -> str:
        """How the flash is coloured: ``success``, ``warning`` or ``danger``."""
        return {"notice": "success", "warning": "warning", "problem": "danger"}.get(
            self.kind, "neutral"
        )

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        return self.options.get(name, default)

    def __repr__(self) -> str:
        if self.message:
            return f"{self.kind}({self.message!r})"
        return f"{self.kind}()"


def notice(message: str, **options: typing.Any) -> Outcome:
    """It worked. Say so, and reload."""
    return Outcome("notice", message, **options)


def warning(message: str, **options: typing.Any) -> Outcome:
    """It worked, partly, or it worked and you should know something."""
    return Outcome("warning", message, **options)


def problem(message: str, **options: typing.Any) -> Outcome:
    """It did not work, and this is why — shown to the person who ran it.

    Distinct from raising: an action that raises is a bug and becomes a 500. An
    action that returns ``problem`` has decided something, and says it.
    """
    return Outcome("problem", message, **options)


def go(url: str, *, message: str = "") -> Outcome:
    """Send them somewhere — a report that was just generated, a created row."""
    return Outcome("go", message, url=url)


def refresh(*, message: str = "") -> Outcome:
    """Reload the list. What ``None`` means, spelled out."""
    return Outcome("refresh", message)


def nothing() -> Outcome:
    """Stay exactly where you are, having done nothing visible."""
    return Outcome("nothing")


def download(
    content: bytes | str | typing.Iterable[bytes] | None = None,
    *,
    filename: str,
    content_type: str = "application/octet-stream",
    url: str | None = None,
) -> Outcome:
    """Hand back a file.

    Either *content* to send now, or *url* to send them at something already
    stored. An export of forty thousand rows should be the second: generated
    by a job, fetched when it is ready, rather than held in memory while the
    request times out.
    """
    if content is None and url is None:
        raise TypeError("download() needs content= or url=.")
    return Outcome(
        "download", "", content=content, filename=filename,
        content_type=content_type, url=url,
    )


def modal(component: str, *, props: typing.Mapping[str, typing.Any] | None = None,
          title: str = "") -> Outcome:
    """Open one of your own components over the list.

    For the action whose result is a *screen* — a diff to review, a preview to
    approve — rather than a sentence.
    """
    return Outcome("modal", title, component=component, props=dict(props or {}))
