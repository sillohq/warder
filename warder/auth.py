"""Authentication, and the four questions permissions answer.

The admin brings its own login and its own user model, and hands both to yours
the moment you say so. Nothing here is a second authorisation system: it
compiles onto ``sillo.permissions``, which already ships ``Permission``,
``Group``, ``UserPermission``, ``UserGroup`` and ``GroupPermission``, and onto
the ``PermissionMixin`` your user model may already carry.

::

    Admin(
        title="Acme Ops",
        auth=Auth(
            users=User,
            backend=SessionAuth(),
            gate=Gate.staff(),
            session=Session(idle="30m", absolute="12h", concurrent=1),
            login=Login(throttle="5/15m", remember=True),
            mfa=MFA.totp(required=Gate.role("owner")),
            impersonation=Impersonation(gate=Gate.permission("users.impersonate")),
            audit=Audit(retain="1y", redact=["password", "token", "secret"]),
        ),
    )

Omit ``auth=`` entirely and you get the bundled user model, a session backend
and ``is_staff`` as the gate — which is the right default for an internal tool
and the wrong one for anything sharing a public user table. Three arrangements
are supported, in increasing order of integration:

1. **Standalone** — the bundled user, an admin-only login.
2. **Shared model, admin login** — ``users=User``, ``gate=Gate.staff()``.
3. **Shared model, shared session** — ``backend=`` the application's own
   authentication. Signed into the product is signed into the admin, subject
   to the gate.

The third is what most applications want.
"""

from __future__ import annotations

import typing

from warder._check import one_of, positive
from warder._time import parse_duration, parse_rate
from warder.access import Gate, Role
from warder.base import Declaration

__all__ = ["MFA", "Audit", "Auth", "Impersonation", "Login", "Session"]

#: Backends built for an `Auth` that did not bring one, keyed by identity so
#: the throttle inside survives between requests.
_BACKENDS: dict[int, typing.Any] = {}


class Session(Declaration):
    """How long a signed-in session lasts, and how many you may hold.

    Two lifetimes, because they answer different questions. *idle* is "you
    walked away"; *absolute* is "this session is old regardless of how busy
    you have been", and only the second bounds a stolen cookie.
    """

    __slots__ = (
        "idle",
        "absolute",
        "concurrent",
        "revoke_on_password_change",
        "cookie",
        "secure",
        "same_site",
        "visible",
    )
    _fields = __slots__

    idle: float | None
    absolute: float | None
    concurrent: int | None
    revoke_on_password_change: bool
    cookie: str
    secure: bool
    same_site: str
    visible: bool

    def __init__(
        self,
        *,
        idle: str | int | None = "30m",
        absolute: str | int | None = "12h",
        concurrent: int | None = None,
        revoke_on_password_change: bool = True,
        cookie: str = "warder_session",
        secure: bool = True,
        same_site: str = "lax",
        visible: bool = True,
    ) -> None:
        self._init(
            idle=parse_duration(idle),
            absolute=parse_duration(absolute),
            concurrent=(
                positive("concurrent", concurrent) if concurrent is not None else None
            ),
            revoke_on_password_change=revoke_on_password_change,
            cookie=cookie,
            secure=secure,
            same_site=one_of("same_site", same_site, ("lax", "strict", "none")),
            visible=visible,
        )

    def __repr__(self) -> str:
        return f"Session(idle={self.idle}, absolute={self.absolute})"


class Login(Declaration):
    """The sign-in page, and what it will put up with.

    Throttling is per identity *and* per address. Per identity alone lets one
    machine work through a user list; per address alone lets a botnet work
    through one password.
    """

    __slots__ = (
        "throttle",
        "remember",
        "providers",
        "redirect",
        "message",
        "field",
        "lockout",
        "password_reset",
    )
    _fields = __slots__

    throttle: tuple[int, float] | None
    remember: bool | float
    providers: tuple[typing.Any, ...]
    redirect: str
    message: str | None
    field: str
    lockout: float | None
    password_reset: bool

    def __init__(
        self,
        *,
        throttle: str | None = "5/15m",
        remember: bool | str = True,
        providers: typing.Sequence[typing.Any] = (),
        redirect: str = "",
        message: str | None = None,
        field: str = "email",
        lockout: str | None = None,
        password_reset: bool = True,
    ) -> None:
        self._init(
            throttle=parse_rate(throttle),
            remember=parse_duration(remember)
            if isinstance(remember, str)
            else remember,
            providers=tuple(providers),
            redirect=redirect,
            message=message,
            field=field,
            lockout=parse_duration(lockout),
            password_reset=password_reset,
        )

    @property
    def attempts(self) -> int | None:
        return self.throttle[0] if self.throttle else None

    @property
    def window(self) -> float | None:
        return self.throttle[1] if self.throttle else None

    def __repr__(self) -> str:
        return f"Login(throttle={self.attempts}/{self.window})"


class MFA(Declaration):
    """A second factor, demanded of some people and not others.

    ``required=`` takes a :class:`~warder.access.Gate`, which is what makes
    this usable: an owner can be made to enrol without every read-only support
    account being made to as well. Rolling it out to everyone at once is the
    version that gets switched off again on the second day.
    """

    __slots__ = (
        "method",
        "required",
        "recovery_codes",
        "issuer",
        "step_up",
        "grace",
        "remember_device",
    )
    _fields = __slots__

    METHODS = ("totp", "webauthn", "email")

    method: str
    required: Gate | bool
    recovery_codes: int
    issuer: str | None
    step_up: tuple[str, ...]
    grace: float | None
    remember_device: float | None

    def __init__(
        self,
        method: str = "totp",
        *,
        required: Gate | bool = False,
        recovery_codes: int = 10,
        issuer: str | None = None,
        step_up: typing.Sequence[str] = (),
        grace: str | None = None,
        remember_device: str | None = "30d",
    ) -> None:
        self._init(
            method=one_of("MFA method", method, self.METHODS),
            required=required,
            recovery_codes=positive("recovery_codes", recovery_codes),
            issuer=issuer,
            step_up=tuple(step_up),
            grace=parse_duration(grace),
            remember_device=parse_duration(remember_device),
        )

    @classmethod
    def totp(cls, **options: typing.Any) -> MFA:
        """An authenticator app. Works offline and needs no third party."""
        return cls("totp", **options)

    @classmethod
    def webauthn(cls, **options: typing.Any) -> MFA:
        """A passkey or a security key. Phishing-resistant; the one to prefer."""
        return cls("webauthn", **options)

    async def demanded_of(self, ctx: typing.Any) -> bool:
        """Whether this person must have a second factor enrolled."""
        if isinstance(self.required, bool):
            return self.required
        return await self.required.allows(ctx)

    def __repr__(self) -> str:
        return f"MFA({self.method!r}, required={self.required!r})"


class Impersonation(Declaration):
    """Signing in as somebody else, safely enough to be allowed at all.

    Four constraints, and dropping any one of them turns this into a back
    door: it is **gated**, it is **banner-marked** so nobody forgets they are
    in it, it **expires**, and it **cannot escalate** — you may not impersonate
    someone holding a permission you lack, or the gate is decorative.
    """

    __slots__ = ("gate", "banner", "maximum", "audit", "readonly", "reason")
    _fields = __slots__

    gate: Gate
    banner: bool
    maximum: float | None
    audit: bool
    readonly: bool
    reason: bool

    def __init__(
        self,
        *,
        gate: Gate | None = None,
        banner: bool = True,
        maximum: str | int | None = "1h",
        audit: bool = True,
        readonly: bool = False,
        reason: bool = False,
    ) -> None:
        self._init(
            gate=gate if gate is not None else Gate.superuser(),
            banner=banner,
            maximum=parse_duration(maximum),
            audit=audit,
            readonly=readonly,
            reason=reason,
        )

    def __repr__(self) -> str:
        return f"Impersonation(maximum={self.maximum})"


class Audit(Declaration):
    """What was done, by whom, to what, and what changed.

    Field-level diffs, because "Order 4182 was changed" is a log line and
    "status went from held to shipped" is an answer. *redact* is applied to
    the diff, not to the display, so a secret never reaches the audit table in
    the first place.
    """

    __slots__ = (
        "retain",
        "redact",
        "actions",
        "diff",
        "address",
        "request_id",
        "reads",
    )
    _fields = __slots__

    retain: float | None
    redact: tuple[str, ...]
    actions: tuple[str, ...]
    diff: bool
    address: bool
    request_id: bool
    reads: bool

    def __init__(
        self,
        *,
        retain: str | int | None = "1y",
        redact: typing.Sequence[str] = ("password", "token", "secret", "key"),
        actions: typing.Sequence[str] = ("add", "change", "delete"),
        diff: bool = True,
        address: bool = True,
        request_id: bool = True,
        reads: bool = False,
    ) -> None:
        self._init(
            retain=parse_duration(retain),
            redact=tuple(redact),
            actions=tuple(actions),
            diff=diff,
            address=address,
            request_id=request_id,
            reads=reads,
        )

    def redacted(
        self, values: typing.Mapping[str, typing.Any]
    ) -> dict[str, typing.Any]:
        """*values* with anything matching :attr:`redact` replaced.

        Matched as a substring of the field name, so ``redact=["token"]``
        covers ``api_token`` and ``token_hash`` without listing both.
        """
        return {
            name: "[redacted]"
            if any(word in name.lower() for word in self.redact)
            else value
            for name, value in values.items()
        }

    def __repr__(self) -> str:
        return f"Audit(retain={self.retain}, {len(self.redact)} redactions)"


class Auth(Declaration):
    """Everything about who may be here, in one value."""

    __slots__ = (
        "users",
        "backend",
        "gate",
        "permissions",
        "session",
        "login",
        "mfa",
        "impersonation",
        "audit",
        "roles",
    )
    _fields = __slots__

    #: Resolve permissions against the ``sillo.permissions`` tables.
    RECORDS: typing.ClassVar[str] = "records"
    #: Resolve nothing; gates and callables only.
    NONE: typing.ClassVar[str] = "none"

    users: type | None
    backend: typing.Any
    gate: Gate
    permissions: str
    session: Session
    login: Login
    mfa: MFA | None
    impersonation: Impersonation | None
    audit: Audit
    roles: tuple[Role, ...]

    def __init__(
        self,
        *,
        users: type | None = None,
        backend: typing.Any = None,
        gate: Gate | None = None,
        permissions: str = RECORDS,
        session: Session | None = None,
        login: Login | None = None,
        mfa: MFA | None = None,
        impersonation: Impersonation | None = None,
        audit: Audit | None = None,
        roles: typing.Sequence[Role] = (),
    ) -> None:
        if users is not None and not isinstance(users, type):
            raise TypeError(f"Auth(users=) takes a model class, got {users!r}.")
        self._init(
            users=users,
            backend=backend,
            gate=gate if gate is not None else Gate.staff(),
            permissions=one_of("permissions", permissions, (self.RECORDS, self.NONE)),
            session=session or Session(),
            login=login or Login(),
            mfa=mfa,
            impersonation=impersonation,
            audit=audit or Audit(),
            roles=tuple(roles),
        )

    def resolve(self) -> typing.Any:
        """The backend this admin authenticates through.

        Built once and cached on the value, because the throttle it carries
        has to be the *same* throttle across requests — a fresh one per request
        counts to one and never blocks anything.
        """
        if self.backend is not None:
            return self.backend
        cached = _BACKENDS.get(id(self))
        if cached is None:
            from warder.backends import SessionAuth

            cached = _BACKENDS[id(self)] = SessionAuth(self.users, policy=self)
        return cached

    async def user(self, ctx: typing.Any) -> typing.Any:
        """The signed-in account, through whichever backend is in use."""
        backend = self.resolve()
        current = getattr(backend, "current", None)
        if current is not None:
            return await current(ctx)
        # A backend that predates `current` -- or somebody's own three-method
        # object -- still works: fall back to the context's own user.
        from warder.access import context_user

        return context_user(ctx)

    @property
    def role_map(self) -> dict[str, Role]:
        return {role.name: role for role in self.roles}

    def grants_of(self, name: str) -> frozenset[str]:
        """Every permission the named role grants, inheritance followed."""
        roles = self.role_map
        role = roles.get(name)
        return role.expand(roles) if role else frozenset()

    async def may_enter(self, ctx: typing.Any) -> bool:
        """Whether this person is allowed into the admin at all.

        The account is resolved first and cached on the request, so the gate,
        every resource's access rule and every field's rule all read one user
        loaded once.
        """
        from warder.access import request_state
        from warder.backends import STATE_KEY

        request_state(ctx)[STATE_KEY] = await self.user(ctx)
        return await self.gate.allows(ctx)

    def __repr__(self) -> str:
        model = self.users.__name__ if self.users else "bundled"
        return f"Auth(users={model}, gate={self.gate!r})"
