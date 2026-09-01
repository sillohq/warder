"""The three screens: ``List``, ``Form``, ``Detail``.

Each is a value describing one page. None of them render anything and none of
them know about an ORM — a ``List`` is a description of a table, and the admin
is one place that happens to draw one. That is what makes

    await admin.render(ctx, ORDERS, Order.filter(team_id=ctx.user.team_id))

work inside your own route, with your own queryset and your own layout.

``List`` carries one piece of derivation worth naming: :attr:`List.joins`
collects the relations its columns and filters traverse, so declaring
``Column.relation("author")`` is what removes the N+1. A ``select_related``
attribute maintained beside the column list is a list that falls out of step,
silently, and costs fifty queries a page when it does.
"""

from __future__ import annotations

import typing

from warder._check import identifier, one_of, positive, sequence
from warder.actions import Action
from warder.base import Declaration
from warder.columns import Column
from warder.fields import Field
from warder.filters import Filter
from warder.layout import Empty, Panel, Section
from warder.sorting import Sort

__all__ = ["Detail", "Form", "List"]

_DENSITIES = ("compact", "normal", "relaxed")
_LAYOUTS = ("stacked", "split", "wide")


class List(Declaration):
    """A table of rows.

    ::

        List(
            Column("title", link=True),
            Column.relation("author", display="email"),
            Column.badge("status", colors={"live": "green"}),
            filters=[Filter.search("title", "body"), Filter.choice("status", STATUSES)],
            actions=[Action("Publish", publish), Action.delete()],
            sort=Sort.desc("published_at"),
            per_page=25,
        )
    """

    __slots__ = (
        "columns",
        "filters",
        "actions",
        "row_actions",
        "sort",
        "select_related",
        "prefetch_related",
        "per_page",
        "per_page_options",
        "empty",
        "selectable",
        "sticky_header",
        "density",
        "totals",
        "group_by",
        "export",
        "limit",
        "description",
    )
    _fields = __slots__
    _parts = "columns"

    def __init__(
        self,
        *columns: Column,
        filters: typing.Sequence[Filter] = (),
        actions: typing.Sequence[Action] = (),
        row_actions: typing.Sequence[Action] = (),
        sort: Sort | str | None = None,
        select_related: typing.Sequence[str] = (),
        prefetch_related: typing.Sequence[str] = (),
        per_page: int = 25,
        per_page_options: typing.Sequence[int] = (25, 50, 100, 250),
        empty: Empty | str | None = None,
        selectable: bool = True,
        sticky_header: bool = True,
        density: str | None = None,
        totals: typing.Mapping[str, str] | None = None,
        group_by: str | None = None,
        export: bool = True,
        limit: int | None = None,
        description: str | None = None,
    ) -> None:
        for name in sequence("select_related", select_related):
            identifier("select_related", name)
        for name in sequence("prefetch_related", prefetch_related):
            identifier("prefetch_related", name)
        for column, how in dict(totals or {}).items():
            one_of(f"totals[{column!r}]", how, ("sum", "avg", "min", "max", "count"))
        self._init(
            columns=columns,
            filters=tuple(filters),
            actions=tuple(actions),
            row_actions=tuple(row_actions),
            sort=Sort.by(sort) if isinstance(sort, str) else sort,
            select_related=tuple(select_related),
            prefetch_related=tuple(prefetch_related),
            per_page=positive("per_page", per_page),
            per_page_options=tuple(per_page_options),
            empty=Empty(empty) if isinstance(empty, str) else empty,
            selectable=selectable,
            sticky_header=sticky_header,
            density=one_of("density", density, _DENSITIES) if density else None,
            totals=dict(totals or {}),
            group_by=identifier("group_by", group_by) if group_by else None,
            export=export,
            limit=positive("limit", limit) if limit is not None else None,
            description=description,
        )

    # -------------------------------------------------------------- questions

    @property
    def joins(self) -> tuple[str, ...]:
        """Every relation this list needs joined, in declaration order.

        Derived from the columns and filters that traverse one, then whatever
        ``select_related=`` adds. Deriving it is the point: the join list
        cannot fall behind the columns because it *is* the columns.
        """
        found: dict[str, None] = {}
        for column in self.columns:
            path = column.relation_path
            if path:
                found[path] = None
        for filter_ in self.filters:
            for field in filter_.fields:
                if "__" in field:
                    found["__".join(field.split("__")[:-1])] = None
        for name in self.select_related:
            found[name] = None
        return tuple(found)

    @property
    def column_map(self) -> dict[str, Column]:
        return {column.key: column for column in self.columns}

    @property
    def filter_map(self) -> dict[str, Filter]:
        return {filter_.key: filter_ for filter_ in self.filters}

    @property
    def action_map(self) -> dict[str, Action]:
        """Every action, bulk and per-row, by key."""
        return {action.key: action for action in (*self.actions, *self.row_actions)}

    @property
    def search(self) -> Filter | None:
        """The search box, if this list has one."""
        for filter_ in self.filters:
            if filter_.kind == "search":
                return filter_
        return None

    @property
    def link_column(self) -> Column | None:
        """The column whose text opens the row.

        The first marked ``link=True``, else the first column that is neither
        computed nor a relation — so a list with no ``link=`` at all is still
        navigable rather than a dead end.
        """
        for column in self.columns:
            if column.link:
                return column
        for column in self.columns:
            if not column.computed and not column.related:
                return column
        return self.columns[0] if self.columns else None

    def sorted_by(self, sort: Sort | None) -> List:
        """This list with a different default ordering."""
        return self.with_(sort=sort)

    def __repr__(self) -> str:
        return (
            f"List({len(self.columns)} columns, {len(self.filters)} filters, "
            f"{len(self.actions)} actions)"
        )


class Form(Declaration):
    """The add and edit screen.

    Takes sections, or bare fields, or both — consecutive bare fields collect
    into one unnamed group, so the short form stays short::

        Form(Field("name"), Field("slug"))
        Form(Section("Content", Field("title")), Section("Audit", collapsed=True))
    """

    __slots__ = (
        "sections",
        "submit",
        "layout",
        "sidebar",
        "on_save",
        "validate",
        "deletable",
        "cancel",
        "description",
        "width",
    )
    _fields = __slots__
    _parts = "sections"

    def __init__(
        self,
        *parts: Section | Field,
        submit: str = "Save",
        layout: str = "stacked",
        sidebar: typing.Sequence[Section] = (),
        on_save: typing.Callable[..., typing.Any] | None = None,
        validate: typing.Callable[..., typing.Any]
        | typing.Sequence[typing.Callable[..., typing.Any]] = (),
        deletable: bool = True,
        cancel: bool = True,
        description: str | None = None,
        width: str = "normal",
    ) -> None:
        checks = (validate,) if callable(validate) else tuple(validate)
        self._init(
            sections=_group(parts),
            submit=submit,
            layout=one_of("layout", layout, _LAYOUTS),
            sidebar=tuple(sidebar),
            on_save=on_save,
            validate=checks,
            deletable=deletable,
            cancel=cancel,
            description=description,
            width=one_of("width", width, ("narrow", "normal", "wide", "full")),
        )

    @property
    def fields(self) -> tuple[Field, ...]:
        """Every field, in order, across sections and sidebar."""
        return tuple(
            field
            for section in (*self.sections, *self.sidebar)
            for field in section.fields
        )

    @property
    def field_map(self) -> dict[str, Field]:
        return {field.name: field for field in self.fields}

    @property
    def writable(self) -> tuple[Field, ...]:
        """The fields a submission may set. The rest are dropped, not trusted."""
        return tuple(field for field in self.fields if field.editable)

    def errors(
        self, values: typing.Mapping[str, typing.Any]
    ) -> dict[str, tuple[str, ...]]:
        """Every field's complaints about *values*, keyed by field name.

        Field checks only. Whole-form checks in ``validate=`` run afterwards,
        in the resolver, where the row and the context exist.
        """
        found = {}
        for field in self.fields:
            if field.show is not None and not field.show.holds(values):
                continue
            messages = field.errors(values.get(field.name))
            if messages:
                found[field.name] = messages
        return found

    def __repr__(self) -> str:
        return f"Form({len(self.sections)} sections, {len(self.fields)} fields)"


class Detail(Declaration):
    """One row, in full.

    ::

        Detail(
            Panel.fields("Overview", "title", "author", "status"),
            Panel.inline("Sections", PostSection, columns=["heading", "position"]),
            Panel.related("Comments", Comment, limit=10),
        )
    """

    __slots__ = ("panels", "actions", "title", "subtitle", "layout", "description")
    _fields = __slots__
    _parts = "panels"

    def __init__(
        self,
        *panels: Panel,
        actions: typing.Sequence[Action] = (),
        title: str | typing.Callable[[typing.Any], str] | None = None,
        subtitle: str | typing.Callable[[typing.Any], str] | None = None,
        layout: str = "split",
        description: str | None = None,
    ) -> None:
        self._init(
            panels=panels,
            actions=tuple(actions),
            title=title,
            subtitle=subtitle,
            layout=one_of("layout", layout, _LAYOUTS),
            description=description,
        )

    @property
    def main(self) -> tuple[Panel, ...]:
        return tuple(p for p in self.panels if p.span in ("main", "full"))

    @property
    def side(self) -> tuple[Panel, ...]:
        return tuple(p for p in self.panels if p.span == "side")

    @property
    def panel_map(self) -> dict[str, Panel]:
        return {panel.key: panel for panel in self.panels}

    def __repr__(self) -> str:
        return f"Detail({len(self.panels)} panels)"


def _group(parts: typing.Sequence[Section | Field]) -> tuple[Section, ...]:
    """Wrap runs of bare fields in unnamed sections, leaving sections alone.

    ``Form(Field("a"), Section("More", Field("b")), Field("c"))`` becomes three
    groups in the order written — the run before, the section, the run after —
    rather than quietly hoisting the loose fields to the top.
    """
    grouped: list[Section] = []
    loose: list[Field] = []
    for part in parts:
        if isinstance(part, Section):
            if loose:
                grouped.append(Section("", *loose))
                loose = []
            grouped.append(part)
        elif isinstance(part, Field):
            loose.append(part)
        else:
            raise TypeError(
                f"Form takes Sections and Fields, got {type(part).__name__}."
            )
    if loose:
        grouped.append(Section("", *loose))
    return tuple(grouped)
