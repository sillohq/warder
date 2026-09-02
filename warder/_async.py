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

__all__ = ["resolved"]


async def resolved(value: typing.Any) -> typing.Any:
    """*value*, awaited if it is a coroutine.

    Querysets, dicts, lists and plain values pass through untouched — including
    querysets, which are awaitable and must not be awaited here.
    """
    if inspect.iscoroutine(value):
        return await value
    return value
