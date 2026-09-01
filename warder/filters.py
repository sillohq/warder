"""``Filter`` — narrowing a list.

Every filter is the same thing wearing different clothes: a control in the
toolbar, a value in the query string, and a transformation of the queryset. It
declares its own control, parses its own value, and applies its own narrowing,
which is why ``Filter.custom`` is not a special case — it has the same three
parts as the built-in kinds and slots into the same pipeline::

    Filter.text("title")
    Filter.choice("status", ["draft", "live"])
    Filter.date_range("published_at", presets=["7d", "30d", "quarter"])
    Filter.toggle("Long reads", lambda rows: rows.filter(word_count__gte=2000))

The state of every filter lives in the URL. That is not an implementation
detail: a filtered list you cannot send to a colleague is a filtered list you
will rebuild by hand every morning.
"""

from __future__ import annotations

import datetime as dt
import typing

from warder._check import callable_, identifier, one_of
from warder.base import Declaration
from warder.naming import coerce_choices, slug

__all__ = ["Filter", "preset_range"]

#: Ranges you can name instead of picking two dates.
PRESETS = (
    "today",
    "yesterday",
    "7d",
    "30d",
    "90d",
    "quarter",
    "month",
    "last_month",
    "ytd",
    "12m",
    "all",
)


class Filter(Declaration):
    """One control in a list's toolbar."""

    __slots__ = ("kind", "label", "name", "narrow", "options")
    _fields = ("kind", "name", "label", "options", "narrow")

    KINDS = (
        "text",
        "search",
        "choice",
        "bool",
        "date_range",
        "number_range",
        "relation",
        "exists",
        "custom",
        "toggle",
    )

    def __init__(
        self,
        kind: str = "text",
        name: str | None = None,
        *,
        label: str | None = None,
        narrow: typing.Callable[..., typing.Any] | None = None,
        **options: typing.Any,
    ) -> None:
        one_of("Filter kind", kind, self.KINDS)
        if kind in ("custom", "toggle"):
            callable_(f"Filter.{kind}", narrow)
            if not label:
                raise TypeError(f"Filter.{kind} needs a label.")
        elif name is None:
            raise TypeError(f"Filter.{kind} needs a field name.")
        self._init(
            kind=kind,
            name=identifier("Filter name", name) if name is not None else None,
            label=label,
            options=options,
            narrow=narrow,
        )

    # ----------------------------------------------------------- constructors

    @classmethod
    def text(
        cls, name: str, *, lookup: str = "icontains", **options: typing.Any
    ) -> Filter:
        """A text box matching one field.

        ``icontains`` by default because that is what someone typing into a
        box means. ``lookup="istartswith"`` when the column is indexed and the
        table is large enough that a leading wildcard hurts.
        """
        return cls("text", name, lookup=lookup, **options)

    @classmethod
    def search(
        cls, *fields: str, label: str = "Search", **options: typing.Any
    ) -> Filter:
        """One box searching several fields at once, OR-ed together.

        The box at the top of the list. Distinct from ``Filter.text`` in that
        it spans columns and is rendered as the list's search rather than as a
        chip.
        """
        if not fields:
            raise TypeError("Filter.search needs at least one field.")
        for field in fields:
            identifier("Filter.search", field)
        return cls(
            "search",
            fields[0],
            label=label,
            fields=tuple(fields),
            lookup=options.pop("lookup", "icontains"),
            **options,
        )

    @classmethod
    def choice(
        cls,
        name: str,
        choices: typing.Iterable[typing.Any] = (),
        *,
        multiple: bool = False,
        **options: typing.Any,
    ) -> Filter:
        """A fixed set of values. Reads ``choices`` off the column when omitted."""
        return cls(
            "choice",
            name,
            choices=coerce_choices(choices),
            multiple=multiple,
            **options,
        )

    @classmethod
    def bool(
        cls,
        name: str,
        *,
        labels: tuple[str, str] = ("Yes", "No"),
        **options: typing.Any,
    ) -> Filter:
        """Yes, no, or unset — three states, because "no filter" is one of them."""
        return cls("bool", name, labels=tuple(labels), **options)

    @classmethod
    def date_range(
        cls,
        name: str,
        *,
        presets: typing.Sequence[str] = ("7d", "30d", "90d"),
        **options: typing.Any,
    ) -> Filter:
        """Two dates, with named shortcuts. See :data:`PRESETS`."""
        for preset in presets:
            one_of("preset", preset, PRESETS)
        return cls("date_range", name, presets=tuple(presets), **options)

    @classmethod
    def number_range(
        cls,
        name: str,
        *,
        min: float | None = None,
        max: float | None = None,
        step: float = 1,
        **options: typing.Any,
    ) -> Filter:
        return cls("number_range", name, min=min, max=max, step=step, **options)

    @classmethod
    def relation(
        cls,
        name: str,
        *,
        display: str | None = None,
        search: typing.Sequence[str] = (),
        multiple: bool = False,
        **options: typing.Any,
    ) -> Filter:
        """A picker over the related table, searched rather than preloaded."""
        return cls(
            "relation",
            name,
            display=display,
            search=tuple(search),
            multiple=multiple,
            **options,
        )

    @classmethod
    def exists(
        cls,
        name: str,
        *,
        labels: tuple[str, str] = ("Set", "Not set"),
        **options: typing.Any,
    ) -> Filter:
        """Whether a nullable column has a value."""
        return cls("exists", name, labels=tuple(labels), **options)

    @classmethod
    def toggle(
        cls,
        label: str,
        narrow: typing.Callable[[typing.Any], typing.Any],
        **options: typing.Any,
    ) -> Filter:
        """A chip that is on or off. *narrow* is called ``(rows)`` when on."""
        return cls("toggle", None, label=label, narrow=narrow, **options)

    @classmethod
    def custom(
        cls,
        label: str,
        narrow: typing.Callable[..., typing.Any],
        *,
        choices: typing.Iterable[typing.Any] = (),
        **options: typing.Any,
    ) -> Filter:
        """Anything else. *narrow* is called ``(rows, value)``.

        With *choices* it renders as a select; without, as a text box. The
        escape hatch has the same three parts as every built-in kind, so it is
        not a second code path.
        """
        return cls(
            "custom",
            None,
            label=label,
            narrow=narrow,
            choices=coerce_choices(choices),
            **options,
        )

    # -------------------------------------------------------------- questions

    @property
    def key(self) -> str:
        """The query-string parameter this filter reads."""
        if self.kind == "search":
            return "q"
        if self.name is not None:
            return self.name
        return slug(typing.cast(str, self.label))

    @property
    def heading(self) -> str:
        if self.label:
            return self.label
        name = typing.cast(str, self.name)
        last = name.split("__")[-1]
        if last.endswith("_id"):
            last = last[:-3]
        return last.replace("_", " ").capitalize()

    @property
    def fields(self) -> tuple[str, ...]:
        """Every field this filter reads — several, for a search box."""
        if self.kind == "search":
            return tuple(self.options.get("fields", ()))
        return (self.name,) if self.name else ()

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        return self.options.get(name, default)

    # ----------------------------------------------------------------- values

    def parse(self, raw: typing.Any) -> typing.Any:
        """The typed value for this filter, or ``None`` when it is not set.

        ``None`` means "this filter is off" and is never a value — a filter
        that could match ``NULL`` uses :meth:`exists` instead, so there is one
        answer to "is this filter doing anything".
        """
        if raw is None or raw == "" or raw == []:
            return None
        if self.kind == "bool":
            return _boolean(raw)
        if self.kind == "exists":
            return _boolean(raw)
        if self.kind == "toggle":
            return True if _boolean(raw) else None
        if self.kind == "number_range":
            return _pair(raw, float)
        if self.kind == "date_range":
            return raw if raw in PRESETS else _pair(raw, _date)
        if self.option("multiple"):
            return tuple(raw) if isinstance(raw, (list, tuple)) else (raw,)
        return raw

    def apply(
        self, rows: typing.Any, raw: typing.Any, *, now: dt.datetime | None = None
    ) -> typing.Any:
        """*rows*, narrowed by this filter's value. Unset leaves *rows* alone."""
        value = self.parse(raw)
        if value is None:
            return rows
        return self.narrow_with(rows, value, now=now)

    def narrow_with(
        self, rows: typing.Any, value: typing.Any, *, now: dt.datetime | None = None
    ) -> typing.Any:
        """The narrowing itself, given an already-parsed *value*."""
        kind, name = self.kind, self.name

        if kind == "toggle":
            return self.narrow(rows)
        if kind == "custom":
            return self.narrow(rows, value)

        if kind == "search":
            return _any_of(rows, self.fields, self.option("lookup", "icontains"), value)
        if kind == "text":
            return rows.filter(
                **{f"{name}__{self.option('lookup', 'icontains')}": value}
            )
        if kind == "bool":
            return rows.filter(**{name: value})
        if kind == "exists":
            return rows.filter(**{f"{name}__isnull": not value})
        if kind in ("choice", "relation"):
            if self.option("multiple"):
                return rows.filter(**{f"{name}__in": list(value)})
            return rows.filter(**{name: value})
        if kind == "number_range":
            return _between(rows, name, value)
        start, end = preset_range(value, now) if isinstance(value, str) else value
        return _between(rows, typing.cast(str, name), (start, end))

    def __repr__(self) -> str:
        head = repr(self.name) if self.name is not None else repr(self.label)
        return f"Filter.{self.kind}({head})"


# ------------------------------------------------------------------ helpers


def _boolean(raw: typing.Any) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "on", "t")


def _pair(
    raw: typing.Any, cast: typing.Callable[[str], typing.Any]
) -> tuple[typing.Any, typing.Any] | None:
    """``"10..50"`` or ``["10", "50"]`` → a two-tuple, either end possibly ``None``."""
    parts = raw.split("..") if isinstance(raw, str) else list(raw)
    if len(parts) != 2:
        return None
    low, high = (str(part).strip() for part in parts)
    bounds = (cast(low) if low else None, cast(high) if high else None)
    return None if bounds == (None, None) else bounds


def _date(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


def _between(
    rows: typing.Any, name: str, bounds: tuple[typing.Any, typing.Any]
) -> typing.Any:
    low, high = bounds
    if low is not None:
        rows = rows.filter(**{f"{name}__gte": low})
    if high is not None:
        rows = rows.filter(**{f"{name}__lte": high})
    return rows


def _any_of(
    rows: typing.Any, fields: typing.Sequence[str], lookup: str, value: typing.Any
) -> typing.Any:
    """OR the same term across several columns, using ``sillo.record``'s ``Q``.

    Imported here rather than at module scope: the declarations must be usable
    — and testable — without the ORM configured, and this is the one line in
    the file that needs it.
    """
    from tortoise.expressions import Q

    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__{lookup}": value})
    return rows.filter(query)


def preset_range(
    preset: str, now: dt.datetime | None = None
) -> tuple[dt.date | None, dt.date | None]:
    """The two dates a named preset stands for, inclusive at both ends.

    ``"all"`` is ``(None, None)`` rather than an error: it is how a preset
    control says "no range", and every caller already handles an open end.
    """
    today = (now or dt.datetime.now()).date()
    if preset == "all":
        return (None, None)
    if preset == "today":
        return (today, today)
    if preset == "yesterday":
        day = today - dt.timedelta(days=1)
        return (day, day)
    if preset in ("7d", "30d", "90d"):
        return (today - dt.timedelta(days=int(preset[:-1])), today)
    if preset == "12m":
        return (today.replace(year=today.year - 1), today)
    if preset == "month":
        return (today.replace(day=1), today)
    if preset == "last_month":
        first = today.replace(day=1)
        end = first - dt.timedelta(days=1)
        return (end.replace(day=1), end)
    if preset == "quarter":
        start_month = 3 * ((today.month - 1) // 3) + 1
        return (today.replace(month=start_month, day=1), today)
    if preset == "ytd":
        return (today.replace(month=1, day=1), today)
    raise ValueError(
        f"Unknown date preset {preset!r}. Use one of: {', '.join(PRESETS)}."
    )
