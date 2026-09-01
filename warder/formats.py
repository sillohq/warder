"""``Format`` — how a value is drawn.

A format is the *read* half of the display pair; :class:`~warder.widgets.Widget`
is the *write* half. Keeping them apart is the reason a status can render as a
coloured badge in a list and as a select in a form without either declaration
knowing about the other.

A ``Format`` is a kind and its options, and nothing more. It carries no
rendering code, because the rendering lives in React and Python must be able to
send this over the wire::

    Format.money("USD")            →  {"kind": "money", "currency": "USD", ...}

Which means adding ``Format.rating()`` is a prop the front end already knows
how to read, not a template.

Alignment lives here too. A number that is not right-aligned cannot be scanned
down a column, and asking every author to remember that is how you get a table
where half the totals line up.
"""

from __future__ import annotations

import typing

from warder._check import one_of
from warder.base import Declaration
from warder.naming import coerce_choices

__all__ = ["Format"]

#: Kinds whose values are compared digit by digit, so they align right and
#: want tabular numerals.
_NUMERIC = frozenset({"number", "money", "percent", "bytes", "duration"})

_ALIGN = {kind: "right" for kind in _NUMERIC}
_ALIGN.update({"bool": "center", "rating": "center", "progress": "left"})


class Format(Declaration):
    """How one value is drawn in a list or on a detail page.

    Build with the classmethods. ``Format("badge", colors={...})`` works and is
    what :meth:`~warder.base.Declaration.with_` rebuilds through, but the named
    constructors document the options each kind accepts.
    """

    __slots__ = ("kind", "options")
    _fields = ("kind", "options")

    KINDS = (
        "text", "number", "money", "percent", "bytes", "duration",
        "date", "bool", "badge", "code", "link", "image", "avatar",
        "json", "tags", "progress", "rating", "color", "markdown", "html",
    )

    def __init__(self, kind: str = "text", **options: typing.Any) -> None:
        self._init(kind=one_of("Format kind", kind, self.KINDS), options=options)

    # ------------------------------------------------------------- text-ish

    @classmethod
    def text(cls, *, truncate: int | None = None, mono: bool = False) -> Format:
        """Plain text, optionally clipped to *truncate* characters.

        ``mono=True`` for identifiers and hashes — a proportional font makes
        two different ids look alike at a glance.
        """
        return cls("text", truncate=truncate, mono=mono)

    @classmethod
    def code(cls, *, language: str | None = None) -> Format:
        """Monospace, in a tinted box."""
        return cls("code", language=language)

    @classmethod
    def markdown(cls) -> Format:
        """Rendered Markdown. Sanitised on the way out; never trusted."""
        return cls("markdown")

    @classmethod
    def html(cls) -> Format:
        """Rendered HTML, sanitised.

        Offered because content models contain HTML and refusing to show it
        helps nobody. The sanitiser is not optional and there is no ``raw=``.
        """
        return cls("html")

    # -------------------------------------------------------------- numbers

    @classmethod
    def number(
        cls,
        *,
        precision: int = 0,
        prefix: str = "",
        suffix: str = "",
        grouping: bool = True,
    ) -> Format:
        """A number, grouped by thousands unless you say otherwise."""
        return cls(
            "number",
            precision=precision,
            prefix=prefix,
            suffix=suffix,
            grouping=grouping,
        )

    @classmethod
    def money(cls, currency: str = "USD", *, precision: int = 2) -> Format:
        """An amount in *currency*, formatted for the viewer's locale."""
        return cls("money", currency=currency, precision=precision)

    @classmethod
    def percent(cls, *, precision: int = 0, of: float = 1.0) -> Format:
        """A proportion. ``of=100`` when the column already holds 0–100."""
        return cls("percent", precision=precision, of=of)

    @classmethod
    def bytes(cls, *, binary: bool = True) -> Format:
        """A size: ``1.4 MiB`` binary, ``1.5 MB`` decimal."""
        return cls("bytes", binary=binary)

    @classmethod
    def duration(cls, *, unit: str = "seconds", style: str = "short") -> Format:
        """An elapsed time — ``2m 14s`` short, ``2 minutes 14 seconds`` long."""
        return cls(
            "duration",
            unit=one_of("unit", unit, ("seconds", "milliseconds", "minutes")),
            style=one_of("style", style, ("short", "long")),
        )

    @classmethod
    def progress(cls, *, max: float = 100.0, colors: typing.Mapping[str, str] | None = None) -> Format:
        """A bar. Reads faster than a percentage when you are scanning for outliers."""
        return cls("progress", max=max, colors=dict(colors or {}))

    @classmethod
    def rating(cls, *, max: int = 5, icon: str = "star") -> Format:
        return cls("rating", max=max, icon=icon)

    # ---------------------------------------------------------------- dates

    @classmethod
    def date(
        cls,
        style: str = "date",
        *,
        pattern: str | None = None,
        tooltip: bool = True,
    ) -> Format:
        """A moment in time.

        ``style="relative"`` renders "3 days ago", which is what you want in a
        list and never what you want when comparing two rows — so the exact
        value stays available as a tooltip unless you turn it off.
        """
        return cls(
            "date",
            style=one_of(
                "style", style, ("date", "datetime", "time", "relative", "iso")
            ),
            pattern=pattern,
            tooltip=tooltip,
        )

    @classmethod
    def relative(cls, *, tooltip: bool = True) -> Format:
        """Shorthand for ``Format.date("relative")``."""
        return cls.date("relative", tooltip=tooltip)

    # --------------------------------------------------------------- states

    @classmethod
    def bool(cls, *, labels: tuple[str, str] = ("Yes", "No"), style: str = "icon") -> Format:
        """True or false, as an icon, a word, or a coloured dot."""
        return cls(
            "bool",
            labels=tuple(labels),
            style=one_of("style", style, ("icon", "text", "dot", "switch")),
        )

    @classmethod
    def badge(
        cls,
        colors: typing.Mapping[typing.Any, str] | None = None,
        *,
        labels: typing.Iterable[typing.Any] | None = None,
        default: str = "zinc",
    ) -> Format:
        """A coloured pill — the right shape for a small closed set of states.

        *colors* maps value to a palette name. *labels* relabels the values,
        accepting any of the three ways a choice list is written.
        """
        return cls(
            "badge",
            colors=dict(colors or {}),
            labels=dict(coerce_choices(labels)) if labels else {},
            default=default,
        )

    @classmethod
    def tags(cls, *, color: str = "zinc", limit: int | None = 3) -> Format:
        """A list of small pills, with the overflow collapsed to ``+4``."""
        return cls("tags", color=color, limit=limit)

    @classmethod
    def color(cls, *, swatch: bool = True) -> Format:
        return cls("color", swatch=swatch)

    # ----------------------------------------------------------------- rich

    @classmethod
    def link(cls, *, to: typing.Callable[[typing.Any], str] | None = None,
             external: bool = False) -> Format:
        """A hyperlink. *to* is called ``(row)`` and returns the href."""
        return cls("link", to=to, external=external)

    @classmethod
    def image(cls, *, size: int = 32, rounded: str = "md") -> Format:
        return cls("image", size=size, rounded=one_of("rounded", rounded, ("none", "sm", "md", "full")))

    @classmethod
    def avatar(cls, *, size: int = 24, fallback: str = "initials") -> Format:
        """A picture with a name beside it — the shape a user column wants."""
        return cls("avatar", size=size, fallback=fallback)

    @classmethod
    def json(cls, *, collapsed: bool = True) -> Format:
        return cls("json", collapsed=collapsed)

    # ------------------------------------------------------------ questions

    @property
    def numeric(self) -> bool:
        """Whether this format's values are compared digit by digit."""
        return self.kind in _NUMERIC

    @property
    def align(self) -> str:
        """Where a cell in this format wants to sit, absent an explicit choice."""
        return _ALIGN.get(self.kind, "left")

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        """One option, or *default*."""
        return self.options.get(name, default)

    def __repr__(self) -> str:
        shown = {k: v for k, v in self.options.items() if v not in (None, "", {}, ())}
        inner = ", ".join(f"{k}={v!r}" for k, v in shown.items())
        return f"Format({self.kind!r}{', ' + inner if inner else ''})"


#: The default when a column says nothing.
TEXT = Format("text")
