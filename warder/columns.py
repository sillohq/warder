"""``Column`` — one cell of a list.

A column names a value and says how to draw it. There is one class; the
classmethods are shorthands that fill in a :class:`~warder.formats.Format`::

    Column("title", link=True)
    Column.badge("status", colors={"live": "green", "draft": "zinc"})
    Column.relation("author", display="email")
    Column.compute("Words", lambda row: len(row.body.split()), sort="word_count")

Three things about it are deliberate.

**A computed column can be sorted.** ``sort=`` names the database column that
stands in for the computed value. A computed column that cannot be sorted is a
column people stop using, so the escape hatch is part of the constructor rather
than a thing you discover you cannot do.

**Declaring a relation column is what removes the N+1.** ``Column.relation`` and
any ``"author__email"`` traversal contribute their relation to the list's
``select_related``. The alternative — a separate ``select_related`` attribute
you must keep in step with your columns — is a list that silently falls out of
step and costs fifty queries a page.

**A column you may not view is not sent.** ``access=`` is applied server-side
and an unviewable column is absent from the props, not hidden in CSS.
"""

from __future__ import annotations

import typing

from warder._check import callable_, identifier, one_of, positive
from warder.access import Access
from warder.base import Declaration
from warder.formats import Format
from warder.naming import slug

__all__ = ["Column"]

_ALIGNMENTS = ("left", "center", "right")


class Column(Declaration):
    """One column of a list or one row of a detail panel."""

    __slots__ = (
        "name", "label", "format", "link", "sort", "align", "width",
        "access", "help", "derive", "display", "hidden", "wrap",
        "empty", "sticky", "toggle",
    )
    _fields = __slots__

    def __init__(
        self,
        name: str | None = None,
        *,
        label: str | None = None,
        format: Format | None = None,
        link: bool = False,
        sort: str | bool | None = None,
        align: str | None = None,
        width: int | str | None = None,
        access: Access | None = None,
        help: str | None = None,
        derive: typing.Callable[[typing.Any], typing.Any] | None = None,
        display: str | None = None,
        hidden: bool = False,
        wrap: bool = False,
        empty: str = "—",
        sticky: bool = False,
        toggle: bool = True,
    ) -> None:
        if derive is None and name is None:
            raise TypeError(
                "Column needs a field name, or a derive= callable with a label."
            )
        if derive is not None:
            callable_("Column derive", derive)
            if not label:
                raise TypeError(
                    "A computed column needs a label — "
                    "Column.compute('Words', lambda row: ...)."
                )
        self._init(
            name=identifier("Column name", name) if name is not None else None,
            label=label,
            format=format,
            link=link,
            sort=identifier("Column sort", sort) if isinstance(sort, str) else sort,
            align=one_of("align", align, _ALIGNMENTS) if align else None,
            width=positive("Column width", width) if isinstance(width, int) else width,
            access=access,
            help=help,
            derive=derive,
            display=identifier("Column display", display) if display else None,
            hidden=hidden,
            wrap=wrap,
            empty=empty,
            sticky=sticky,
            toggle=toggle,
        )

    # ------------------------------------------------------------ shorthands

    @classmethod
    def text(cls, name: str, **options: typing.Any) -> Column:
        """Plain text. ``truncate=`` and ``mono=`` reach the format."""
        return cls(name, format=Format.text(
            truncate=options.pop("truncate", None), mono=options.pop("mono", False)
        ), **options)

    @classmethod
    def code(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.code(language=options.pop("language", None)), **options)

    @classmethod
    def number(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.number(
            precision=options.pop("precision", 0),
            prefix=options.pop("prefix", ""),
            suffix=options.pop("suffix", ""),
            grouping=options.pop("grouping", True),
        ), **options)

    @classmethod
    def money(cls, name: str, currency: str = "USD", **options: typing.Any) -> Column:
        return cls(name, format=Format.money(
            currency, precision=options.pop("precision", 2)
        ), **options)

    @classmethod
    def percent(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.percent(
            precision=options.pop("precision", 0), of=options.pop("of", 1.0)
        ), **options)

    @classmethod
    def bytes(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.bytes(binary=options.pop("binary", True)), **options)

    @classmethod
    def duration(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.duration(
            unit=options.pop("unit", "seconds"), style=options.pop("style", "short")
        ), **options)

    @classmethod
    def date(cls, name: str, style: str = "date", **options: typing.Any) -> Column:
        """A moment. ``Column.date("created_at", "relative")`` is the common one."""
        return cls(name, format=Format.date(
            style, pattern=options.pop("pattern", None),
            tooltip=options.pop("tooltip", True),
        ), **options)

    @classmethod
    def bool(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.bool(
            labels=options.pop("labels", ("Yes", "No")),
            style=options.pop("style", "icon"),
        ), **options)

    @classmethod
    def badge(
        cls,
        name: str,
        colors: typing.Mapping[typing.Any, str] | None = None,
        **options: typing.Any,
    ) -> Column:
        """A coloured pill. The right shape for a small closed set of states."""
        return cls(name, format=Format.badge(
            colors, labels=options.pop("labels", None),
            default=options.pop("default", "zinc"),
        ), **options)

    @classmethod
    def tags(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.tags(
            color=options.pop("color", "zinc"), limit=options.pop("limit", 3)
        ), **options)

    @classmethod
    def image(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.image(
            size=options.pop("size", 32), rounded=options.pop("rounded", "md")
        ), sort=options.pop("sort", False), **options)

    @classmethod
    def avatar(cls, name: str, **options: typing.Any) -> Column:
        """A picture and a name — what a user column usually wants to be."""
        return cls(name, format=Format.avatar(
            size=options.pop("size", 24), fallback=options.pop("fallback", "initials")
        ), **options)

    @classmethod
    def json(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.json(collapsed=options.pop("collapsed", True)),
                   sort=options.pop("sort", False), **options)

    @classmethod
    def progress(cls, name: str, **options: typing.Any) -> Column:
        return cls(name, format=Format.progress(
            max=options.pop("max", 100.0), colors=options.pop("colors", None)
        ), **options)

    @classmethod
    def relation(
        cls,
        name: str,
        *,
        display: str | None = None,
        link: bool = False,
        **options: typing.Any,
    ) -> Column:
        """A foreign key, drawn as the *display* attribute of the far row.

        ``link=True`` links to that row's own admin page, not to this one's,
        which is the thing you almost always want and the thing a plain
        ``Column("author")`` cannot express.
        """
        return cls(name, display=display, link=link,
                   format=options.pop("format", None), **options)

    @classmethod
    def compute(
        cls,
        label: str,
        value: typing.Callable[[typing.Any], typing.Any],
        **options: typing.Any,
    ) -> Column:
        """A value derived in Python — ``(row) -> anything``.

        Pass ``sort="word_count"`` to name the database column that orders it.
        Without one the header is not clickable, which is honest: there is
        nothing the database can order by.
        """
        return cls(None, label=label, derive=value,
                   sort=options.pop("sort", False), **options)

    @classmethod
    def url(cls, label: str, to: typing.Callable[[typing.Any], str],
             *, text: str | typing.Callable[[typing.Any], str] = "Open",
             external: bool = False, **options: typing.Any) -> Column:
        """A link built from the row — an invoice PDF, an upstream dashboard."""
        resolve = text if callable(text) else (lambda row: text)
        return cls(None, label=label, derive=resolve, sort=False,
                   format=Format.link(to=to, external=external), **options)

    # ------------------------------------------------------------- questions

    @property
    def key(self) -> str:
        """The stable identifier used in props, query strings and preferences."""
        if self.name is not None:
            return self.name
        return slug(typing.cast(str, self.label))

    @property
    def heading(self) -> str:
        """The text in the header cell."""
        if self.label:
            return self.label
        name = typing.cast(str, self.name)
        last = name.split("__")[-1]
        if last.endswith("_id"):
            last = last[:-3]
        return last.replace("_", " ").capitalize()

    @property
    def computed(self) -> bool:
        """Whether the value comes from Python rather than from a column."""
        return self.derive is not None

    @property
    def traversal(self) -> tuple[str, ...]:
        """``"author__email"`` → ``("author", "email")``; a plain name → one part."""
        return tuple(self.name.split("__")) if self.name else ()

    @property
    def relation_path(self) -> str | None:
        """The relation this column needs joined, or ``None``.

        Both spellings contribute: ``Column("author__email")`` through its
        traversal and ``Column.relation("author")`` through its ``display``.
        """
        parts = self.traversal
        if len(parts) > 1:
            return "__".join(parts[:-1])
        if self.display and self.name:
            return self.name
        return None

    @property
    def sortable(self) -> bool:
        return self.sort is not False

    @property
    def sort_field(self) -> str | None:
        """The column to order by when this header is clicked.

        A relation column sorts by what it *shows*: ``Column.relation("author",
        display="email")`` orders by ``author__email``, because ordering by the
        foreign key gives you insertion order under a column of email
        addresses, which looks like a bug and is one.
        """
        if self.sort is False:
            return None
        if isinstance(self.sort, str):
            return self.sort
        if self.display and self.name:
            return f"{self.name}__{self.display}"
        return self.name

    @property
    def alignment(self) -> str:
        """The explicit alignment, or the one this format asks for."""
        if self.align:
            return self.align
        return (self.format or Format("text")).align

    def __repr__(self) -> str:
        head = repr(self.name) if self.name is not None else repr(self.label)
        extras = []
        if self.name is not None and self.label:
            extras.append(f"label={self.label!r}")
        if self.format is not None:
            extras.append(f"format={self.format!r}")
        for flag in ("link", "hidden", "sticky"):
            if getattr(self, flag):
                extras.append(f"{flag}=True")
        if self.sort is not None:
            extras.append(f"sort={self.sort!r}")
        if self.display:
            extras.append(f"display={self.display!r}")
        return f"Column({', '.join([head, *extras])})"
