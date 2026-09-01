"""The errors Warder raises, and the rule for which is which.

There are two kinds of wrong, and they belong at different times.

:class:`DeclarationError` is a **programming mistake**: a column naming a field
the model does not have, an action whose handler cannot be called, a gate given
a permission nothing registers. It is raised at ``mount()``, once, at start-up
— never mid-request — because a mistake in a declaration is not a condition to
handle, it is a build failure that happens to be spelled in Python. It carries
the source location of the declaration that is wrong, because "column 'titel'
is not a field of Post" is only half an error message without it.

:class:`Denied` is a **runtime answer**: this person may not do this. It is
expected, it is not a bug, and the route layer turns it into a response.

Everything else inherits :class:`WarderError`, so an application can catch the
whole package with one name.
"""

from __future__ import annotations

import difflib
import typing

__all__ = [
    "ActionFailed",
    "DeclarationError",
    "Denied",
    "NotConfigured",
    "WarderError",
]


class WarderError(Exception):
    """Base for everything this package raises."""


class DeclarationError(WarderError):
    """A declaration is wrong, and the process should not start.

    The message is built in three parts, because an error you can act on
    without opening a second file is worth the formatting:

    * what is wrong, naming the declaration and the model;
    * a suggestion, when there is a near-miss among the valid names;
    * where the declaration was written.
    """

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        where: str | None = None,
        options: typing.Iterable[str] = (),
        got: str | None = None,
    ) -> None:
        self.message = message
        self.where = where
        self.hint = hint if hint is not None else _did_you_mean(got, options)
        super().__init__(self.render())

    def render(self) -> str:
        lines = [self.message]
        if self.hint:
            lines.append(f"  {self.hint}")
        if self.where:
            lines.append(f"  Declared at {self.where}")
        return "\n".join(lines)


class Denied(WarderError):
    """This person may not do this. Expected; not a bug.

    *status* distinguishes the two honest answers. 403 says "you are known and
    the answer is no". 401 says "who are you" and is only correct when nobody
    is signed in — sending it to a signed-in user starts a login loop.
    """

    def __init__(self, message: str = "Forbidden", *, status: int = 403) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


class ActionFailed(WarderError):
    """An action stopped itself with a message meant for the person who ran it.

    Distinct from an unexpected exception: this one is shown, not swallowed
    into a 500.
    """

    def __init__(self, message: str, *, status: int = 400) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


class NotConfigured(WarderError):
    """Something was used before the thing it needs was set up."""


def _did_you_mean(got: str | None, options: typing.Iterable[str]) -> str | None:
    """``Did you mean 'title'?`` when *got* is a near-miss, else ``None``.

    Only ever one suggestion. Three guesses is not a hint, it is a list.
    """
    if not got:
        return None
    names = [str(option) for option in options]
    close = difflib.get_close_matches(got, names, n=1, cutoff=0.6)
    if close:
        return f"Did you mean {close[0]!r}?"
    if names and len(names) <= 8:
        return "Available: " + ", ".join(repr(name) for name in sorted(names))
    return None
