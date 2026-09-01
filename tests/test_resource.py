"""Resource: one model's surface, and the four permissions it declares."""

from __future__ import annotations

import pytest
from fakes import Ctx, Post, Rows, User, model

from warder.access import Access, Scope
from warder.resource import Resource, crud
from warder.screens import List
from warder.sorting import Sort


def test_a_resource_takes_a_class_not_an_instance():
    with pytest.raises(TypeError, match=r"Resource\(Post\), not Resource\(Post\(\)\)"):
        Resource(Post())


def test_labels_are_derived_from_the_model_name():
    resource = Resource(model("BlogPost"))
    assert resource.label == "Blog post"
    assert resource.plural == "Blog posts"


def test_labels_can_be_given():
    resource = Resource(Post, label="Article", plural="Articles")
    assert (resource.label, resource.plural) == ("Article", "Articles")


def test_a_plural_is_derived_from_a_given_label():
    assert Resource(Post, label="Entry").plural == "Entries"


def test_the_slug_is_derived_from_the_model_name():
    assert Resource(model("BlogPost")).slug == "blog-post"


def test_the_slug_can_be_given():
    assert Resource(Post, slug="articles").slug == "articles"


def test_the_route_hangs_off_the_prefix():
    assert Resource(Post).route("/admin") == "/admin/post"


def test_a_resource_declares_four_permissions():
    assert Resource(Post).permissions == (
        "post.view",
        "post.add",
        "post.change",
        "post.delete",
    )


def test_the_permission_stem_can_be_given():
    assert Resource(Post, stem="article").permissions[0] == "article.view"


def test_search_fields_are_checked():
    with pytest.raises(ValueError, match="non-empty field name"):
        Resource(Post, search=[""])


def test_search_rejects_a_bare_string():
    with pytest.raises(TypeError, match="not a single"):
        Resource(Post, search="title")


def test_a_string_sort_is_parsed():
    assert Resource(Post, sort="-created_at").sort.as_terms() == ("-created_at",)


def test_flags_close_actions_regardless_of_permissions():
    # A row created by a job and never by hand: a statement about the model,
    # which Access alone cannot make.
    rules = Resource(Post, creatable=False, access=Access(add="post.add")).rules()
    assert rules.rule("add") is False


def test_flags_leave_the_declared_rules_alone_otherwise():
    rules = Resource(Post, access=Access(add="post.add")).rules()
    assert rules.rule("add") == "post.add"


def test_an_undeclared_rule_stays_undecided():
    assert Resource(Post).rules().rule("view") is None


async def test_allows_delegates_to_the_rules():
    resource = Resource(Post, access=Access(view="post.view"))
    assert await resource.allows(Ctx(User(permissions=["post.view"])), "view")
    assert not await resource.allows(Ctx(User()), "view")


async def test_rows_applies_the_queryset_then_the_scope():
    resource = Resource(
        Post,
        queryset=lambda ctx, rows: rows.filter(archived=False),
        scope=Scope.tenant("team_id"),
    )
    narrowed = await resource.rows(Ctx(User(team_id=3)), Rows())
    assert narrowed.filters == [{"archived": False}, {"team_id": 3}]


async def test_rows_accepts_an_async_queryset():
    async def narrow(ctx, rows):
        return rows.filter(a=1)

    narrowed = await Resource(Post, queryset=narrow).rows(Ctx(User()), Rows())
    assert narrowed.filters == [{"a": 1}]


async def test_rows_with_neither_leaves_the_queryset_alone():
    base = Rows()
    assert await Resource(Post).rows(Ctx(User()), base) is base


def test_a_bare_resource_leaves_its_screens_to_be_derived():
    resource = Resource(Post)
    assert resource.list is None
    assert resource.form is None
    assert resource.detail is None


def test_resources_extend_without_mutating():
    base = Resource(Post, group="Content")
    assert base.with_(group="Blog").group == "Blog"
    assert base.group == "Content"


def test_repr_names_the_model():
    assert repr(Resource(Post)) == "Resource(Post)"


# ---------------------------------------------------------------------- crud


def test_crud_builds_a_list_and_a_form():
    resource = crud(model("Tag"), "name", "slug")
    assert [c.key for c in resource.list.columns] == ["name", "slug"]
    assert [f.name for f in resource.form.fields] == ["name", "slug"]


def test_crud_links_the_first_column():
    resource = crud(model("Tag"), "name", "slug")
    assert resource.list.link_column.key == "name"


def test_crud_sorts_on_the_first_field():
    assert crud(model("Tag"), "name").list.sort.as_terms() == ("name",)


def test_crud_passes_options_through():
    resource = crud(model("Tag"), "name", group="Reference", access=Access.readonly())
    assert resource.group == "Reference"
    assert resource.rules().rule("change") is False


def test_crud_needs_a_field():
    with pytest.raises(TypeError, match="at least one field"):
        crud(model("Tag"))


def test_crud_returns_an_ordinary_resource_you_can_extend():
    resource = crud(model("Tag"), "name")
    assert isinstance(resource.with_(icon="tag").list, List)
    assert isinstance(crud(model("Tag"), "name").list.sort, Sort)
