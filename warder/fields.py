"""``Field`` — one input on a form.

A field names a model column and, when the default is wrong, says how to edit
it::

    Field("title", placeholder="A short, specific title")
    Field("body", widget=Widget.markdown(height=400))
    Field.readonly("created_at")
    Field("published_at", show=When("status", equals="live"))

**Most fields say nothing but their name.** The widget, whether the input is
required, its maximum length and its choices are all read from the *database
column* at mount — from the schema, which states them, rather than from an
annotation, which describes a type. Naming a widget is for when the default is
wrong about the *meaning*: ``body`` and ``internal_note`` are both ``TextField``
and only one of them wants Markdown.

**A readonly field is readonly on the server.** ``Field.readonly("created_at")``
renders the input disabled *and* drops any value submitted for it. The two have
to agree, or the first is decoration.

**A hidden field is not a secret.** ``hidden=True`` means "not drawn"; it is
still sent and still writable. To keep a value away from the browser, use
``access=`` — an unviewable field is left out of the props entirely.
"""

from __future__ import annotations

import typing

from warder._check import callable_, identifier, positive
from warder.access import Access
from warder.base import Declaration
from warder.conditions import When
from warder.widgets import Widget

__all__ = ["Field"]


class Field(Declaration):
    """One input."""

    __slots__ = (
        "name",
        "label",
        "widget",
        "help",
        "placeholder",
        "required",
        "editable",
        "default",
        "access",
        "hidden",
        "span",
        "show",
        "validate",
        "autofocus",
        "unit",
    )
    _fields = __slots__

    #: Distinguishes "no default given" from ``default=None``, which is a
    #: perfectly ordinary thing to want on a nullable column.
    UNSET: typing.ClassVar[object] = object()

    name: str
    label: str | None
    widget: Widget | None
    help: str | None
    placeholder: str | None
    required: bool | None
    editable: bool
    default: typing.Any
    access: Access | None
    hidden: bool
    span: int
    show: When | None
    validate: tuple[typing.Callable[[typing.Any], typing.Any], ...]
    autofocus: bool
    unit: str | None

    def __init__(
        self,
        name: str,
        *,
        label: str | None = None,
        widget: Widget | None = None,
        help: str | None = None,
        placeholder: str | None = None,
        required: bool | None = None,
        editable: bool = True,
        default: typing.Any = UNSET,
        access: Access | None = None,
        hidden: bool = False,
        span: int = 1,
        show: When | None = None,
        validate: typing.Callable[[typing.Any], typing.Any]
        | typing.Sequence[typing.Callable[[typing.Any], typing.Any]] = (),
        autofocus: bool = False,
        unit: str | None = None,
    ) -> None:
        checks = (validate,) if callable(validate) else tuple(validate)
        for check in checks:
            callable_("Field validate", check)
        self._init(
            name=identifier("Field name", name),
            label=label,
            widget=widget,
            help=help,
            placeholder=placeholder,
            required=required,
            editable=editable,
            default=default,
            access=access,
            hidden=hidden,
            span=positive("Field span", span),
            show=show,
            validate=checks,
            autofocus=autofocus,
            unit=unit,
        )

    # ------------------------------------------------------------ shorthands

    @classmethod
    def readonly(cls, name: str, **options: typing.Any) -> Field:
        """Shown, never written.

        The constructor spells this ``editable=False``. The slot cannot also
        be called ``readonly`` and this shorthand is what reads correctly at a
        call site, so the keyword is the one that gave way.
        """
        return cls(name, editable=False, **options)

    @classmethod
    def text(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.text(
                prefix=options.pop("prefix", ""),
                suffix=options.pop("suffix", ""),
                mono=options.pop("mono", False),
            ),
            **options,
        )

    @classmethod
    def textarea(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.textarea(
                rows=options.pop("rows", 4), autosize=options.pop("autosize", True)
            ),
            **options,
        )

    @classmethod
    def markdown(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.markdown(
                height=options.pop("height", 320), preview=options.pop("preview", True)
            ),
            **options,
        )

    @classmethod
    def rich(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name, widget=Widget.rich(height=options.pop("height", 320)), **options
        )

    @classmethod
    def code(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.code(
                language=options.pop("language", "json"),
                height=options.pop("height", 240),
            ),
            **options,
        )

    @classmethod
    def password(cls, name: str = "password", **options: typing.Any) -> Field:
        """A password box.

        Never populated from the stored value and never sent back. Left empty,
        it means "leave the existing hash alone", which is the only behaviour
        that makes an edit form usable.
        """
        return cls(
            name,
            widget=Widget.password(
                confirm=options.pop("confirm", False),
                strength=options.pop("strength", True),
            ),
            **options,
        )

    @classmethod
    def slug(
        cls, name: str = "slug", *, source: str | None = None, **options: typing.Any
    ) -> Field:
        """A URL slug that follows *source* until someone edits it by hand."""
        return cls(name, widget=Widget.slug(source=source), **options)

    @classmethod
    def email(cls, name: str = "email", **options: typing.Any) -> Field:
        """An email box, with the keyboard and validation a browser gives one."""
        return cls(name, widget=Widget.email(), **options)

    @classmethod
    def url(cls, name: str, **options: typing.Any) -> Field:
        return cls(name, widget=Widget.url(), **options)

    @classmethod
    def phone(
        cls, name: str = "phone", *, region: str | None = None, **options: typing.Any
    ) -> Field:
        """A telephone box. *region* is the country the number is read in."""
        return cls(name, widget=Widget.phone(region=region), **options)

    @classmethod
    def color(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name, widget=Widget.color(palette=options.pop("palette", ())), **options
        )

    @classmethod
    def range(cls, name: str, **options: typing.Any) -> Field:
        """A slider. Right when the *shape* of the value matters more than it."""
        return cls(
            name,
            widget=Widget.range(
                min=options.pop("min", 0),
                max=options.pop("max", 100),
                step=options.pop("step", 1),
            ),
            **options,
        )

    @classmethod
    def duration(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name, widget=Widget.duration(unit=options.pop("unit", "seconds")), **options
        )

    @classmethod
    def time(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name, widget=Widget.time(seconds=options.pop("seconds", False)), **options
        )

    @classmethod
    def number(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.number(
                min=options.pop("min", None),
                max=options.pop("max", None),
                step=options.pop("step", 1),
                precision=options.pop("precision", None),
            ),
            **options,
        )

    @classmethod
    def money(cls, name: str, currency: str = "USD", **options: typing.Any) -> Field:
        return cls(name, widget=Widget.money(currency), **options)

    @classmethod
    def select(
        cls, name: str, choices: typing.Iterable[typing.Any] = (), **options: typing.Any
    ) -> Field:
        return cls(
            name,
            widget=Widget.select(
                choices,
                multiple=options.pop("multiple", False),
                searchable=options.pop("searchable", None),
            ),
            **options,
        )

    @classmethod
    def radio(
        cls, name: str, choices: typing.Iterable[typing.Any] = (), **options: typing.Any
    ) -> Field:
        return cls(
            name,
            widget=Widget.radio(choices, inline=options.pop("inline", False)),
            **options,
        )

    @classmethod
    def switch(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name, widget=Widget.switch(labels=options.pop("labels", None)), **options
        )

    @classmethod
    def tags(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.tags(
                choices=options.pop("choices", ()), create=options.pop("create", True)
            ),
            **options,
        )

    @classmethod
    def date(cls, name: str, **options: typing.Any) -> Field:
        return cls(name, widget=Widget.date(), **options)

    @classmethod
    def datetime(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.datetime(
                seconds=options.pop("seconds", False),
                timezone=options.pop("timezone", None),
            ),
            **options,
        )

    @classmethod
    def file(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.file(
                accept=options.pop("accept", ()),
                multiple=options.pop("multiple", False),
                max_size=options.pop("max_size", None),
            ),
            **options,
        )

    @classmethod
    def image(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name,
            widget=Widget.image(
                aspect=options.pop("aspect", None),
                max_size=options.pop("max_size", None),
            ),
            **options,
        )

    @classmethod
    def json(cls, name: str, **options: typing.Any) -> Field:
        return cls(
            name, widget=Widget.json(height=options.pop("height", 240)), **options
        )

    @classmethod
    def keyvalue(cls, name: str, **options: typing.Any) -> Field:
        return cls(name, widget=Widget.keyvalue(), **options)

    @classmethod
    def relation(
        cls,
        name: str,
        *,
        display: str | None = None,
        search: typing.Sequence[str] = (),
        **options: typing.Any,
    ) -> Field:
        """A picker over the related table, searching rather than preloading."""
        return cls(
            name,
            widget=Widget.relation(
                display=display,
                search=search,
                multiple=options.pop("multiple", False),
                create=options.pop("create", False),
            ),
            **options,
        )

    # ------------------------------------------------------------- questions

    @property
    def key(self) -> str:
        return self.name

    @property
    def heading(self) -> str:
        """The label above the input."""
        if self.label:
            return self.label
        name = self.name[:-3] if self.name.endswith("_id") else self.name
        return name.replace("_", " ").capitalize()

    @property
    def has_default(self) -> bool:
        return self.default is not Field.UNSET

    def errors(self, value: typing.Any) -> tuple[str, ...]:
        """Every message this field's checks produce for *value*.

        A check returns a message to complain and ``None`` to pass, so writing
        one takes no imports. All of them run, so a form reports everything
        wrong with a value at once rather than one thing per submission.
        """
        found: list[str] = []
        for check in self.validate:
            message = check(value)
            if message:
                found.append(str(message))
        return tuple(found)

    def __repr__(self) -> str:
        extras = []
        if self.label:
            extras.append(f"label={self.label!r}")
        if self.widget is not None:
            extras.append(f"widget={self.widget!r}")
        if not self.editable:
            extras.append("editable=False")
        for flag in ("hidden", "autofocus"):
            if getattr(self, flag):
                extras.append(f"{flag}=True")
        if self.show is not None:
            extras.append(f"show={self.show!r}")
        return f"Field({', '.join([repr(self.name), *extras])})"
