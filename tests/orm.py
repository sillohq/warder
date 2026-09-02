"""Real ``sillo.record`` models, for the half of the package that needs them.

The declaration layer is tested without a database — that is the point of it.
The resolver is not: it reads ``_meta.fields_map``, follows foreign keys and
decides what a column wants to be, and testing that against a fake would test
the fake.

These are ordinary models, linked but never connected. ``related_model`` on a
foreign key is a *string* until Tortoise resolves it, and half of what the
resolver does is follow one — but resolving them needs no database, only
``init_models``. So the suite still opens no connection.
"""

from __future__ import annotations

from enum import Enum, IntEnum

from sillo.record import Model
from sillo.record.fields import PasswordField, SlugField
from sillo.users import UserBaseModel
from tortoise import Tortoise, fields


class Kind(str, Enum):
    ALPHA = "alpha"
    BETA = "beta"


class Rank(IntEnum):
    LOW = 1
    HIGH = 2


class Author(Model):
    """The far side of a foreign key, with an obvious display column."""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120)
    email = fields.CharField(max_length=200, unique=True)
    is_active = fields.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        table = "warder_authors"


class Tag(Model):
    id = fields.IntField(primary_key=True)
    label = fields.CharField(max_length=60, unique=True)

    class Meta:
        table = "warder_tags"


class Post(Model):
    """One of most things: text, prose, a state, money, JSON, a key, a secret."""

    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=200, description="The headline")
    slug = SlugField(max_length=200)
    body = fields.TextField(null=True)
    status = fields.CharField(max_length=20, default="draft")
    words = fields.IntField(default=0)
    price = fields.DecimalField(max_digits=8, decimal_places=2, null=True)
    live = fields.BooleanField(default=False)
    meta = fields.JSONField(default=dict)
    secret = PasswordField()
    published_at = fields.DatetimeField(null=True)
    author = fields.ForeignKeyField("models.Author", related_name="posts", null=True)
    tags = fields.ManyToManyField("models.Tag", related_name="posts")

    def __str__(self) -> str:
        return self.title

    class Meta:
        table = "warder_posts"


class Comment(Model):
    """Two foreign keys to one model, which is the ambiguity `via=` exists for."""

    id = fields.IntField(primary_key=True)
    body = fields.TextField()
    post = fields.ForeignKeyField("models.Post", related_name="comments")
    author = fields.ForeignKeyField("models.Author", related_name="comments", null=True)
    reviewer = fields.ForeignKeyField(
        "models.Author", related_name="reviewed", null=True
    )

    class Meta:
        table = "warder_comments"


class Wide(Model):
    """One column of every remaining kind, so the inference has no blind spots."""

    id = fields.UUIDField(primary_key=True)
    kind = fields.CharEnumField(Kind, default=Kind.ALPHA)
    rank = fields.IntEnumField(Rank, default=Rank.LOW)
    ratio = fields.FloatField(default=0.0)
    on = fields.DateField(null=True)
    at = fields.TimeField(null=True)
    blob = fields.BinaryField(null=True)
    prose = fields.CharField(max_length=4000, null=True)
    tags = fields.ManyToManyField("models.Tag", related_name="wides")

    class Meta:
        table = "warder_wide"


class Person(UserBaseModel):
    """Somebody's own user model — what `Auth(users=...)` points at."""

    display = fields.CharField(max_length=120, null=True)

    def __str__(self) -> str:
        return self.display or self.email

    class Meta:
        table = "warder_people"


class Sparse(UserBaseModel):
    """A user model with no staff flag, to prove the gate warning fires."""

    class Meta:
        table = "warder_sparse"


class Required(Model):
    """A column that is required, has no default and cannot be null."""

    id = fields.IntField(primary_key=True)
    code = fields.CharField(max_length=10)

    class Meta:
        table = "warder_required"


# Links the foreign keys — turning `"models.Author"` into the class — without
# a connection, a schema or an event loop.
Tortoise.init_models([__name__], "models")
