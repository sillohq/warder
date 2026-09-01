"""Argument checks that run at construction time.

The rule this package follows: **a wrong value fails when you write it; a wrong
reference fails when you mount.** ``align="middle"`` needs nothing but the
string to be judged, so it raises from the constructor with the frame still on
the stack. ``Column("titel")`` cannot be judged until there is a model to check
it against, so it waits for ``mount()`` — see :mod:`warder.errors`.

Keeping the first kind out of ``mount()`` matters: an error raised where the
mistake was typed is worth several raised somewhere else.
"""

from __future__ import annotations

import typing

__all__ = ["callable_", "identifier", "non_negative", "one_of", "positive", "sequence"]


def one_of(name: str, value: typing.Any, allowed: typing.Sequence[str]) -> str:
    """*value* if it is in *allowed*, else a ``ValueError`` that lists them."""
    if value not in allowed:
        raise ValueError(
            f"{name}={value!r} is not valid. "
            f"Use one of: {', '.join(repr(item) for item in allowed)}."
        )
    return typing.cast(str, value)


def identifier(name: str, value: typing.Any) -> str:
    """*value* if it is a usable field reference.

    Traversals like ``"author__email"`` are references too, so only emptiness
    and the wrong type are rejected here. Whether the field exists is a
    question for the model, at mount.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty field name, got {value!r}.")
    return value


def callable_(name: str, value: typing.Any) -> typing.Any:
    """*value* if it can be called."""
    if not callable(value):
        raise TypeError(f"{name} must be callable, got {type(value).__name__}.")
    return value


def positive(name: str, value: typing.Any) -> int:
    """*value* if it is an integer above zero."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}.")
    return value


def non_negative(name: str, value: typing.Any) -> int:
    """*value* if it is an integer of zero or more."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be zero or more, got {value!r}.")
    return value


def sequence(name: str, value: typing.Any) -> tuple[typing.Any, ...]:
    """*value* as a tuple, rejecting the string that was meant to be a list.

    ``select_related="author"`` is a common slip and iterating it silently
    gives seven one-character relations, so it is caught rather than obeyed.
    """
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of names, not a single {value!r}.")
    return tuple(value)
