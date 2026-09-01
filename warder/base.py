"""What every declaration is, underneath.

A declaration is a **value**: frozen once built, comparable, printable, and
extendable only by producing a new one. That is the whole idea of this package
— an admin screen is data you can name, store in a variable, pass to a
function, generate in a loop, and check before the server starts.

Three properties come from here.

**Immutable.** Attributes cannot be set after construction, and sequence and
mapping arguments are copied into read-only forms. A ``List`` shared between
forty resources cannot be edited from a distance by the thirty-ninth.

**Extendable.** :meth:`Declaration.with_` returns a *new* declaration with
extra positional parts appended and keywords replaced. Nothing mutates, so a
base declaration stays a base declaration.

**Locatable.** Every declaration records the file and line it was written on,
found by walking out of this package's own frames. That is what turns

    Resource(Post).list column 'titel' is not a field of Post.

into an error you can act on without going looking for it.

Nothing here reads an annotation. Defaults are discovered from the constructor
signature — which is *values*, not types — so ``repr`` can show only what was
actually asked for.
"""

from __future__ import annotations

import inspect
import os
import sys
import types
import typing

__all__ = ["Declaration", "origin"]

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULTS: dict[type, dict[str, typing.Any]] = {}


def origin(skip: int = 0) -> str | None:
    """``"app/admin.py:24"`` for the first frame outside this package.

    Declarations are usually built at module import, so the first frame that
    is not ours is the line the author wrote. Returns ``None`` where frames
    are unavailable, which costs nothing but the location in the message.
    """
    try:
        frame: types.FrameType | None = sys._getframe(1 + skip)
    except (AttributeError, ValueError):  # pragma: no cover - not CPython
        return None
    while frame is not None:
        filename = frame.f_code.co_filename
        if not filename.startswith(_HERE):
            return f"{_shorten(filename)}:{frame.f_lineno}"
        frame = frame.f_back
    return None


def _shorten(path: str) -> str:
    """Make a path readable: relative to the working directory when it is under it."""
    try:
        relative = os.path.relpath(path, os.getcwd())
    except (OSError, ValueError):  # pragma: no cover - unusual filesystems
        return path
    return path if relative.startswith("..") else relative


def freeze(value: typing.Any) -> typing.Any:
    """Copy *value* into a form that cannot be edited through the original.

    Lists and tuples become tuples; dicts become read-only mappings. Anything
    else — a model class, a callable, a string — is left alone, because it is
    either already immutable or not ours to copy.
    """
    if isinstance(value, (list, tuple)):
        return tuple(value)
    if isinstance(value, dict):
        return types.MappingProxyType(dict(value))
    if isinstance(value, (set, frozenset)):
        return frozenset(value)
    return value


class Declaration:
    """A frozen, comparable, extendable value.

    Subclasses declare two things:

    ``_fields``
        every constructor keyword, in order, which drives ``repr``, ``==``
        and :meth:`with_`.

    ``_parts``
        the name of the attribute holding positionally-collected parts —
        ``List(*columns)``, ``Section(*fields)`` — or ``None`` when the
        declaration takes none.
    """

    __slots__ = ("_where",)

    _fields: typing.ClassVar[tuple[str, ...]] = ()
    _parts: typing.ClassVar[str | None] = None

    # ------------------------------------------------------------------ build

    def _init(self, **values: typing.Any) -> None:
        """Set every field, once, from inside a constructor.

        The only supported way to populate a declaration. After this returns,
        :meth:`__setattr__` refuses.
        """
        for name, value in values.items():
            object.__setattr__(self, name, freeze(value))
        object.__setattr__(self, "_where", origin(2))

    def __setattr__(self, name: str, value: typing.Any) -> typing.NoReturn:
        raise AttributeError(
            f"{type(self).__name__} is a value and cannot be modified. "
            f"Use .with_({name}=...) to build a new one."
        )

    def __delattr__(self, name: str) -> typing.NoReturn:
        raise AttributeError(f"{type(self).__name__} is a value and cannot be modified.")

    # ----------------------------------------------------------------- extend

    def with_(self, *parts: typing.Any, **options: typing.Any) -> typing.Self:
        """A new declaration: *parts* appended, *options* replaced.

        ::

            BASE = List(Column("id"), Column("name"), per_page=50)
            BASE.with_(Column("slug"))              # three columns, still 50
            BASE.with_(per_page=100)                # two columns, now 100

        Appending rather than replacing is the deliberate choice: a shared base
        exists to be added to, and a caller who wants to start over can build a
        new ``List``.
        """
        unknown = set(options) - set(self._fields)
        if unknown:
            raise TypeError(
                f"{type(self).__name__}.with_() got unexpected keyword"
                f"{'s' if len(unknown) > 1 else ''} "
                + ", ".join(repr(name) for name in sorted(unknown))
                + ". Accepts: "
                + ", ".join(self._fields)
            )
        values = {name: getattr(self, name) for name in self._fields}
        values.update(options)
        if self._parts is None:
            if parts:
                raise TypeError(
                    f"{type(self).__name__}.with_() takes no positional parts."
                )
            return typing.cast("typing.Self", type(self)(**values))
        collected = tuple(values.pop(self._parts)) + parts
        return typing.cast("typing.Self", type(self)(*collected, **values))

    # ------------------------------------------------------------- comparison

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return all(
            getattr(self, name) == getattr(other, name) for name in self._fields
        )

    __hash__ = None  # type: ignore[assignment]

    # ------------------------------------------------------------------ print

    def __repr__(self) -> str:
        defaults = _constructor_defaults(type(self))
        shown: list[str] = []
        for name in self._fields:
            value = getattr(self, name)
            if name == self._parts:
                shown.extend(repr(part) for part in value)
                continue
            if name in defaults and _same(defaults[name], value):
                continue
            shown.append(f"{name}={value!r}")
        return f"{type(self).__name__}({', '.join(shown)})"

    @property
    def where(self) -> str | None:
        """Where this declaration was written, as ``"file.py:24"``."""
        return self._where


def _constructor_defaults(cls: type) -> dict[str, typing.Any]:
    """The defaulted parameters of ``cls.__init__``, cached per class.

    Read from the signature's *default values*. Annotations are not consulted
    here or anywhere else.
    """
    cached = _DEFAULTS.get(cls)
    if cached is None:
        cached = {
            name: parameter.default
            for name, parameter in inspect.signature(cls.__init__).parameters.items()
            if parameter.default is not inspect.Parameter.empty
        }
        _DEFAULTS[cls] = cached
    return cached


def _same(default: typing.Any, value: typing.Any) -> bool:
    """Whether *value* is the frozen form of *default*.

    ``freeze`` turns ``[]`` into ``()`` and ``{}`` into a mapping proxy, so a
    plain ``==`` against the raw default would report every collection as
    changed and print it.
    """
    if default is value:
        return True
    try:
        return bool(freeze(default) == value)
    except Exception:  # pragma: no cover - exotic __eq__
        return False
