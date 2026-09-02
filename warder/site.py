"""``Admin`` — the site: what is registered, and where it is mounted.

Everything else in this package is a frozen value. This one is not, and the
difference is deliberate: an admin site is a *registry*, built up over the
lifetime of an application's start-up, and pretending otherwise would mean
threading a growing tuple through every module that wants to add a screen.

::

    admin = Admin(title="Acme Ops", prefix="/admin")
    admin.add(Resource(Post, list=List(Column("title", link=True))))
    admin.add(*billing.resources)
    admin.mount(app)

**Nothing registers itself.** A package ships declarations and the application
decides whether to mount them, so importing a module never changes what your
admin contains. That is the property a decorator-and-metaclass registry cannot
have, and it is why ``admin.add`` takes arguments rather than being a
decorator.

**Mounting is when the declarations are checked.** Every field reference,
relation, sort column and permission name is resolved against the models once,
at start-up, and a mistake is a start-up failure with the line it was written
on. A misspelled column should never become an empty cell in production.
"""

from __future__ import annotations

import typing

from warder._check import identifier
from warder.access import Role
from warder.auth import Auth
from warder.errors import DeclarationError, NotConfigured
from warder.pages import Card, Dashboard, Page
from warder.resource import Resource
from warder.theme import Theme

if typing.TYPE_CHECKING:
    from warder.resolve import Bound
    from warder.screens import List

__all__ = ["Admin"]

Registerable = Resource | Page | Dashboard | Card


class Admin:
    """One admin site."""

    def __init__(
        self,
        *,
        title: str = "Admin",
        prefix: str = "/admin",
        auth: Auth | None = None,
        theme: Theme | None = None,
        brand: str | None = None,
        logo: str | None = None,
        favicon: str | None = None,
        groups: typing.Sequence[str] = (),
        footer: str | None = None,
        timezone: str | None = None,
        assets: str = "full",
        name: str = "warder",
    ) -> None:
        if not prefix.startswith("/"):
            raise ValueError(f"Admin prefix must start with '/', got {prefix!r}.")
        self.title = title
        self.prefix = "/" + prefix.strip("/")
        self.auth = auth if auth is not None else Auth()
        self.theme = theme if theme is not None else Theme()
        self.brand = brand or title
        self.logo = logo
        self.favicon = favicon
        self.footer = footer
        self.timezone = timezone
        self.assets = assets
        self.name = identifier("Admin name", name)

        #: Declared group order. Groups not named here follow, alphabetically.
        self.group_order: tuple[str, ...] = tuple(groups)
        self.resources: list[Resource] = []
        self.pages: list[Page] = []
        self.dashboard: Dashboard | None = None
        self.slots: dict[str, str] = {}
        self.mounted: typing.Any = None
        self.bound: dict[str, Bound] = {}
        #: The built interface, once :meth:`mount` has looked for it.
        self.bundle: typing.Any = None
        self._by_slug: dict[str, Resource] = {}
        self._by_model: dict[type, Resource] = {}

    # ---------------------------------------------------------- registration

    def add(self, *items: Registerable) -> Admin:
        """Register resources, pages and a dashboard. Returns self, so it chains.

        Duplicate slugs and duplicate models are refused here rather than at
        mount: two resources over one model is either a mistake or a case for
        ``slug=``, and finding out at the second registration names both.
        """
        for item in items:
            if isinstance(item, Resource):
                self._add_resource(item)
            elif isinstance(item, Page):
                self._add_page(item)
            elif isinstance(item, Dashboard):
                self.dashboard = item
            elif isinstance(item, Card):
                self.dashboard = (self.dashboard or Dashboard()).with_(item)
            else:
                raise TypeError(
                    "admin.add() takes Resources, Pages, Cards and a Dashboard, "
                    f"got {type(item).__name__}."
                )
        return self

    def _add_resource(self, resource: Resource) -> None:
        existing = self._by_slug.get(resource.slug)
        if existing is not None:
            raise DeclarationError(
                f"Two resources are registered at {resource.slug!r}: "
                f"{existing.model.__name__} and {resource.model.__name__}.",
                hint="Give one of them slug= to separate them.",
                where=resource.where,
            )
        clash = self._by_model.get(resource.model)
        if clash is not None:
            raise DeclarationError(
                f"{resource.model.__name__} is registered twice, "
                f"at {clash.slug!r} and {resource.slug!r}.",
                hint="Registering a model twice is usually a copied line.",
                where=resource.where,
            )
        self.resources.append(resource)
        self._by_slug[resource.slug] = resource
        self._by_model[resource.model] = resource

    def _add_page(self, page: Page) -> None:
        for existing in self.pages:
            if existing.path == page.path:
                raise DeclarationError(
                    f"Two pages are registered at {page.path!r}: "
                    f"{existing.title!r} and {page.title!r}.",
                    where=page.where,
                )
        self.pages.append(page)

    def roles(self, *roles: Role) -> Admin:
        """Declare roles. They compile to ``sillo.permissions`` groups on sync."""
        self.auth = self.auth.with_(roles=(*self.auth.roles, *roles))
        return self

    def slot(self, name: str, component: str) -> Admin:
        """Mount one of your own components into a named region of the shell.

        ``admin.slot("list.toolbar", "acme/ExportButton")``. The component is
        loaded from your application's own build, so this needs your Vite
        setup and not ours — which is the middle rung between theme tokens and
        ejecting.
        """
        self.slots[name] = component
        return self

    # -------------------------------------------------------------- look-ups

    def resource_for(self, model: type) -> Resource | None:
        """The resource registered for *model*, if there is one."""
        return self._by_model.get(model)

    def at(self, slug_: str) -> Resource | None:
        """The resource at a URL slug."""
        return self._by_slug.get(slug_)

    @property
    def permissions(self) -> tuple[str, ...]:
        """Every permission this site declares, sorted.

        What ``warder permissions sync`` writes, and what a role may name.
        Derived from what is registered, so it cannot fall behind.
        """
        found = {name for resource in self.resources for name in resource.permissions}
        found.add(f"{self.name}.access")
        return tuple(sorted(found))

    def navigation(
        self, groups: typing.Mapping[str, bool] | None = None
    ) -> list[dict[str, typing.Any]]:
        """The sidebar, as groups of links.

        *groups* optionally filters to what the current user may see — the
        route layer passes the result of the access checks, so a resource
        nobody may view is not merely disabled in the nav, it is absent.
        """
        buckets: dict[str, list[dict[str, typing.Any]]] = {}
        listed: tuple[Resource | Page, ...] = (*self.resources, *self.pages)
        for item in listed:
            if item.hidden:
                continue
            if groups is not None and not groups.get(item.key, True):
                continue
            entry = {
                "key": item.key,
                "label": item.plural if isinstance(item, Resource) else item.title,
                "href": item.route(self.prefix),
                "icon": item.icon,
                "weight": item.weight,
                "kind": "resource" if isinstance(item, Resource) else "page",
            }
            buckets.setdefault(item.group or "", []).append(entry)

        ordered = sorted(
            buckets,
            key=lambda name: (
                self.group_order.index(name)
                if name in self.group_order
                else len(self.group_order),
                name,
            ),
        )
        return [
            {
                "label": name,
                "items": sorted(buckets[name], key=lambda e: (e["weight"], e["label"])),
            }
            for name in ordered
        ]

    # ------------------------------------------------------------ validation

    def check(self) -> list[DeclarationError]:
        """Everything wrong that can be found without touching the ORM.

        Model references are :meth:`bind`'s job. These are not, so they are
        available to a test that never defines a model — which is most of
        them.
        """
        problems: list[DeclarationError] = []
        declared = set(self.permissions)
        role_names = set(self.auth.role_map)

        for role in self.auth.roles:
            for parent in role.inherits:
                if parent not in role_names:
                    problems.append(
                        DeclarationError(
                            f"Role {role.name!r} inherits {parent!r}, "
                            "which is not declared.",
                            where=role.where,
                            got=parent,
                            options=role_names,
                        )
                    )
            if role.unrestricted:
                continue
            for grant in role.grants:
                if grant not in declared:
                    problems.append(
                        DeclarationError(
                            f"Role {role.name!r} grants {grant!r}, "
                            "which no registered resource declares.",
                            where=role.where,
                            got=grant,
                            options=declared,
                        )
                    )

        for resource in self.resources:
            problems.extend(_check_resource(resource))
        return problems

    def bind(self) -> dict[str, Bound]:
        """Resolve every resource against its model, deriving what was left out.

        This is where ``Resource(Post)`` with no screens becomes a list, a form
        and a detail page, and where every field reference is checked against
        the model. Raises on the first problem, with the line the declaration
        was written on.

        Separate from :meth:`check` because the two need different things: this
        one needs models, that one needs nothing.
        """
        from warder.resolve import bind as bind_resource
        from warder.resolve import check as check_resource

        problems: list[DeclarationError] = []
        for resource in self.resources:
            if getattr(resource.model, "_meta", None) is None:
                problems.append(
                    DeclarationError(
                        f"Resource({resource.model.__name__}) is not a "
                        "sillo.record model — it has no _meta.",
                        hint="Warder resolves declarations against the ORM's "
                        "own metadata.",
                        where=resource.where,
                    )
                )
                continue
            problems.extend(check_resource(resource))
        if problems:
            raise problems[0]
        self.bound = {
            resource.slug: bind_resource(resource) for resource in self.resources
        }
        return self.bound

    def mount(self, app: typing.Any) -> Admin:
        """Register the admin's routes on *app*, after checking every declaration.

        The checks run first and raise on the first problem, so a start-up that
        gets past this line has an admin whose every reference resolves. A
        misspelled column should never become an empty cell in production.
        """
        problems = self.check()
        if problems:
            raise problems[0]
        self.bind()
        try:
            from warder.routes import build
        except ImportError as missing:
            # Almost always the framework: Warder needs the context API, and an
            # older `sillo-framework` has no `sillo.responses` at all. Naming
            # the import that failed turns a mystifying NotConfigured into an
            # actionable one.
            raise NotConfigured(
                f"Warder's routes could not be imported: {missing}. "
                "Warder needs Sillo's context API (HttpContext, ctx-first "
                "handlers, sillo.responses), which is the framework's v1."
            ) from missing
        build(self, app)
        self.mounted = app
        return self

    async def render(
        self, ctx: typing.Any, screen: List, rows: typing.Any, **options: typing.Any
    ) -> typing.Any:
        """Draw a :class:`~warder.screens.List` in your own route, over *rows*.

        The declarations are usable outside the admin, and this is the seam::

            ORDERS = List(Column("id"), Column.money("total"))

            @app.get("/team/orders")
            async def team_orders(ctx: HttpContext):
                return await admin.render(ctx, ORDERS,
                                          Order.filter(team_id=ctx.user.team_id))
        """
        from warder.routes import render_list

        return await render_list(self, ctx, screen, rows, **options)

    def __repr__(self) -> str:
        return (
            f"Admin({self.title!r}, prefix={self.prefix!r}, "
            f"{len(self.resources)} resources, {len(self.pages)} pages)"
        )


def _check_resource(resource: Resource) -> list[DeclarationError]:
    """Problems findable from the declaration alone, without the model."""
    problems: list[DeclarationError] = []
    screen = resource.list
    keys: set[str] = set()
    action_keys: set[str] = set()

    for column in screen.columns if screen else ():
        if column.key in keys:
            problems.append(
                DeclarationError(
                    f"Resource({resource.model.__name__}).list has two columns "
                    f"keyed {column.key!r}.",
                    hint="Give one of them a different label, or a different name.",
                    where=column.where,
                )
            )
        keys.add(column.key)

    filter_keys: set[str] = set()
    for filter_ in screen.filters if screen else ():
        if filter_.key in filter_keys:
            problems.append(
                DeclarationError(
                    f"Resource({resource.model.__name__}).list has two filters "
                    f"keyed {filter_.key!r}, so they would share a query parameter.",
                    where=filter_.where,
                )
            )
        filter_keys.add(filter_.key)

    for total in screen.totals if screen else ():
        if total not in keys:
            problems.append(
                DeclarationError(
                    f"Resource({resource.model.__name__}).list totals {total!r}, "
                    "which is not one of its columns.",
                    where=screen.where if screen else resource.where,
                    got=total,
                    options=keys,
                )
            )

    from_list = (*screen.actions, *screen.row_actions) if screen else ()
    for action in (*from_list, *resource.actions):
        if action.key in action_keys:
            problems.append(
                DeclarationError(
                    f"Resource({resource.model.__name__}) has two actions named "
                    f"{action.key!r}.",
                    hint="Pass name= to tell them apart.",
                    where=action.where,
                )
            )
        action_keys.add(action.key)

    if resource.form is not None:
        names: set[str] = set()
        for field in resource.form.fields:
            if field.name in names:
                problems.append(
                    DeclarationError(
                        f"Resource({resource.model.__name__}).form has two fields "
                        f"named {field.name!r}.",
                        where=field.where,
                    )
                )
            names.add(field.name)
            if field.show is not None:
                missing = field.show.fields() - {f.name for f in resource.form.fields}
                for name in sorted(missing):
                    problems.append(
                        DeclarationError(
                            f"Field {field.name!r} is shown when {name!r} has a value, "
                            "but that field is not on this form.",
                            where=field.where,
                            got=name,
                            options=names,
                        )
                    )
    return problems
