"""``resolved`` — await a coroutine, and leave everything else alone.

There is one trap here and it is worth a module.

A ``sillo.record`` queryset is **awaitable**: ``await Post.filter(...)`` runs the
query and hands back a list. So the usual test for "did this callback need
awaiting" —

    if inspect.isawaitable(result):
        result = await result

— is true for a queryset, and quietly executes it. A ``Scope.query`` that
narrows and returns its queryset would come back as a list of rows, and the very
next ``.filter()`` on it raises ``'list' object has no attribute 'filter'`` from
somewhere else entirely.

The distinction that actually matters is **coroutine**, not awaitable: an
``async def`` callback returns a coroutine, and a queryset does not. So that is
what is checked, everywhere a declaration hands back a value that might have
come from an ``async def``.
"""

from __future__ import annotations

import inspect
import typing

__all__ = ["awaited", "resolved"]


async def resolved(value: typing.Any) -> typing.Any:
    """*value*, awaited only if it is a coroutine.

    For callbacks whose contract is **to return a queryset**: ``Scope.query``
    and ``Resource(queryset=...)``. Awaiting one there would execute it and
    hand back rows, and the next ``.filter()`` would fail somewhere else.
    """
    if inspect.iscoroutine(value):
        return await value
    return value


async def awaited(value: typing.Any) -> typing.Any:
    """*value*, awaited if it is awaitable at all.

    For callbacks whose contract is **to return data**: a dashboard card's
    loader, a page handler, a validator, an action. There, ``lambda ctx:
    Post.all().count()`` is the obvious thing to write and the count is what
    was meant — so an awaitable query is run rather than serialised as
    ``<CountQuery object at 0x…>``, which is what the reader would otherwise
    see on their dashboard.

    The two functions exist because the two contracts genuinely differ, and
    one rule cannot serve both: a queryset is awaitable, and whether awaiting
    it is right depends entirely on what the caller asked for.
    """
    if inspect.isawaitable(value):
        return await value
    return value
