"""The two tables Warder brings, and why they are not imported for you.

``AdminUser`` is the account you sign in with when the application has no user
model of its own — an internal tool, a fresh project, the first hour of a new
one. Point ``Auth(users=YourUser)`` at your own model and this one is never
touched.

``Activity`` is the audit trail: who did what, to which row, and what changed.
Field-level, because "Order 4182 was changed" is a log line and "status went
from held to shipped" is an answer.

**Neither is registered by importing Warder.** Model discovery scans a module's
namespace, so a package that imported these would put ``warder_users`` and
``warder_activity`` into the database of every project that installed it —
including the majority that pass their own user model and would never write a
row to either. You opt in by naming this module::

    setup_record(app, config, model_modules=["myapp.models", "warder.models"])
"""

from __future__ import annotations

import typing

from sillo.record import Model
from sillo.users import UserBaseModel
from tortoise import fields

__all__ = ["Activity", "AdminUser"]


class AdminUser(UserBaseModel):
    """The bundled account, for an admin that brings its own users.

    A ``UserBaseModel``, so it already carries ``email``, ``username``,
    ``password``, ``is_active``, ``is_staff``, ``is_superuser`` and
    ``last_login``, and already knows how to hash and check a password through
    ``sillo.hashing``. Warder adds a display name and the timestamps.

    Subclass it to add fields; ``Auth(users=YourAdminUser)`` will use yours.
    """

    name = fields.CharField(max_length=150, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name or self.username or self.email

    class Meta:
        table = "warder_users"


class Activity(Model):
    """One thing somebody did.

    Written by the admin itself on every create, change and delete, with the
    field-level diff, so the answer to "who set this to zero on Tuesday" is a
    query rather than an investigation.

    ``actor`` is a string rather than a foreign key on purpose: the trail has
    to survive the account being deleted, and a cascade would remove exactly
    the rows you most want when an account is deleted.
    """

    id = fields.IntField(primary_key=True)
    at = fields.DatetimeField(auto_now_add=True, db_index=True)

    actor = fields.CharField(max_length=200, db_index=True)
    actor_id = fields.CharField(max_length=64, null=True)

    action = fields.CharField(max_length=20, db_index=True)
    resource = fields.CharField(max_length=100, db_index=True)
    object_id = fields.CharField(max_length=64, null=True)
    label = fields.CharField(max_length=300, null=True)

    changes: fields.Field[dict] = fields.JSONField(default=dict)
    address = fields.CharField(max_length=64, null=True)
    request_id = fields.CharField(max_length=64, null=True)

    def __str__(self) -> str:
        return (
            f"{self.actor} {self.action} {self.resource} {self.object_id or ''}".strip()
        )

    @property
    def summary(self) -> str:
        """What changed, in one line: ``status: held → shipped``."""
        if not self.changes:
            return ""
        parts = [
            f"{name}: {_short(pair.get('from'))} → {_short(pair.get('to'))}"
            for name, pair in list(self.changes.items())[:3]
            if isinstance(pair, dict)
        ]
        extra = len(self.changes) - len(parts)
        if extra > 0:
            parts.append(f"and {extra} more")
        return ", ".join(parts)

    class Meta:
        table = "warder_activity"
        ordering: typing.ClassVar[list[str]] = ["-at"]


def _short(value: typing.Any, at: int = 40) -> str:
    text = "—" if value is None else str(value)
    return text if len(text) <= at else f"{text[:at].rstrip()}…"
