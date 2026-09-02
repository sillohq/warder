"""Actions, permissions, scope and login — the paths that decide what happens.

Separate from `test_routes.py`, which proves the screens render. This module is
about what the server *refuses*: a button the interface hides is a courtesy, and
every one of these checks has to hold against a request that skips the browser
entirely.
"""

from __future__ import annotations

import httpx
import pytest
from orm import Author, Post, Tag
from sillo import SilloApp
from test_routes import INERTIA, _delete, _get, _post, page_of
from tortoise import Tortoise

from warder import (
    Access,
    Action,
    Admin,
    Column,
    Field,
    Filter,
    Form,
    Gate,
    List,
    Page,
    Resource,
    Scope,
    Section,
    download,
    go,
    notice,
    problem,
)
from warder.auth import Auth
from warder.errors import ActionFailed, Denied


@pytest.fixture
async def database():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["orm"]})
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


@pytest.fixture
async def posts(database):
    author = await Author.create(name="Ada", email="ada@example.com")
    for index in range(4):
        await Post.create(
            title=f"Post {index}",
            slug=f"post-{index}",
            status="draft",
            words=index,
            secret="x",
            author=author,
        )
    return author


def site(*resources, **options) -> Admin:
    admin = Admin(
        title="Ops",
        auth=options.pop("auth", Auth(gate=Gate.custom(lambda ctx: True))),
        **options,
    )
    admin.add(*resources)
    return admin


def client(admin: Admin) -> httpx.AsyncClient:
    app = SilloApp()
    admin.mount(app)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://admin.test"
    )


# ----------------------------------------------------------------- actions


async def published(ctx, rows):
    count = await rows.update(status="live")
    return notice(f"Published {count} posts")


def with_action(action: Action, **list_options) -> Admin:
    return site(
        Resource(Post, list=List(Column("title"), actions=[action], **list_options))
    )


async def test_an_action_runs_over_the_selected_rows(posts):
    first = await Post.first()
    admin = with_action(Action("Publish", published))
    await _post(client(admin), "/admin/post/actions/publish", json={"ids": [first.pk]})
    await first.refresh_from_db()
    assert first.status == "live"
    assert await Post.filter(status="draft").count() == 3


async def test_an_action_gets_a_queryset_not_a_list(posts):
    # Forty thousand rows should be one statement, not forty thousand.
    seen = {}

    async def count_them(ctx, rows):
        seen["count"] = await rows.count()
        return None

    admin = with_action(Action("Count", count_them))
    ids = [post.pk for post in await Post.all()]
    await _post(client(admin), "/admin/post/actions/count", json={"ids": ids})
    assert seen["count"] == 4


async def test_an_action_with_no_selection_says_so(posts):
    admin = with_action(Action("Publish", published))
    response = await _post(
        client(admin), "/admin/post/actions/publish", json={"ids": []}
    )
    assert response.status_code == 303
    assert await Post.filter(status="live").count() == 0


async def test_an_action_that_needs_no_selection_runs_anyway(posts):
    admin = with_action(Action("Publish", published, selection="none"))
    await _post(client(admin), "/admin/post/actions/publish", json={"ids": []})
    assert await Post.filter(status="live").count() == 4


async def test_an_action_with_fields_is_given_them(posts):
    seen = {}

    async def assign(ctx, rows, values):
        seen.update(values)
        return None

    action = Action("Assign", assign, fields=[Field("note")])
    admin = with_action(action)
    first = await Post.first()
    await _post(
        client(admin),
        "/admin/post/actions/assign",
        json={"ids": [first.pk], "values": {"note": "hello"}},
    )
    assert seen == {"note": "hello"}


async def test_the_built_in_delete_removes_the_selection(posts):
    first = await Post.first()
    admin = with_action(Action.delete())
    await _post(client(admin), "/admin/post/actions/delete", json={"ids": [first.pk]})
    assert not await Post.filter(pk=first.pk).exists()
    assert await Post.all().count() == 3


async def test_an_unknown_action_is_a_404(posts):
    admin = with_action(Action("Publish", published))
    response = await _post(client(admin), "/admin/post/actions/nope", json={"ids": []})
    assert response.status_code == 404


async def test_an_action_can_send_you_somewhere(posts):
    admin = with_action(
        Action("Report", lambda ctx, rows: go("/reports/1"), selection="none")
    )
    response = await _post(
        client(admin), "/admin/post/actions/report", json={"ids": []}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/reports/1"


async def test_an_action_can_hand_back_a_file(posts):
    action = Action(
        "Export",
        lambda ctx, rows: download(
            "a,b\n1,2", filename="rows.csv", content_type="text/csv"
        ),
        selection="none",
    )
    response = await _post(
        client(with_action(action)), "/admin/post/actions/export", json={}
    )
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="rows.csv"'
    assert response.text == "a,b\n1,2"


async def test_an_action_can_stop_itself_with_a_message(posts):
    def refuse(ctx, rows):
        raise ActionFailed("Nothing to publish.")

    admin = with_action(Action("Publish", refuse, selection="none"))
    response = await _post(client(admin), "/admin/post/actions/publish", json={})
    assert response.status_code == 303


async def test_an_action_can_refuse_the_person_running_it(posts):
    def refuse(ctx, rows):
        raise Denied("Not for you.")

    admin = with_action(Action("Publish", refuse, selection="none"))
    assert (
        await _post(client(admin), "/admin/post/actions/publish", json={})
    ).status_code == 303


async def test_a_problem_outcome_is_not_a_crash(posts):
    admin = with_action(
        Action("Try", lambda ctx, rows: problem("It did not work."), selection="none")
    )
    assert (
        await _post(client(admin), "/admin/post/actions/try", json={})
    ).status_code == 303


async def test_an_action_gate_is_enforced_on_the_server(posts):
    # The interface hides the button. That is a courtesy, not a control.
    action = Action("Publish", published, gate=Gate.superuser(), selection="none")
    response = await _post(
        client(with_action(action)), "/admin/post/actions/publish", json={}
    )
    assert page_of(response)["component"] == "Denied"
    assert await Post.filter(status="live").count() == 0


async def test_an_action_cannot_widen_what_the_resource_allows(posts):
    admin = site(
        Resource(
            Post,
            access=Access(change=False),
            list=List(
                Column("title"),
                actions=[Action("Publish", published, selection="none")],
            ),
        )
    )
    response = await _post(client(admin), "/admin/post/actions/publish", json={})
    assert page_of(response)["component"] == "Denied"
    assert await Post.filter(status="live").count() == 0


# ------------------------------------------------------------- permissions


async def test_a_resource_you_may_not_view_is_refused(posts):
    admin = site(Resource(Post, access=Access(view=False)))
    assert page_of(await _get(client(admin), "/admin/post"))["component"] == "Denied"


async def test_a_resource_you_may_not_add_to_refuses_the_form(posts):
    admin = site(Resource(Post, access=Access(add=False)))
    assert (
        page_of(await _get(client(admin), "/admin/post/new"))["component"] == "Denied"
    )


async def test_a_resource_you_may_not_add_to_refuses_the_write(posts):
    admin = site(Resource(Post, access=Access(add=False)))
    before = await Post.all().count()
    await _post(client(admin), "/admin/post", json={"title": "Sneaky"})
    assert await Post.all().count() == before


async def test_a_row_you_may_not_change_refuses_the_write(posts):
    first = await Post.first()
    admin = site(Resource(Post, access=Access(change=False)))
    await _post(client(admin), f"/admin/post/{first.pk}", json={"title": "Renamed"})
    await first.refresh_from_db()
    assert first.title != "Renamed"


async def test_a_row_you_may_not_delete_survives(posts):
    first = await Post.first()
    admin = site(Resource(Post, access=Access(delete=False)))
    await _delete(client(admin), f"/admin/post/{first.pk}")
    assert await Post.filter(pk=first.pk).exists()


async def test_a_row_level_rule_is_applied_to_the_row(posts):
    first = await Post.first()
    admin = site(Resource(Post, access=Access(change=lambda ctx, row: row.words > 100)))
    await _post(client(admin), f"/admin/post/{first.pk}", json={"title": "Renamed"})
    await first.refresh_from_db()
    assert first.title != "Renamed"


async def test_the_list_reports_what_you_may_do(posts):
    admin = site(Resource(Post, access=Access(add=False, delete=False)))
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert props["can"] == {"add": False, "change": True, "delete": False}


# ------------------------------------------------------------------- scope


async def test_a_scope_narrows_the_list(posts):
    admin = site(
        Resource(Post, scope=Scope.query(lambda ctx, rows: rows.filter(words__gte=2)))
    )
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert props["total"] == 2


async def test_a_row_outside_your_scope_is_a_404_not_a_403(posts):
    # Telling you a row exists that you may not see is itself a disclosure.
    first = await Post.filter(words=0).first()
    admin = site(
        Resource(Post, scope=Scope.query(lambda ctx, rows: rows.filter(words__gte=2)))
    )
    assert (await _get(client(admin), f"/admin/post/{first.pk}")).status_code == 404


async def test_an_action_cannot_reach_outside_the_scope(posts):
    first = await Post.filter(words=0).first()
    admin = site(
        Resource(
            Post,
            scope=Scope.query(lambda ctx, rows: rows.filter(words__gte=2)),
            list=List(Column("title"), actions=[Action("Publish", published)]),
        )
    )
    await _post(client(admin), "/admin/post/actions/publish", json={"ids": [first.pk]})
    await first.refresh_from_db()
    assert first.status == "draft"


# ---------------------------------------------------------- field access


async def test_a_column_you_may_not_view_never_reaches_the_browser(posts):
    admin = site(
        Resource(
            Post,
            list=List(Column("title"), Column("words", access=Access(view=False))),
        )
    )
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert [column["key"] for column in props["columns"]] == ["title"]
    assert "words" not in props["rows"][0]["cells"]


async def test_a_field_you_may_not_view_is_absent_from_the_form(posts):
    admin = site(
        Resource(
            Post,
            form=Form(
                Section("", Field("title"), Field("words", access=Access(view=False)))
            ),
        )
    )
    props = page_of(await _get(client(admin), "/admin/post/new", headers=INERTIA))[
        "props"
    ]
    names = [
        field["name"] for section in props["sections"] for field in section["fields"]
    ]
    assert names == ["title"]


async def test_a_field_you_may_not_change_is_not_written(posts):
    first = await Post.first()
    admin = site(
        Resource(
            Post,
            form=Form(
                Section("", Field("title"), Field("words", access=Access(change=False)))
            ),
        )
    )
    await _post(
        client(admin),
        f"/admin/post/{first.pk}",
        json={"title": "Renamed", "words": 9999},
    )
    await first.refresh_from_db()
    assert first.title == "Renamed"
    assert first.words != 9999


async def test_a_readonly_field_is_readonly_on_the_server(posts):
    first = await Post.first()
    admin = site(
        Resource(Post, form=Form(Section("", Field("title"), Field.readonly("words"))))
    )
    await _post(
        client(admin), f"/admin/post/{first.pk}", json={"title": "Fine", "words": 9999}
    )
    await first.refresh_from_db()
    assert first.words != 9999


# ------------------------------------------------------------------ forms


async def test_a_field_check_returns_the_form_with_the_error(posts):
    admin = site(
        Resource(
            Post,
            form=Form(
                Section(
                    "",
                    Field("title", validate=lambda v: "Required" if not v else None),
                )
            ),
        )
    )
    props = page_of(await _post(client(admin), "/admin/post", json={"title": ""}))[
        "props"
    ]
    assert props["errors"]["title"] == ["Required"]


async def test_a_failed_submission_keeps_what_was_typed(posts):
    admin = site(
        Resource(
            Post,
            form=Form(
                Section(
                    "", Field("title", validate=lambda v: "No" if v == "bad" else None)
                )
            ),
        )
    )
    props = page_of(await _post(client(admin), "/admin/post", json={"title": "bad"}))[
        "props"
    ]
    assert props["values"]["title"] == "bad"


async def test_a_unique_constraint_becomes_a_readable_error(posts):
    await Tag.create(label="taken")
    admin = site(Resource(Tag, form=Form(Section("", Field("label")))))
    props = page_of(await _post(client(admin), "/admin/tag", json={"label": "taken"}))[
        "props"
    ]
    assert "already exists" in props["errors"]["__all__"]


async def test_a_whole_form_check_runs_after_the_fields(posts):
    def together(ctx, values, row):
        return {"title": "Reserved"} if values.get("title") == "admin" else None

    admin = site(
        Resource(Post, form=Form(Section("", Field("title")), validate=together))
    )
    props = page_of(await _post(client(admin), "/admin/post", json={"title": "admin"}))[
        "props"
    ]
    assert props["errors"]["title"] == "Reserved"


# ------------------------------------------------------------------ login


class Backend:
    """The smallest thing that satisfies the admin's auth backend."""

    def __init__(self) -> None:
        self.signed_in = False

    async def login(self, ctx, identity, secret):
        self.signed_in = identity == "ada@example.com" and secret == "correct"
        return self.signed_in

    async def logout(self, ctx):
        self.signed_in = False


async def test_signing_in_redirects_into_the_admin(posts):
    backend = Backend()
    admin = site(Resource(Post), auth=Auth(backend=backend, gate=Gate.never()))
    response = await _post(
        client(admin),
        "/admin/login",
        json={"email": "ada@example.com", "password": "correct"},
    )
    assert response.status_code in (302, 303)
    assert backend.signed_in


async def test_a_wrong_password_says_nothing_useful(posts):
    # One message for a wrong name and a wrong password, so the form cannot be
    # used to find out which accounts exist.
    admin = site(Resource(Post), auth=Auth(backend=Backend(), gate=Gate.never()))
    props = page_of(
        await _post(
            client(admin),
            "/admin/login",
            json={"email": "ada@example.com", "password": "no"},
        )
    )["props"]
    assert props["errors"]["__all__"] == "Those details did not match."


async def test_an_admin_with_no_backend_still_has_one(posts):
    # `Admin()` with no auth= signs people in against the bundled user model.
    # There is no "no backend configured" state to report.
    from warder.backends import SessionAuth

    assert isinstance(Auth().resolve(), SessionAuth)


async def test_a_blank_sign_in_is_refused(posts):
    admin = site(Resource(Post), auth=Auth(gate=Gate.never()))
    props = page_of(await _post(client(admin), "/admin/login", json={}))["props"]
    assert props["errors"]["__all__"] == "Those details did not match."


async def test_an_already_admitted_visitor_is_sent_onward(posts):
    admin = site(Resource(Post))
    response = await _get(client(admin), "/admin/login")
    assert response.status_code == 302
    assert response.headers["location"] == "/admin"


async def test_signing_out_returns_to_the_login_page(posts):
    backend = Backend()
    admin = site(Resource(Post), auth=Auth(backend=backend))
    response = await _post(client(admin), "/admin/logout")
    assert response.status_code == 303
    assert response.headers["location"].endswith("/admin/login")


# ------------------------------------------------------------------ pages


async def test_a_custom_page_renders_its_props(posts):
    async def reconcile(ctx):
        return {"unmatched": await Post.filter(status="draft").count()}

    admin = site(Resource(Post))
    admin.add(Page("/reconcile", "Reconciliation", reconcile))
    props = page_of(await _get(client(admin), "/admin/reconcile", headers=INERTIA))[
        "props"
    ]
    assert props["page"] == {"unmatched": 4}


async def test_a_page_gate_is_enforced(posts):
    admin = site(Resource(Post))
    admin.add(Page("/secret", "Secret", lambda ctx: {}, gate=Gate.superuser()))
    assert page_of(await _get(client(admin), "/admin/secret"))["component"] == "Denied"


async def test_a_page_may_return_an_outcome(posts):
    admin = site(Resource(Post))
    admin.add(Page("/away", "Away", lambda ctx: go("/elsewhere")))
    response = await _get(client(admin), "/admin/away")
    assert response.status_code == 303
    assert response.headers["location"] == "/elsewhere"


# ---------------------------------------------------------------- filters


async def test_a_toggle_filter_narrows(posts):
    admin = site(
        Resource(
            Post,
            list=List(
                Column("title"),
                filters=[Filter.toggle("Long", lambda rows: rows.filter(words__gte=2))],
            ),
        )
    )
    props = page_of(await _get(client(admin), "/admin/post?long=1", headers=INERTIA))[
        "props"
    ]
    assert props["total"] == 2


async def test_a_custom_filter_receives_its_value(posts):
    admin = site(
        Resource(
            Post,
            list=List(
                Column("title"),
                filters=[
                    Filter.custom(
                        "Words", lambda rows, value: rows.filter(words=int(value))
                    )
                ],
            ),
        )
    )
    props = page_of(await _get(client(admin), "/admin/post?words=3", headers=INERTIA))[
        "props"
    ]
    assert props["total"] == 1


async def test_a_card_loader_may_return_a_query(posts):
    # `lambda ctx: Post.all().count()` is the obvious thing to write, and the
    # count is what was meant -- not "<CountQuery object at 0x...>".
    from warder import Card, Dashboard

    admin = site(Resource(Post))
    admin.add(Dashboard(Card.number("Posts", lambda ctx: Post.all().count())))
    props = page_of(await _get(client(admin), "/admin", headers=INERTIA))["props"]
    assert props["cards"][0]["data"] == 4


async def test_a_page_handler_may_return_a_query_result(posts):
    admin = site(Resource(Post))
    admin.add(Page("/count", "Count", lambda ctx: Post.all().count()))
    props = page_of(await _get(client(admin), "/admin/count", headers=INERTIA))["props"]
    assert props["page"] == 4


# ------------------------------------------------------------------- export


def exportable(**list_options) -> Admin:
    return site(
        Resource(
            Post,
            list=List(
                Column("title"),
                Column.money("fee") if False else Column("words"),
                filters=[Filter.choice("status", ["draft", "live"])],
                **list_options,
            ),
        )
    )


async def test_csv_carries_the_columns_headings(posts):
    response = await _get(client(exportable()), "/admin/post/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.lstrip("﻿").splitlines()[0] == "Title,Words"


async def test_the_download_is_named_after_the_resource(posts):
    response = await _get(client(exportable()), "/admin/post/export?format=csv")
    assert 'filename="post-' in response.headers["content-disposition"]


async def test_export_takes_the_filtered_set_not_the_page(posts):
    # "Export" means everything I am looking at. Making somebody select forty
    # thousand rows first is a way of not having the feature.
    response = await _get(
        client(exportable(per_page=1)), "/admin/post/export?format=csv"
    )
    assert len(response.text.strip().splitlines()) == 5  # header + 4 rows


async def test_export_honours_a_filter(posts):
    first = await Post.first()
    first.status = "live"
    await first.save()
    response = await _get(
        client(exportable()), "/admin/post/export?format=csv&status=live"
    )
    assert len(response.text.strip().splitlines()) == 2


async def test_json_export_is_a_list_of_objects(posts):
    import json

    response = await _get(client(exportable()), "/admin/post/export?format=json")
    rows = json.loads(response.text)
    assert len(rows) == 4
    assert set(rows[0]) == {"Title", "Words"}


async def test_an_unknown_format_falls_back_to_csv(posts):
    response = await _get(client(exportable()), "/admin/post/export?format=xlsx")
    assert response.headers["content-type"].startswith("text/csv")


async def test_a_cell_that_looks_like_a_formula_is_defused(posts):
    # A spreadsheet runs anything starting with = + - or @, so an admin export
    # is how a cell somebody typed becomes code somebody else runs.
    first = await Post.first()
    first.title = "=cmd|'/c calc'!A1"
    await first.save()
    response = await _get(client(exportable()), "/admin/post/export?format=csv")
    assert "\"'=cmd" in response.text or "'=cmd" in response.text
    assert not any(line.startswith("=") for line in response.text.splitlines())


async def test_export_needs_permission_to_view(posts):
    admin = site(Resource(Post, access=Access(view=False), list=List(Column("title"))))
    response = await _get(client(admin), "/admin/post/export?format=csv")
    assert page_of(response)["component"] == "Denied"


async def test_export_can_be_switched_off(posts):
    admin = site(Resource(Post, list=List(Column("title"), export=False)))
    assert (await _get(client(admin), "/admin/post/export")).status_code == 404


async def test_export_is_scoped_like_everything_else(posts):
    admin = site(
        Resource(
            Post,
            list=List(Column("title")),
            scope=Scope.query(lambda ctx, rows: rows.filter(words__gte=2)),
        )
    )
    response = await _get(client(admin), "/admin/post/export?format=csv")
    assert len(response.text.strip().splitlines()) == 3


# ----------------------------------------------------------- detail panels


async def test_a_related_panel_reuses_the_child_resources_columns(posts):
    # "Comments" on a post should look the way the Comments screen looks, and
    # nobody should have declared it twice.
    from warder import Detail, Panel

    admin = site(
        Resource(Author, detail=Detail(Panel.related("Posts", Post))),
        Resource(Post, list=List(Column("title"), Column.badge("status"))),
    )
    author = await Author.first()
    props = page_of(
        await _get(client(admin), f"/admin/author/{author.pk}", headers=INERTIA)
    )["props"]
    panel = next(p for p in props["panels"] if p["kind"] == "related")
    assert [c["key"] for c in panel["options"]["columns"]] == ["title", "status"]
    assert panel["options"]["rows"][0]["cells"]["title"]


async def test_a_related_panel_counts_what_it_did_not_show(posts):
    from warder import Detail, Panel

    admin = site(
        Resource(Author, detail=Detail(Panel.related("Posts", Post, limit=2))),
        Resource(Post),
    )
    author = await Author.first()
    props = page_of(
        await _get(client(admin), f"/admin/author/{author.pk}", headers=INERTIA)
    )["props"]
    panel = next(p for p in props["panels"] if p["kind"] == "related")
    assert len(panel["options"]["rows"]) == 2
    assert panel["options"]["total"] == 4
    assert panel["options"]["more"] is True


async def test_a_related_panel_links_to_the_filtered_list(posts):
    from warder import Detail, Panel

    admin = site(
        Resource(Author, detail=Detail(Panel.related("Posts", Post))),
        Resource(Post, list=List(Column("title"), filters=[Filter.relation("author")])),
    )
    author = await Author.first()
    props = page_of(
        await _get(client(admin), f"/admin/author/{author.pk}", headers=INERTIA)
    )["props"]
    panel = next(p for p in props["panels"] if p["kind"] == "related")
    assert panel["options"]["href"] == f"/admin/post?author={author.pk}"


async def test_a_related_panel_does_not_pretend_to_filter(posts):
    # Without a matching filter on the child list, a query string would do
    # nothing and the link would quietly show every row — which reads as a
    # broken filter rather than a link that was never going to filter.
    from warder import Detail, Panel

    admin = site(
        Resource(Author, detail=Detail(Panel.related("Posts", Post))),
        Resource(Post, list=List(Column("title"))),
    )
    author = await Author.first()
    props = page_of(
        await _get(client(admin), f"/admin/author/{author.pk}", headers=INERTIA)
    )["props"]
    panel = next(p for p in props["panels"] if p["kind"] == "related")
    assert panel["options"]["href"] == "/admin/post"


# ------------------------------------------------------- references you click


async def test_a_relation_cell_is_a_link_to_that_row(posts):
    # The author on a post goes to that author. It is the reason both screens
    # exist, and a name you cannot click is a dead end.
    admin = site(
        Resource(Post, list=List(Column("title"), Column.relation("author"))),
        Resource(Author),
    )
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    author = props["rows"][0]["cells"]["author"]
    assert author["label"] == "Ada"
    assert author["href"] == "/admin/author/1"


async def test_a_relation_to_an_unregistered_model_has_no_link(posts):
    # Nowhere to go, so nothing to click — rather than a link to a 404.
    admin = site(Resource(Post, list=List(Column("title"), Column.relation("author"))))
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert props["rows"][0]["cells"]["author"]["href"] is None
    assert props["rows"][0]["cells"]["author"]["label"] == "Ada"


async def test_a_plain_column_naming_a_relation_still_links(posts):
    # Column("author") and Column.relation("author") must not differ when the
    # model says the same thing about both.
    admin = site(
        Resource(Post, list=List(Column("title"), Column("author"))), Resource(Author)
    )
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert props["rows"][0]["cells"]["author"]["href"] == "/admin/author/1"


async def test_a_many_to_many_cell_is_a_list_of_links(posts):
    first = await Post.first()
    tag = await Tag.create(label="engineering")
    other = await Tag.create(label="design")
    await first.tags.add(tag, other)

    admin = site(
        Resource(Post, list=List(Column("title"), Column.many("tags"))), Resource(Tag)
    )
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    row = next(r for r in props["rows"] if r["id"] == first.pk)
    assert sorted(item["label"] for item in row["cells"]["tags"]) == [
        "design",
        "engineering",
    ]
    assert all(item["href"].startswith("/admin/tag/") for item in row["cells"]["tags"])


async def test_a_many_to_many_is_prefetched_not_joined(posts):
    # One post with four tags is four rows if you join it. The page count has
    # to stay right, which is what proves it was prefetched.
    first = await Post.first()
    await first.tags.add(await Tag.create(label="a"), await Tag.create(label="b"))
    admin = site(Resource(Post, list=List(Column("title"), Column.many("tags"))))
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert props["total"] == 4
    assert len(props["rows"]) == 4


async def test_an_empty_many_to_many_is_an_empty_list(posts):
    admin = site(Resource(Post, list=List(Column("title"), Column.many("tags"))))
    props = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))["props"]
    assert props["rows"][0]["cells"]["tags"] == []


async def test_the_detail_page_links_its_relations(posts):
    from warder import Detail, Panel

    first = await Post.first()
    admin = site(
        Resource(Post, detail=Detail(Panel.fields("Overview", "title", "author"))),
        Resource(Author),
    )
    props = page_of(
        await _get(client(admin), f"/admin/post/{first.pk}", headers=INERTIA)
    )["props"]
    value = props["panels"][0]["options"]["values"]["author"]
    assert value["label"] == "Ada"
    assert value["href"] == "/admin/author/1"


async def test_a_child_panel_drops_the_column_pointing_back(posts):
    # Every comment on a post's panel has the same post, and a column of one
    # repeated value only takes up room.
    from warder import Detail, Panel

    admin = site(
        Resource(Author, detail=Detail(Panel.related("Posts", Post))),
        Resource(
            Post,
            list=List(Column("title"), Column.relation("author"), Column("status")),
        ),
    )
    author = await Author.first()
    props = page_of(
        await _get(client(admin), f"/admin/author/{author.pk}", headers=INERTIA)
    )["props"]
    panel = next(p for p in props["panels"] if p["kind"] == "related")
    assert [c["key"] for c in panel["options"]["columns"]] == ["title", "status"]


# ------------------------------------------------------- editing a set of them


async def test_a_picker_resolves_labels_for_what_is_already_chosen(posts):
    # Without this an edit form opens showing raw numbers for everything
    # already selected, because the search has not returned those rows yet.
    tag = await Tag.create(label="engineering")
    admin = site(Resource(Post))
    response = await _get(client(admin), f"/admin/post/options/tags?ids={tag.pk}")
    assert response.json()["options"] == [{"id": tag.pk, "label": "engineering"}]


async def test_the_form_carries_the_current_set(posts):
    first = await Post.first()
    tag = await Tag.create(label="engineering")
    await first.tags.add(tag)

    admin = site(
        Resource(
            Post,
            form=Form(Section("", Field("title"), Field("tags"))),
        )
    )
    props = page_of(
        await _get(client(admin), f"/admin/post/{first.pk}/edit", headers=INERTIA)
    )["props"]
    assert props["values"]["tags"] == [tag.pk]


async def test_saving_replaces_the_whole_set(posts):
    first = await Post.first()
    one = await Tag.create(label="one")
    two = await Tag.create(label="two")
    await first.tags.add(one)

    admin = site(Resource(Post, form=Form(Section("", Field("title"), Field("tags")))))
    await _post(
        client(admin),
        f"/admin/post/{first.pk}",
        json={"title": first.title, "tags": [two.pk]},
    )
    assert [tag.label for tag in await first.tags.all()] == ["two"]


async def test_an_empty_set_clears_it(posts):
    first = await Post.first()
    await first.tags.add(await Tag.create(label="one"))
    admin = site(Resource(Post, form=Form(Section("", Field("title"), Field("tags")))))
    await _post(
        client(admin),
        f"/admin/post/{first.pk}",
        json={"title": first.title, "tags": []},
    )
    assert await first.tags.all() == []
