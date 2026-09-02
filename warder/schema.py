"""What Warder needs to know about a model, and where it gets it.

The admin is a ``sillo.record`` product. It reads ``_meta.fields_map``, follows
foreign keys and writes through model saves, and there is no abstraction layer
over the ORM — an admin that could drive any data source would be able to
express only what every data source has in common, which is roughly nothing.

This module is where that coupling lives. Everything above it deals in
:class:`ModelField`, a normalised description of one column: its kind, whether
it may be null, what it defaults to, and what it points at. Swapping the ORM
would mean a second :class:`Schema`, not a rewrite.

**It works before the database is up.** Tortoise fills ``fields_map`` when the
class is defined but only resolves ``related_model`` at ``Tortoise.init``. A
relation whose far side is still a string is reported as *unresolved* rather
than treated as missing, because refusing to start over a relation the ORM has
not linked yet would make the admin unmountable in exactly the applications
that need it.
"""

from __future__ import annotations

import dataclasses
import typing

__all__ = ["KINDS", "ModelField", "Schema"]

#: Every kind a column can be, as far as the admin is concerned. Deliberately
#: coarser than the ORM's field classes: what changes the interface is whether
#: something is long text or short text, not whether it is a ``CharField`` or a
#: ``CharEnumField``.
KINDS = (
    "text",
    "longtext",
    "integer",
    "decimal",
    "float",
    "boolean",
    "json",
    "datetime",
    "date",
    "time",
    "uuid",
    "binary",
    "password",
    "slug",
    "enum",
    "relation",
    "backward",
    "m2m",
    "unknown",
)

#: Tortoise field class names, mapped by walking the MRO so a subclass of
#: ``CharField`` is still text.
_BY_CLASS = {
    "TextField": "longtext",
    "PasswordField": "password",
    "SlugField": "slug",
    "CharField": "text",
    "BooleanField": "boolean",
    "SmallIntField": "integer",
    "BigIntField": "integer",
    "IntField": "integer",
    "DecimalField": "decimal",
    "FloatField": "float",
    "JSONField": "json",
    "DatetimeField": "datetime",
    "DateField": "date",
    "TimeField": "time",
    "TimeDeltaField": "integer",
    "UUIDField": "uuid",
    "BinaryField": "binary",
}

#: Columns the base model adds that a form should never offer to edit.
MANAGED = ("created_at", "updated_at", "deleted_at")


@dataclasses.dataclass(frozen=True)
class ModelField:
    """One column, described in the admin's own terms."""

    name: str
    kind: str
    column: str | None = None
    null: bool = False
    required: bool = False
    default: typing.Any = None
    has_default: bool = False
    max_length: int | None = None
    choices: tuple[tuple[typing.Any, str], ...] = ()
    related: type | None = None
    related_name: str | None = None
    generated: bool = False
    primary: bool = False
    unique: bool = False
    description: str | None = None
    shadow: bool = False

    @property
    def relational(self) -> bool:
        return self.kind in ("relation", "backward", "m2m")

    @property
    def unresolved(self) -> bool:
        """A relation whose far side the ORM has not linked yet."""
        return self.relational and self.related is None

    @property
    def managed(self) -> bool:
        """Written by the ORM, never by a person."""
        return self.generated or self.name in MANAGED

    @property
    def editable(self) -> bool:
        """Whether a form should offer to write this."""
        return not self.managed and not self.shadow and self.kind != "backward"

    @property
    def writable_when_blank(self) -> bool:
        """Whether leaving it empty is allowed.

        A required column with no default and no null makes a form
        unsubmittable if it is also readonly — which is the check in
        :mod:`warder.resolve` that saves an afternoon.
        """
        return self.null or self.has_default or self.generated


class Schema:
    """One model's columns, normalised and cached.

    ::

        schema = Schema.of(Post)
        schema.has("title")            # True
        schema.resolve("author__email")  # the far side's ModelField
    """

    _CACHE: typing.ClassVar[dict[type, Schema]] = {}

    def __init__(self, model: type) -> None:
        self.model = model
        meta = getattr(model, "_meta", None)
        if meta is None:
            raise TypeError(
                f"{model.__name__} is not a sillo.record model — it has no _meta. "
                "Warder resolves declarations against the ORM's own metadata."
            )
        self.meta = meta
        self.pk: str = getattr(meta, "pk_attr", "id")
        self.fields: dict[str, ModelField] = _describe(meta)

    @classmethod
    def of(cls, model: type) -> Schema:
        """The schema for *model*, built once.

        Cached because ``mount()`` asks for the same model from every column,
        filter, panel and permission check, and because a model's columns do
        not change after the class is defined.
        """
        cached = cls._CACHE.get(model)
        if cached is None:
            cached = cls._CACHE[model] = cls(model)
        return cached

    @classmethod
    def forget(cls, model: type | None = None) -> None:
        """Drop the cache. For tests that redefine models between cases."""
        if model is None:
            cls._CACHE.clear()
        else:
            cls._CACHE.pop(model, None)

    # ------------------------------------------------------------- questions

    def has(self, name: str) -> bool:
        return name in self.fields

    def get(self, name: str) -> ModelField | None:
        return self.fields.get(name)

    @property
    def names(self) -> tuple[str, ...]:
        """Every column name, for a did-you-mean."""
        return tuple(self.fields)

    @property
    def editable(self) -> tuple[ModelField, ...]:
        """The columns a form may write, in declaration order."""
        return tuple(f for f in self.fields.values() if f.editable)

    @property
    def shadows(self) -> tuple[str, ...]:
        """The raw ``author_id`` columns standing behind a foreign key."""
        return tuple(f.name for f in self.fields.values() if f.shadow)

    @property
    def relations(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields.values() if f.relational)

    def resolve(self, path: str) -> ModelField | None:
        """Follow a ``"author__email"`` traversal, or ``None`` if it breaks.

        A hop through a relation the ORM has not linked yet stops the walk and
        returns the relation itself, whose ``unresolved`` flag tells the caller
        that "not found" would be the wrong conclusion.
        """
        current: Schema = self
        parts = path.split("__")
        for index, part in enumerate(parts):
            field = current.fields.get(part)
            if field is None:
                return None
            if index == len(parts) - 1:
                return field
            if field.related is None:
                return field
            current = Schema.of(field.related)
        return None  # pragma: no cover - an empty path cannot reach here

    def __repr__(self) -> str:
        return f"Schema({self.model.__name__}, {len(self.fields)} fields)"


def _describe(meta: typing.Any) -> dict[str, ModelField]:
    """Every field on *meta*, in declaration order, as :class:`ModelField`."""
    fk = set(getattr(meta, "fk_fields", ()) or ())
    o2o = set(getattr(meta, "o2o_fields", ()) or ())
    backward = set(getattr(meta, "backward_fk_fields", ()) or ()) | set(
        getattr(meta, "backward_o2o_fields", ()) or ()
    )
    m2m = set(getattr(meta, "m2m_fields", ()) or ())
    pk = getattr(meta, "pk_attr", "id")

    # A foreign key appears twice: as `author` and as the raw column
    # `author_id`. Both are real and both are filterable, but a form that
    # offers both offers two ways to write one value, and they disagree.
    shadows = {
        getattr(meta.fields_map[name], "source_field", None)
        for name in (fk | o2o)
        if name in meta.fields_map
    } - {None}

    described: dict[str, ModelField] = {}
    for name, field in meta.fields_map.items():
        if name in fk or name in o2o:
            kind = "relation"
        elif name in backward:
            kind = "backward"
        elif name in m2m:
            kind = "m2m"
        else:
            kind = _kind_of(field)
        default = getattr(field, "default", None)
        described[name] = ModelField(
            name=name,
            kind=kind,
            column=getattr(field, "source_field", None) or name,
            null=bool(getattr(field, "null", False)),
            required=bool(getattr(field, "required", False)),
            default=default,
            has_default=default is not None,
            max_length=getattr(field, "max_length", None),
            choices=_choices_of(field),
            related=_related_of(field),
            related_name=getattr(field, "model_name", None),
            generated=bool(getattr(field, "generated", False)),
            primary=name == pk,
            unique=bool(getattr(field, "unique", False)),
            description=getattr(field, "description", None),
            shadow=name in shadows,
        )
    return described


def _kind_of(field: typing.Any) -> str:
    """The kind for a concrete column, found by walking the field's MRO.

    By MRO rather than by exact class, so ``PasswordField(CharField)`` is a
    password and anybody's ``UpperCaseCharField(CharField)`` is still text.
    """
    if getattr(field, "password", False):
        return "password"
    # An enum column is recognised by the enum it names, not by its class:
    # Tortoise's `CharEnumField` is a factory and the runtime class is
    # `CharEnumFieldInstance`, which no name-based map would ever match.
    if getattr(field, "enum_type", None) is not None:
        return "enum"
    for cls in type(field).__mro__:
        kind = _BY_CLASS.get(cls.__name__)
        if kind is not None:
            return kind
    return "unknown"


def _choices_of(field: typing.Any) -> tuple[tuple[typing.Any, str], ...]:
    """The closed set a column accepts, if it declares one.

    Two spellings are read: an enum field's ``enum_type``, and a plain
    ``choices`` sequence, which several projects add by convention.
    """
    from warder.naming import coerce_choices

    enum = getattr(field, "enum_type", None)
    if enum is not None:
        try:
            return tuple(
                (member.value, str(member.name).replace("_", " ").capitalize())
                for member in enum
            )
        except TypeError:  # pragma: no cover - not iterable after all
            return ()
    declared = getattr(field, "choices", None)
    if declared:
        return coerce_choices(declared)
    return ()


def _related_of(field: typing.Any) -> type | None:
    """The far model, or ``None`` while the ORM has it as a string."""
    related = getattr(field, "related_model", None)
    return related if isinstance(related, type) else None
