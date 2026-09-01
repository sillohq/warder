"""``Action`` — something a person can do to rows.

::

    Action("Publish", publish, icon="upload", confirm="Publish {count} posts?")
    Action.delete()
    Action("Assign", assign, fields=[Field.relation("assignee")])

**The handler is given a queryset, not a list of ids.** ``rows`` is already
scoped, already filtered, and not yet evaluated, so an action over forty
thousand selected rows is one statement rather than forty thousand round
trips::

    async def publish(ctx, rows):
        count = await rows.filter(status="draft").update(status="live")
        return notice(f"Published {count} posts")

**How the handler is called is decided by the declaration, visibly.** With no
``fields=`` it is ``run(ctx, rows)``. With ``fields=`` it is
``run(ctx, rows, values)``, where *values* is the little form the confirmation
dialog collected. Nothing is inferred from the handler's signature — the
difference is a keyword you wrote.

**Selection is part of the declaration.** ``selection="one"`` for something
that only makes sense on a single row, ``"none"`` for something that acts on
the filtered set as a whole ("export everything matching"), ``"many"`` — the
default — for the ordinary case.
"""

from __future__ import annotations

import typing

from warder._check import callable_, identifier, one_of
from warder.access import Access, Gate
from warder.base import Declaration
from warder.naming import slug

if typing.TYPE_CHECKING:
    from warder.fields import Field

__all__ = ["Action"]

_STYLES = ("default", "primary", "danger", "ghost")
_SELECTION = ("many", "one", "none")
_PLACES = ("toolbar", "row", "both")


class Action(Declaration):
    """A button, and what it runs."""

    __slots__ = (
        "label",
        "run",
        "name",
        "icon",
        "confirm",
        "access",
        "gate",
        "style",
        "selection",
        "place",
        "fields",
        "description",
        "keyboard",
        "options",
    )
    _fields = __slots__

    def __init__(
        self,
        label: str,
        run: typing.Callable[..., typing.Any] | None = None,
        *,
        name: str | None = None,
        icon: str | None = None,
        confirm: str | None = None,
        access: Access | None = None,
        gate: Gate | None = None,
        style: str = "default",
        selection: str = "many",
        place: str = "toolbar",
        fields: typing.Sequence[Field] = (),
        description: str | None = None,
        keyboard: str | None = None,
        options: typing.Mapping[str, typing.Any] | None = None,
    ) -> None:
        if run is not None:
            callable_("Action run", run)
        self._init(
            label=label,
            run=run,
            name=identifier("Action name", name) if name else slug(label),
            icon=icon,
            confirm=confirm,
            access=access,
            gate=gate,
            style=one_of("style", style, _STYLES),
            selection=one_of("selection", selection, _SELECTION),
            place=one_of("place", place, _PLACES),
            fields=tuple(fields),
            description=description,
            keyboard=keyboard,
            options=dict(options or {}),
        )

    # ----------------------------------------------------------- constructors

    @classmethod
    def delete(
        cls,
        label: str = "Delete",
        *,
        confirm: str = "Delete {count} selected? This cannot be undone.",
        **options: typing.Any,
    ) -> Action:
        """The built-in delete.

        ``run`` is left unset: deleting is the one action the resource itself
        performs, through the same ``delete`` rule in ``Access`` that hides the
        button — so it cannot be granted by adding an action.
        """
        return cls(
            label,
            None,
            name=options.pop("name", "delete"),
            icon=options.pop("icon", "trash"),
            confirm=confirm,
            style=options.pop("style", "danger"),
            **options,
        )

    @classmethod
    def export(
        cls,
        label: str = "Export CSV",
        *,
        format: str = "csv",
        columns: typing.Sequence[str] = (),
        **options: typing.Any,
    ) -> Action:
        """Export the *filtered* set, whether or not anything is selected.

        ``selection="none"`` on purpose: exporting means "everything I am
        looking at", and making people select forty thousand rows first is a
        way of not having the feature.
        """
        return cls(
            label,
            None,
            name=options.pop("name", f"export-{format}"),
            icon=options.pop("icon", "download"),
            selection=options.pop("selection", "none"),
            options={"format": format, "columns": tuple(columns)},
            **options,
        )

    @classmethod
    def link(
        cls, label: str, to: typing.Callable[[typing.Any], str], **options: typing.Any
    ) -> Action:
        """A row button that navigates rather than mutating.

        *to* is called ``(row)`` and returns a URL.
        """
        return cls(
            label,
            callable_("Action.link to", to),
            selection=options.pop("selection", "one"),
            place=options.pop("place", "row"),
            name=options.pop("name", slug(label)),
            **options,
        )

    # -------------------------------------------------------------- questions

    @property
    def key(self) -> str:
        """The identifier the browser sends back to ask for this action."""
        return self.name

    @property
    def builtin(self) -> bool:
        """Whether the resource performs this rather than a handler.

        ``Action.delete()`` and ``Action.export()`` have no ``run``: they are
        the two things the resource already knows how to do, declared so their
        label, icon, position and confirmation are yours to set.
        """
        return self.run is None

    @property
    def collects(self) -> bool:
        """Whether running this opens a form first."""
        return bool(self.fields)

    @property
    def destructive(self) -> bool:
        return self.style == "danger"

    @property
    def needs_selection(self) -> bool:
        return self.selection != "none"

    def option(self, name: str, default: typing.Any = None) -> typing.Any:
        """One of the kind-specific extras — an export's format, say."""
        return self.options.get(name, default)

    def prompt(self, count: int) -> str | None:
        """The confirmation text for *count* rows, or ``None``.

        ``{count}`` is substituted, and ``{n}`` alongside it, because both get
        typed. A missing placeholder is left as it was written rather than
        raising — an admin should not fail to render over a brace.
        """
        if not self.confirm:
            return None
        try:
            return self.confirm.format(count=count, n=count)
        except (KeyError, IndexError, ValueError):
            return self.confirm

    async def allowed(self, ctx: typing.Any, row: typing.Any = None) -> bool:
        """Whether this action's own gate and access let *ctx* run it.

        Only the action's own rules. The resource's ``change`` rule is checked
        by the caller, so an action cannot widen what the resource allows —
        only narrow it.
        """
        if self.gate is not None and not await self.gate.allows(ctx):
            return False
        if self.access is None:
            return True
        return await self.access.allows(ctx, "change", row)

    def __repr__(self) -> str:
        extras = [f"name={self.name!r}"] if self.name != slug(self.label) else []
        if self.style != "default":
            extras.append(f"style={self.style!r}")
        if self.selection != "many":
            extras.append(f"selection={self.selection!r}")
        if self.fields:
            extras.append(f"fields={len(self.fields)}")
        return f"Action({', '.join([repr(self.label), *extras])})"
