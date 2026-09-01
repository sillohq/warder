"""List, Form and Detail — the three screens, and what they derive."""

from __future__ import annotations

import pytest

from warder.actions import Action
from warder.columns import Column
from warder.fields import Field
from warder.filters import Filter
from warder.layout import Empty, Panel, Section
from warder.screens import Detail, Form, List
from warder.sorting import Sort

# --------------------------------------------------------------------- joins


def test_joins_are_derived_from_relation_columns():
    screen = List(Column.relation("author", display="email"))
    assert screen.joins == ("author",)


def test_joins_are_derived_from_traversals():
    assert List(Column("author__email")).joins == ("author",)


def test_joins_are_derived_from_filters_too():
    assert List(filters=[Filter.text("author__email")]).joins == ("author",)


def test_explicit_select_related_is_added():
    assert List(select_related=["category"]).joins == ("category",)


def test_joins_are_deduplicated_and_ordered():
    screen = List(
        Column("author__email"),
        Column.relation("author"),
        Column("team__name"),
        select_related=["author"],
    )
    assert screen.joins == ("author", "team")


def test_a_plain_list_needs_no_joins():
    assert List(Column("title")).joins == ()


def test_select_related_rejects_a_bare_string():
    # The slip that would otherwise iterate seven one-character relations.
    with pytest.raises(TypeError, match="not a single 'author'"):
        List(select_related="author")


def test_prefetch_related_rejects_a_bare_string():
    with pytest.raises(TypeError, match="not a single"):
        List(prefetch_related="tags")


# ------------------------------------------------------------------- look-ups


def test_columns_are_indexed_by_key():
    assert sorted(List(Column("a"), Column("b")).column_map) == ["a", "b"]


def test_filters_are_indexed_by_key():
    assert sorted(List(filters=[Filter.text("a")]).filter_map) == ["a"]


def test_actions_include_row_actions():
    screen = List(actions=[Action("A", None)], row_actions=[Action("B", None)])
    assert sorted(screen.action_map) == ["a", "b"]


def test_the_search_filter_is_found():
    screen = List(filters=[Filter.text("a"), Filter.search("title")])
    assert screen.search.kind == "search"


def test_a_list_without_search_reports_none():
    assert List(filters=[Filter.text("a")]).search is None


# -------------------------------------------------------------- link column


def test_the_link_column_is_the_one_marked():
    screen = List(Column("id"), Column("title", link=True))
    assert screen.link_column.key == "title"


def test_without_a_marked_column_the_first_plain_one_is_used():
    screen = List(Column.relation("author"), Column("title"))
    assert screen.link_column.key == "title"


def test_a_relation_column_is_skipped_when_choosing_a_link_column():
    screen = List(Column.relation("author"), Column("title"))
    assert screen.link_column.key == "title"


def test_a_list_of_only_relations_still_links_somewhere():
    screen = List(Column.relation("author", display="email"))
    assert screen.link_column.key == "author"


def test_an_empty_list_has_no_link_column():
    assert List().link_column is None


# -------------------------------------------------------------- other checks


def test_per_page_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        List(per_page=0)


def test_a_hard_limit_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        List(limit=0)


def test_density_is_checked():
    with pytest.raises(ValueError, match="'compact', 'normal', 'relaxed'"):
        List(density="airy")


def test_totals_are_checked():
    with pytest.raises(ValueError, match="'sum', 'avg', 'min', 'max', 'count'"):
        List(Column("a"), totals={"a": "median"})


def test_a_string_sort_is_parsed():
    assert List(sort="-created_at").sort.as_terms() == ("-created_at",)


def test_a_string_empty_state_is_wrapped():
    assert List(empty="Nothing yet").empty == Empty("Nothing yet")


def test_sorted_by_returns_a_new_list():
    base = List(Column("a"))
    assert base.sorted_by(Sort.desc("a")).sort.as_terms() == ("-a",)
    assert base.sort is None


def test_list_repr_counts_its_parts():
    screen = List(Column("a"), filters=[Filter.text("a")], actions=[Action("X", None)])
    assert repr(screen) == "List(1 columns, 1 filters, 1 actions)"


# ---------------------------------------------------------------------- Form


def test_loose_fields_group_into_an_unnamed_section():
    form = Form(Field("a"), Field("b"))
    assert len(form.sections) == 1
    assert form.sections[0].title == ""


def test_loose_fields_group_where_they_were_written():
    # Not hoisted to the top: the order on the page is the order in the call.
    form = Form(Field("a"), Section("More", Field("b")), Field("c"))
    assert [s.title for s in form.sections] == ["", "More", ""]
    assert [f.name for f in form.fields] == ["a", "b", "c"]


def test_a_form_of_only_sections_is_left_alone():
    form = Form(Section("One", Field("a")))
    assert len(form.sections) == 1


def test_sidebar_fields_are_part_of_the_form():
    form = Form(Field("a"), sidebar=[Section("Meta", Field("b"))])
    assert [f.name for f in form.fields] == ["a", "b"]


def test_fields_are_indexed_by_name():
    assert sorted(Form(Field("a"), Field("b")).field_map) == ["a", "b"]


def test_only_editable_fields_are_writable():
    form = Form(Field("a"), Field.readonly("b"))
    assert [f.name for f in form.writable] == ["a"]


def test_form_errors_collect_per_field():
    form = Form(Field("a", validate=lambda v: "Required" if not v else None))
    assert form.errors({}) == {"a": ("Required",)}


def test_a_hidden_conditional_field_is_not_validated():
    from warder.conditions import When

    form = Form(
        Field("status"),
        Field(
            "at",
            show=When("status", equals="live"),
            validate=lambda v: "Required" if not v else None,
        ),
    )
    assert form.errors({"status": "draft"}) == {}
    assert "at" in form.errors({"status": "live"})


def test_a_form_takes_only_sections_and_fields():
    with pytest.raises(TypeError, match="got str"):
        Form("nope")


def test_form_layout_is_checked():
    with pytest.raises(ValueError, match="'stacked', 'split', 'wide'"):
        Form(layout="columns")


def test_form_width_is_checked():
    with pytest.raises(ValueError, match="'narrow', 'normal', 'wide', 'full'"):
        Form(width="huge")


def test_form_repr_counts_its_parts():
    assert repr(Form(Field("a"))) == "Form(1 sections, 1 fields)"


# -------------------------------------------------------------------- Detail


def test_panels_split_by_span():
    detail = Detail(
        Panel.fields("Overview", "a"),
        Panel.custom("Meta", "acme/X", span="side"),
        Panel.custom("Wide", "acme/Y", span="full"),
    )
    assert [p.key for p in detail.main] == ["overview", "wide"]
    assert [p.key for p in detail.side] == ["meta"]


def test_panels_are_indexed_by_key():
    assert sorted(Detail(Panel.fields("Overview", "a")).panel_map) == ["overview"]


def test_a_detail_title_may_be_a_callable():
    detail = Detail(title=lambda row: row.name)
    assert callable(detail.title)


def test_detail_repr_counts_its_panels():
    assert repr(Detail(Panel.fields("A", "a"))) == "Detail(1 panels)"
