"""Grouping: ``Section`` on a form, ``Panel`` on a detail page, ``Empty`` for
the state everyone forgets.

A form of twenty inputs in one column is a form nobody finishes. Sections are
the smallest thing that fixes that, and they cost one line::

    Form(
        Section("Content", Field("title"), Field("body")),
        Section("Publishing", Field("status"), Field("published_at")),
        Section("Audit", Field.readonly("created_at"), collapsed=True),
    )

Panels are the detail page's equivalent, and they are more than field groups:
a panel can be a child table you edit in place, a related list you page
through, or one of your own components.
"""

from __future__ import annotations

import typing

from warder._check import identifier, non_negative, one_of, positive
from warder.access import Access
from warder.base import Declaration
from warder.conditions import When
from warder.naming import slug
from warder.sorting import Sort

if typing.TYPE_CHECKING:
    from warder.actions import Action
    from warder.columns import Column
    from warder.fields import Field

__all__ = ["Empty", "Panel", "Section"]


class Section(Declaration):
    """A named group of inputs on a form.

    An empty *title* makes an unlabelled group — the right shape for the two
    or three fields at the top of a form that need no heading over them.
    """

    __slots__ = (
        "access",
        "collapsed",
        "columns",
        "description",
        "fields",
        "icon",
        "show",
        "title",
    )
    _fields = (
        "title",
        "fields",
        "description",
        "collapsed",
        "columns",
        "show",
        "access",
        "icon",
    )
    _parts = "fields"
    _head = ("title",)

    title: str
    fields: tuple[Field, ...]
    description: str | None
    collapsed: bool
    columns: int
    show: When | None
    access: Access | None
    icon: str | None

    def __init__(
        self,
        title: str,
        *fields: Field,
        description: str | None = None,
        collapsed: bool = False,
        columns: int = 1,
        show: When | None = None,
        access: Access | None = None,
        icon: str | None = None,
    ) -> None:
        self._init(
            title=title,
            fields=fields,
            description=description,
            collapsed=collapsed,
            columns=positive("Section columns", columns),
            show=show,
            access=access,
            icon=icon,
        )

    @property
    def key(self) -> str:
        return slug(self.title) or "main"

    def __repr__(self) -> str:
        return f"Section({self.title!r}, {len(self.fields)} fields)"


class Panel(Declaration):
    """One block on a detail page.

    Five kinds, and the difference between the middle two is the one worth
    knowing: an **inline** panel edits child rows in place and saves with the
    parent; a **related** panel is a read-only window onto rows that belong to
    themselves and links out to their own screens.
    """

    __slots__ = ("access", "icon", "kind", "options", "span", "target", "title")
    _fields = ("kind", "title", "target", "options", "access", "icon", "span")
    _extras = "options"

    KINDS = ("fields", "inline", "related", "custom", "text")

    kind: str
    title: str
    target: typing.Any
    options: typing.Mapping[str, typing.Any]
    access: Access | None
    icon: str | None
    span: str

    def __init__(
        self,
        kind: str,
        title: str,
        target: typing.Any = None,
        *,
        access: Access | None = None,
        icon: str | None = None,
        span: str = "main",
        **options: typing.Any,
    ) -> None:
        self._init(
            kind=one_of("Panel kind", kind, self.KINDS),
            title=title,
            target=target,
            options=options,
            access=access,
            icon=icon,
            span=one_of("span", span, ("main", "side", "full")),
        )

    @classmethod
    def fields(cls, title: str, *names: str | Column, **options: typing.Any) -> Panel:
        """Values from the row itself.

        Takes field names or whole :class:`~warder.columns.Column`\\ s, so a
        detail page can reuse the list's formatting rather than restate it.
        """
        for name in names:
            if isinstance(name, str):
                identifier("Panel.fields", name)
        return cls("fields", title, tuple(names), **options)

    @classmethod
    def inline(
        cls,
        title: str,
        model: type,
        *,
        fields: typing.Sequence[str | Field] = (),
        columns: typing.Sequence[str | Column] = (),
        editable: bool = True,
        extra: int = 1,
        maximum: int | None = None,
        deletable: bool = True,
        sort: Sort | None = None,
        via: str | None = None,
        **options: typing.Any,
    ) -> Panel:
        """Child rows edited in place and saved with their parent.

        *via* names the foreign key on *model* pointing back here, and is
        worked out at mount when there is exactly one candidate. Two candidates
        is an error rather than a guess — picking the first of
        ``author`` and ``editor`` would be wrong half the time and silent both
        halves.
        """
        return cls(
            "inline",
            title,
            model,
            fields=tuple(fields),
            columns=tuple(columns),
            editable=editable,
            extra=non_negative("Panel.inline extra", extra),
            maximum=maximum,
            deletable=deletable,
            sort=sort,
            via=identifier("Panel.inline via", via) if via else None,
            **options,
        )

    @classmethod
    def related(
        cls,
        title: str,
        model: type,
        *,
        columns: typing.Sequence[str | Column] = (),
        limit: int = 10,
        sort: Sort | None = None,
        via: str | None = None,
        link: bool = True,
        **options: typing.Any,
    ) -> Panel:
        """A window onto rows that belong to themselves.

        *limit* rows, with a link to the full filtered list — which is the
        honest shape, because a customer with nine hundred orders should not
        render nine hundred rows on their profile.
        """
        return cls(
            "related",
            title,
            model,
            columns=tuple(columns),
            limit=positive("Panel.related limit", limit),
            sort=sort,
            via=identifier("Panel.related via", via) if via else None,
            link=link,
            **options,
        )

    @classmethod
    def custom(
        cls,
        title: str,
        component: str,
        *,
        props: typing.Mapping[str, typing.Any]
        | typing.Callable[..., typing.Any]
        | None = None,
        **options: typing.Any,
    ) -> Panel:
        """One of your own React components, mounted with props you build.

        *props* is either a mapping or a callable ``(ctx, row)`` returning one,
        so the panel can load whatever it needs without a second endpoint.
        """
        return cls("custom", title, component, props=props, **options)

    @classmethod
    def text(
        cls,
        title: str,
        render: typing.Callable[[typing.Any], str],
        *,
        format: str = "text",
        **options: typing.Any,
    ) -> Panel:
        """Prose built in Python — a summary, a computed explanation."""
        return cls(
            "text",
            title,
            render,
            format=one_of("format", format, ("text", "markdown", "html")),
            **options,
        )

    @property
    def key(self) -> str:
        return slug(self.title) or self.kind

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        return self.options.get(name, default)

    def __repr__(self) -> str:
        target = getattr(self.target, "__name__", None)
        inner = f", {target}" if target else ""
        return f"Panel.{self.kind}({self.title!r}{inner})"


class Empty(Declaration):
    """What a list shows when there is nothing in it.

    Worth declaring rather than defaulting. "No results" after a filter and
    "nothing here yet" on a new install are different messages, and the second
    is the first thing a new user of your admin ever reads.
    """

    __slots__ = ("action", "description", "icon", "title")
    _fields = ("title", "description", "action", "icon")

    title: str
    description: str | None
    action: Action | None
    icon: str | None

    def __init__(
        self,
        title: str = "Nothing here yet",
        *,
        description: str | None = None,
        action: Action | None = None,
        icon: str | None = None,
    ) -> None:
        self._init(title=title, description=description, action=action, icon=icon)

    def __repr__(self) -> str:
        return f"Empty({self.title!r})"
