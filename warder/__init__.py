"""Warder — a declarative admin for Sillo.

A warder keeps the keys. This one keeps your models: what is listed, what is
editable, who may see it, and which rows are theirs.

::

    from warder import Access, Admin, Column, Field, Filter, List, Resource, Section

    admin = Admin(title="Acme Ops", prefix="/admin")

    admin.add(Resource(
        Post,
        group="Content",
        list=List(
            Column("title", link=True),
            Column.relation("author", display="email"),
            Column.badge("status", colors={"live": "green", "draft": "zinc"}),
            filters=[Filter.search("title", "body"), Filter.choice("status", STATUSES)],
            actions=[Action("Publish", publish)],
            sort=Sort.desc("published_at"),
        ),
        form=Form(Section("Content", Field("title"), Field("body"))),
        access=Access(view=True, add="post.add", delete=False),
    ))

    admin.mount(app)

Three ideas hold the whole package up.

**A type annotation describes a type. It never selects behaviour.** Nothing
here reads ``__annotations__``, and nothing changes because a parameter is
spelled one way rather than another. Where something must be injected it
arrives as a value — a default, a keyword — because a value is visible and an
annotation is not.

**A declaration is a value.** Nameable, storable, comparable, generatable in a
loop, extendable with :meth:`~warder.base.Declaration.with_`. There is no
metaclass and no import-time registration: a package ships declarations and
the application decides whether to mount them.

**Mistakes fail at mount, not at request.** Every reference is resolved once,
at start-up, against the model — with the file and line the declaration was
written on in the message. A misspelled column should never become an empty
cell in production.
"""

from __future__ import annotations

from warder.access import Access, Gate, Role, Scope
from warder.actions import Action
from warder.auth import MFA, Audit, Auth, Impersonation, Login, Session
from warder.base import Declaration
from warder.columns import Column
from warder.conditions import When
from warder.errors import (
    ActionFailed,
    DeclarationError,
    Denied,
    NotConfigured,
    WarderError,
)
from warder.fields import Field
from warder.filters import Filter
from warder.formats import Format
from warder.layout import Empty, Panel, Section
from warder.pages import Card, Dashboard, Page
from warder.resource import Resource, crud
from warder.results import (
    Outcome,
    download,
    go,
    modal,
    nothing,
    notice,
    problem,
    refresh,
    warning,
)
from warder.screens import Detail, Form, List
from warder.site import Admin
from warder.sorting import Sort, SortTerm
from warder.theme import Theme
from warder.widgets import Widget

__version__ = "0.1.0"

__all__ = [
    "MFA",
    "Access",
    "Action",
    "ActionFailed",
    "Admin",
    "Audit",
    "Auth",
    "Card",
    "Column",
    "Dashboard",
    "Declaration",
    "DeclarationError",
    "Denied",
    "Detail",
    "Empty",
    "Field",
    "Filter",
    "Form",
    "Format",
    "Gate",
    "Impersonation",
    "List",
    "Login",
    "NotConfigured",
    "Outcome",
    "Page",
    "Panel",
    "Resource",
    "Role",
    "Scope",
    "Section",
    "Session",
    "Sort",
    "SortTerm",
    "Theme",
    "WarderError",
    "When",
    "Widget",
    "__version__",
    "crud",
    "download",
    "go",
    "modal",
    "nothing",
    "notice",
    "problem",
    "refresh",
    "warning",
]
