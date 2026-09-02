"""The interface, end to end.

A real application, a real database and a real HTTP client. The declaration
layer is tested without any of those on purpose; this is the half where that
would be testing the fake.

Two shapes are checked for every screen, because Inertia has two: a fresh tab
gets a document with the page object embedded, and the client-side router gets
the same props as JSON. If those ever disagree, refreshing the page changes what
you see.
"""

from __future__ import annotations

import json as jsonlib

import httpx
import pytest
from orm import Author, Post, Tag
from sillo import SilloApp
from tortoise import Tortoise

from warder import (
    Admin,
    Column,
    Field,
    Filter,
    Form,
    Gate,
    List,
    Resource,
    Section,
    Sort,
)
from warder.auth import Auth

#: What the client-side router sends. No version header: the server then
#: compares its own version against itself and never asks for a reload,
#: which is the behaviour a fresh client gets too.
INERTIA = {"X-Inertia": "true"}


@pytest.fixture
async def database():
    """A real database, on the test's own event loop.

    The application is driven through an ASGI transport on *this* loop rather
    than through a threaded client, and that matters twice over. Tortoise
    reconnects when it sees a different loop, and a reconnect to `:memory:`
    opens a new, empty database — every query then fails with "no such table",
    which looks like a bug in the admin and is a property of SQLite. And
    `aiosqlite` starts a worker thread that is *not* a daemon, so a connection
    opened on a loop nobody closes keeps the process alive after the last test
    has passed.
    """
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["orm"]})
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


@pytest.fixture
async def seeded(database):
    author = await Author.create(name="Ada Lovelace", email="ada@example.com")
    other = await Author.create(name="Alan Turing", email="alan@example.com")
    await Tag.create(label="engineering")
    for index in range(3):
        await Post.create(
            title=f"Post {index}",
            slug=f"post-{index}",
            body="Something to read." * 4,
            status="live" if index else "draft",
            words=index * 10,
            secret="hunter2",
            author=author if index else other,
        )
    return author


def build(**options) -> Admin:
    """An admin with the gate open, which is what a test wants to exercise."""
    admin = Admin(
        title="Acme Ops",
        prefix="/admin",
        auth=Auth(gate=Gate.custom(lambda ctx: True)),
        **options,
    )
    admin.add(
        Resource(
            Post,
            group="Content",
            list=List(
                Column("title", link=True),
                Column.relation("author", display="email"),
                Column.badge("status", colors={"live": "green", "draft": "zinc"}),
                Column.compute("Length", lambda row: len(row.title)),
                filters=[
                    Filter.search("title", "body"),
                    Filter.choice("status", ["draft", "live"]),
                ],
                sort=Sort.desc("id"),
                per_page=2,
            ),
            form=Form(
                Section(
                    "Content",
                    Field("title"),
                    Field("slug"),
                    Field("body"),
                    Field.password("secret"),
                )
            ),
        )
    )
    admin.add(Resource(Author), Resource(Tag))
    return admin


def client(admin: Admin) -> httpx.AsyncClient:
    """An HTTP client that drives the application in this event loop."""
    app = SilloApp()
    admin.mount(app)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://admin.test"
    )


async def _get(web: httpx.AsyncClient, url: str, **options) -> httpx.Response:
    async with web:
        return await web.get(url, **options)


async def _post(web: httpx.AsyncClient, url: str, **options) -> httpx.Response:
    async with web:
        return await web.post(url, **options)


async def _delete(web: httpx.AsyncClient, url: str, **options) -> httpx.Response:
    async with web:
        return await web.delete(url, **options)


def page_of(response) -> dict:
    """The Inertia page object, from JSON or from the embedded document."""
    if response.headers.get("content-type", "").startswith("application/json"):
        return jsonlib.loads(response.text)
    body = response.text
    start = body.index('data-page="') + len('data-page="')
    end = body.index('"', start)
    return jsonlib.loads(body[start:end].replace("&quot;", '"'))


# ------------------------------------------------------------------ the shell


async def test_a_fresh_tab_gets_a_document(seeded):
    response = await _get(client(build()), "/admin/post")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<!doctype html>" in response.text.lower()


async def test_the_document_embeds_the_page_object(seeded):
    page = page_of(await _get(client(build()), "/admin/post"))
    assert page["component"] == "List"


async def test_the_router_gets_json(seeded):
    response = await _get(client(build()), "/admin/post", headers=INERTIA)
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["x-inertia"] == "true"


async def test_both_shapes_carry_the_same_props(seeded):
    admin = build()
    document = page_of(await _get(client(admin), "/admin/post"))
    router = page_of(await _get(client(admin), "/admin/post", headers=INERTIA))
    assert document["props"]["columns"] == router["props"]["columns"]
    assert len(document["props"]["rows"]) == len(router["props"]["rows"])


async def test_the_document_loads_the_built_bundle(seeded):
    body = (await _get(client(build()), "/admin/post")).text
    assert "/admin/assets/warder." in body
    assert 'id="app"' in body


async def test_the_theme_is_written_into_the_document(seeded):
    body = (await _get(client(build()), "/admin/post")).text
    assert "--wd-accent" in body
    assert "prefers-color-scheme: dark" in body


async def test_the_navigation_is_grouped(seeded):
    page = page_of(await _get(client(build()), "/admin/post", headers=INERTIA))
    groups = {group["label"] for group in page["props"]["nav"]}
    assert "Content" in groups


# ------------------------------------------------------------------ the list


async def test_the_list_carries_its_rows(seeded):
    props = page_of(await _get(client(build()), "/admin/post", headers=INERTIA))[
        "props"
    ]
    assert len(props["rows"]) == 2  # per_page=2
    assert props["total"] == 3
    assert props["pages"] == 2


async def test_a_computed_column_is_evaluated(seeded):
    props = page_of(await _get(client(build()), "/admin/post", headers=INERTIA))[
        "props"
    ]
    assert props["rows"][0]["cells"]["length"] == len("Post 2")


async def test_a_relation_column_carries_the_display_value(seeded):
    props = page_of(await _get(client(build()), "/admin/post", headers=INERTIA))[
        "props"
    ]
    assert props["rows"][0]["cells"]["author"]["label"] == "ada@example.com"


async def test_a_password_column_is_never_sent(seeded):
    props = page_of(await _get(client(build()), "/admin/post", headers=INERTIA))[
        "props"
    ]
    assert "secret" not in props["rows"][0]["cells"]
    assert "hunter2" not in jsonlib.dumps(props)


async def test_paging_moves(seeded):
    props = page_of(await _get(client(build()), "/admin/post?page=2", headers=INERTIA))[
        "props"
    ]
    assert len(props["rows"]) == 1


async def test_a_filter_narrows(seeded):
    props = page_of(
        await _get(client(build()), "/admin/post?status=draft", headers=INERTIA)
    )["props"]
    assert props["total"] == 1


async def test_search_narrows(seeded):
    props = page_of(
        await _get(client(build()), "/admin/post?q=Post+1", headers=INERTIA)
    )["props"]
    assert props["total"] == 1


async def test_sorting_is_applied(seeded):
    props = page_of(
        await _get(client(build()), "/admin/post?sort=title", headers=INERTIA)
    )["props"]
    titles = [row["cells"]["title"] for row in props["rows"]]
    assert titles == sorted(titles)


async def test_an_unsortable_column_in_the_url_is_ignored(seeded):
    # A stale bookmark should show the list, not an error page.
    response = await _get(client(build()), "/admin/post?sort=nonsense", headers=INERTIA)
    assert response.status_code == 200


async def test_per_page_is_capped(seeded):
    props = page_of(
        await _get(client(build()), "/admin/post?per_page=999999", headers=INERTIA)
    )["props"]
    assert props["query"]["perPage"] <= 500


# ------------------------------------------------------------ detail and form


async def test_the_detail_page_renders(seeded):
    first = await Post.first()
    page = page_of(
        await _get(client(build()), f"/admin/post/{first.pk}", headers=INERTIA)
    )
    assert page["component"] == "Detail"
    assert page["props"]["title"] == str(first)


async def test_a_missing_row_is_a_404(seeded):
    assert (await _get(client(build()), "/admin/post/9999")).status_code == 404


async def test_the_add_form_renders(seeded):
    page = page_of(await _get(client(build()), "/admin/post/new", headers=INERTIA))
    assert page["component"] == "Form"
    assert page["props"]["mode"] == "add"


async def test_the_edit_form_is_populated(seeded):
    first = await Post.first()
    props = page_of(
        await _get(client(build()), f"/admin/post/{first.pk}/edit", headers=INERTIA)
    )["props"]
    assert props["mode"] == "change"
    assert props["values"]["title"] == first.title


async def test_a_derived_form_never_returns_a_password(seeded):
    admin = Admin(title="Ops", auth=Auth(gate=Gate.custom(lambda ctx: True)))
    admin.add(Resource(Post))
    first = await Post.first()
    props = page_of(
        await _get(client(admin), f"/admin/post/{first.pk}/edit", headers=INERTIA)
    )["props"]
    assert props["values"]["secret"] is None


async def test_creating_a_row_redirects_to_it(seeded):
    response = await _post(
        client(build()),
        "/admin/post",
        json={"title": "Fresh", "slug": "fresh", "body": "New", "secret": "s3cret"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert await Post.filter(title="Fresh").exists()


async def test_updating_a_row_saves(seeded):
    first = await Post.first()
    await _post(
        client(build()),
        f"/admin/post/{first.pk}",
        json={"title": "Renamed", "slug": first.slug, "body": first.body},
        follow_redirects=False,
    )
    await first.refresh_from_db()
    assert first.title == "Renamed"


async def test_deleting_a_row_removes_it(seeded):
    first = await Post.first()
    response = await _delete(
        client(build()), f"/admin/post/{first.pk}", follow_redirects=False
    )
    # A mutation must redirect with 303, or the browser repeats the DELETE.
    assert response.status_code == 303
    assert not await Post.filter(pk=first.pk).exists()


async def test_a_field_not_on_the_form_is_not_written(seeded):
    # The browser decides what to draw; the server decides what to save.
    first = await Post.first()
    await _post(
        client(build()),
        f"/admin/post/{first.pk}",
        json={
            "title": first.title,
            "slug": first.slug,
            "body": first.body,
            "words": 9999,
        },
        follow_redirects=False,
    )
    await first.refresh_from_db()
    assert first.words != 9999


# ---------------------------------------------------------------- the pickers


async def test_a_relation_picker_searches(seeded):
    response = await _get(client(build()), "/admin/post/options/author?q=ada")
    body = response.json()
    assert [option["label"] for option in body["options"]] == ["Ada Lovelace"]


async def test_a_picker_over_a_plain_column_is_a_404(seeded):
    assert (await _get(client(build()), "/admin/post/options/title")).status_code == 404


# ------------------------------------------------------------------- the gate


async def test_an_anonymous_visitor_is_sent_to_the_login_page(seeded):
    admin = Admin(title="Ops", auth=Auth(gate=Gate.never()))
    admin.add(Resource(Post))
    response = await _get(client(admin), "/admin/post", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].endswith("/admin/login")


async def test_the_router_is_told_to_reload_rather_than_redirected(seeded):
    # The client-side router follows redirects itself and would try to render
    # a login page as a page object.
    admin = Admin(title="Ops", auth=Auth(gate=Gate.never()))
    admin.add(Resource(Post))
    response = await _get(
        client(admin), "/admin/post", headers=INERTIA, follow_redirects=False
    )
    assert response.status_code == 409
    assert response.headers["x-inertia-location"].endswith("/admin/login")


async def test_the_login_page_renders(seeded):
    admin = Admin(title="Ops", auth=Auth(gate=Gate.never()))
    admin.add(Resource(Post))
    page = page_of(await _get(client(admin), "/admin/login", headers=INERTIA))
    assert page["component"] == "Login"


# -------------------------------------------------------------- the dashboard


async def test_the_dashboard_renders(seeded):
    page = page_of(await _get(client(build()), "/admin", headers=INERTIA))
    assert page["component"] == "Dashboard"


async def test_a_stale_asset_version_asks_for_a_reload(seeded):
    response = await _get(
        client(build()),
        "/admin/post",
        headers={"X-Inertia": "true", "X-Inertia-Version": "ancient"},
        follow_redirects=False,
    )
    assert response.status_code == 409
    assert "x-inertia-location" in response.headers


async def test_a_partial_reload_sends_only_what_was_asked_for(seeded):
    props = page_of(
        await _get(
            client(build()),
            "/admin/post",
            headers={
                **INERTIA,
                "X-Inertia-Partial-Component": "List",
                "X-Inertia-Partial-Data": "rows,total",
            },
        )
    )["props"]
    assert set(props) == {"rows", "total"}


# ----------------------------------------------------------------- the bundle


async def test_the_stylesheet_is_served(seeded):
    from warder.assets import Assets

    entry = Assets().entry()
    response = await _get(client(build()), f"/admin/assets/{entry['css'][0]}")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


async def test_the_script_is_served(seeded):
    from warder.assets import Assets

    entry = Assets().entry()
    response = await _get(client(build()), f"/admin/assets/{entry['file']}")
    assert response.status_code == 200
    assert response.text.startswith(("import", "var", "const", "function", "(", "!"))


async def test_the_bundle_is_cached_forever(seeded):
    # Content-hashed filenames, so the answer to "may I cache this" is yes.
    from warder.assets import Assets

    response = await _get(client(build()), f"/admin/assets/{Assets().entry()['file']}")
    assert "immutable" in response.headers.get("cache-control", "")


async def test_the_admin_is_not_indexed(seeded):
    body = (await _get(client(build()), "/admin/post")).text
    assert 'name="robots" content="noindex,nofollow"' in body


async def test_the_document_names_no_external_host(seeded):
    # Air-gapped networks and strict CSPs are the normal conditions for the
    # people who most want an admin panel.
    body = (await _get(client(build()), "/admin/post")).text
    assert "http://" not in body.replace("http://admin.test", "")
    assert "cdn" not in body.lower()


async def test_a_second_admin_can_be_mounted_at_another_prefix(seeded):
    admin = Admin(
        title="Internal",
        prefix="/internal/ops",
        auth=Auth(gate=Gate.custom(lambda c: True)),
    )
    admin.add(Resource(Tag))
    response = await _get(client(admin), "/internal/ops/tag")
    assert response.status_code == 200
    assert "/internal/ops/assets/warder." in response.text
