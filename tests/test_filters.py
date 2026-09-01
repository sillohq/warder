"""Filter: one control, one query parameter, one queryset transformation."""

from __future__ import annotations

import datetime as dt

import pytest
from fakes import Rows

from warder.filters import PRESETS, Filter, preset_range

NOW = dt.datetime(2026, 9, 1, 12, 0)


def test_text_uses_icontains_by_default():
    assert Filter.text("title").apply(Rows(), "hello").filters == [
        {"title__icontains": "hello"}
    ]


def test_the_lookup_can_be_changed():
    assert Filter.text("title", lookup="istartswith").apply(Rows(), "a").filters == [
        {"title__istartswith": "a"}
    ]


def test_an_unset_filter_leaves_the_queryset_alone():
    rows = Rows()
    assert Filter.text("title").apply(rows, None) is rows
    assert Filter.text("title").apply(rows, "") is rows


def test_search_spans_several_fields():
    # Needs Q from the ORM, which the rest of this layer avoids.
    pytest.importorskip("tortoise")
    narrowed = Filter.search("title", "body").apply(Rows(), "x")
    assert len(narrowed.calls) == 1


def test_search_reads_the_q_parameter():
    assert Filter.search("title").key == "q"


def test_search_reports_all_its_fields():
    assert Filter.search("title", "body").fields == ("title", "body")


def test_search_needs_at_least_one_field():
    with pytest.raises(TypeError, match="at least one field"):
        Filter.search()


def test_choice_matches_exactly():
    assert Filter.choice("status", ["a"]).apply(Rows(), "a").filters == [
        {"status": "a"}
    ]


def test_a_multiple_choice_filter_uses_in():
    filter_ = Filter.choice("status", ["a", "b"], multiple=True)
    assert filter_.apply(Rows(), ["a", "b"]).filters == [{"status__in": ["a", "b"]}]


def test_a_single_value_for_a_multiple_filter_is_wrapped():
    filter_ = Filter.choice("status", ["a"], multiple=True)
    assert filter_.apply(Rows(), "a").filters == [{"status__in": ["a"]}]


@pytest.mark.parametrize("raw", ["1", "true", "yes", "on", True])
def test_truthy_spellings(raw):
    assert Filter.boolean("active").apply(Rows(), raw).filters == [{"active": True}]


def test_falsey_spellings():
    assert Filter.boolean("active").apply(Rows(), "no").filters == [{"active": False}]


def test_exists_becomes_an_isnull_lookup():
    assert Filter.exists("deleted_at").apply(Rows(), "yes").filters == [
        {"deleted_at__isnull": False}
    ]


def test_a_number_range_becomes_two_bounds():
    assert Filter.number_range("total").apply(Rows(), "10..50").filters == [
        {"total__gte": 10.0},
        {"total__lte": 50.0},
    ]


def test_an_open_ended_range_emits_one_bound():
    assert Filter.number_range("total").apply(Rows(), "10..").filters == [
        {"total__gte": 10.0}
    ]


def test_a_range_with_neither_end_is_no_filter():
    rows = Rows()
    assert Filter.number_range("total").apply(rows, "..") is rows


def test_a_malformed_range_is_no_filter():
    rows = Rows()
    assert Filter.number_range("total").apply(rows, "10..50..90") is rows


def test_a_date_range_accepts_two_dates():
    narrowed = Filter.date_range("at").apply(Rows(), "2026-01-01..2026-02-01")
    assert narrowed.filters == [
        {"at__gte": dt.date(2026, 1, 1)},
        {"at__lte": dt.date(2026, 2, 1)},
    ]


def test_a_date_range_accepts_a_preset():
    narrowed = Filter.date_range("at").apply(Rows(), "7d", now=NOW)
    assert narrowed.filters == [
        {"at__gte": dt.date(2026, 8, 25)},
        {"at__lte": dt.date(2026, 9, 1)},
    ]


def test_presets_are_checked_at_declaration_time():
    with pytest.raises(ValueError, match="not valid"):
        Filter.date_range("at", presets=["fortnight"])


@pytest.mark.parametrize("preset", PRESETS)
def test_every_preset_resolves(preset):
    start, _ = preset_range(preset, NOW)
    assert (start is None) == (preset == "all")


def test_preset_ranges():
    assert preset_range("today", NOW) == (dt.date(2026, 9, 1), dt.date(2026, 9, 1))
    assert preset_range("yesterday", NOW) == (
        dt.date(2026, 8, 31),
        dt.date(2026, 8, 31),
    )
    assert preset_range("quarter", NOW)[0] == dt.date(2026, 7, 1)
    assert preset_range("month", NOW)[0] == dt.date(2026, 9, 1)
    assert preset_range("last_month", NOW) == (
        dt.date(2026, 8, 1),
        dt.date(2026, 8, 31),
    )
    assert preset_range("ytd", NOW)[0] == dt.date(2026, 1, 1)
    assert preset_range("12m", NOW)[0] == dt.date(2025, 9, 1)


def test_an_unknown_preset_is_refused():
    with pytest.raises(ValueError, match="Unknown date preset"):
        preset_range("fortnight")


def test_preset_range_defaults_to_now():
    assert preset_range("today")[0] == dt.date.today()


def test_a_toggle_narrows_when_it_is_on():
    filter_ = Filter.toggle("Long reads", lambda rows: rows.filter(words__gte=2000))
    assert filter_.apply(Rows(), "1").filters == [{"words__gte": 2000}]


def test_a_toggle_that_is_off_narrows_nothing():
    rows = Rows()
    filter_ = Filter.toggle("Long reads", lambda r: r.filter(words__gte=2000))
    assert filter_.apply(rows, "0") is rows


def test_a_toggle_keys_off_its_label():
    assert Filter.toggle("Long reads", lambda r: r).key == "long-reads"


def test_a_custom_filter_receives_the_value():
    filter_ = Filter.custom("Region", lambda rows, value: rows.filter(region=value))
    assert filter_.apply(Rows(), "eu").filters == [{"region": "eu"}]


def test_custom_and_toggle_need_a_label():
    with pytest.raises(TypeError, match="needs a label"):
        Filter.custom("", lambda rows, value: rows)


def test_custom_and_toggle_need_a_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Filter.custom("Region", "nope")


def test_other_kinds_need_a_field_name():
    with pytest.raises(TypeError, match="needs a field name"):
        Filter("text")


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="not valid"):
        Filter("vibes", "a")


def test_the_heading_humanises_the_field():
    assert Filter.choice("published_at").heading == "Published at"
    assert Filter.choice("author_id").heading == "Author"
    assert Filter.text("author__email").heading == "Email"


def test_relation_filters_carry_their_display():
    assert Filter.relation("author", display="email").option("display") == "email"


def test_repr_names_the_kind():
    assert repr(Filter.text("title")) == "Filter.text('title')"
    assert repr(Filter.toggle("Long", lambda r: r)) == "Filter.toggle('Long')"


def test_filter_options_survive_extension():
    assert Filter.text("title").with_(label="Title").option("lookup") == "icontains"


def test_a_filter_lookup_can_be_changed_by_extension():
    assert Filter.text("title").with_(lookup="iexact").option("lookup") == "iexact"
