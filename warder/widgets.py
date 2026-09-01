"""``Widget`` — how a value is edited.

The write half of the display pair. Same shape as
:class:`~warder.formats.Format`: a kind and its options, serialised straight
into props, with the actual control living in React.

Most fields never name one. ``Field("body")`` picks a widget from the model's
column — a ``TextField`` gets a textarea, a ``BooleanField`` gets a switch, a
``ForeignKeyField`` gets a searching relation picker. That inference happens in
:mod:`warder.resolve` against the *database column*, which is a value the
schema states, not something read off an annotation.

Name one when the default is wrong for the meaning rather than for the type:
``body`` is a ``TextField`` and so is ``internal_note``, but only one of them
wants a Markdown editor.
"""

from __future__ import annotations

import typing

from warder._check import one_of
from warder.base import Declaration
from warder.naming import coerce_choices

__all__ = ["Widget"]


class Widget(Declaration):
    """A form control."""

    __slots__ = ("kind", "options")
    _fields = ("kind", "options")

    KINDS = (
        "text",
        "textarea",
        "markdown",
        "rich",
        "code",
        "password",
        "slug",
        "email",
        "url",
        "phone",
        "number",
        "money",
        "range",
        "select",
        "radio",
        "checkbox",
        "switch",
        "tags",
        "date",
        "datetime",
        "time",
        "duration",
        "file",
        "image",
        "json",
        "keyvalue",
        "color",
        "relation",
        "hidden",
    )

    def __init__(self, kind: str = "text", **options: typing.Any) -> None:
        self._init(kind=one_of("Widget kind", kind, self.KINDS), options=options)

    # ---------------------------------------------------------------- text

    @classmethod
    def text(cls, *, prefix: str = "", suffix: str = "", mono: bool = False) -> Widget:
        """One line. *prefix* and *suffix* are the affixes drawn inside the box —
        a currency sign, a domain, a unit."""
        return cls("text", prefix=prefix, suffix=suffix, mono=mono)

    @classmethod
    def textarea(cls, *, rows: int = 4, autosize: bool = True) -> Widget:
        return cls("textarea", rows=rows, autosize=autosize)

    @classmethod
    def markdown(
        cls, *, height: int = 320, preview: bool = True, toolbar: bool = True
    ) -> Widget:
        """A Markdown editor with a live preview."""
        return cls("markdown", height=height, preview=preview, toolbar=toolbar)

    @classmethod
    def rich(
        cls,
        *,
        height: int = 320,
        tools: typing.Sequence[str] = ("bold", "italic", "link", "list", "heading"),
    ) -> Widget:
        """A rich-text editor that stores sanitised HTML."""
        return cls("rich", height=height, tools=tuple(tools))

    @classmethod
    def code(cls, *, language: str = "json", height: int = 240) -> Widget:
        return cls("code", language=language, height=height)

    @classmethod
    def password(cls, *, confirm: bool = False, strength: bool = True) -> Widget:
        """A password box.

        The value is written through ``sillo.hashing`` and is never sent back
        to the browser — the form shows an empty box and an unchanged field
        leaves the hash alone.
        """
        return cls("password", confirm=confirm, strength=strength)

    @classmethod
    def slug(cls, *, source: str | None = None, editable: bool = True) -> Widget:
        """A URL slug, tracking *source* until someone types in it."""
        return cls("slug", source=source, editable=editable)

    @classmethod
    def email(cls) -> Widget:
        return cls("email")

    @classmethod
    def url(cls) -> Widget:
        return cls("url")

    @classmethod
    def phone(cls, *, region: str | None = None) -> Widget:
        return cls("phone", region=region)

    # -------------------------------------------------------------- numbers

    @classmethod
    def number(
        cls,
        *,
        min: float | None = None,
        max: float | None = None,
        step: float = 1,
        precision: int | None = None,
    ) -> Widget:
        return cls("number", min=min, max=max, step=step, precision=precision)

    @classmethod
    def money(cls, currency: str = "USD", *, min: float | None = None) -> Widget:
        return cls("money", currency=currency, min=min)

    @classmethod
    def range(cls, *, min: float = 0, max: float = 100, step: float = 1) -> Widget:
        return cls("range", min=min, max=max, step=step)

    # -------------------------------------------------------------- choices

    @classmethod
    def select(
        cls,
        choices: typing.Iterable[typing.Any] = (),
        *,
        multiple: bool = False,
        searchable: bool | None = None,
        clearable: bool = True,
    ) -> Widget:
        """A dropdown.

        *searchable* defaults to on once there are more than ten options,
        because a ten-item list is faster to read than to type into and a
        forty-item one is the reverse.
        """
        normalised = coerce_choices(choices)
        return cls(
            "select",
            choices=normalised,
            multiple=multiple,
            searchable=len(normalised) > 10 if searchable is None else searchable,
            clearable=clearable,
        )

    @classmethod
    def radio(
        cls, choices: typing.Iterable[typing.Any] = (), *, inline: bool = False
    ) -> Widget:
        """Every option visible at once. Right below about five options."""
        return cls("radio", choices=coerce_choices(choices), inline=inline)

    @classmethod
    def checkbox(cls, choices: typing.Iterable[typing.Any] = ()) -> Widget:
        """Several of a set. With no *choices*, a single box for a boolean."""
        return cls("checkbox", choices=coerce_choices(choices))

    @classmethod
    def switch(cls, *, labels: tuple[str, str] | None = None) -> Widget:
        """On or off, applied immediately in feel if not in fact."""
        return cls("switch", labels=tuple(labels) if labels else None)

    @classmethod
    def tags(
        cls,
        *,
        choices: typing.Iterable[typing.Any] = (),
        create: bool = True,
        limit: int | None = None,
    ) -> Widget:
        """Free-form labels. ``create=False`` restricts to *choices*."""
        return cls("tags", choices=coerce_choices(choices), create=create, limit=limit)

    # ---------------------------------------------------------------- times

    @classmethod
    def date(cls, *, min: str | None = None, max: str | None = None) -> Widget:
        return cls("date", min=min, max=max)

    @classmethod
    def datetime(cls, *, seconds: bool = False, timezone: str | None = None) -> Widget:
        """A date and a time. *timezone* names the zone the input is read in."""
        return cls("datetime", seconds=seconds, timezone=timezone)

    @classmethod
    def time(cls, *, seconds: bool = False) -> Widget:
        return cls("time", seconds=seconds)

    @classmethod
    def duration(cls, *, unit: str = "seconds") -> Widget:
        return cls("duration", unit=unit)

    # ----------------------------------------------------------------- data

    @classmethod
    def file(
        cls,
        *,
        accept: typing.Sequence[str] = (),
        multiple: bool = False,
        max_size: str | None = None,
    ) -> Widget:
        """An upload, stored through ``sillo.storage``."""
        return cls("file", accept=tuple(accept), multiple=multiple, max_size=max_size)

    @classmethod
    def image(
        cls,
        *,
        aspect: str | None = None,
        max_size: str | None = None,
        preview: bool = True,
    ) -> Widget:
        return cls("image", aspect=aspect, max_size=max_size, preview=preview)

    @classmethod
    def json(
        cls, *, height: int = 240, schema: typing.Mapping[str, typing.Any] | None = None
    ) -> Widget:
        """Raw JSON, validated in the browser before it is sent."""
        return cls("json", height=height, schema=dict(schema or {}))

    @classmethod
    def keyvalue(cls, *, key_label: str = "Key", value_label: str = "Value") -> Widget:
        """A JSON object edited as rows. What most ``JSONField``s actually hold."""
        return cls("keyvalue", key_label=key_label, value_label=value_label)

    @classmethod
    def color(cls, *, palette: typing.Sequence[str] = ()) -> Widget:
        return cls("color", palette=tuple(palette))

    # ------------------------------------------------------------ relations

    @classmethod
    def relation(
        cls,
        *,
        display: str | None = None,
        search: typing.Sequence[str] = (),
        multiple: bool = False,
        create: bool = False,
        preload: int = 20,
    ) -> Widget:
        """A picker for a related row.

        It searches over the wire rather than loading every row into a
        ``<select>``, which is the difference between a foreign key to
        ``Country`` and one to ``Customer``. *preload* is how many arrive
        before anyone types.
        """
        return cls(
            "relation",
            display=display,
            search=tuple(search),
            multiple=multiple,
            create=create,
            preload=preload,
        )

    @classmethod
    def hidden(cls) -> Widget:
        """Submitted, not shown. Not a security measure — see ``Access``."""
        return cls("hidden")

    # ------------------------------------------------------------ questions

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        return self.options.get(name, default)

    @property
    def choices(self) -> tuple[tuple[typing.Any, str], ...]:
        """The options this widget offers, empty when it offers none."""
        return tuple(self.options.get("choices") or ())

    def __repr__(self) -> str:
        shown = {
            k: v for k, v in self.options.items() if v not in (None, "", (), {}, False)
        }
        inner = ", ".join(f"{k}={v!r}" for k, v in shown.items())
        return f"Widget({self.kind!r}{', ' + inner if inner else ''})"
