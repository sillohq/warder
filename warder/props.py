"""Turning a resolved declaration into props.

This is the seam the whole interface hangs on. **Python sends a resolved
declaration; React is a generic renderer for that shape.** The front end does
not know what a ``Post`` is — it knows what a badge column is, what a relation
picker is, and how to draw a form section. So adding ``Column.badge("status",
colors=…)`` changes a prop rather than a template, and a new resource never
needs the interface rebuilt.

The division of labour is deliberate:

* **Python extracts.** Which columns exist for *this* person, which rows they
  may see, what value each cell holds. All of it authorisation-dependent, all
  of it impossible to do safely in the browser.
* **React formats.** Money to two places in the viewer's locale, a timestamp to
  "3 days ago", a status to a coloured pill. All of it locale- and
  viewport-dependent, all of it wasteful to do on the server.

A column you may not view is **absent from these props**, not flagged hidden —
so it never reaches the browser at all, and no amount of devtools brings it
back.
"""

from __future__ import annotations

import datetime as dt
import decimal
import enum
import typing
import uuid

from warder._async import awaited
from warder.access import Access
from warder.filters import Filter
from warder.schema import Schema
from warder.sorting import Sort

if typing.TYPE_CHECKING:
    from warder.actions import Action
    from warder.columns import Column
    from warder.fields import Field
    from warder.layout import Panel
    from warder.resolve import Bound
    from warder.screens import Form, List
    from warder.site import Admin

__all__ = [
    "Query",
    "cell",
    "detail_page",
    "form_page",
    "jsonable",
    "list_page",
    "shell",
]

#: The largest page anyone may ask for. Without a ceiling, `?per_page=1000000`
#: is a denial-of-service anybody with a login can perform by accident.
MAX_PER_PAGE = 500


def jsonable(value: typing.Any) -> typing.Any:
    """A JSON-safe form of *value*, losing as little as possible.

    Decimals become floats: the admin *displays* them, and the format says to
    how many places. A model instance becomes its ``str()`` and its key, which
    is what a relation cell needs to draw a link.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, enum.Enum):
        return jsonable(value.value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, dt.timedelta):
        return value.total_seconds()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in value]
    if hasattr(value, "pk"):
        return {"id": jsonable(value.pk), "label": str(value)}
    return str(value)


class Query:
    """What the URL is asking for: a page, an ordering, and some filters.

    Every part of a list's state lives in the query string, because a filtered
    list you cannot send to a colleague is a filtered list you rebuild every
    morning. This reads it back, and refuses the values that would hurt.
    """

    __slots__ = ("page", "per_page", "sort", "values", "selection", "search")

    def __init__(self, ctx: typing.Any, screen: List) -> None:
        params = ctx.query_params
        self.page = max(1, _int(params.get("page"), 1))
        self.per_page = min(
            MAX_PER_PAGE, max(1, _int(params.get("per_page"), screen.per_page))
        )
        self.sort = _sort(params.get("sort"), screen)
        self.values = {
            filter_.key: params.get(filter_.key)
            for filter_ in screen.filters
            if params.get(filter_.key) not in (None, "")
        }
        self.search = self.values.get("q")
        self.selection = [
            value for value in _all(params, "id") if value not in (None, "")
        ]

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def as_props(self) -> dict[str, typing.Any]:
        return {
            "page": self.page,
            "perPage": self.per_page,
            "sort": [str(term) for term in self.sort.terms] if self.sort else [],
            "filters": dict(self.values),
        }


async def apply(
    ctx: typing.Any, bound: Bound, rows: typing.Any, query: Query
) -> typing.Any:
    """*rows* narrowed by scope, then by the query's filters, then ordered.

    In that order, and all three: scope is who you are, filters are what you
    asked for, and ordering is how you want to read it. Skipping the first is a
    leak; skipping the third makes page two repeat rows from page one.
    """
    screen = bound.list
    rows = await bound.resource.rows(ctx, rows)
    for filter_ in screen.filters:
        raw = query.values.get(filter_.key)
        if raw is not None:
            rows = filter_.apply(rows, raw)
    if screen.joins:
        rows = rows.select_related(*screen.joins)
    if screen.prefetches:
        # Many-to-many cannot be joined into one row, so it is prefetched --
        # one extra query for the page rather than one per row.
        rows = rows.prefetch_related(*screen.prefetches)
    order = query.sort or screen.sort
    if order:
        rows = rows.order_by(*order.as_terms())
    return rows


# ------------------------------------------------------------------ the shell


async def shell(admin: Admin, ctx: typing.Any) -> dict[str, typing.Any]:
    """The props every page carries: who you are, where you can go, how it looks."""
    from warder.access import current_user

    user = current_user(ctx)
    allowed = {}
    for resource in admin.resources:
        allowed[resource.slug] = await resource.allows(ctx, "view")
    for page in admin.pages:
        allowed[page.key] = page.gate is None or await page.gate.allows(ctx)

    return {
        "site": {
            "title": admin.title,
            "brand": admin.brand,
            "logo": admin.logo,
            "prefix": admin.prefix,
            "footer": admin.footer,
            "wide": admin.theme.wide,
        },
        "nav": admin.navigation(allowed),
        "user": _user_props(user),
        "theme": {
            "style": admin.theme.style,
            "density": admin.theme.density,
            "dark": admin.theme.dark,
        },
        "slots": dict(admin.slots),
        "flash": _flash(ctx),
    }


def _user_props(user: typing.Any) -> dict[str, typing.Any] | None:
    if user is None:
        return None
    label = (
        getattr(user, "name", None)
        or getattr(user, "username", None)
        or getattr(user, "email", None)
        or str(user)
    )
    return {
        "id": jsonable(getattr(user, "pk", getattr(user, "id", None))),
        "label": str(label),
        "email": getattr(user, "email", None),
        "superuser": bool(getattr(user, "is_superuser", False)),
    }


def _flash(ctx: typing.Any) -> list[dict[str, str]]:
    """Messages left in the session by the last request, read once.

    Popped rather than read: a flash that survives a refresh is a flash that
    tells you your row saved every time you look at the page.
    """
    try:
        session = ctx.session
    except (AttributeError, ValueError, LookupError, AssertionError):
        # An admin mounted on an application with no session middleware still
        # renders; it just cannot carry a message across a redirect.
        return []
    try:
        messages = session.pop("_warder_flash", None)
    except (AttributeError, TypeError):  # pragma: no cover - exotic session
        return []
    return list(messages or [])


# ------------------------------------------------------------------ the list


async def list_page(
    admin: Admin,
    bound: Bound,
    ctx: typing.Any,
    rows: typing.Sequence[typing.Any],
    query: Query,
    *,
    total: int,
) -> dict[str, typing.Any]:
    """Everything the list screen draws."""
    screen = bound.list
    resource = bound.resource
    columns = await visible(ctx, screen.columns)
    links = links_for(admin)
    may = {
        action: await resource.allows(ctx, action)
        for action in ("add", "change", "delete")
    }
    return {
        "resource": _resource_props(admin, bound),
        "columns": [column_props(column) for column in columns],
        "rows": [_row_props(admin, bound, row, columns, links) for row in rows],
        "filters": [filter_props(filter_) for filter_ in screen.filters],
        "actions": [
            action_props(action)
            for action in screen.actions
            if await _action_allowed(ctx, resource, action, may)
        ],
        "rowActions": [
            action_props(action)
            for action in screen.row_actions
            if await _action_allowed(ctx, resource, action, may)
        ],
        "query": query.as_props(),
        "total": total,
        "pages": max(1, -(-total // query.per_page)),
        "perPageOptions": list(screen.per_page_options),
        "selectable": screen.selectable and any(may.values()),
        "density": screen.density or admin.theme.density,
        "stickyHeader": screen.sticky_header,
        "totals": dict(screen.totals),
        "empty": _empty_props(screen),
        "can": may,
        "export": screen.export,
        "description": screen.description,
    }


def _resource_props(admin: Admin, bound: Bound) -> dict[str, typing.Any]:
    resource = bound.resource
    return {
        "slug": resource.slug,
        "label": resource.label,
        "plural": resource.plural,
        "icon": resource.icon,
        "group": resource.group,
        "href": resource.route(admin.prefix),
        "description": resource.description,
        "pk": bound.schema.pk,
    }


def _row_props(
    admin: Admin,
    bound: Bound,
    row: typing.Any,
    columns: typing.Sequence[Column],
    links: typing.Mapping[type, str],
) -> dict[str, typing.Any]:
    key = jsonable(getattr(row, bound.schema.pk, None))
    cells = {
        column.key: cell(row, column, schema=bound.schema, links=links)
        for column in columns
    }
    return {
        "id": key,
        "href": f"{bound.resource.route(admin.prefix)}/{key}",
        "label": str(row),
        "cells": cells,
    }


def cell(
    row: typing.Any,
    column: Column,
    *,
    schema: Schema | None = None,
    links: typing.Mapping[type, str] | None = None,
) -> typing.Any:
    """The value of one cell, extracted but not formatted.

    Formatting is the renderer's job: it knows the viewer's locale and how wide
    the column is, and the server knows neither.

    A relation carries an ``href`` when the far model is registered, so the
    author on a post is a link to that author rather than a dead name. A
    many-to-many carries a list of them. Both are computed here because only
    the server knows what is registered and who may see it.
    """
    if column.derive is not None:
        return jsonable(column.derive(row))

    described = schema.get(column.name) if schema and column.name else None
    if described is not None and described.kind == "m2m":
        return _many(row, column, described, links)

    value: typing.Any = row
    for part in column.traversal:
        if value is None:
            return None
        value = getattr(value, part, None)

    if value is None:
        return None
    if column.display is not None or _is_row(value):
        return _reference(value, column.display, links)
    return jsonable(value)


def _many(
    row: typing.Any,
    column: Column,
    described: typing.Any,
    links: typing.Mapping[type, str] | None,
) -> list[dict[str, typing.Any]] | None:
    """Every row on the far side of a many-to-many, as references.

    ``None`` rather than an empty list when the relation was not prefetched:
    "we did not load this" and "there are none" are different answers, and
    showing the second for the first is how a column quietly lies.
    """
    manager = getattr(row, typing.cast(str, column.name), None)
    if manager is None or not getattr(manager, "_fetched", False):
        return None
    return [_reference(item, column.display, links) for item in manager]


def _reference(
    value: typing.Any, display: str | None, links: typing.Mapping[type, str] | None
) -> dict[str, typing.Any]:
    """One related row: what to call it, and where to click through to."""
    label = getattr(value, display, None) if display else None
    key = jsonable(getattr(value, "pk", None))
    base = (links or {}).get(type(value))
    return {
        "id": key,
        "label": jsonable(label) if label is not None else str(value),
        "href": f"{base}/{key}" if base and key is not None else None,
    }


def _is_row(value: typing.Any) -> bool:
    """Whether *value* is a model instance rather than a plain column value."""
    return hasattr(value, "_meta") and hasattr(value, "pk")


def links_for(admin: Admin) -> dict[type, str]:
    """Where each registered model's detail pages live.

    Built once per page rather than per cell: a hundred rows with three
    relation columns each would otherwise walk the registry three hundred
    times to answer the same question.
    """
    return {
        resource.model: resource.route(admin.prefix) for resource in admin.resources
    }


def _empty_props(screen: List) -> dict[str, typing.Any]:
    empty = screen.empty
    if empty is None:
        return {"title": "Nothing here yet", "description": None, "icon": None}
    return {
        "title": empty.title,
        "description": empty.description,
        "icon": empty.icon,
        "action": action_props(empty.action) if empty.action else None,
    }


# ------------------------------------------------------- the form and detail


async def form_page(
    admin: Admin,
    bound: Bound,
    ctx: typing.Any,
    *,
    row: typing.Any = None,
    values: typing.Mapping[str, typing.Any] | None = None,
    errors: typing.Mapping[str, typing.Any] | None = None,
) -> dict[str, typing.Any]:
    """The add and edit screen, with whatever the last submission got wrong."""
    form = bound.form
    action = "change" if row is not None else "add"
    sections = [await _section_props(ctx, section, row) for section in form.sections]
    sidebar = [await _section_props(ctx, section, row) for section in form.sidebar]
    present = dict(values) if values is not None else _values(bound, form, row)
    return {
        "resource": _resource_props(admin, bound),
        "sections": [section for section in sections if section["fields"]],
        "sidebar": [section for section in sidebar if section["fields"]],
        "values": {name: jsonable(value) for name, value in present.items()},
        "errors": dict(errors or {}),
        "submit": form.submit,
        "layout": form.layout,
        "width": form.width,
        "cancel": form.cancel,
        "mode": action,
        "id": jsonable(getattr(row, bound.schema.pk, None))
        if row is not None
        else None,
        "label": str(row) if row is not None else None,
        "can": {
            "delete": form.deletable
            and row is not None
            and await bound.resource.allows(ctx, "delete", row)
        },
        "description": form.description,
    }


def _values(bound: Bound, form: Form, row: typing.Any) -> dict[str, typing.Any]:
    """The form's starting values: the row's, or the declared defaults."""
    from warder.fields import Field as FieldValue

    values: dict[str, typing.Any] = {}
    for field in form.fields:
        if field.widget is not None and field.widget.kind == "password":
            # Never sent back. An empty box on an edit form means "leave the
            # stored hash alone", which is the only behaviour that is usable.
            values[field.name] = None
            continue
        if row is None:
            if field.default is not FieldValue.UNSET:
                values[field.name] = field.default
                continue
            described = bound.schema.get(field.name)
            default = described.default if described else None
            values[field.name] = default() if callable(default) else default
            continue
        described = bound.schema.get(field.name)
        if described is not None and described.kind == "m2m":
            manager = getattr(row, field.name, None)
            values[field.name] = (
                [jsonable(getattr(item, "pk", None)) for item in manager]
                if manager is not None and getattr(manager, "_fetched", False)
                else []
            )
            continue
        current = getattr(row, field.name, None)
        if described is not None and described.kind == "relation":
            current = getattr(row, f"{described.column}", None)
        values[field.name] = current
    return values


async def _section_props(
    ctx: typing.Any, section: typing.Any, row: typing.Any
) -> dict[str, typing.Any]:
    fields = await visible(ctx, section.fields, row=row)
    return {
        "key": section.key,
        "title": section.title,
        "description": section.description,
        "collapsed": section.collapsed,
        "columns": section.columns,
        "icon": section.icon,
        "show": _condition_props(section.show),
        "fields": [await field_props(ctx, field, row) for field in fields],
    }


async def detail_page(
    admin: Admin, bound: Bound, ctx: typing.Any, row: typing.Any
) -> dict[str, typing.Any]:
    """One row, in full."""
    detail = bound.detail
    resource = bound.resource
    title = detail.title(row) if callable(detail.title) else (detail.title or str(row))
    subtitle = detail.subtitle(row) if callable(detail.subtitle) else detail.subtitle
    panels = [
        await _panel_props(admin, bound, ctx, panel, row) for panel in detail.panels
    ]
    return {
        "resource": _resource_props(admin, bound),
        "id": jsonable(getattr(row, bound.schema.pk, None)),
        "title": str(title),
        "subtitle": subtitle,
        "layout": detail.layout,
        "panels": [panel for panel in panels if panel is not None],
        "actions": [
            action_props(action)
            for action in detail.actions
            if await action.allowed(ctx, row)
        ],
        "can": {
            "change": await resource.allows(ctx, "change", row),
            "delete": await resource.allows(ctx, "delete", row),
        },
    }


async def _panel_props(
    admin: Admin, bound: Bound, ctx: typing.Any, panel: Panel, row: typing.Any
) -> dict[str, typing.Any] | None:
    """One panel, with the data it draws.

    A panel that this person may not view is dropped entirely rather than
    returned empty — the same rule as a column, for the same reason.
    """
    if panel.access is not None and not await panel.access.allows(ctx, "view", row):
        return None

    target = panel.target
    props: dict[str, typing.Any] = {
        "key": panel.key,
        "kind": panel.kind,
        "title": panel.title,
        "span": panel.span,
        "icon": panel.icon,
        "component": target if isinstance(target, str) else None,
        "options": {
            name: jsonable(value)
            for name, value in panel.options.items()
            if not callable(value)
        },
    }

    if panel.kind == "fields":
        props["options"].update(await _field_panel(admin, ctx, bound, panel, row))
    elif panel.kind in ("inline", "related"):
        props["options"].update(await _rows_panel(admin, bound, panel, row))
    elif panel.kind == "text":
        body = panel.target(row) if callable(panel.target) else ""
        props["options"]["body"] = str(body)
    elif panel.kind == "custom" and callable(panel.option("props")):
        built = await awaited(panel.option("props")(ctx, row))
        props["options"]["props"] = jsonable(built)

    return props


async def _field_panel(
    admin: Admin, ctx: typing.Any, bound: Bound, panel: Panel, row: typing.Any
) -> dict[str, typing.Any]:
    """The values a ``Panel.fields`` shows, after per-field access.

    Relations come through as references, so the author on a post's detail page
    is a link to that author — which is the whole point of having both screens.
    """
    from warder.columns import Column as ColumnValue

    links = links_for(admin)
    names: list[str] = []
    values: dict[str, typing.Any] = {}
    formats: dict[str, typing.Any] = {}
    for entry in panel.target:
        column = entry if isinstance(entry, ColumnValue) else ColumnValue(entry)
        if column.access is not None and not await column.access.allows(
            ctx, "view", row
        ):
            continue
        described = bound.schema.get(column.name) if column.name else None
        if described is not None:
            # A detail page formats a value the way the list does. Without
            # this, a status is raw text beside the same status drawn as a
            # badge one click away, and a date reads "2010-01-01".
            from warder.resolve import display_for, format_for

            changes: dict[str, typing.Any] = {}
            if described.relational and not column.display:
                changes["display"] = display_for(described.related)
                changes["related"] = True
                changes["multiple"] = described.kind == "m2m"
            if column.format is None and not described.relational:
                changes["format"] = format_for(described)
            if changes:
                column = column.with_(**changes)
        names.append(column.key)
        values[column.key] = cell(row, column, schema=bound.schema, links=links)
        formats[column.key] = format_props(column)
    return {"names": names, "values": values, "formats": formats}


async def _rows_panel(
    admin: Admin, bound: Bound, panel: Panel, row: typing.Any
) -> dict[str, typing.Any]:
    """The child rows an inline or related panel shows, as a real table.

    Not a list of labels. When the child model is registered, its own list
    columns are reused — so "Comments" on a post looks like the Comments screen
    looks, formats money the same way, and needed no second declaration.

    Capped at the declared limit with a link to the full filtered list, because
    a customer with nine hundred orders should not render nine hundred rows on
    their profile.
    """
    model = panel.target
    via = panel.option("via") or _back_reference(bound, model)
    if via is None:
        return {"rows": [], "columns": []}

    key = getattr(row, bound.schema.pk, None)
    limit = int(panel.option("limit", 10) or 10)
    child = admin.resource_for(model)
    columns = _panel_columns(panel, child, model, via)

    rows = typing.cast(typing.Any, model).filter(**{via: key})
    joins = tuple(path for path in (column.relation_path for column in columns) if path)
    if joins:
        rows = rows.select_related(*dict.fromkeys(joins))
    sort = panel.option("sort") or (child.sort if child is not None else None)
    if sort is not None:
        rows = rows.order_by(*sort.as_terms())

    found = await rows.limit(limit + 1)
    more = len(found) > limit
    found = found[:limit]

    base = child.route(admin.prefix) if child is not None else None
    total = await typing.cast(typing.Any, model).filter(**{via: key}).count()
    return {
        "columns": [column_props(column) for column in columns],
        "rows": [
            {
                "id": jsonable(getattr(item, "pk", None)),
                "label": str(item),
                "href": f"{base}/{jsonable(getattr(item, 'pk', None))}"
                if base
                else None,
                "cells": {column.key: cell(item, column) for column in columns},
            }
            for item in found
        ],
        "href": _panel_link(base, child, via, key),
        "total": total,
        "more": more,
    }


def _panel_link(
    base: str | None, child: typing.Any, via: str, key: typing.Any
) -> str | None:
    """Where "View all" goes.

    Pre-filtered only when the child's list actually has a filter keyed on the
    relation — otherwise the query string does nothing and the link quietly
    shows every row, which reads as a bug in the filter rather than a link that
    was never going to filter.
    """
    if base is None:
        return None
    keys = set(child.list.filter_map) if child is not None and child.list else set()
    for candidate in (via, f"{via}_id", via.removesuffix("_id")):
        if candidate in keys:
            return f"{base}?{candidate}={jsonable(key)}"
    return base


def _panel_columns(
    panel: Panel,
    child: typing.Any,
    model: typing.Any,
    via: str | None = None,
) -> tuple[Column, ...]:
    """What a child table shows: what the panel said, else the child's own list.

    Falling back to the registered resource is the point — a related panel
    inherits the formatting somebody already wrote for that model rather than
    restating it, and stays in step when they change it.
    """
    from warder.columns import Column as ColumnValue

    declared = panel.option("columns") or ()
    if declared:
        return tuple(
            entry if isinstance(entry, ColumnValue) else ColumnValue(entry)
            for entry in declared
        )
    if child is not None and child.list is not None:
        # Two or three columns; a panel is a window, not the screen itself.
        #
        # The column pointing back at the parent is dropped: every comment on
        # a post's panel has the same post, and a column of one repeated value
        # only takes up room.
        back = {via, f"{via}_id"} if via else set()
        return tuple(
            column
            for column in child.list.columns
            if not column.hidden and column.name not in back
        )[:3]
    schema = Schema.of(model)
    names = [
        field.name
        for field in schema.fields.values()
        if field.editable and field.kind in ("text", "slug", "enum", "integer")
    ][:2]
    return tuple(ColumnValue(name) for name in names) or (ColumnValue(schema.pk),)


def _back_reference(bound: Bound, model: typing.Any) -> str | None:
    """The one relation on *model* pointing back, when there is exactly one.

    A foreign key or a many-to-many: a class's subjects is a many-to-many and
    is exactly as much "the rows belonging to this one" as a post's comments
    are. Two candidates is refused at mount by :func:`warder.resolve.check`, so
    by the time a panel renders there is either one or none.
    """
    if not isinstance(model, type):
        return None
    return _one_relation_to(Schema.of(model), bound.model)


def _one_relation_to(far: Schema, parent: type) -> str | None:
    """The single relation on *far* pointing at *parent*, or ``None``."""
    candidates = relations_to(far, parent)
    return candidates[0] if len(candidates) == 1 else None


def relations_to(far: Schema, parent: type) -> list[str]:
    """Every relation on *far* that points at *parent*, forward or many."""
    return [
        field.name
        for field in far.fields.values()
        if field.kind in ("relation", "m2m") and field.related is parent
    ]


# ------------------------------------------------------------ the small parts


def column_props(column: Column) -> dict[str, typing.Any]:
    return {
        "key": column.key,
        "label": column.heading,
        "align": column.alignment,
        "width": column.width,
        "link": column.link,
        "sort": column.sort_field,
        "sortable": column.sortable,
        "format": format_props(column),
        "help": column.help,
        "wrap": column.wrap,
        "empty": column.empty,
        "sticky": column.sticky,
        "toggle": column.toggle,
        "relation": column.related,
        "multiple": column.multiple,
    }


def format_props(column: Column) -> dict[str, typing.Any]:
    fmt = column.format
    if fmt is None:
        return {"kind": "text", "options": {}}
    return {
        "kind": fmt.kind,
        "options": {
            name: jsonable(value)
            for name, value in fmt.options.items()
            if not callable(value)
        },
    }


def filter_props(filter_: Filter) -> dict[str, typing.Any]:
    return {
        "key": filter_.key,
        "kind": filter_.kind,
        "label": filter_.heading,
        "options": {
            name: jsonable(value)
            for name, value in filter_.options.items()
            if not callable(value)
        },
    }


def action_props(action: Action) -> dict[str, typing.Any]:
    return {
        "key": action.key,
        "label": action.label,
        "icon": action.icon,
        "style": action.style,
        "confirm": action.confirm,
        "selection": action.selection,
        "place": action.place,
        "description": action.description,
        "keyboard": action.keyboard,
        "fields": [_bare_field_props(field) for field in action.fields],
    }


async def field_props(
    ctx: typing.Any, field: Field, row: typing.Any = None
) -> dict[str, typing.Any]:
    """One input, with whether *this* person may write it."""
    writable = field.editable
    if writable and field.access is not None:
        writable = await field.access.allows(ctx, "change", row)
    props = _bare_field_props(field)
    props["editable"] = writable
    return props


def _bare_field_props(field: Field) -> dict[str, typing.Any]:
    widget = field.widget
    return {
        "name": field.name,
        "label": field.heading,
        "help": field.help,
        "placeholder": field.placeholder,
        "required": bool(field.required),
        "editable": field.editable,
        "hidden": field.hidden,
        "span": field.span,
        "unit": field.unit,
        "autofocus": field.autofocus,
        "show": _condition_props(field.show),
        "widget": {
            "kind": widget.kind if widget else "text",
            "options": {
                name: jsonable(value)
                for name, value in (widget.options.items() if widget else ())
                if not callable(value)
            },
        },
    }


def _condition_props(condition: typing.Any) -> dict[str, typing.Any] | None:
    if condition is None:
        return None
    return {
        "field": condition.field,
        "test": condition.test,
        "value": jsonable(condition.value),
        "conditions": [_condition_props(inner) for inner in condition.conditions],
    }


# ------------------------------------------------------------- authorisation


async def visible(
    ctx: typing.Any, items: typing.Sequence[typing.Any], *, row: typing.Any = None
) -> list[typing.Any]:
    """The columns or fields *ctx* may view.

    A value you may not see is dropped here, before serialisation, so it never
    leaves the process. Hiding it in the browser would put it in the props, in
    devtools, and in every proxy log between here and there.
    """
    allowed = []
    for item in items:
        access: Access | None = getattr(item, "access", None)
        if access is None or await access.allows(ctx, "view", row):
            allowed.append(item)
    return allowed


async def _action_allowed(
    ctx: typing.Any,
    resource: typing.Any,
    action: Action,
    may: typing.Mapping[str, bool],
) -> bool:
    """An action needs the resource's permission *and* its own.

    Its own can narrow and never widen: an action cannot grant what the
    resource withholds, or `Access(change=False)` would be advisory.
    """
    needed = "delete" if action.key == "delete" else "change"
    if not may.get(needed, False):
        return False
    return await action.allowed(ctx)


# ------------------------------------------------------------------- helpers


def _int(raw: typing.Any, fallback: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback


def _sort(raw: typing.Any, screen: List) -> Sort | None:
    """The ordering the URL asked for, if it names a column that can be sorted.

    An unsortable name is ignored rather than refused: a stale bookmark should
    show the list, not an error page.
    """
    if not raw:
        return None
    sortable = {column.sort_field for column in screen.columns if column.sort_field}
    terms = [term for term in str(raw).split(",") if term.lstrip("-+") in sortable]
    return Sort.by(*terms) if terms else None


def _all(params: typing.Any, key: str) -> list[str]:
    """Every value for *key*, however this query-params object spells that."""
    getter = getattr(params, "getlist", None) or getattr(params, "get_list", None)
    if getter is not None:
        return list(getter(key))
    value = params.get(key)  # pragma: no cover - single-value mappings
    return [value] if value is not None else []


def schema_of(model: type) -> Schema:
    """Convenience for callers that hold a model rather than a bound resource."""
    return Schema.of(model)
