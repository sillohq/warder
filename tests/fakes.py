"""Fakes standing in for the ORM and the request context.

The declaration layer touches neither, which is the point of it — so the whole
suite runs without a database, a connection, or a running application. Where a
declaration does reach out (``Scope.apply`` narrowing a queryset,
``Access.allows`` asking a user for a permission) it does so through two very
small surfaces, and these are them.

Not in ``conftest.py``: an editable install of the framework puts *its*
``tests`` package on ``sys.path``, so ``from tests.conftest import ...`` would
resolve to the wrong project.
"""

from __future__ import annotations

import typing


class Rows:
    """A queryset that records what was asked of it instead of running it.

    Every call returns a new ``Rows``, the way a real queryset does, so a test
    can assert on the chain without asserting on the object identity of
    something that is supposed to be immutable.
    """

    def __init__(self, calls: tuple = ()) -> None:
        self.calls = calls

    def filter(self, *args: typing.Any, **kwargs: typing.Any) -> Rows:
        return Rows((*self.calls, ("filter", args, kwargs)))

    def exclude(self, **kwargs: typing.Any) -> Rows:
        return Rows((*self.calls, ("exclude", (), kwargs)))

    def order_by(self, *terms: str) -> Rows:
        return Rows((*self.calls, ("order_by", terms, {})))

    def select_related(self, *names: str) -> Rows:
        return Rows((*self.calls, ("select_related", names, {})))

    @property
    def filters(self) -> list[dict[str, typing.Any]]:
        """Just the keyword filters, in order — what most assertions want."""
        return [kwargs for name, _, kwargs in self.calls if name == "filter"]


class User:
    """A user model's surface, as ``warder.access`` uses it."""

    def __init__(
        self,
        id: int = 1,
        *,
        permissions: typing.Iterable[str] = (),
        groups: typing.Iterable[str] = (),
        is_staff: bool = False,
        is_superuser: bool = False,
        is_active: bool = True,
        **extra: typing.Any,
    ) -> None:
        self.id = id
        self._permissions = set(permissions)
        self._groups = set(groups)
        self.is_staff = is_staff
        self.is_superuser = is_superuser
        self.is_active = is_active
        self.loaded = 0
        for name, value in extra.items():
            setattr(self, name, value)

    async def load_permissions(self) -> set[str]:
        self.loaded += 1
        return self._permissions

    def has_permission(self, name: str) -> bool:
        return name in self._permissions

    async def is_in_group(self, name: str) -> bool:
        return name in self._groups


class Ctx:
    """A request context with a ``user``, and nothing else."""

    def __init__(self, user: User | None = None) -> None:
        self._user = user

    @property
    def user(self) -> User:
        if self._user is None:
            # What sillo does with no authentication middleware installed:
            # raises rather than returning None.
            raise ValueError("No authentication middleware is installed.")
        return self._user


def model(name: str, **attributes: typing.Any) -> type:
    """A stand-in model class. Only its name is ever read at this layer."""
    return type(name, (), attributes)


Post = model("Post")
Tag = model("Tag")
Comment = model("Comment")
Order = model("Order")
