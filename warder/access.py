"""Who may do what, and to which rows.

Four questions, and they are genuinely different questions:

===========================================  ==================================
May you get in at all?                       :class:`Gate`
May you do this to this *model*?             :class:`Access`
May you do it to *this row*?                 :class:`Access` callable, :class:`Scope`
May you see *this field*?                    :class:`Access` on a column or field
===========================================  ==================================

:class:`Access` and :class:`Scope` are both needed and neither substitutes for
the other. ``Access`` decides whether a button is shown and whether a write is
allowed; ``Scope`` decides what is in the queryset at all. Access without scope
leaks the existence of rows through pagination counts and search results; scope
without access leaves a writable object reachable by its id.

**No arity sniffing.** A rule callable is *always* called as ``(ctx, row)`` and
``row`` is ``None`` when the question is not about one particular row. The
alternative — inspecting how many parameters you wrote — is the kind of
invisible behaviour this package exists to avoid. A :class:`Gate` callable
takes ``(ctx)`` alone, because a gate is never about a row.

Rules may be async. Everything here is awaited.
"""

from __future__ import annotations

import inspect
import typing

from warder._check import callable_, identifier
from warder.base import Declaration
from warder.naming import permission

if typing.TYPE_CHECKING:
    from warder.sorting import Sort  # noqa: F401

__all__ = ["ACTIONS", "Access", "Gate", "Role", "Scope"]

#: The four things you can do to a row, in the order they escalate.
ACTIONS = ("view", "add", "change", "delete")

#: A rule is a fixed answer, a permission name, or something callable.
Rule = typing.Union[bool, str, typing.Callable[..., typing.Any], None]


async def _resolve(rule: Rule, ctx: typing.Any, row: typing.Any = None) -> bool:
    """Answer one rule.

    ``True``/``False`` answer themselves. A string is a permission name. A
    callable is called ``(ctx, row)`` and awaited if it needs to be.
    """
    if rule is None:
        return True
    if rule is True or rule is False:
        return bool(rule)
    if isinstance(rule, str):
        return await holds_permission(ctx, rule)
    result = rule(ctx, row)
    if inspect.isawaitable(result):
        result = await result
    return bool(result)


async def holds_permission(ctx: typing.Any, name: str) -> bool:
    """Whether the signed-in user holds the permission *name*.

    Resolved against ``sillo.permissions`` when the user model carries
    ``PermissionMixin``, which caches on the instance — so the loading call is
    made once per request and not once per column.

    A user model without the mixin is not an error; it simply grants nothing
    by permission, and such an application is expected to use gates and
    callables instead.
    """
    user = current_user(ctx)
    if user is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    loader = getattr(user, "load_permissions", None)
    if loader is not None:
        await loader()
    checker = getattr(user, "has_permission", None)
    if checker is None:
        return False
    return bool(checker(name))


def current_user(ctx: typing.Any) -> typing.Any:
    """The signed-in user, or ``None``.

    ``ctx.user`` raises rather than returning ``None`` when no authentication
    middleware is installed, and an admin asked "may this person view" before
    login is a perfectly ordinary state — so the raise is turned back into the
    answer the caller is looking for.
    """
    try:
        return ctx.user
    except (AttributeError, ValueError, LookupError):
        return None


# --------------------------------------------------------------------- Gate


class Gate(Declaration):
    """May this person be in the admin at all?

    This matters more than it looks. When the admin shares the application's
    user model — the ordinary arrangement — every registered account holds a
    session, and admitting anyone who has one hands over the database.

    ::

        Gate.staff()
        Gate.permission("admin.access")
        Gate.any(Gate.role("owner"), Gate.permission("admin.access"))
    """

    __slots__ = ("kind", "value", "gates")
    _fields = ("kind", "value", "gates")

    KINDS = ("always", "never", "staff", "superuser", "permission", "role",
             "custom", "any", "all", "not")

    def __init__(
        self,
        kind: str = "always",
        value: typing.Any = None,
        gates: typing.Sequence[Gate] = (),
    ) -> None:
        if kind not in self.KINDS:
            raise ValueError(
                f"Gate kind {kind!r} is not one of {', '.join(self.KINDS)}. "
                "Build gates with the classmethods rather than the constructor."
            )
        self._init(kind=kind, value=value, gates=tuple(gates))

    @classmethod
    def always(cls) -> Gate:
        """Anyone signed in. The right answer for a single-tenant internal tool."""
        return cls("always")

    @classmethod
    def never(cls) -> Gate:
        """Nobody. Useful for switching a surface off without unmounting it."""
        return cls("never")

    @classmethod
    def staff(cls) -> Gate:
        """Active, and ``is_staff`` or ``is_superuser``. The default."""
        return cls("staff")

    @classmethod
    def superuser(cls) -> Gate:
        """``is_superuser`` only."""
        return cls("superuser")

    @classmethod
    def permission(cls, name: str) -> Gate:
        """Holds the named permission."""
        return cls("permission", identifier("Gate.permission", name))

    @classmethod
    def role(cls, name: str) -> Gate:
        """Belongs to the named role, which is a ``sillo.permissions`` group."""
        return cls("role", identifier("Gate.role", name))

    @classmethod
    def custom(cls, check: typing.Callable[[typing.Any], typing.Any]) -> Gate:
        """*check* is called ``(ctx)`` and may be async."""
        return cls("custom", callable_("Gate.custom", check))

    @classmethod
    def any(cls, *gates: Gate) -> Gate:
        """Passes when any of *gates* passes. Empty means nobody."""
        return cls("any", None, gates)

    @classmethod
    def all(cls, *gates: Gate) -> Gate:
        """Passes when every one of *gates* passes. Empty means everybody."""
        return cls("all", None, gates)

    def __invert__(self) -> Gate:
        """``~gate`` — passes exactly when *gate* does not."""
        return Gate("not", None, (self,))

    def __or__(self, other: Gate) -> Gate:
        return Gate.any(self, other)

    def __and__(self, other: Gate) -> Gate:
        return Gate.all(self, other)

    async def allows(self, ctx: typing.Any) -> bool:
        """Whether this gate lets *ctx* through."""
        if self.kind == "always":
            return current_user(ctx) is not None
        if self.kind == "never":
            return False
        if self.kind == "any":
            for gate in self.gates:
                if await gate.allows(ctx):
                    return True
            return False
        if self.kind == "all":
            for gate in self.gates:
                if not await gate.allows(ctx):
                    return False
            return True
        if self.kind == "not":
            return not await self.gates[0].allows(ctx)
        if self.kind == "custom":
            result = self.value(ctx)
            if inspect.isawaitable(result):
                result = await result
            return bool(result)

        user = current_user(ctx)
        if user is None:
            return False
        if self.kind == "superuser":
            return bool(getattr(user, "is_superuser", False))
        if self.kind == "staff":
            if getattr(user, "is_active", True) is False:
                return False
            return bool(
                getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
            )
        if self.kind == "permission":
            return await holds_permission(ctx, self.value)
        return await _in_role(user, self.value)


async def _in_role(user: typing.Any, name: str) -> bool:
    """Group membership, however this user model spells it.

    ``PermissionMixin.is_in_group`` when it is there; otherwise a ``role``
    attribute compared by slug or name, which is what the bundled admin user
    carries.
    """
    if getattr(user, "is_superuser", False):
        return True
    membership = getattr(user, "is_in_group", None)
    if membership is not None:
        if await membership(name):
            return True
    role = getattr(user, "role", None)
    if role is None:
        return False
    return name in {getattr(role, "slug", None), getattr(role, "name", None)}


# ------------------------------------------------------------------- Access


class Access(Declaration):
    """May this person do this, to this model or to this row?

    ::

        Access(view=True, add="post.add",
               change=lambda ctx, row: row.author_id == ctx.user.id,
               delete=False)

    Each of the four takes ``True``, ``False``, a permission name, or a
    callable invoked as ``(ctx, row)`` — with ``row`` set to ``None`` when the
    question is about the model rather than one row ("may this person reach the
    Add screen at all?").

    On a :class:`~warder.columns.Column` or :class:`~warder.fields.Field` only
    ``view`` and ``change`` are consulted. A field you may not view is left out
    of the props entirely rather than hidden with CSS, so it never reaches the
    browser.
    """

    __slots__ = ("view", "add", "change", "delete")
    _fields = ("view", "add", "change", "delete")

    def __init__(
        self,
        view: Rule = None,
        add: Rule = None,
        change: Rule = None,
        delete: Rule = None,
    ) -> None:
        self._init(view=view, add=add, change=change, delete=delete)

    @classmethod
    def open(cls) -> Access:
        """Everything allowed. What you get when no ``access=`` is given."""
        return cls(True, True, True, True)

    @classmethod
    def readonly(cls) -> Access:
        """Look, do not touch."""
        return cls(view=True, add=False, change=False, delete=False)

    @classmethod
    def none(cls) -> Access:
        """Nothing, including view — the resource disappears from the nav."""
        return cls(False, False, False, False)

    @classmethod
    def by_permission(cls, stem: str, *, delete: Rule = None) -> Access:
        """The four standard permissions for *stem* — ``post.view`` and friends.

        ``delete=False`` is the common override, so it is a keyword rather
        than a second call.
        """
        return cls(
            view=permission(stem, "view"),
            add=permission(stem, "add"),
            change=permission(stem, "change"),
            delete=permission(stem, "delete") if delete is None else delete,
        )

    def rule(self, action: str) -> Rule:
        """The rule for *action*, unresolved."""
        if action not in ACTIONS:
            raise ValueError(f"{action!r} is not one of {', '.join(ACTIONS)}.")
        return typing.cast(Rule, getattr(self, action))

    async def allows(
        self, ctx: typing.Any, action: str, row: typing.Any = None
    ) -> bool:
        """Whether *ctx* may perform *action*, optionally on *row*.

        An unset rule means "not decided here" and answers ``True``; the layer
        above — the resource's access, the gate — has already had its say.
        """
        return await _resolve(self.rule(action), ctx, row)

    def merged_under(self, parent: Access | None) -> Access:
        """This access, with *parent* filling in whatever it leaves unset.

        How a field's access combines with its resource's: the field narrows,
        it never widens, and anything the field does not mention is the
        resource's answer.
        """
        if parent is None:
            return self
        return Access(
            *(
                getattr(parent, action) if getattr(self, action) is None
                else getattr(self, action)
                for action in ACTIONS
            )
        )

    def __bool__(self) -> bool:
        return any(getattr(self, action) is not None for action in ACTIONS)


# -------------------------------------------------------------------- Scope


class Scope(Declaration):
    """Which rows exist, for this person.

    A scope narrows the queryset before anything else touches it — the list,
    the detail lookup, the form's save, and every action. Something outside
    your scope is not "hidden"; as far as your session is concerned it is not
    there, which is the only version of this that does not leak through a
    count.

    ::

        Scope.tenant("team_id")
        Scope.owner("author_id")
        Scope.by(lambda ctx: {"team_id": ctx.user.team_id})
        Scope.query(lambda ctx, rows: rows.filter(region__in=ctx.user.regions))
    """

    __slots__ = ("kind", "value")
    _fields = ("kind", "value")

    KINDS = ("all", "none", "filters", "query")

    def __init__(self, kind: str = "all", value: typing.Any = None) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"Scope kind {kind!r} is not one of {self.KINDS}.")
        self._init(kind=kind, value=value)

    @classmethod
    def all(cls) -> Scope:
        """Every row. The default."""
        return cls("all")

    @classmethod
    def none(cls) -> Scope:
        """No rows. A resource that is registered but not yet switched on."""
        return cls("none")

    @classmethod
    def by(cls, build: typing.Callable[[typing.Any], typing.Mapping[str, typing.Any]]) -> Scope:
        """*build* is called ``(ctx)`` and returns filter keywords."""
        return cls("filters", callable_("Scope.by", build))

    @classmethod
    def query(cls, narrow: typing.Callable[..., typing.Any]) -> Scope:
        """*narrow* is called ``(ctx, rows)`` and returns a narrowed queryset.

        The escape hatch, for anything ``filter(**kwargs)`` cannot say —
        ``Q`` objects, joins, exclusions.
        """
        return cls("query", callable_("Scope.query", narrow))

    @classmethod
    def owner(cls, field: str = "user_id") -> Scope:
        """Rows whose *field* is the signed-in user's id."""
        name = identifier("Scope.owner", field)
        return cls("filters", lambda ctx: {name: current_user(ctx).id})

    @classmethod
    def tenant(cls, field: str = "tenant_id", *, source: str | None = None) -> Scope:
        """Rows belonging to the signed-in user's tenant.

        *source* names the attribute on the user holding the tenant id, and
        defaults to *field* — so ``Scope.tenant("team_id")`` reads
        ``ctx.user.team_id``, which is the arrangement almost every
        multi-tenant schema already has.
        """
        name = identifier("Scope.tenant", field)
        attribute = source or name
        return cls("filters", lambda ctx: {name: getattr(current_user(ctx), attribute)})

    async def apply(self, ctx: typing.Any, rows: typing.Any) -> typing.Any:
        """*rows*, narrowed for *ctx*."""
        if self.kind == "all":
            return rows
        if self.kind == "none":
            return rows.filter(pk__in=[])
        if self.kind == "filters":
            filters = self.value(ctx)
            if inspect.isawaitable(filters):
                filters = await filters
            return rows.filter(**dict(filters)) if filters else rows
        narrowed = self.value(ctx, rows)
        if inspect.isawaitable(narrowed):
            narrowed = await narrowed
        return narrowed

    def __bool__(self) -> bool:
        return self.kind != "all"


# --------------------------------------------------------------------- Role


class Role(Declaration):
    """A named bundle of permissions.

    A role compiles to a ``sillo.permissions`` group with its permission rows,
    so after the first ``warder permissions sync`` roles are *data* — editable
    in the admin itself, by someone who is not going to edit Python.

    ::

        Role("support", grants=["order.view", "customer.view"])
        Role("editor", grants=Role.crud(Post, Tag), inherits=["support"])
        Role("owner", grants="*")
    """

    __slots__ = ("name", "grants", "inherits", "label", "description")
    _fields = ("name", "grants", "inherits", "label", "description")

    def __init__(
        self,
        name: str,
        *,
        grants: typing.Sequence[str] | str = (),
        inherits: typing.Sequence[str] = (),
        label: str | None = None,
        description: str | None = None,
    ) -> None:
        self._init(
            name=identifier("Role name", name),
            grants=("*",) if grants == "*" else tuple(grants),
            inherits=tuple(inherits),
            label=label or name.replace("_", " ").replace("-", " ").capitalize(),
            description=description,
        )

    @property
    def unrestricted(self) -> bool:
        """Whether this role grants everything, now and in future."""
        return self.grants == ("*",)

    @staticmethod
    def crud(*models: type, actions: typing.Sequence[str] = ACTIONS) -> tuple[str, ...]:
        """``Role.crud(Post, Tag)`` → the eight standard permission names.

        Uses the same stem a :class:`~warder.resource.Resource` derives, so a
        role written this way stays correct as resources are added.
        """
        from warder.naming import slug_for

        return tuple(
            permission(slug_for(model), action)
            for model in models
            for action in actions
        )

    def expand(self, roles: typing.Mapping[str, Role]) -> frozenset[str]:
        """Every permission this role grants, following ``inherits``.

        Cycles are survived rather than diagnosed — a role inheriting itself
        through three hops is a strange thing to write but not a reason to
        refuse to start.
        """
        seen: set[str] = set()
        grants: set[str] = set()
        stack = [self.name]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            role = roles.get(current)
            if role is None:
                continue
            grants.update(role.grants)
            stack.extend(role.inherits)
        return frozenset(grants)
