"""``Page`` and ``Card`` — everything that is not a model.

Every admin grows screens that are not a table of one model: a reconciliation
tool, a queue you work through, a page of numbers someone opens every Monday.
Those are :class:`Page`\\ s, and they are gated, grouped and navigated the same
way resources are — because the alternative is a route somewhere else in the
application with its own idea of who may see it.

::

    admin.add(Page("/reconcile", "Reconciliation", reconcile,
                   icon="scale", group="Finance",
                   gate=Gate.permission("finance.reconcile")))

    async def reconcile(ctx):
        return {"unmatched": await Payment.filter(matched=False).count()}

A handler returns props for its component, or an
:class:`~warder.results.Outcome` to redirect or download instead.
"""

from __future__ import annotations

import typing

from warder._check import callable_, identifier, one_of, positive
from warder.access import Gate
from warder.base import Declaration
from warder.naming import slug

if typing.TYPE_CHECKING:
    from warder.screens import List

__all__ = ["Card", "Dashboard", "Page"]


class Page(Declaration):
    """A screen of your own, inside the admin's shell and behind its gate."""

    __slots__ = (
        "path",
        "title",
        "render",
        "icon",
        "group",
        "gate",
        "component",
        "name",
        "weight",
        "description",
        "hidden",
    )
    _fields = __slots__
    _head = ("path", "title", "render")

    path: str
    title: str
    render: typing.Callable[..., typing.Any]
    icon: str | None
    group: str | None
    gate: Gate | None
    component: str | None
    name: str
    weight: int
    description: str | None
    hidden: bool

    def __init__(
        self,
        path: str,
        title: str,
        render: typing.Callable[..., typing.Any],
        *,
        icon: str | None = None,
        group: str | None = None,
        gate: Gate | None = None,
        component: str | None = None,
        name: str | None = None,
        weight: int = 0,
        description: str | None = None,
        hidden: bool = False,
    ) -> None:
        if not path.startswith("/"):
            raise ValueError(f"Page path must start with '/', got {path!r}.")
        self._init(
            path=path,
            title=title,
            render=callable_("Page render", render),
            icon=icon,
            group=group,
            gate=gate,
            component=component,
            name=identifier("Page name", name) if name else slug(title),
            weight=weight,
            description=description,
            hidden=hidden,
        )

    @property
    def key(self) -> str:
        return self.name

    def route(self, prefix: str = "") -> str:
        return f"{prefix.rstrip('/')}{self.path}"

    def __repr__(self) -> str:
        return f"Page({self.path!r}, {self.title!r})"


class Card(Declaration):
    """One tile on a dashboard.

    A card's *load* is called ``(ctx)`` and returns whatever its kind needs: a
    number, a list of points, a page of rows. The card says how to draw it.
    """

    __slots__ = (
        "kind",
        "title",
        "load",
        "options",
        "span",
        "gate",
        "icon",
        "description",
    )
    _fields = __slots__
    _extras = "options"

    KINDS = ("number", "chart", "table", "list", "custom")

    kind: str
    title: str
    load: typing.Callable[..., typing.Any] | None
    options: typing.Mapping[str, typing.Any]
    span: int
    gate: Gate | None
    icon: str | None
    description: str | None

    def __init__(
        self,
        kind: str,
        title: str,
        load: typing.Callable[..., typing.Any] | None = None,
        *,
        span: int = 1,
        gate: Gate | None = None,
        icon: str | None = None,
        description: str | None = None,
        **options: typing.Any,
    ) -> None:
        self._init(
            kind=one_of("Card kind", kind, self.KINDS),
            title=title,
            load=callable_("Card load", load) if load is not None else None,
            options=options,
            span=positive("Card span", span),
            gate=gate,
            icon=icon,
            description=description,
        )

    @classmethod
    def number(
        cls,
        title: str,
        load: typing.Callable[..., typing.Any],
        *,
        format: typing.Any = None,
        compare: str | None = None,
        goal: float | None = None,
        **options: typing.Any,
    ) -> Card:
        """A single figure.

        *compare* names a period — ``"7d"``, ``"30d"`` — and the loader is
        called a second time for it, so the card can show a delta. Without one
        there is no second call and no delta, because a number with a made-up
        trend beside it is worse than a number.
        """
        return cls(
            "number", title, load, format=format, compare=compare, goal=goal, **options
        )

    @classmethod
    def chart(
        cls,
        title: str,
        load: typing.Callable[..., typing.Any],
        *,
        kind: str = "line",
        stacked: bool = False,
        **options: typing.Any,
    ) -> Card:
        """A series. *load* returns ``[{"label": ..., "value": ...}, ...]``."""
        return cls(
            "chart",
            title,
            load,
            span=options.pop("span", 2),
            chart=one_of("kind", kind, ("line", "bar", "area", "donut")),
            stacked=stacked,
            **options,
        )

    @classmethod
    def table(
        cls,
        title: str,
        columns: List,
        load: typing.Callable[..., typing.Any],
        *,
        link: str | None = None,
        **options: typing.Any,
    ) -> Card:
        """A few rows, drawn by a :class:`~warder.screens.List` you already have.

        Reusing the list declaration is the point: the dashboard's "latest
        orders" and the orders screen format money and status the same way
        because they are the same value.
        """
        return cls(
            "table",
            title,
            load,
            span=options.pop("span", 3),
            columns=columns,
            link=link,
            **options,
        )

    @classmethod
    def custom(
        cls,
        title: str,
        component: str,
        *,
        load: typing.Callable[..., typing.Any] | None = None,
        **options: typing.Any,
    ) -> Card:
        return cls("custom", title, load, component=component, **options)

    @property
    def key(self) -> str:
        return slug(self.title)

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        return self.options.get(name, default)

    def __repr__(self) -> str:
        return f"Card.{self.kind}({self.title!r})"


class Dashboard(Declaration):
    """The admin's front page.

    Without one, the front page lists the resources — which is a reasonable
    thing for it to be and a poor thing for it to stay, because the first
    screen is the one everybody opens first.
    """

    __slots__ = ("cards", "title", "columns", "description")
    _fields = __slots__
    _parts = "cards"

    cards: tuple[Card, ...]
    title: str
    columns: int
    description: str | None

    def __init__(
        self,
        *cards: Card,
        title: str = "Overview",
        columns: int = 4,
        description: str | None = None,
    ) -> None:
        self._init(
            cards=cards,
            title=title,
            columns=positive("Dashboard columns", columns),
            description=description,
        )

    def __repr__(self) -> str:
        return f"Dashboard({len(self.cards)} cards)"
