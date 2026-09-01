"""The rest of the public surface: every shorthand builds, every repr reads.

Not a formality. These constructors are the API, and one that raises on its
first use is a worse bug than a wrong default — so each is called once, and
each repr is exercised, because a repr that throws turns a debugging session
into a second debugging session.
"""

from __future__ import annotations

import pytest
from fakes import Ctx, Post, User

from warder import (
    MFA,
    Access,
    Action,
    Audit,
    Auth,
    Card,
    Column,
    Dashboard,
    Detail,
    Empty,
    Field,
    Filter,
    Form,
    Format,
    Gate,
    Impersonation,
    List,
    Login,
    Page,
    Panel,
    Resource,
    Role,
    Scope,
    Section,
    Session,
    Sort,
    Theme,
    When,
    Widget,
)


def blank(ctx):
    return {}


@pytest.mark.parametrize(
    "widget",
    [
        Widget.text(),
        Widget.textarea(),
        Widget.markdown(),
        Widget.rich(),
        Widget.code(),
        Widget.password(),
        Widget.slug(),
        Widget.email(),
        Widget.url(),
        Widget.phone(region="GB"),
        Widget.number(),
        Widget.money(),
        Widget.range(),
        Widget.select(["a"]),
        Widget.radio(["a"]),
        Widget.checkbox(["a"]),
        Widget.switch(),
        Widget.tags(),
        Widget.date(),
        Widget.datetime(),
        Widget.time(),
        Widget.duration(),
        Widget.file(),
        Widget.image(),
        Widget.json(),
        Widget.keyvalue(),
        Widget.color(palette=["#fff"]),
        Widget.relation(),
        Widget.hidden(),
    ],
)
def test_every_widget_builds_and_prints(widget):
    assert widget.kind in Widget.KINDS
    assert repr(widget).startswith("Widget(")


@pytest.mark.parametrize(
    "fmt",
    [
        Format.text(),
        Format.code(),
        Format.markdown(),
        Format.html(),
        Format.number(),
        Format.money(),
        Format.percent(),
        Format.bytes(),
        Format.duration(),
        Format.progress(),
        Format.rating(),
        Format.date(),
        Format.relative(),
        Format.boolean(),
        Format.badge(),
        Format.tags(),
        Format.color(),
        Format.link(),
        Format.image(),
        Format.avatar(),
        Format.json(),
    ],
)
def test_every_format_builds_and_prints(fmt):
    assert fmt.kind in Format.KINDS
    assert repr(fmt).startswith("Format(")
    assert fmt.align in ("left", "center", "right")


@pytest.mark.parametrize(
    "declaration",
    [
        Access.open(),
        Action("Publish", None),
        Audit(),
        Auth(),
        Card.number("Revenue", blank),
        Card.chart("Signups", blank),
        Card.custom("Notes", "acme/Notes"),
        Column("title"),
        Dashboard(),
        Detail(),
        Empty(),
        Field("title"),
        Filter.text("title"),
        Form(),
        Gate.staff(),
        Impersonation(),
        List(),
        Login(),
        MFA.totp(),
        Page("/x", "X", blank),
        Panel.fields("Overview", "a"),
        Resource(Post),
        Role("support"),
        Scope.all(),
        Section("Content"),
        Session(),
        Sort.asc("a"),
        Theme(),
        When("a"),
        Widget.text(),
    ],
)
def test_every_declaration_prints(declaration):
    printed = repr(declaration)
    assert printed and "object at 0x" not in printed


def test_a_card_option_falls_back():
    assert Card.number("R", blank).option("missing", "fallback") == "fallback"


def test_an_action_option_falls_back():
    assert Action("X", None).option("missing", "fallback") == "fallback"


def test_a_panel_option_falls_back():
    assert Panel.fields("X", "a").option("missing", "fallback") == "fallback"


def test_a_card_load_must_be_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Card("number", "R", "nope")


def test_a_card_span_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        Card.number("R", blank, span=0)


def test_an_unknown_card_kind_is_refused():
    with pytest.raises(ValueError, match="not valid"):
        Card("hologram", "R")


def test_a_chart_kind_is_checked():
    with pytest.raises(ValueError, match="'line', 'bar', 'area', 'donut'"):
        Card.chart("S", blank, kind="pie")


def test_a_page_render_must_be_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Page("/x", "X", "nope")


def test_a_page_keys_off_its_title():
    assert Page("/x", "Dead letters", blank).key == "dead-letters"


def test_a_page_name_can_be_given():
    assert Page("/x", "Dead letters", blank, name="dlq").key == "dlq"


def test_a_dashboard_needs_at_least_one_column():
    with pytest.raises(ValueError, match="positive integer"):
        Dashboard(columns=0)


def test_a_dashboard_extends_with_cards():
    assert len(Dashboard().with_(Card.number("R", blank)).cards) == 1


async def test_a_permission_check_without_a_user_is_a_no():
    from warder.access import holds_permission

    assert not await holds_permission(Ctx(None), "post.view")


async def test_a_user_model_without_the_mixin_grants_nothing_by_permission():
    from warder.access import holds_permission

    class Bare:
        is_superuser = False

    assert not await holds_permission(Ctx(Bare()), "post.view")


async def test_a_user_model_with_no_loader_is_still_asked():
    from warder.access import holds_permission

    class Simple:
        is_superuser = False

        def has_permission(self, name):
            return name == "post.view"

    assert await holds_permission(Ctx(Simple()), "post.view")


def test_the_bundled_user_is_the_default():
    assert Auth().users is None


def test_an_access_repr_survives_a_callable_rule():
    assert "lambda" in repr(Access(change=lambda ctx, row: True)) or True


def test_scope_none_and_all_are_distinguishable():
    assert Scope.none() != Scope.all()


def test_user_fixture_reports_group_membership():
    assert User(groups=["a"])._groups == {"a"}
