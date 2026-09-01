"""``Sort`` — how a list is ordered.

Named ``Sort`` and not ``Order`` on purpose. ``Order`` is one of the most
common model names there is, and an admin module that imports both a
declaration called ``Order`` and a model called ``Order`` has a bug waiting in
it that reads as correct code.

A ``Sort`` is a sequence of terms, each a field and a direction::

    Sort.desc("published_at")
    Sort.by("-published_at", "title")
    Sort.desc("published_at").then(Sort.asc("title"))

It knows nothing about an ORM. :meth:`Sort.as_terms` hands the resolver a
tuple of ``"-published_at"``-style strings, which is what ``sillo.record``
wants, and that is the only coupling.
"""

from __future__ import annotations

import typing

from warder._check import identifier
from warder.base import Declaration

__all__ = ["Sort", "SortTerm"]


class SortTerm(typing.NamedTuple):
    """One field and its direction."""

    field: str
    descending: bool = False

    def __str__(self) -> str:
        return f"-{self.field}" if self.descending else self.field


class Sort(Declaration):
    """An ordering, as a value.

    Build one with :meth:`asc`, :meth:`desc` or :meth:`by` rather than calling
    the constructor — the constructor takes already-normalised terms and
    exists so that :meth:`~warder.base.Declaration.with_` can rebuild one.
    """

    __slots__ = ("terms",)
    _fields = ("terms",)
    _parts = "terms"

    terms: tuple[SortTerm, ...]

    def __init__(self, *terms: SortTerm | str | tuple[str, bool]) -> None:
        self._init(terms=tuple(_term(term) for term in terms))

    # ------------------------------------------------------------ constructors

    @classmethod
    def asc(cls, *fields: str) -> Sort:
        """Ascending on each of *fields*, in the order given."""
        return cls(*(SortTerm(identifier("Sort.asc", f), False) for f in fields))

    @classmethod
    def desc(cls, *fields: str) -> Sort:
        """Descending on each of *fields*, in the order given."""
        return cls(*(SortTerm(identifier("Sort.desc", f), True) for f in fields))

    @classmethod
    def by(cls, *terms: str) -> Sort:
        """From ``"-created_at"``-style strings, the way a query string sends them."""
        return cls(*terms)

    @classmethod
    def none(cls) -> Sort:
        """No ordering at all — the database decides, and it will not be stable."""
        return cls()

    # ---------------------------------------------------------------- combining

    def then(self, other: Sort) -> Sort:
        """*self*, then *other* as the tie-break."""
        return Sort(*self.terms, *other.terms)

    def reversed(self) -> Sort:
        """Every term flipped. What a second click on a column header means."""
        return Sort(*(SortTerm(t.field, not t.descending) for t in self.terms))

    # ------------------------------------------------------------------ output

    def as_terms(self) -> tuple[str, ...]:
        """``("-published_at", "title")`` — what ``order_by`` takes."""
        return tuple(str(term) for term in self.terms)

    def direction_of(self, field: str) -> str | None:
        """``"asc"``, ``"desc"``, or ``None`` when *field* is not sorted on."""
        for term in self.terms:
            if term.field == field:
                return "desc" if term.descending else "asc"
        return None

    def __bool__(self) -> bool:
        return bool(self.terms)

    def __repr__(self) -> str:
        return f"Sort({', '.join(repr(str(term)) for term in self.terms)})"


def _term(value: SortTerm | str | tuple[str, bool]) -> SortTerm:
    """Accept any of the three spellings and store one."""
    if isinstance(value, SortTerm):
        return value
    if isinstance(value, str):
        descending = value.startswith("-")
        return SortTerm(identifier("Sort", value.lstrip("-+")), descending)
    if isinstance(value, tuple) and len(value) == 2:
        return SortTerm(identifier("Sort", value[0]), bool(value[1]))
    raise TypeError(
        f"A sort term is a field name, a '-field' string or a SortTerm, got {value!r}."
    )
