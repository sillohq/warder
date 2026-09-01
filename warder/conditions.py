"""``When`` — a condition the browser can evaluate.

Form fields that appear only when another field has a particular value are
ordinary, and the obvious way to express it is a callable. A callable cannot
cross the wire, so the field would only appear after a round trip and the form
would flicker.

``When`` is that condition as *data*. It serialises into props and the renderer
evaluates it against the form's current values, so ``published_at`` appears the
instant ``status`` becomes ``live``::

    Field("published_at", show=When("status", equals="live"))
    Field("reason", show=When("status", any_of=["rejected", "held"]))
    Field("vat", show=When.all(When("country", equals="GB"),
                               When("business", is_true=True)))

The server checks the same condition before accepting a write, so a hidden
field is not merely hidden.
"""

from __future__ import annotations

import typing

from warder._check import identifier
from warder.base import Declaration

__all__ = ["When"]

_UNSET = object()


class When(Declaration):
    """A condition over the values of other fields."""

    __slots__ = ("conditions", "field", "test", "value")
    _fields = ("field", "test", "value", "conditions")

    TESTS = (
        "equals",
        "not_equals",
        "any_of",
        "none_of",
        "is_true",
        "is_false",
        "filled",
        "empty",
        "any",
        "all",
        "not",
    )

    field: str | None
    test: str
    value: typing.Any
    conditions: tuple[When, ...]

    def __init__(
        self,
        field: str | None = None,
        *,
        test: str = "filled",
        value: typing.Any = None,
        conditions: typing.Sequence[When] = (),
        equals: typing.Any = _UNSET,
        not_equals: typing.Any = _UNSET,
        any_of: typing.Sequence[typing.Any] | None = None,
        none_of: typing.Sequence[typing.Any] | None = None,
        is_true: bool = False,
        is_false: bool = False,
        empty: bool = False,
    ) -> None:
        if equals is not _UNSET:
            test, value = "equals", equals
        elif not_equals is not _UNSET:
            test, value = "not_equals", not_equals
        elif any_of is not None:
            test, value = "any_of", tuple(any_of)
        elif none_of is not None:
            test, value = "none_of", tuple(none_of)
        elif is_true:
            test = "is_true"
        elif is_false:
            test = "is_false"
        elif empty:
            test = "empty"
        if test not in self.TESTS:
            raise ValueError(
                f"When test {test!r} is not one of {', '.join(self.TESTS)}."
            )
        if test not in ("any", "all", "not") and field is None:
            raise ValueError("When needs a field name — When('status', equals='live').")
        self._init(
            field=identifier("When field", field) if field is not None else None,
            test=test,
            value=value,
            conditions=tuple(conditions),
        )

    @classmethod
    def any(cls, *conditions: When) -> When:
        """True when any of *conditions* is."""
        return cls(test="any", conditions=conditions)

    @classmethod
    def all(cls, *conditions: When) -> When:
        """True when every one of *conditions* is."""
        return cls(test="all", conditions=conditions)

    def __invert__(self) -> When:
        return When(test="not", conditions=(self,))

    def __or__(self, other: When) -> When:
        return When.any(self, other)

    def __and__(self, other: When) -> When:
        return When.all(self, other)

    def holds(self, values: typing.Mapping[str, typing.Any]) -> bool:
        """Evaluate against *values* — the same answer the browser reaches.

        One implementation in each language is one too many, so this one is
        the authority: the server re-checks it before a write and rejects a
        value for a field the condition says is not there.
        """
        if self.test == "any":
            return any(c.holds(values) for c in self.conditions)
        if self.test == "all":
            return all(c.holds(values) for c in self.conditions)
        if self.test == "not":
            return not self.conditions[0].holds(values)

        current = values.get(typing.cast(str, self.field))
        if self.test == "equals":
            return bool(current == self.value)
        if self.test == "not_equals":
            return bool(current != self.value)
        if self.test == "any_of":
            return current in typing.cast(tuple, self.value)
        if self.test == "none_of":
            return current not in typing.cast(tuple, self.value)
        if self.test == "is_true":
            return bool(current)
        if self.test == "is_false":
            return not current
        if self.test == "empty":
            return current in (None, "", [], {}, ())
        return current not in (None, "", [], {}, ())

    def fields(self) -> frozenset[str]:
        """Every field this condition reads. What the renderer watches."""
        if self.conditions:
            return frozenset().union(*(c.fields() for c in self.conditions))
        return frozenset({typing.cast(str, self.field)})

    def __repr__(self) -> str:
        if self.conditions:
            inner = ", ".join(repr(c) for c in self.conditions)
            return f"When.{self.test}({inner})"
        if self.value is None:
            return f"When({self.field!r}, test={self.test!r})"
        return f"When({self.field!r}, {self.test}={self.value!r})"
