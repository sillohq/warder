"""Turning model classes into the words a person reads.

Every default here is overridable on the declaration that uses it. They exist
so that ``Resource(Post)`` alone produces a usable screen — "Post", "Posts",
``/admin/post``, and the permissions ``post.view`` … ``post.delete`` — not so
that anything is inferred you cannot see and replace.

The pluraliser handles regular English and the four common irregular endings.
It is deliberately small: guessing harder produces confident nonsense on
domain nouns, and ``Resource(Person, plural="People")`` is one keyword.
"""

from __future__ import annotations

import re
import typing

__all__ = ["label_for", "permission", "plural_of", "slug", "slug_for"]

_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NON_WORD = re.compile(r"[^a-z0-9]+")

#: Endings that take ``-es`` rather than ``-s``.
_SIBILANT = ("s", "x", "z", "ch", "sh")

#: The irregulars worth carrying. Anything else takes ``plural=``.
_IRREGULAR = {
    "person": "people",
    "child": "children",
    "man": "men",
    "woman": "women",
    "foot": "feet",
    "tooth": "teeth",
    "goose": "geese",
    "mouse": "mice",
    "datum": "data",
    "index": "indexes",
    "matrix": "matrices",
    "analysis": "analyses",
}


def slug(text: str) -> str:
    """``"BlogPost"`` → ``"blog-post"``; ``"Order Item"`` → ``"order-item"``."""
    spaced = _BOUNDARY.sub(" ", text)
    return _NON_WORD.sub("-", spaced.lower()).strip("-")


def slug_for(model: type) -> str:
    """The URL and permission stem for *model* — ``Post`` → ``"post"``."""
    return slug(model.__name__)


def label_for(model: type) -> str:
    """The human name for *model* — ``BlogPost`` → ``"Blog post"``."""
    words = _BOUNDARY.sub(" ", model.__name__).replace("_", " ").split()
    if not words:  # pragma: no cover - a class with an empty name
        return model.__name__
    first, *rest = words
    return " ".join([first.capitalize(), *(word.lower() for word in rest)])


def plural_of(label: str) -> str:
    """``"Post"`` → ``"Posts"``; ``"Category"`` → ``"Categories"``.

    Only the last word is inflected, so "Blog post" pluralises correctly.
    """
    if not label:  # pragma: no cover - guarded by callers
        return label
    head, _, last = label.rpartition(" ")
    inflected = _inflect(last)
    return f"{head} {inflected}" if head else inflected


def _inflect(word: str) -> str:
    lowered = word.lower()
    if lowered in _IRREGULAR:
        return _match_case(word, _IRREGULAR[lowered])
    if lowered.endswith("y") and len(lowered) > 1 and lowered[-2] not in "aeiou":
        return word[:-1] + "ies"
    if lowered.endswith(_SIBILANT):
        return word + "es"
    return word + "s"


def _match_case(original: str, replacement: str) -> str:
    """Carry *original*'s capitalisation onto *replacement*."""
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement.capitalize()
    return replacement


def permission(stem: str, action: str) -> str:
    """The permission name for an action on a resource — ``"post.change"``."""
    return f"{stem}.{action}"


def coerce_choices(
    choices: typing.Iterable[typing.Any],
) -> tuple[tuple[typing.Any, str], ...]:
    """Normalise the three ways people write a choice list.

    ``["draft", "live"]``, ``[("draft", "Draft")]`` and a ``{value: label}``
    mapping all mean the same thing, and all three are written in the wild, so
    all three are accepted and stored one way.
    """
    if isinstance(choices, typing.Mapping):
        return tuple((value, str(label)) for value, label in choices.items())
    normalised: list[tuple[typing.Any, str]] = []
    for choice in choices:
        if isinstance(choice, (tuple, list)) and len(choice) == 2:
            value, label = choice
            normalised.append((value, str(label)))
        else:
            normalised.append((choice, str(choice).replace("_", " ").capitalize()))
    return tuple(normalised)
