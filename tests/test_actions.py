"""Action: what a person can do to rows, and what comes back."""

from __future__ import annotations

import pytest
from fakes import Ctx, User

from warder.access import Access, Gate
from warder.actions import Action
from warder.fields import Field
from warder.results import (
    download,
    go,
    modal,
    nothing,
    notice,
    problem,
    refresh,
    warning,
)


def test_an_action_keys_off_its_label():
    assert Action("Publish now", lambda ctx, rows: None).key == "publish-now"


def test_an_explicit_name_wins():
    assert Action("Publish", lambda c, r: None, name="go_live").key == "go_live"


def test_a_handler_must_be_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Action("Publish", "nope")


def test_the_style_is_checked():
    with pytest.raises(ValueError, match="'default', 'primary', 'danger'"):
        Action("X", None, style="loud")


def test_the_selection_mode_is_checked():
    with pytest.raises(ValueError, match="'many', 'one', 'none'"):
        Action("X", None, selection="some")


def test_the_placement_is_checked():
    with pytest.raises(ValueError, match="'toolbar', 'row', 'both'"):
        Action("X", None, place="footer")


def test_an_action_with_no_handler_is_built_in():
    assert Action.delete().builtin
    assert not Action("Publish", lambda c, r: None).builtin


def test_delete_is_dangerous_and_confirms():
    delete = Action.delete()
    assert delete.destructive
    assert "cannot be undone" in delete.prompt(2)


def test_a_confirmation_counts_the_rows():
    assert Action("X", None, confirm="Do {count}?").prompt(4) == "Do 4?"


def test_n_is_accepted_as_well_as_count():
    assert Action("X", None, confirm="Do {n}?").prompt(4) == "Do 4?"


def test_an_unknown_placeholder_is_left_alone():
    # An admin should not fail to render over a brace.
    assert Action("X", None, confirm="Do {bogus}?").prompt(1) == "Do {bogus}?"


def test_no_confirmation_means_none():
    assert Action("X", None).prompt(1) is None


def test_export_acts_on_the_filtered_set_rather_than_a_selection():
    export = Action.export()
    assert not export.needs_selection
    assert export.option("format") == "csv"


def test_export_carries_its_columns():
    assert Action.export(columns=["id", "total"]).option("columns") == ("id", "total")


def test_an_action_with_fields_collects_first():
    action = Action("Assign", lambda c, r, v: None, fields=[Field("assignee")])
    assert action.collects


def test_an_action_without_fields_does_not():
    assert not Action("Publish", lambda c, r: None).collects


def test_a_link_action_defaults_to_one_row_in_the_row_menu():
    link = Action.link("Open", to=lambda row: "/x")
    assert link.selection == "one"
    assert link.place == "row"


def test_a_link_action_needs_a_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Action.link("Open", to="/x")


async def test_an_action_with_no_rules_is_allowed():
    assert await Action("X", None).allowed(Ctx(User()))


async def test_an_action_gate_is_consulted():
    action = Action("X", None, gate=Gate.superuser())
    assert not await action.allowed(Ctx(User(is_staff=True)))
    assert await action.allowed(Ctx(User(is_superuser=True)))


async def test_an_action_access_rule_is_consulted():
    action = Action("X", None, access=Access(change="post.publish"))
    assert not await action.allowed(Ctx(User()))
    assert await action.allowed(Ctx(User(permissions=["post.publish"])))


def test_repr_shows_a_renamed_action():
    assert "name='go_live'" in repr(Action("Publish", None, name="go_live"))


def test_repr_counts_collected_fields():
    assert "fields=1" in repr(Action("X", None, fields=[Field("a")]))


# ----------------------------------------------------------------- outcomes


def test_outcome_tones():
    assert notice("x").tone == "success"
    assert warning("x").tone == "warning"
    assert problem("x").tone == "danger"
    assert refresh().tone == "neutral"


def test_go_carries_a_url():
    assert go("/reports/1").option("url") == "/reports/1"


def test_nothing_says_nothing():
    assert nothing().kind == "nothing"


def test_download_takes_content():
    result = download(b"a,b", filename="x.csv", content_type="text/csv")
    assert result.option("filename") == "x.csv"
    assert result.option("content") == b"a,b"


def test_download_takes_a_url_instead():
    assert (
        download(url="/files/x.csv", filename="x.csv").option("url") == "/files/x.csv"
    )


def test_download_needs_one_or_the_other():
    with pytest.raises(TypeError, match="needs content= or url="):
        download(filename="x.csv")


def test_modal_carries_its_component_and_props():
    result = modal("acme/Diff", props={"a": 1}, title="Review")
    assert result.option("component") == "acme/Diff"
    assert result.option("props") == {"a": 1}
    assert result.message == "Review"


def test_an_unknown_outcome_kind_is_refused():
    from warder.results import Outcome

    with pytest.raises(ValueError, match="not one of"):
        Outcome("explode")


def test_outcome_repr():
    assert repr(notice("Done")) == "notice('Done')"
    assert repr(refresh()) == "refresh()"
