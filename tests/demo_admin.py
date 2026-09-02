"""An admin the CLI can import, in the three states it has to report on.

A module rather than a fixture, because ``warder check`` takes a
``module:attribute`` target and importing one is the thing being tested.
"""

from __future__ import annotations

from orm import Author, Post

from warder import Admin, Column, List, Resource

#: Resolves cleanly.
admin = Admin(title="Demo Ops")
admin.add(Resource(Post, list=List(Column("title", link=True))), Resource(Author))

#: Fails at bind: the column does not exist.
broken = Admin(title="Broken")
broken.add(Resource(Post, list=List(Column("titel"))))

#: Fails at check, twice, without needing a model at all.
declaration_problems = Admin(title="Duplicated")
declaration_problems.add(
    Resource(Post, list=List(Column("title"), Column("title"), totals={"nope": "sum"}))
)

#: Not an Admin.
not_an_admin = 42
