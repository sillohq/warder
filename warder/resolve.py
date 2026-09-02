"""Binding declarations to models: deriving what was left out, checking the rest.

Two jobs, and they are the same job seen from either end.

**Deriving.** ``Resource(Post)`` with no screens is a working admin: the list,
the form and the detail page are built from the model's own columns at mount.
That is the difference between an admin you can point at a new model in ten
seconds and one you configure before you can look at anything. Every derived
part is replaced by naming it, and nothing here fights a declaration that
exists.

**Checking.** Every field a declaration names is resolved against the model
once, at start-up. A misspelled column is a start-up failure with the line it
was written on, not an empty cell in production three weeks later.

The inference reads the **schema** — what the database says a column is — and
never an annotation. A ``TextField`` gets a textarea because the column is long
text, not because anything was spelled a particular way.
"""

from __future__ import annotations

import typing

from warder.columns import Column
from warder.errors import DeclarationError
from warder.fields import Field
from warder.filters import Filter
from warder.formats import Format
from warder.layout import Panel, Section
from warder.naming import label_for, plural_of
from warder.schema import ModelField, Schema
from warder.screens import Detail, Form, List
from warder.sorting import Sort
from warder.widgets import Widget

if typing.TYPE_CHECKING:
    from warder.resource import Resource

__all__ = [
    "Bound",
    "bind",
    "check",
    "derive_detail",
    "derive_form",
    "derive_list",
    "dress",
]

#: Names a related row is usually known by, best first. Consulted before
#: falling back to "the first text column", because a `Customer` picker
#: showing `address_line_1` is technically a string and practically useless.
DISPLAY_NAMES = (
    "name",
    "title",
    "label",
    "email",
    "username",
    "slug",
    "code",
    "reference",
    "number",
)

#: How many columns a derived list shows before it stops. Seven is about what
#: fits before a table starts scrolling sideways on a laptop, and a derived
#: list is a starting point rather than a finished screen.
LIST_WIDTH = 7

#: Kinds that are never worth a column of their own in a derived list.
_NOT_LISTED = frozenset({"password", "binary", "backward", "m2m", "longtext"})

#: Kinds a total can be taken over.
_SUMMABLE = frozenset({"integer", "decimal", "float"})


class Bound:
    """One resource, resolved against its model.

    Holds the three screens as they will actually be rendered — declared where
    they were declared, derived where they were not — so the route layer never
    has to ask "was this given or inferred".
    """

    __slots__ = ("resource", "schema", "list", "form", "detail")

    def __init__(
        self,
        resource: Resource,
        schema: Schema,
        list: List,
        form: Form,
        detail: Detail,
    ) -> None:
        self.resource = resource
        self.schema = schema
        self.list = list
        self.form = form
        self.detail = detail

    @property
    def model(self) -> type:
        return self.resource.model

    def __repr__(self) -> str:
        return f"Bound({self.resource.model.__name__})"


def bind(resource: Resource) -> Bound:
    """Resolve *resource*: derive what is missing, keep what is not."""
    schema = Schema.of(resource.model)
    declared = resource.list is not None
    screen = typing.cast(List, resource.list) if declared else derive_list(schema)

    # A derived list carries a *default* ordering and a *default* search box,
    # and `Resource(sort=..., search=...)` is how you say what those should be
    # without writing a whole `List`. So the resource wins over a derived
    # screen, and gives way to a declared one -- where the author has already
    # said it in the more specific place.
    if resource.sort is not None and (not declared or screen.sort is None):
        screen = screen.with_(sort=resource.sort)
    if resource.search and (not declared or screen.search is None):
        others = tuple(f for f in screen.filters if f.kind != "search")
        screen = screen.with_(filters=(Filter.search(*resource.search), *others))
    form = (
        dress(resource.form, schema)
        if resource.form is not None
        else derive_form(schema)
    )
    detail = (
        resource.detail if resource.detail is not None else derive_detail(schema, form)
    )
    return Bound(resource, schema, screen, form, detail)


# ---------------------------------------------------------------- derivation


def derive_list(schema: Schema) -> List:
    """A list built from *schema*: identity first, then state, then time."""
    columns: list[Column] = [Column(schema.pk, width=80, sort=schema.pk)]
    identifying: list[ModelField] = []
    stateful: list[ModelField] = []
    relations: list[ModelField] = []
    timestamps: list[ModelField] = []

    for field in schema.fields.values():
        if field.primary or field.shadow or field.kind in _NOT_LISTED:
            continue
        if field.name in ("deleted_at",):
            continue
        if field.kind == "relation":
            relations.append(field)
        elif field.choices or field.kind in ("boolean", "enum"):
            stateful.append(field)
        elif field.kind in ("datetime", "date"):
            timestamps.append(field)
        elif field.kind in ("text", "slug", "integer", "decimal", "float", "uuid"):
            identifying.append(field)

    chosen = [*identifying[:3], *stateful[:2], *relations[:1], *timestamps[:1]]
    for field in chosen[: LIST_WIDTH - 1]:
        columns.append(column_for(field))

    if len(columns) > 1:
        columns[1] = columns[1].with_(link=True)
        columns[0] = columns[0].with_(format=Format.text(mono=True))
    else:
        columns[0] = columns[0].with_(link=True)

    return List(
        *columns,
        filters=derive_filters(schema),
        sort=_default_sort(schema),
        totals=None,
    )


def derive_filters(schema: Schema) -> tuple[Filter, ...]:
    """A search box over the text columns, a chip per state, a date range."""
    filters: list[Filter] = []
    searchable = [
        f.name
        for f in schema.fields.values()
        if f.kind in ("text", "slug") and not f.shadow and not f.managed
    ][:3]
    if searchable:
        filters.append(Filter.search(*searchable))
    for field in schema.fields.values():
        if len(filters) >= 5:
            break
        if field.shadow or field.managed:
            continue
        if field.choices:
            filters.append(Filter.choice(field.name, field.choices))
        elif field.kind == "boolean":
            filters.append(Filter.boolean(field.name))
    for field in schema.fields.values():
        if field.kind == "datetime" and field.name not in MANAGED_ORDER:
            filters.append(Filter.date_range(field.name))
            break
    return tuple(filters)


def dress(form: Form, schema: Schema) -> Form:
    """Fill in what a declared form left unsaid.

    "Most fields say nothing but their name" has to hold for a form you wrote
    as well as one that was derived, or ``Field("published_at")`` inside a
    ``Section`` would render as a text box while the same field on a derived
    form got a date picker — the same declaration behaving differently
    depending on how much of the screen you spelled out.

    Only the unset is filled: a named widget always wins, and so does an
    explicit ``required=``.
    """
    sections = tuple(_dressed(section, schema) for section in form.sections)
    sidebar = tuple(_dressed(section, schema) for section in form.sidebar)
    return Form(
        *sections,
        submit=form.submit,
        layout=form.layout,
        sidebar=sidebar,
        on_save=form.on_save,
        validate=form.validate,
        deletable=form.deletable,
        cancel=form.cancel,
        description=form.description,
        width=form.width,
    )


def _dressed(section: Section, schema: Schema) -> Section:
    return Section(
        section.title,
        *(_dressed_field(field, schema) for field in section.fields),
        description=section.description,
        collapsed=section.collapsed,
        columns=section.columns,
        show=section.show,
        access=section.access,
        icon=section.icon,
    )


def _dressed_field(field: Field, schema: Schema) -> Field:
    described = schema.resolve(field.name)
    if described is None:
        # A field naming nothing is `check`'s problem, not this one's. Leaving
        # it alone keeps the error about the reference rather than about a
        # widget nobody asked for.
        return field
    changes: dict[str, typing.Any] = {}
    if field.widget is None:
        changes["widget"] = widget_for(described)
    if field.required is None:
        changes["required"] = described.required and not described.has_default
    if field.help is None and described.description:
        changes["help"] = described.description
    return field.with_(**changes) if changes else field


def derive_form(schema: Schema) -> Form:
    """Every writable column, with the timestamps in a collapsed group."""
    fields = [field_for(f) for f in schema.editable]
    audit = [
        Field.readonly(name)
        for name in MANAGED_ORDER
        if schema.has(name) and name != "deleted_at"
    ]
    sections: list[Section] = [Section("", *fields)] if fields else []
    if audit:
        sections.append(Section("Audit", *audit, collapsed=True))
    return Form(*sections)


def derive_detail(schema: Schema, form: Form) -> Detail:
    """The form's fields as a panel, plus a window onto each child table."""
    panels: list[Panel] = []
    names = [f.name for f in form.fields]
    if names:
        panels.append(Panel.fields("Overview", *names))
    for field in schema.fields.values():
        if field.kind != "backward" or field.related is None:
            continue
        if len(panels) > 4:
            break
        panels.append(
            Panel.related(
                plural_of(label_for(field.related)),
                field.related,
                limit=10,
                sort=_default_sort(Schema.of(field.related)),
            )
        )
    return Detail(*panels)


#: The base model's own timestamps, in the order a form should show them.
MANAGED_ORDER = ("created_at", "updated_at", "deleted_at")


def column_for(field: ModelField) -> Column:
    """The column a schema field wants to be."""
    if field.kind == "relation":
        return Column.relation(
            field.name, display=display_for(field.related), link=True
        )
    return Column(field.name, format=format_for(field))


def field_for(field: ModelField) -> Field:
    """The input a schema field wants to be."""
    return Field(
        field.name,
        widget=widget_for(field),
        help=field.description,
        required=field.required and not field.has_default,
    )


def format_for(field: ModelField) -> Format | None:
    """How a schema field's values are drawn, or ``None`` for plain text."""
    if field.choices:
        return Format.badge(labels=field.choices)
    if field.kind == "boolean":
        return Format.boolean()
    if field.kind == "datetime":
        return Format.date("relative" if field.name in MANAGED_ORDER else "datetime")
    if field.kind == "date":
        return Format.date("date")
    if field.kind == "time":
        return Format.date("time")
    if field.kind == "decimal":
        return Format.number(precision=2)
    if field.kind in ("integer", "float"):
        return Format.number()
    if field.kind == "json":
        return Format.json()
    if field.kind == "longtext":
        return Format.text(truncate=80)
    if field.kind in ("uuid", "binary"):
        return Format.text(mono=True)
    return None


def widget_for(field: ModelField) -> Widget:
    """How a schema field is edited.

    Read off the column, which *states* these things. Naming a widget is for
    when the default is wrong about the meaning rather than about the type:
    ``body`` and ``internal_note`` are both long text and only one wants
    Markdown.
    """
    if field.kind == "password":
        return Widget.password()
    if field.kind == "slug":
        return Widget.slug()
    if field.choices:
        return Widget.select(field.choices, clearable=field.null)
    if field.kind == "relation":
        return Widget.relation(display=display_for(field.related))
    if field.kind == "m2m":
        return Widget.relation(display=display_for(field.related), multiple=True)
    if field.kind == "boolean":
        return Widget.switch()
    if field.kind == "longtext":
        return Widget.textarea()
    if field.kind == "json":
        return Widget.json()
    if field.kind == "datetime":
        return Widget.datetime()
    if field.kind == "date":
        return Widget.date()
    if field.kind == "time":
        return Widget.time()
    if field.kind == "integer":
        return Widget.number()
    if field.kind in ("decimal", "float"):
        return Widget.number(step=0.01, precision=2)
    if field.kind in ("uuid", "binary"):
        return Widget.text(mono=True)
    # A CharField with no length, or a very long one, is prose in a short
    # field's clothing.
    if field.max_length is None or field.max_length > 255:
        return Widget.textarea(rows=3)
    return Widget.text()


def display_for(model: type | None) -> str | None:
    """What a related row should be called in a picker or a cell.

    Conventional names first, then the first unique text column, then the
    first text column at all. ``None`` when the far side is not resolved yet
    — the renderer falls back to ``str(row)``, which is what the model itself
    says it is called.
    """
    if model is None:
        return None
    schema = Schema.of(model)
    for name in DISPLAY_NAMES:
        candidate = schema.get(name)
        if candidate is not None and candidate.kind in ("text", "slug"):
            return name
    for field in schema.fields.values():
        if field.kind in ("text", "slug") and field.unique and not field.managed:
            return field.name
    for field in schema.fields.values():
        if field.kind in ("text", "slug") and not field.managed:
            return field.name
    return None


def _default_sort(schema: Schema) -> Sort:
    """Newest first when there is a timestamp, else the key descending.

    Never no ordering at all: an unordered page two can repeat a row from page
    one and skip another, which reads as data loss.
    """
    if schema.has("created_at"):
        return Sort.desc("created_at")
    return Sort.desc(schema.pk)


# ---------------------------------------------------------------- validation


def check(resource: Resource) -> list[DeclarationError]:
    """Everything wrong with *resource* that only the model can reveal.

    Returns rather than raises, so ``mount`` can decide whether to report the
    first problem or all of them, and so a test can assert on the list.

    A relation the ORM has not linked yet is skipped rather than reported. The
    admin has to be mountable before ``Tortoise.init`` in the applications that
    build their routes first, and "cannot check" is not "wrong".
    """
    schema = Schema.of(resource.model)
    problems: list[DeclarationError] = []
    where = resource.where
    name = resource.model.__name__

    for column in resource.list.columns if resource.list else ():
        problems.extend(_check_column(column, schema, name))
    if resource.list is not None:
        problems.extend(_check_list(resource.list, schema, name))

    for field in resource.form.fields if resource.form else ():
        problems.extend(_check_field(field, schema, name))

    for panel in resource.detail.panels if resource.detail else ():
        problems.extend(_check_panel(panel, schema, name))

    for searched in resource.search:
        if schema.resolve(searched) is None:
            problems.append(
                _missing(f"Resource({name}).search", searched, schema, where)
            )

    for term in resource.sort.terms if resource.sort else ():
        if schema.resolve(term.field) is None:
            problems.append(
                _missing(f"Resource({name}).sort", term.field, schema, where)
            )

    return problems


def _check_column(column: Column, schema: Schema, model: str) -> list[DeclarationError]:
    problems: list[DeclarationError] = []
    label = f"Resource({model}).list column {column.key!r}"

    if column.name is not None:
        target = schema.resolve(column.name)
        if target is None:
            # Named directly rather than through _missing: the label already
            # carries the reference, and "column 'titel' names 'titel'" is a
            # sentence nobody should have to read.
            problems.append(
                DeclarationError(
                    f"{label} is not a field of {schema.model.__name__}.",
                    where=column.where,
                    got=column.name.split("__")[0],
                    options=schema.names,
                )
            )
            return problems
        if column.related and not target.relational:
            problems.append(
                DeclarationError(
                    f"{label} is declared with Column.relation but {column.name!r} "
                    f"is a {target.kind} column, not a relation.",
                    hint="Use Column(...) for a plain column.",
                    where=column.where,
                )
            )
        if column.display and target.related is not None:
            far = Schema.of(target.related)
            if not far.has(column.display):
                problems.append(
                    DeclarationError(
                        f"{label} displays {column.display!r}, which is not a field "
                        f"of {target.related.__name__}.",
                        where=column.where,
                        got=column.display,
                        options=far.names,
                    )
                )

    # Only an explicit `sort="..."` can be wrong. A computed column with no
    # sort is not an error: `Column.sort_field` already answers None for it, so
    # the header is simply not clickable — which is honest, because there is
    # nothing for the database to order by.
    if isinstance(column.sort, str) and schema.resolve(column.sort) is None:
        problems.append(
            DeclarationError(
                f"{label} sorts by {column.sort!r}, which is not a field of {model}.",
                where=column.where,
                got=column.sort,
                options=schema.names,
            )
        )
    return problems


def _check_list(screen: List, schema: Schema, model: str) -> list[DeclarationError]:
    problems: list[DeclarationError] = []
    label = f"Resource({model}).list"

    for filter_ in screen.filters:
        for field in filter_.fields:
            if schema.resolve(field) is None:
                problems.append(
                    _missing(
                        f"{label} filter {filter_.key!r}", field, schema, filter_.where
                    )
                )

    for name in (*screen.select_related, *screen.prefetch_related):
        target = schema.resolve(name)
        if target is None:
            problems.append(
                _missing(f"{label} select_related", name, schema, screen.where)
            )
        elif not target.relational:
            problems.append(
                DeclarationError(
                    f"{label} joins {name!r}, which is a {target.kind} column, "
                    "not a relation.",
                    where=screen.where,
                )
            )

    columns = screen.column_map
    for key, how in screen.totals.items():
        column = columns.get(key)
        target = schema.resolve(column.name) if column and column.name else None
        if target is not None and how != "count" and target.kind not in _SUMMABLE:
            problems.append(
                DeclarationError(
                    f"{label} takes the {how} of {key!r}, which is a "
                    f"{target.kind} column.",
                    hint="Only integer, decimal and float columns can be summed.",
                    where=screen.where,
                )
            )

    if screen.group_by and schema.resolve(screen.group_by) is None:
        problems.append(
            _missing(f"{label} group_by", screen.group_by, schema, screen.where)
        )

    for term in screen.sort.terms if screen.sort else ():
        if schema.resolve(term.field) is None:
            problems.append(_missing(f"{label} sort", term.field, schema, screen.where))

    return problems


def _check_field(field: Field, schema: Schema, model: str) -> list[DeclarationError]:
    label = f"Resource({model}).form field {field.name!r}"
    target = schema.resolve(field.name)
    if target is None:
        return [
            DeclarationError(
                f"{label} is not a field of {schema.model.__name__}.",
                where=field.where,
                got=field.name.split("__")[0],
                options=schema.names,
            )
        ]
    if target.kind == "backward":
        return [
            DeclarationError(
                f"{label} is a reverse relation, which a form cannot write.",
                hint="Use Panel.inline on the detail page instead.",
                where=field.where,
            )
        ]
    if not field.editable and not target.writable_when_blank and not field.has_default:
        # The form would render, submit, and fail at the database with a NOT
        # NULL violation that names a column the user was never shown.
        return [
            DeclarationError(
                f"{label} is readonly, but {field.name!r} is required and has no "
                "default — a new row could never be saved.",
                hint="Give the field a default=, or make it editable.",
                where=field.where,
            )
        ]
    return []


def _check_panel(panel: Panel, schema: Schema, model: str) -> list[DeclarationError]:
    label = f"Resource({model}).detail panel {panel.title!r}"

    if panel.kind == "fields":
        problems = []
        for entry in panel.target:
            # Panel.fields takes names or whole Columns, so a detail page can
            # reuse the list's formatting rather than restate it.
            reference = entry if isinstance(entry, str) else entry.name
            if reference is not None and schema.resolve(reference) is None:
                problems.append(_missing(label, reference, schema, panel.where))
        return problems

    if panel.kind not in ("inline", "related"):
        return []
    child = panel.target
    if not isinstance(child, type) or getattr(child, "_meta", None) is None:
        return [
            DeclarationError(
                f"{label} takes a model class, got {child!r}.", where=panel.where
            )
        ]

    far = Schema.of(child)
    via = panel.option("via")
    if via is not None:
        target = far.get(via)
        if target is None:
            return [_missing(f"{label} via", via, far, panel.where)]
        return []

    candidates = [
        f.name
        for f in far.fields.values()
        if f.kind == "relation" and f.related is schema.model
    ]
    if len(candidates) > 1:
        # Picking the first of `author` and `editor` would be wrong half the
        # time and silent both halves.
        return [
            DeclarationError(
                f"{label} could reach {model} through {len(candidates)} foreign keys "
                f"on {child.__name__}: {', '.join(sorted(candidates))}.",
                hint="Pass via= to say which one.",
                where=panel.where,
            )
        ]
    if not candidates and any(f.kind == "relation" for f in far.fields.values()):
        return [
            DeclarationError(
                f"{label} has no foreign key from {child.__name__} back to {model}.",
                where=panel.where,
            )
        ]
    return []


def _missing(
    label: str, name: str, schema: Schema, where: str | None
) -> DeclarationError:
    """The message every reference failure shares."""
    return DeclarationError(
        f"{label} names {name!r}, which is not a field of {schema.model.__name__}.",
        where=where,
        got=name.split("__")[0],
        options=schema.names,
    )
