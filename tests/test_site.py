"""Admin: the registry, the navigation, and the checks that run at mount."""

from __future__ import annotations

import pytest
from fakes import Post, Tag, model

from warder.access import Role
from warder.actions import Action
from warder.columns import Column
from warder.conditions import When
from warder.errors import DeclarationError
from warder.fields import Field
from warder.filters import Filter
from warder.layout import Section
from warder.pages import Card, Dashboard, Page
from warder.resource import Resource
from warder.screens import Form, List
from warder.site import Admin
from warder.theme import Theme


def blank(ctx):
    return {}


# -------------------------------------------------------------- registration


def test_the_prefix_is_normalised():
    assert Admin(prefix="/admin/").prefix == "/admin"


def test_the_prefix_must_be_absolute():
    with pytest.raises(ValueError, match="must start with '/'"):
        Admin(prefix="admin")


def test_add_returns_the_site_so_it_chains():
    admin = Admin()
    assert admin.add(Resource(Post)) is admin


def test_resources_are_found_by_model():
    admin = Admin().add(Resource(Post))
    assert admin.resource_for(Post).model is Post
    assert admin.resource_for(Tag) is None


def test_resources_are_found_by_slug():
    admin = Admin().add(Resource(Post))
    assert admin.at("post").model is Post
    assert admin.at("nope") is None


def test_two_resources_at_one_slug_are_refused():
    admin = Admin().add(Resource(Post, slug="thing"))
    with pytest.raises(DeclarationError, match="Two resources are registered"):
        admin.add(Resource(Tag, slug="thing"))


def test_the_slug_clash_suggests_the_way_out():
    admin = Admin().add(Resource(Post, slug="thing"))
    with pytest.raises(DeclarationError, match="Give one of them slug="):
        admin.add(Resource(Tag, slug="thing"))


def test_one_model_registered_twice_is_refused():
    admin = Admin().add(Resource(Post))
    with pytest.raises(DeclarationError, match="registered twice"):
        admin.add(Resource(Post, slug="other"))


def test_two_pages_at_one_path_are_refused():
    admin = Admin().add(Page("/x", "One", blank))
    with pytest.raises(DeclarationError, match="Two pages are registered"):
        admin.add(Page("/x", "Two", blank))


def test_a_dashboard_can_be_registered():
    admin = Admin().add(Dashboard(Card.number("Revenue", blank)))
    assert len(admin.dashboard.cards) == 1


def test_a_loose_card_starts_a_dashboard():
    admin = Admin().add(Card.number("Revenue", blank))
    assert len(admin.dashboard.cards) == 1


def test_loose_cards_accumulate():
    admin = Admin().add(Card.number("A", blank), Card.number("B", blank))
    assert len(admin.dashboard.cards) == 2


def test_anything_else_is_refused():
    with pytest.raises(TypeError, match="got Column"):
        Admin().add(Column("title"))


def test_roles_are_added_to_auth():
    admin = Admin().roles(Role("support"))
    assert "support" in admin.auth.role_map


def test_roles_accumulate():
    admin = Admin().roles(Role("a")).roles(Role("b"))
    assert sorted(admin.auth.role_map) == ["a", "b"]


def test_slots_are_recorded():
    admin = Admin().slot("list.toolbar", "acme/Export")
    assert admin.slots == {"list.toolbar": "acme/Export"}


# --------------------------------------------------------------- permissions


def test_permissions_are_derived_from_what_is_registered():
    admin = Admin().add(Resource(Post), Resource(Tag))
    assert "post.view" in admin.permissions
    assert "tag.delete" in admin.permissions


def test_the_site_declares_its_own_access_permission():
    assert "warder.access" in Admin().permissions


def test_the_access_permission_follows_the_site_name():
    assert "ops.access" in Admin(name="ops").permissions


# ---------------------------------------------------------------- navigation


def test_navigation_groups_by_group():
    admin = Admin(groups=["Content", "Reference"])
    admin.add(Resource(Post, group="Content"), Resource(Tag, group="Reference"))
    assert [g["label"] for g in admin.navigation()] == ["Content", "Reference"]


def test_declared_group_order_wins_over_the_alphabet():
    admin = Admin(groups=["Zebra", "Apple"])
    admin.add(Resource(Post, group="Zebra"), Resource(Tag, group="Apple"))
    assert [g["label"] for g in admin.navigation()] == ["Zebra", "Apple"]


def test_undeclared_groups_follow_alphabetically():
    admin = Admin(groups=["First"])
    admin.add(
        Resource(model("A"), group="First"),
        Resource(model("B"), group="Zebra"),
        Resource(model("C"), group="Apple"),
    )
    assert [g["label"] for g in admin.navigation()] == ["First", "Apple", "Zebra"]


def test_navigation_uses_the_plural_for_a_resource():
    admin = Admin().add(Resource(Post))
    assert admin.navigation()[0]["items"][0]["label"] == "Posts"


def test_navigation_uses_the_title_for_a_page():
    admin = Admin().add(Page("/x", "Reconciliation", blank))
    assert admin.navigation()[0]["items"][0]["label"] == "Reconciliation"


def test_navigation_links_to_the_prefixed_route():
    admin = Admin(prefix="/ops").add(Resource(Post))
    assert admin.navigation()[0]["items"][0]["href"] == "/ops/post"


def test_weight_orders_within_a_group():
    admin = Admin()
    admin.add(Resource(model("B"), weight=1), Resource(model("A"), weight=0))
    assert [i["key"] for i in admin.navigation()[0]["items"]] == ["a", "b"]


def test_hidden_resources_are_left_out():
    admin = Admin().add(Resource(Post, hidden=True), Resource(Tag))
    assert [i["key"] for i in admin.navigation()[0]["items"]] == ["tag"]


def test_navigation_can_be_filtered_by_what_a_user_may_see():
    # A resource nobody may view is absent, not disabled.
    admin = Admin().add(Resource(Post), Resource(Tag))
    visible = admin.navigation({"post": True, "tag": False})
    assert [i["key"] for i in visible[0]["items"]] == ["post"]


# ---------------------------------------------------------------- validation


def test_a_clean_site_has_nothing_to_report():
    admin = Admin().add(Resource(Post, list=List(Column("title"))))
    assert admin.check() == []


def test_a_role_inheriting_a_missing_role_is_reported():
    admin = Admin().roles(Role("a", inherits=["ghost"]))
    assert "inherits 'ghost'" in str(admin.check()[0])


def test_a_role_granting_an_undeclared_permission_is_reported():
    admin = Admin().add(Resource(Post)).roles(Role("a", grants=["ghost.view"]))
    assert "no registered resource declares" in str(admin.check()[0])


def test_a_near_miss_is_suggested():
    admin = Admin().add(Resource(Post)).roles(Role("a", grants=["post.veiw"]))
    assert "Did you mean 'post.view'?" in str(admin.check()[0])


def test_a_wildcard_role_grants_everything_and_is_not_checked():
    admin = Admin().add(Resource(Post)).roles(Role("owner", grants="*"))
    assert admin.check() == []


def test_duplicate_column_keys_are_reported():
    admin = Admin().add(Resource(Post, list=List(Column("a"), Column("a"))))
    assert "two columns keyed 'a'" in str(admin.check()[0])


def test_duplicate_filter_keys_are_reported():
    admin = Admin().add(
        Resource(Post, list=List(filters=[Filter.text("a"), Filter.choice("a")]))
    )
    assert "share a query parameter" in str(admin.check()[0])


def test_totals_over_a_missing_column_are_reported():
    admin = Admin().add(Resource(Post, list=List(Column("a"), totals={"b": "sum"})))
    assert "totals 'b'" in str(admin.check()[0])


def test_duplicate_action_names_are_reported():
    admin = Admin().add(
        Resource(
            Post, list=List(actions=[Action("Publish", None), Action("Publish", None)])
        )
    )
    assert "two actions named 'publish'" in str(admin.check()[0])


def test_row_and_toolbar_actions_share_a_namespace():
    admin = Admin().add(
        Resource(
            Post,
            list=List(
                actions=[Action("Publish", None)], row_actions=[Action("Publish", None)]
            ),
        )
    )
    assert "two actions named" in str(admin.check()[0])


def test_duplicate_form_fields_are_reported():
    admin = Admin().add(Resource(Post, form=Form(Field("a"), Field("a"))))
    assert "two fields named 'a'" in str(admin.check()[0])


def test_a_condition_on_a_field_that_is_not_on_the_form_is_reported():
    admin = Admin().add(
        Resource(Post, form=Form(Field("a", show=When("ghost", equals=1))))
    )
    assert "not on this form" in str(admin.check()[0])


def test_a_condition_on_a_field_that_is_on_the_form_is_fine():
    admin = Admin().add(
        Resource(
            Post,
            form=Form(Field("status"), Field("at", show=When("status", equals="live"))),
        )
    )
    assert admin.check() == []


def test_a_resource_without_a_list_has_nothing_to_check():
    assert Admin().add(Resource(Post)).check() == []


def test_problems_carry_the_line_they_were_written_on():
    admin = Admin().add(Resource(Post, list=List(Column("a"), Column("a"))))
    assert "Declared at" in str(admin.check()[0])


def test_mount_raises_on_the_first_problem():
    admin = Admin().add(Resource(Post, list=List(Column("a"), Column("a"))))
    with pytest.raises(DeclarationError, match="two columns keyed"):
        admin.mount(object())


# ---------------------------------------------------------------------- misc


def test_a_theme_can_be_given():
    assert Admin(theme=Theme.paper()).theme.style == "paper"


def test_the_default_theme_is_console():
    assert Admin().theme.style == "console"


def test_the_brand_falls_back_to_the_title():
    assert Admin(title="Acme Ops").brand == "Acme Ops"


def test_repr_counts_what_is_registered():
    admin = Admin(title="Ops").add(Resource(Post), Page("/x", "X", blank))
    assert repr(admin) == "Admin('Ops', prefix='/admin', 1 resources, 1 pages)"


def test_a_form_section_holding_no_fields_is_not_a_problem():
    assert Admin().add(Resource(Post, form=Form(Section("Empty")))).check() == []
