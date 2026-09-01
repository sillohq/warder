"""The README's examples, run.

Documentation that does not compile is worse than none, because it is trusted.
Every snippet in the README appears here; if one changes, this fails.
"""

from __future__ import annotations

import pytest
from fakes import model

from warder import (
    MFA,
    Access,
    Action,
    Admin,
    Audit,
    Auth,
    Column,
    Field,
    Filter,
    Form,
    Gate,
    Impersonation,
    List,
    Login,
    Resource,
    Role,
    Scope,
    Section,
    Session,
    Sort,
    Theme,
    notice,
)

Post = model("Post")
Tag = model("Tag")
Team = model("Team")
Order = model("Order")
Category = model("Category")
Region = model("Region")
Currency = model("Currency")
User = model("User")


async def publish(ctx, rows):
    count = await rows.filter(status="draft").update(status="live")
    return notice(f"Published {count} posts")


def test_the_opening_example():
    admin = Admin(title="Acme Ops", prefix="/admin")
    admin.add(
        Resource(
            Post,
            group="Content",
            icon="file-text",
            list=List(
                Column("title", link=True),
                Column.relation("author", display="email"),
                Column.badge("status", colors={"live": "green", "draft": "zinc"}),
                Column.date("published_at", label="Published", style="relative"),
                Column.compute(
                    "Words", lambda row: len(row.body.split()), sort="word_count"
                ),
                filters=[
                    Filter.search("title", "body"),
                    Filter.choice("status", ["draft", "live"]),
                    Filter.date_range("published_at", presets=["7d", "30d", "quarter"]),
                ],
                actions=[Action("Publish", publish, confirm="Publish {count} posts?")],
                sort=Sort.desc("published_at"),
            ),
            form=Form(
                Section("Content", Field("title"), Field.markdown("body")),
                Section("Publishing", Field("status"), Field("published_at")),
                Section("Audit", Field.readonly("created_at"), collapsed=True),
            ),
            access=Access(
                view=True,
                add="post.add",
                change=lambda ctx, row: row.author_id == ctx.user.id,
                delete=False,
            ),
        )
    )
    assert admin.check() == []
    assert admin.navigation()[0]["label"] == "Content"


def test_generating_resources_in_a_loop():
    def reference_data(model_, *fields):
        return Resource(
            model_,
            group="Reference",
            list=List(*[Column(f) for f in fields], sort=Sort.asc(fields[0])),
            form=Form(Section("", *[Field(f) for f in fields])),
            access=Access.by_permission("reference", delete=False),
        )

    admin = Admin()
    for model_ in (Tag, Category, Region, Currency):
        admin.add(reference_data(model_, "name", "slug"))
    assert len(admin.resources) == 4


def test_extending_a_shared_base():
    base = List(Column("id"), Column("name"), per_page=50)
    admin = Admin()
    admin.add(Resource(Tag, list=base.with_(Column("slug"))))
    admin.add(Resource(Team, list=base.with_(Column.relation("owner"))))
    assert len(base.columns) == 2
    assert admin.at("tag").list.per_page == 50


def test_joins_are_derived():
    screen = List(Column("author__email"), Column.relation("team"), Column("title"))
    assert screen.joins == ("author", "team")


def test_a_value_error_names_the_alternatives():
    with pytest.raises(ValueError) as caught:
        Column("total", align="middle")
    assert str(caught.value) == (
        "align='middle' is not valid. Use one of: 'left', 'center', 'right'."
    )


def test_an_action_that_collects_input():
    action = Action("Assign", lambda c, r, v: None, fields=[Field.relation("assignee")])
    assert action.collects


def test_the_auth_example():
    admin = Admin(
        title="Acme Ops",
        auth=Auth(
            users=User,
            gate=Gate.staff(),
            session=Session(idle="30m", absolute="12h", concurrent=1),
            login=Login(throttle="5/15m", remember=True),
            mfa=MFA.totp(required=Gate.role("owner")),
            impersonation=Impersonation(gate=Gate.permission("users.impersonate")),
            audit=Audit(retain="1y", redact=["password", "token", "secret"]),
        ),
    )
    admin.add(Resource(Post), Resource(Tag))
    admin.roles(
        Role("editor", grants=Role.crud(Post, Tag)),
        Role("owner", grants="*"),
    )
    assert admin.check() == []
    assert admin.auth.grants_of("editor") >= {"post.view", "tag.delete"}


def test_access_and_scope_together():
    resource = Resource(
        Order,
        access=Access(change=lambda ctx, row: row.team_id == ctx.user.team_id),
        scope=Scope.tenant("team_id"),
    )
    assert resource.scope.kind == "filters"


def test_a_field_can_be_kept_out_of_the_props():
    field = Field("salary", access=Access(view="hr.salary.view"))
    assert field.access.rule("view") == "hr.salary.view"


def test_the_themes_in_the_table():
    assert (
        Admin(theme=Theme.console(accent="#4f46e5", density="compact")).theme.density
        == "compact"
    )
    assert Admin(theme=Theme.native()).theme.style == "native"


def test_mount_is_honest_about_not_being_finished():
    from warder.errors import NotConfigured

    with pytest.raises(NotConfigured, match=r"warder\.routes"):
        Admin().mount(object())
