"""``Resource`` — one model's whole surface.

::

    Resource(
        Post,
        label="Post", icon="file-text", group="Content",
        list=List(...), form=Form(...), detail=Detail(...),
        access=Access(view=True, add="post.add", delete=False),
        scope=Scope.tenant("team_id"),
    )

**Everything is optional but the model.** ``Resource(Post)`` alone produces a
working list, form and detail page, derived at mount from the model's own
columns. That is the difference between an admin you can put in front of a new
model in ten seconds and one you configure before you can look at anything.
Every derived part is replaced by naming it.

**Registering a resource declares four permissions** — ``post.view``,
``post.add``, ``post.change``, ``post.delete`` — and ``warder permissions
sync`` writes any that are missing. So what a deployment can grant is derived
from what is registered, rather than typed once here and again in a fixtures
file that drifts.

**A resource is a value.** Generating forty of them is a function that returns
one, called forty times.
"""

from __future__ import annotations

import typing

from warder._async import resolved
from warder._check import identifier, sequence
from warder.access import ACTIONS, Access, Scope
from warder.base import Declaration
from warder.naming import label_for, permission, plural_of, slug_for
from warder.screens import Detail, Form, List
from warder.sorting import Sort

if typing.TYPE_CHECKING:
    from warder.actions import Action

__all__ = ["Resource"]


class Resource(Declaration):
    """One model, and everything the admin does with it."""

    __slots__ = (
        "model",
        "label",
        "plural",
        "icon",
        "group",
        "slug",
        "list",
        "form",
        "detail",
        "access",
        "scope",
        "queryset",
        "search",
        "sort",
        "stem",
        "description",
        "weight",
        "creatable",
        "editable",
        "deletable",
        "actions",
        "hidden",
    )
    _fields = __slots__
    _head = ("model",)

    model: type
    label: str
    plural: str
    icon: str | None
    group: str | None
    slug: str
    list: List | None
    form: Form | None
    detail: Detail | None
    access: Access | None
    scope: Scope | None
    queryset: typing.Callable[..., typing.Any] | None
    search: tuple[str, ...]
    sort: Sort | None
    stem: str
    description: str | None
    weight: int
    creatable: bool
    editable: bool
    deletable: bool
    actions: tuple[Action, ...]
    hidden: bool

    def __init__(
        self,
        model: type,
        *,
        label: str | None = None,
        plural: str | None = None,
        icon: str | None = None,
        group: str | None = None,
        slug: str | None = None,
        list: List | None = None,
        form: Form | None = None,
        detail: Detail | None = None,
        access: Access | None = None,
        scope: Scope | None = None,
        queryset: typing.Callable[..., typing.Any] | None = None,
        search: typing.Sequence[str] = (),
        sort: Sort | str | None = None,
        stem: str | None = None,
        description: str | None = None,
        weight: int = 0,
        creatable: bool = True,
        editable: bool = True,
        deletable: bool = True,
        actions: typing.Sequence[Action] = (),
        hidden: bool = False,
    ) -> None:
        if not isinstance(model, type):
            raise TypeError(
                f"Resource takes a model class, got {model!r}. "
                "Resource(Post), not Resource(Post())."
            )
        for name in sequence("search", search):
            identifier("search", name)
        name = label or label_for(model)
        self._init(
            model=model,
            label=name,
            plural=plural or plural_of(name),
            icon=icon,
            group=group,
            slug=identifier("slug", slug) if slug else slug_for(model),
            list=list,
            form=form,
            detail=detail,
            access=access,
            scope=scope,
            queryset=queryset,
            search=tuple(search),
            sort=Sort.by(sort) if isinstance(sort, str) else sort,
            stem=identifier("stem", stem) if stem else slug_for(model),
            description=description,
            weight=weight,
            creatable=creatable,
            editable=editable,
            deletable=deletable,
            actions=tuple(actions),
            hidden=hidden,
        )

    # -------------------------------------------------------------- questions

    @property
    def key(self) -> str:
        """The slug this resource lives under — ``/admin/blog-post``."""
        return self.slug

    @property
    def permissions(self) -> tuple[str, ...]:
        """The four permission names this resource declares."""
        return tuple(permission(self.stem, action) for action in ACTIONS)

    @property
    def default_access(self) -> Access:
        """The access used when none is given: everything, narrowed by the flags.

        ``creatable=False`` is a statement about the *model* — a row created by
        a job, never by hand — and it holds however the permissions are set,
        which ``Access`` alone cannot say.
        """
        return Access(
            view=True,
            add=None if self.creatable else False,
            change=None if self.editable else False,
            delete=None if self.deletable else False,
        )

    def rules(self) -> Access:
        """The access actually applied: what was declared, under the flags."""
        declared = self.access or Access()
        flags = self.default_access
        return Access(
            *(
                False if getattr(flags, action) is False else getattr(declared, action)
                for action in ACTIONS
            )
        )

    async def allows(
        self, ctx: typing.Any, action: str, row: typing.Any = None
    ) -> bool:
        """Whether *ctx* may perform *action* here."""
        return await self.rules().allows(ctx, action, row)

    async def rows(self, ctx: typing.Any, base: typing.Any) -> typing.Any:
        """*base*, narrowed by ``queryset=`` and then by ``scope=``.

        In that order, and both applied: ``queryset`` is the resource's own
        idea of what it manages (soft-deleted rows excluded, say) and
        ``scope`` is this person's slice of it. Skipping either is a leak.
        """
        narrowed = base
        if self.queryset is not None:
            narrowed = await resolved(self.queryset(ctx, narrowed))
        if self.scope is not None:
            narrowed = await self.scope.apply(ctx, narrowed)
        return narrowed

    def route(self, prefix: str = "") -> str:
        return f"{prefix.rstrip('/')}/{self.slug}"

    def __repr__(self) -> str:
        return f"Resource({self.model.__name__})"


def crud(
    model: type,
    *fields: str,
    group: str | None = None,
    stem: str | None = None,
    **options: typing.Any,
) -> Resource:
    """A resource over *fields*, listed and editable, in three words.

    The shape most reference tables want — countries, tags, categories — where
    the columns and the form are the same handful of names::

        for model in (Tag, Category, Region):
            admin.add(crud(model, "name", "slug", group="Reference"))

    A convenience, not a layer: it returns an ordinary ``Resource`` you can
    take apart with ``.with_()``.
    """
    from warder.columns import Column
    from warder.fields import Field
    from warder.layout import Section

    if not fields:
        raise TypeError("crud() needs at least one field name.")
    return Resource(
        model,
        group=group,
        stem=stem,
        list=List(
            *(Column(name, link=name == fields[0]) for name in fields),
            sort=Sort.asc(fields[0]),
            **{k: options.pop(k) for k in ("filters", "actions") if k in options},
        ),
        form=Form(Section("", *(Field(name) for name in fields))),
        **options,
    )
