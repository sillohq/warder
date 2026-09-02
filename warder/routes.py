"""The admin's routes.

One route table, generated from the declarations. Adding a resource adds nine
routes; nothing here is written per model, and nothing per model needs to be.

Every handler follows the same shape, and it is worth stating once:

1. **The gate first.** Nothing below runs for someone who may not be here.
2. **Scope before anything reads a row.** ``resource.rows`` applies the
   resource's own queryset and then this person's scope, so a row outside your
   scope is a 404 rather than a 403 — telling you a row exists that you may not
   see is itself a disclosure.
3. **Permission per action**, checked on the server, on the row where there is
   one. The interface hides buttons; that is a courtesy, not a control.
4. **Render, or redirect.** A mutation always redirects, so a refresh does not
   repeat it.

Handlers return Inertia responses: a page object for the client-side router, a
full document for a fresh tab, with the same props either way.
"""

from __future__ import annotations

import os
import secrets
import typing
import warnings

from sillo import responses
from sillo.core.routing import Group, Route
from sillo.static import StaticFiles

from warder import inertia, props
from warder._async import awaited
from warder.assets import Assets
from warder.errors import ActionFailed, Denied
from warder.results import Outcome

if typing.TYPE_CHECKING:
    from sillo import HttpContext
    from sillo.core.http.response import BaseResponse

    from warder.resolve import Bound
    from warder.site import Admin

__all__ = ["build", "render_list", "routes"]

#: Where a mutation's message waits for the redirect that follows it.
FLASH = "_warder_flash"


def build(admin: Admin, app: typing.Any) -> None:
    """Register the admin on *app*: sessions, then assets, then routes."""
    assets = Assets()
    admin.bundle = assets
    _ensure_sessions(admin, app)
    _mount_assets(admin, app)
    for route in routes(admin, assets):
        app.router.add_route(route)


def _ensure_sessions(admin: Admin, app: typing.Any) -> None:
    """Install session middleware if the application has none.

    The admin owns a sign-in page, and a sign-in page without a session is a
    form that forgets you. Mounting one on an application that has not thought
    about sessions yet should work, so this adds the middleware rather than
    failing at the first login with a message about middleware.

    An application that already installed its own is left alone — that is the
    shared-session arrangement, and replacing it would sign everybody out.
    """
    if not admin.sessions:
        return
    try:
        from sillo.session import SessionConfig, SessionMiddleware
    except ImportError:  # pragma: no cover - sessions ship with the framework
        return

    installed = getattr(app, "middleware_stack", None) or getattr(
        app, "_middleware", ()
    )
    for entry in installed or ():
        if type(entry).__name__ == "SessionMiddleware":
            return

    policy = admin.auth.session
    app.use(
        SessionMiddleware(
            config=SessionConfig(
                session_cookie_name=policy.cookie,
                session_cookie_secure=policy.secure,
                session_cookie_httponly=True,
                session_cookie_samesite=policy.same_site,
                # The cookie outlives the absolute lifetime by a minute, so the
                # *server* is what ends a session. A cookie that vanishes on its
                # own gives you a login page and no explanation; the backend can
                # at least say why.
                session_expiration_time=int(policy.absolute or 43200) + 60,
            ),
            secret_key=session_secret(admin),
        )
    )


def session_secret(admin: Admin) -> str:
    """The key session cookies are signed with.

    From ``Admin(secret=)``, then ``WARDER_SECRET_KEY``, then
    ``SILLO_SECRET_KEY``. Failing all three a random one is generated and said
    so out loud: it works, and every restart signs everybody out — which is
    fine on a laptop and is not a thing to discover in production from a
    support ticket.
    """
    given = (
        admin.secret
        or os.environ.get("WARDER_SECRET_KEY")
        or os.environ.get("SILLO_SECRET_KEY")
    )
    if given:
        return given

    warnings.warn(
        "Warder generated a random session key, so every restart signs "
        "everyone out. Set WARDER_SECRET_KEY, or pass Admin(secret=...), "
        "before deploying this.",
        RuntimeWarning,
        stacklevel=3,
    )
    return secrets.token_urlsafe(48)


def _mount_assets(admin: Admin, app: typing.Any) -> None:
    """Serve the built bundle under the admin's own prefix.

    Under the prefix rather than at the application root, so mounting an admin
    never claims a path the application might want and one process can carry
    two admins.
    """
    static = StaticFiles(
        directory=str(Assets().directory),
        cache_control="public, max-age=31536000, immutable",
    )
    app.router.routes.append(Group(path=f"{admin.prefix}/assets", app=static))


def routes(admin: Admin, assets: Assets | None = None) -> list[Route]:
    """Every route this admin serves."""
    assets = assets or Assets()
    site = _Site(admin, assets)
    prefix = admin.prefix
    name = admin.name
    built: list[Route] = [
        Route(
            f"{prefix}/login", site.login, methods=["GET", "POST"], name=f"{name}.login"
        ),
        Route(
            f"{prefix}/logout",
            site.logout,
            methods=["POST", "GET"],
            name=f"{name}.logout",
        ),
        Route(f"{prefix}", site.dashboard, methods=["GET"], name=f"{name}.dashboard"),
        Route(
            f"{prefix}/",
            site.dashboard,
            methods=["GET"],
            name=f"{name}.dashboard.slash",
        ),
    ]

    for declared in admin.pages:
        built.append(
            Route(
                declared.route(prefix),
                site.page(declared),
                methods=["GET"],
                name=f"{name}.page.{declared.key}",
            )
        )

    for resource in admin.resources:
        base = resource.route(prefix)
        slug = resource.slug
        built += [
            Route(base, site.index(slug), methods=["GET"], name=f"{name}.{slug}.index"),
            Route(
                f"{base}/new",
                site.new(slug),
                methods=["GET"],
                name=f"{name}.{slug}.new",
            ),
            Route(
                base, site.create(slug), methods=["POST"], name=f"{name}.{slug}.create"
            ),
            Route(
                f"{base}/options/{{field}}",
                site.options(slug),
                methods=["GET"],
                name=f"{name}.{slug}.options",
            ),
            Route(
                f"{base}/actions/{{action}}",
                site.act(slug),
                methods=["POST"],
                name=f"{name}.{slug}.action",
            ),
            Route(
                f"{base}/{{id}}",
                site.show(slug),
                methods=["GET"],
                name=f"{name}.{slug}.show",
            ),
            Route(
                f"{base}/{{id}}/edit",
                site.edit(slug),
                methods=["GET"],
                name=f"{name}.{slug}.edit",
            ),
            Route(
                f"{base}/{{id}}",
                site.update(slug),
                methods=["POST", "PATCH", "PUT"],
                name=f"{name}.{slug}.update",
            ),
            Route(
                f"{base}/{{id}}",
                site.destroy(slug),
                methods=["DELETE"],
                name=f"{name}.{slug}.destroy",
            ),
        ]
    return built


class _Site:
    """The handlers, closed over one admin.

    Every handler takes ``**_params``: Sillo calls a route handler as
    ``handler(ctx, **path_params)``, and the values are read back off the
    context rather than from the signature — so a route's path can change
    without its handler's parameters having to agree.

    A class rather than a module of functions because every handler needs the
    same three things — the admin, its bound resources, its assets — and
    threading those through as arguments would mean a closure per route anyway.
    """

    def __init__(self, admin: Admin, assets: Assets) -> None:
        self.admin = admin
        self.assets = assets

    # ---------------------------------------------------------------- render

    async def render(
        self, ctx: HttpContext, component: str, page: typing.Mapping[str, typing.Any]
    ) -> BaseResponse:
        """One page, with the shell props every screen carries."""
        shell = await props.shell(self.admin, ctx)
        return await inertia.render(
            ctx,
            component,
            {**shell, **page},
            version=self.assets.version,
            document=lambda payload, _page: self.assets.document(self.admin, payload),
        )

    # ------------------------------------------------------------------ gate

    async def guard(self, ctx: HttpContext) -> BaseResponse | None:
        """``None`` when this person may be here, a response when they may not.

        Anonymous gets the login page; signed-in-but-not-admitted gets told no.
        Sending a signed-in user to a login page builds a loop they cannot
        escape by signing in again.
        """
        from warder.access import current_user

        if await self.admin.auth.may_enter(ctx):
            return None
        target = f"{self.admin.prefix}/login"
        if current_user(ctx) is None:
            if inertia.is_inertia(ctx):
                return inertia.location(target)
            return responses.redirect(target, status_code=302)
        return await self.render(ctx, "Denied", {"reason": "gate"})

    def resource(self, slug: str) -> Bound:
        bound = self.admin.bound.get(slug)
        if bound is None:  # pragma: no cover - routes come from the same map
            raise KeyError(slug)
        return bound

    # ------------------------------------------------------------- dashboard

    async def dashboard(self, ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
        denied = await self.guard(ctx)
        if denied is not None:
            return denied
        board = self.admin.dashboard
        cards = []
        for card in board.cards if board else ():
            if card.gate is not None and not await card.gate.allows(ctx):
                continue
            cards.append(await _card_props(ctx, card))
        return await self.render(
            ctx,
            "Dashboard",
            {
                "title": board.title if board else "Overview",
                "columns": board.columns if board else 4,
                "cards": cards,
                "description": board.description if board else None,
            },
        )

    def page(self, declared: typing.Any) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            if declared.gate is not None and not await declared.gate.allows(ctx):
                return await self.render(ctx, "Denied", {"reason": "page"})
            result = await awaited(declared.render(ctx))
            if isinstance(result, Outcome):
                return self.outcome(ctx, result, fallback=self.admin.prefix)
            return await self.render(
                ctx,
                declared.component or "Page",
                {
                    "title": declared.title,
                    "description": declared.description,
                    "page": props.jsonable(result or {}),
                },
            )

        return handler

    # ----------------------------------------------------------------- login

    def _login_props(self, **extra: typing.Any) -> dict[str, typing.Any]:
        login = self.admin.auth.login
        return {
            "title": self.admin.title,
            "brand": self.admin.brand,
            "field": login.field,
            "message": login.message,
            "remember": bool(login.remember),
            "reset": login.password_reset,
            "providers": [str(p) for p in login.providers],
            "errors": {},
            **extra,
        }

    async def login(self, ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
        if ctx.method == "GET":
            if await self.admin.auth.may_enter(ctx):
                return responses.redirect(self.admin.prefix, status_code=302)
            return await self.render(ctx, "Login", self._login_props())

        backend = self.admin.auth.resolve()
        payload = await _payload(ctx)
        identity = str(payload.get(self.admin.auth.login.field) or "")
        secret = str(payload.get("password") or "")

        if await backend.login(ctx, identity, secret):
            return inertia.redirect(ctx, self.admin.prefix)

        # One message for a wrong name, a wrong password and an account that
        # does not exist, so the form cannot be used to find out which accounts
        # do. The only thing worth distinguishing is being locked out, because
        # otherwise you keep trying a password that is already correct.
        wait = getattr(backend, "wait", None)
        seconds = wait(ctx, identity) if wait else 0
        message = (
            f"Too many attempts. Try again in {seconds}s."
            if seconds
            else "Those details did not match."
        )
        return await self.render(
            ctx, "Login", self._login_props(errors={"__all__": message})
        )

    async def logout(self, ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
        await self.admin.auth.resolve().logout(ctx)
        return inertia.redirect(ctx, f"{self.admin.prefix}/login", status=303)

    # ------------------------------------------------------------------ list

    def index(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            if not await bound.resource.allows(ctx, "view"):
                return await self.render(ctx, "Denied", {"reason": "view"})

            query = props.Query(ctx, bound.list)
            rows = await props.apply(ctx, bound, _all(bound), query)
            total = await rows.count()
            page = await rows.offset(query.offset).limit(query.per_page)
            return await self.render(
                ctx,
                "List",
                await props.list_page(self.admin, bound, ctx, page, query, total=total),
            )

        return handler

    # ------------------------------------------------------------------ form

    def new(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            if not await bound.resource.allows(ctx, "add"):
                return await self.render(ctx, "Denied", {"reason": "add"})
            return await self.render(
                ctx, "Form", await props.form_page(self.admin, bound, ctx)
            )

        return handler

    def edit(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            row = await self.find(ctx, bound)
            if row is None:
                return responses.not_found()
            if not await bound.resource.allows(ctx, "change", row):
                return await self.render(ctx, "Denied", {"reason": "change"})
            return await self.render(
                ctx, "Form", await props.form_page(self.admin, bound, ctx, row=row)
            )

        return handler

    def create(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            if not await bound.resource.allows(ctx, "add"):
                return await self.render(ctx, "Denied", {"reason": "add"})
            return await self.save(ctx, bound, row=None)

        return handler

    def update(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            row = await self.find(ctx, bound)
            if row is None:
                return responses.not_found()
            if not await bound.resource.allows(ctx, "change", row):
                return await self.render(ctx, "Denied", {"reason": "change"})
            return await self.save(ctx, bound, row=row)

        return handler

    def destroy(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            row = await self.find(ctx, bound)
            if row is None:
                return responses.not_found()
            if not await bound.resource.allows(ctx, "delete", row):
                return await self.render(ctx, "Denied", {"reason": "delete"})
            label = str(row)
            await row.delete()
            _flash(ctx, f"Deleted {label}.")
            return inertia.redirect(
                ctx, bound.resource.route(self.admin.prefix), status=303
            )

        return handler

    # ---------------------------------------------------------------- detail

    def show(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            row = await self.find(ctx, bound)
            if row is None:
                return responses.not_found()
            if not await bound.resource.allows(ctx, "view", row):
                return await self.render(ctx, "Denied", {"reason": "view"})
            return await self.render(
                ctx, "Detail", await props.detail_page(self.admin, bound, ctx, row)
            )

        return handler

    # --------------------------------------------------------------- actions

    def act(self, slug: str) -> typing.Callable[..., typing.Any]:
        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            key = str(ctx.path_params.get("action"))
            action = bound.list.action_map.get(key)
            back = bound.resource.route(self.admin.prefix)
            if action is None:
                return responses.not_found()

            needed = "delete" if action.key == "delete" else "change"
            if not await bound.resource.allows(ctx, needed):
                return await self.render(ctx, "Denied", {"reason": needed})
            if not await action.allowed(ctx):
                return await self.render(ctx, "Denied", {"reason": "action"})

            payload = await _payload(ctx)
            if action.needs_selection and not payload.get("ids"):
                _flash(ctx, "Nothing was selected.", tone="warning")
                return inertia.redirect(ctx, back, status=303)

            rows = await self.selected(ctx, bound, payload)
            try:
                result = await _run(action, ctx, rows, payload.get("values") or {})
            except (ActionFailed, Denied) as stopped:
                _flash(ctx, stopped.message, tone="danger")
                return inertia.redirect(ctx, back, status=303)
            return self.outcome(ctx, result, fallback=back)

        return handler

    def outcome(
        self, ctx: HttpContext, result: typing.Any, *, fallback: str
    ) -> BaseResponse:
        """Turn what an action returned into a response.

        ``None`` means "it worked, reload", which is what most actions want and
        what happens when a handler writes no return at all.
        """
        if not isinstance(result, Outcome):
            return inertia.redirect(ctx, fallback, status=303)
        if result.kind == "nothing":
            return responses.empty(status_code=204)
        if result.kind == "download":
            return _download(result)
        if result.message:
            _flash(ctx, result.message, tone=result.tone)
        if result.kind == "go":
            return inertia.redirect(ctx, str(result.option("url")), status=303)
        if result.kind == "modal":
            return responses.json(
                {
                    "modal": result.option("component"),
                    "props": result.option("props"),
                    "title": result.message,
                }
            )
        return inertia.redirect(ctx, fallback, status=303)

    # --------------------------------------------------------------- pickers

    def options(self, slug: str) -> typing.Callable[..., typing.Any]:
        """Search the far side of a relation, for a picker.

        Over the wire rather than preloaded, which is the difference between a
        foreign key to ``Country`` and one to ``Customer``.
        """

        async def handler(ctx: HttpContext, **_params: typing.Any) -> BaseResponse:
            denied = await self.guard(ctx)
            if denied is not None:
                return denied
            bound = self.resource(slug)
            if not await bound.resource.allows(ctx, "view"):
                return await self.render(ctx, "Denied", {"reason": "view"})

            described = bound.schema.get(str(ctx.path_params.get("field")))
            if described is None or described.related is None:
                return responses.not_found()

            from warder.resolve import display_for

            display = display_for(described.related)
            rows = typing.cast(typing.Any, described.related).all()
            term = ctx.query_params.get("q")
            if term and display:
                rows = rows.filter(**{f"{display}__icontains": term})
            found = await rows.limit(20)
            return responses.json(
                {
                    "options": [
                        {
                            "id": props.jsonable(row.pk),
                            # What the picker *searches* is what it shows. A
                            # model whose __str__ is the default would
                            # otherwise offer a list of "<Author>".
                            "label": _option_label(row, display),
                        }
                        for row in found
                    ]
                }
            )

        return handler

    # ---------------------------------------------------------------- shared

    async def find(self, ctx: HttpContext, bound: Bound) -> typing.Any:
        """One row, within this person's scope.

        Outside the scope is ``None`` and therefore a 404, not a 403: telling
        someone a row exists that they may not see is itself a disclosure.
        """
        rows = await bound.resource.rows(ctx, _all(bound))
        key = ctx.path_params.get("id")
        return await rows.filter(**{bound.schema.pk: key}).first()

    async def selected(
        self, ctx: HttpContext, bound: Bound, payload: typing.Mapping[str, typing.Any]
    ) -> typing.Any:
        """The rows an action runs over — a queryset, never a list of ids.

        Scoped first, so an action can never touch a row its caller could not
        have listed, and left unevaluated, so publishing forty thousand rows is
        one statement.
        """
        rows = await bound.resource.rows(ctx, _all(bound))
        ids = payload.get("ids")
        if ids:
            return rows.filter(**{f"{bound.schema.pk}__in": list(ids)})
        query = props.Query(ctx, bound.list)
        sent = payload.get("filters") or {}
        for filter_ in bound.list.filters:
            raw = sent.get(filter_.key) or query.values.get(filter_.key)
            if raw is not None:
                rows = filter_.apply(rows, raw)
        return rows

    async def save(
        self, ctx: HttpContext, bound: Bound, *, row: typing.Any
    ) -> BaseResponse:
        """Write a submission, or return the form with what it got wrong."""
        payload = await _payload(ctx)
        form = bound.form
        submitted = {
            name: value for name, value in payload.items() if not name.startswith("_")
        }

        writable = []
        for field in form.fields:
            # A field this person cannot write, or that its condition says is
            # not on the form, is dropped rather than trusted. The browser
            # decides what to draw; the server decides what to save.
            if not field.editable:
                continue
            if field.access is not None and not await field.access.allows(
                ctx, "change", row
            ):
                continue
            if field.show is not None and not field.show.holds(submitted):
                continue
            writable.append(field)

        values = {
            field.name: submitted.get(field.name)
            for field in writable
            if field.name in submitted
        }
        errors: dict[str, typing.Any] = dict(form.errors(values))
        if not errors:
            errors = await _form_errors(form, ctx, values, row)

        if errors:
            return await self.render(
                ctx,
                "Form",
                await props.form_page(
                    self.admin, bound, ctx, row=row, values=submitted, errors=errors
                ),
            )

        created = row is None
        target = row if row is not None else bound.model()
        for field in writable:
            if field.name not in values:
                continue
            described = bound.schema.get(field.name)
            value = values[field.name]
            if described is not None and described.kind == "relation":
                # Written through the raw column, so setting a foreign key is
                # one statement and no extra query for the far row.
                setattr(target, str(described.column), value or None)
                continue
            if described is not None and described.kind == "password" and not value:
                # An empty password box on an edit form means "leave the stored
                # hash alone", which is the only behaviour that is usable.
                continue
            setattr(target, field.name, value)

        if form.on_save is not None:
            await awaited(form.on_save(ctx, target, values))

        try:
            await target.save()
        except Exception as refused:
            # A constraint the form could not know about — a unique index, a
            # NOT NULL on a column nobody put on the form. The person who
            # pressed Save should get their work back with an explanation, not
            # a 500 and an empty form.
            if not _is_integrity(refused):
                raise
            return await self.render(
                ctx,
                "Form",
                await props.form_page(
                    self.admin,
                    bound,
                    ctx,
                    row=row,
                    values=submitted,
                    errors={"__all__": _readable(refused)},
                ),
            )

        _flash(ctx, f"{'Created' if created else 'Saved'} {target}.")
        base = bound.resource.route(self.admin.prefix)
        key = props.jsonable(getattr(target, bound.schema.pk))
        return inertia.redirect(ctx, f"{base}/{key}", status=303)


# ------------------------------------------------------------------- helpers


async def render_list(
    admin: Admin,
    ctx: HttpContext,
    screen: typing.Any,
    rows: typing.Any,
    *,
    component: str = "Embedded",
    title: str | None = None,
) -> BaseResponse:
    """Draw a :class:`~warder.screens.List` in someone else's route.

    The declarations are usable outside the admin, and this is the seam. The
    screen is rendered over the queryset you hand it — no resource, no
    registration, and no admin permission consulted, because it is *your* route
    and you have already decided who may be on it.
    """
    from warder.resolve import Bound
    from warder.resource import Resource
    from warder.schema import Schema
    from warder.screens import Detail, Form

    model = rows.model
    resource = Resource(model, list=screen)
    bound = Bound(resource, Schema.of(model), screen, Form(), Detail())
    query = props.Query(ctx, screen)
    narrowed = await props.apply(ctx, bound, rows, query)
    total = await narrowed.count()
    page = await narrowed.offset(query.offset).limit(query.per_page)
    body = await props.list_page(admin, bound, ctx, page, query, total=total)
    shell = await props.shell(admin, ctx)
    assets = Assets()
    return await inertia.render(
        ctx,
        component,
        {**shell, **body, "title": title or resource.plural},
        version=assets.version,
        document=lambda payload, _page: assets.document(admin, payload),
    )


def _option_label(row: typing.Any, display: str | None) -> str:
    """What a relation picker calls a row.

    The model's own ``__str__`` when it has one, because that is the name the
    application chose; the searched column when it does not.
    """
    named = str(row)
    if not named.startswith("<") and named != object.__repr__(row):
        return named
    if display is not None:
        return str(getattr(row, display, named))
    return named


def _all(bound: Bound) -> typing.Any:
    """Every row of a bound resource's model, before anything narrows it."""
    return typing.cast(typing.Any, bound.model).all()


async def _payload(ctx: HttpContext) -> dict[str, typing.Any]:
    """The submitted body, however it was sent.

    Inertia posts JSON unless the form carries a file, in which case it is
    multipart. Both arrive here as one mapping.
    """
    if ctx.is_json:
        try:
            body = await ctx.json
        except ValueError:
            return {}
        return dict(body) if isinstance(body, dict) else {}
    try:
        form = await ctx.form
    except Exception:  # pragma: no cover - malformed multipart
        return {}
    return {key: form.get(key) for key in form}


async def _form_errors(
    form: typing.Any,
    ctx: HttpContext,
    values: typing.Mapping[str, typing.Any],
    row: typing.Any,
) -> dict[str, typing.Any]:
    """Whole-form checks, which run only once every field passed its own."""
    found: dict[str, typing.Any] = {}
    for check in form.validate:
        result = await awaited(check(ctx, values, row))
        if isinstance(result, dict):
            found.update(result)
        elif result:
            found["__all__"] = str(result)
    return found


async def _run(
    action: typing.Any,
    ctx: HttpContext,
    rows: typing.Any,
    values: typing.Mapping[str, typing.Any],
) -> typing.Any:
    """Call an action the way its declaration says it is called.

    ``fields=`` means ``(ctx, rows, values)``; no ``fields=`` means
    ``(ctx, rows)``. Decided by the declaration, visibly, and never by
    inspecting the handler's signature.
    """
    if action.builtin:
        return await _builtin(action, rows)
    return await awaited(
        action.run(ctx, rows, dict(values))
        if action.collects
        else action.run(ctx, rows)
    )


async def _builtin(action: typing.Any, rows: typing.Any) -> Outcome:
    """``Action.delete``, which the resource performs rather than a handler."""
    from warder.results import notice

    if action.key == "delete":
        count = await rows.count()
        await rows.delete()
        return notice(f"Deleted {count} {'row' if count == 1 else 'rows'}.")
    return notice("Nothing to do.")


def _is_integrity(error: Exception) -> bool:
    """Whether *error* is the database refusing a write, rather than a bug.

    Matched by class name so this module does not import the ORM's exception
    hierarchy for one check, and so a different backend's equivalent is
    recognised too.
    """
    names = {base.__name__ for base in type(error).__mro__}
    return bool(names & {"IntegrityError", "ValidationError"})


def _readable(error: Exception) -> str:
    """The database's complaint, in a sentence a person can act on."""
    text = str(error).strip()
    if "UNIQUE constraint failed" in text or "duplicate key" in text.lower():
        column = text.rsplit(".", 1)[-1].strip(" :\"'")
        return f"Something with that {column or 'value'} already exists."
    if "NOT NULL constraint failed" in text:
        column = text.rsplit(".", 1)[-1].strip(" :\"'")
        return f"{column or 'A required value'} cannot be empty."
    return f"The database refused this: {text}"


def _download(result: Outcome) -> BaseResponse:
    url = result.option("url")
    if url:
        return responses.redirect(str(url), status_code=303)
    content = result.option("content")
    body = content.encode() if isinstance(content, str) else content
    filename = result.option("filename")
    return responses.raw(
        body,
        content_type=str(result.option("content_type")),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _card_props(ctx: HttpContext, card: typing.Any) -> dict[str, typing.Any]:
    data: typing.Any = None
    if card.load is not None:
        data = await awaited(card.load(ctx))
    return {
        "key": card.key,
        "kind": card.kind,
        "title": card.title,
        "span": card.span,
        "icon": card.icon,
        "description": card.description,
        "data": props.jsonable(data),
        "options": {
            name: props.jsonable(value)
            for name, value in card.options.items()
            if not callable(value)
        },
    }


def _flash(ctx: HttpContext, message: str, *, tone: str = "success") -> None:
    """Leave a message for the page after the redirect.

    In the session rather than the query string: a message in the URL survives
    a bookmark, a share and a refresh, and reappears every time.
    """
    try:
        session = ctx.session
    except (AttributeError, ValueError, LookupError, AssertionError):
        # No session middleware: the write still happens, the message is just
        # not carried across the redirect. Losing a flash is not worth a 500.
        return
    try:
        queued = list(session.get(FLASH) or [])
        queued.append({"tone": tone, "message": message})
        session[FLASH] = queued
    except (AttributeError, TypeError):  # pragma: no cover - exotic session
        return
