"""Signing in.

The admin brings its own login and hands it to yours the moment you say so.
There are three arrangements and all three go through this module:

**Standalone.** ``Admin()`` with no ``auth=``. The bundled
:class:`~warder.models.AdminUser`, an admin-only sign-in page, ``is_staff`` as
the gate. Right for an internal tool with no public user model.

**Shared model, admin login.** ``Auth(users=User)``. Your accounts, your
password hashes, a separate sign-in page for the admin. This is where
``Gate.staff()`` earns its keep: every registered account holds a session, and
admitting anyone who has one hands over the database.

**Shared session.** ``Auth(backend=YourBackend())``. Signed into the product is
signed into the admin, subject to the gate. A backend is three methods.

Two things here are not decoration.

**Throttling is per identity *and* per address.** Per identity alone lets one
machine work through a list of usernames; per address alone lets a botnet work
through one password. Both, or neither is worth having.

**The session carries an id and two timestamps, never a user.** Every request
reloads the account, so deactivating someone takes effect on their next click
rather than on their next sign-in — which is the only version of "revoke" that
is worth the word.
"""

from __future__ import annotations

import contextlib
import time
import typing

if typing.TYPE_CHECKING:
    from warder.auth import Auth

__all__ = ["Backend", "SessionAuth", "Throttle"]

#: Where the signed-in identity lives in the session.
SESSION_KEY = "warder.user"

#: Where the resolved account is cached for the life of one request, so a page
#: that asks ten access questions makes one query rather than ten.
STATE_KEY = "warder.user"


class Backend:
    """What the admin needs from an authentication system.

    Three methods. Implement them against JWT, LDAP, your own session table or
    anything else, and pass it as ``Auth(backend=…)``.
    """

    async def current(self, ctx: typing.Any) -> typing.Any:
        """The signed-in account, or ``None``."""
        return None

    async def login(self, ctx: typing.Any, identity: str, secret: str) -> bool:
        """Sign someone in. ``True`` on success."""
        return False

    async def logout(self, ctx: typing.Any) -> None:
        """Sign the current person out."""


class Throttle:
    """A fixed window of attempts per key.

    In process memory, which is the honest scope: it survives a page reload and
    not a restart, and two workers count separately. That is enough to stop a
    script and not enough to stop a botnet — for which the answer is a shared
    store, and this is the seam to replace when you need one.
    """

    __slots__ = ("limit", "window", "_seen")

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._seen: dict[str, list[float]] = {}

    def blocked(self, *keys: str | None) -> bool:
        """Whether any of *keys* has spent its attempts."""
        now = time.monotonic()
        return any(len(self._recent(key, now)) >= self.limit for key in keys if key)

    def record(self, *keys: str | None) -> None:
        """Count one failed attempt against each key."""
        now = time.monotonic()
        for key in keys:
            if key:
                self._recent(key, now).append(now)

    def clear(self, *keys: str | None) -> None:
        """Forget a key's attempts. Called on a successful sign-in."""
        for key in keys:
            if key:
                self._seen.pop(key, None)

    def retry_in(self, *keys: str | None) -> int:
        """Seconds until a *blocked* key frees up, or 0 if none is blocked.

        Only blocked keys count. Reporting a wait after the first wrong
        password would tell someone they are locked out when they have four
        tries left, and they would stop trying the password that works.
        """
        now = time.monotonic()
        waits = [
            self.window - (now - attempts[0])
            for key in keys
            if key and len(attempts := self._recent(key, now)) >= self.limit
        ]
        return max(1, int(max(waits))) if waits else 0

    def _recent(self, key: str, now: float) -> list[float]:
        attempts = [at for at in self._seen.get(key, ()) if now - at < self.window]
        self._seen[key] = attempts
        return attempts


class SessionAuth(Backend):
    """Session sign-in against a ``sillo.users`` model.

    Works with the bundled :class:`~warder.models.AdminUser` or any
    ``UserBaseModel`` subclass — your own included — because the password work
    lives on the model, in ``sillo.hashing``, and is never reimplemented here.
    """

    def __init__(
        self,
        users: type | None = None,
        *,
        policy: Auth | None = None,
    ) -> None:
        self._users = users
        self.policy = policy
        self.throttle: Throttle | None = None
        if policy is not None and policy.login.throttle:
            attempts, window = policy.login.throttle
            self.throttle = Throttle(attempts, window)

    @property
    def users(self) -> type:
        """The user model. Imported late, so the models are opt-in."""
        if self._users is not None:
            return self._users
        from warder.models import AdminUser

        return AdminUser

    # ------------------------------------------------------------------ read

    async def current(self, ctx: typing.Any) -> typing.Any:
        """The signed-in account, reloaded, or ``None``.

        Reloaded on every request rather than trusted from the session, so a
        deactivated account stops working on its next click.
        """
        cached = _state(ctx).get(STATE_KEY, _MISSING)
        if cached is not _MISSING:
            return cached

        entry = _session_entry(ctx)
        user = None if entry is None else await self._load(entry)
        if user is not None and not self._fresh(ctx, entry or {}):
            await self.logout(ctx)
            user = None
        _state(ctx)[STATE_KEY] = user
        return user

    async def _load(self, entry: typing.Mapping[str, typing.Any]) -> typing.Any:
        identity = entry.get("id")
        if identity is None:
            return None
        try:
            model = typing.cast(typing.Any, self.users)
            user = await model.load_user(str(identity))
        except Exception:
            # A session naming an account this model cannot load is not an
            # error to surface; it is simply not a signed-in request.
            return None
        return user if user is not None and getattr(user, "is_active", True) else None

    def _fresh(self, ctx: typing.Any, entry: typing.Mapping[str, typing.Any]) -> bool:
        """Whether this session is still inside both of its lifetimes.

        Two, because they answer different questions. *idle* is "you walked
        away"; *absolute* is "this session is old however busy you have been",
        and only the second bounds a cookie somebody copied.
        """
        policy = self.policy.session if self.policy else None
        if policy is None:
            return True
        now = time.time()
        if policy.absolute and now - float(entry.get("at", now)) > policy.absolute:
            return False
        if policy.idle and now - float(entry.get("seen", now)) > policy.idle:
            return False
        session = _session(ctx)
        if session is not None:
            session[SESSION_KEY] = {**entry, "seen": now}
        return True

    # ----------------------------------------------------------------- write

    async def login(self, ctx: typing.Any, identity: str, secret: str) -> bool:
        """Check the credentials and start a session."""
        address = _address(ctx)
        if self.throttle and self.throttle.blocked(identity, address):
            return False

        user = None
        try:
            model = typing.cast(typing.Any, self.users)
            user = await model.verify_credentials(identity, secret)
        except Exception:
            user = None

        if user is None or not getattr(user, "is_active", True):
            if self.throttle:
                self.throttle.record(identity, address)
            return False

        session = _session(ctx)
        if session is None:
            return False
        now = time.time()
        session[SESSION_KEY] = {
            "id": str(getattr(user, "pk", getattr(user, "id", ""))),
            "at": now,
            "seen": now,
        }
        _state(ctx)[STATE_KEY] = user
        if self.throttle:
            self.throttle.clear(identity, address)
        setter = getattr(user, "set_last_login", None)
        if setter is not None:
            # Signing in should not fail because a bookkeeping column could
            # not be written.
            with contextlib.suppress(Exception):
                await setter()
        return True

    async def logout(self, ctx: typing.Any) -> None:
        session = _session(ctx)
        if session is not None:
            # `clear()` is what marks the session modified, which is what makes
            # the backend write the emptied cookie. Popping keys mutates a dict
            # the session may not know changed, and the browser keeps a cookie
            # that still signs you in.
            cleared = getattr(session, "clear", None)
            if cleared is not None:
                with contextlib.suppress(Exception):
                    cleared()
            for key in (SESSION_KEY, "admin_user", "user"):
                with contextlib.suppress(AttributeError, TypeError, KeyError):
                    session[key] = None
        _state(ctx)[STATE_KEY] = None

    def wait(self, ctx: typing.Any, identity: str) -> int:
        """Seconds before this identity or address may try again."""
        if not self.throttle:
            return 0
        return self.throttle.retry_in(identity, _address(ctx))


# ------------------------------------------------------------------ plumbing


class _Missing:
    __slots__ = ()


_MISSING = _Missing()


def _session(ctx: typing.Any) -> typing.Any:
    """The session, or ``None`` when no middleware provides one.

    ``ctx.session`` asserts rather than raising when the middleware is absent,
    and an admin without a session should say "no session backend" rather than
    return a 500.
    """
    try:
        return ctx.session
    except (AttributeError, ValueError, LookupError, AssertionError):
        return None


def _session_entry(ctx: typing.Any) -> dict[str, typing.Any] | None:
    session = _session(ctx)
    if session is None:
        return None
    try:
        entry = session.get(SESSION_KEY)
    except (AttributeError, TypeError):  # pragma: no cover - exotic session
        return None
    if isinstance(entry, dict):
        return entry
    # A bare identity, which is what an application's own middleware may have
    # left behind. Accepted so a shared session works without a translation
    # layer.
    return {"id": entry} if entry else None


def _state(ctx: typing.Any) -> dict[str, typing.Any]:
    """Per-request scratch space, so one page makes one user query."""
    from warder.access import request_state

    return request_state(ctx)


def _address(ctx: typing.Any) -> str | None:
    client = getattr(ctx, "client", None)
    host = getattr(client, "host", None)
    return str(host) if host else None
