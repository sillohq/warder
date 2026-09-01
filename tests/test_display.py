"""Format and Widget: a kind, its options, and no rendering code."""

from __future__ import annotations

import pytest

from warder.formats import Format
from warder.widgets import Widget


def test_a_format_is_a_kind_and_options():
    money = Format.money("EUR")
    assert money.kind == "money"
    assert money.option("currency") == "EUR"


def test_an_unknown_format_kind_is_refused():
    with pytest.raises(ValueError, match="not valid"):
        Format("hologram")


def test_numeric_formats_align_right():
    for builder in (Format.number, Format.money, Format.percent, Format.bytes):
        assert builder().align == "right"


def test_text_aligns_left():
    assert Format.text().align == "left"


def test_booleans_centre():
    assert Format.bool().align == "center"


def test_numeric_reports_which_formats_are_compared_digit_by_digit():
    assert Format.money().numeric
    assert not Format.text().numeric


def test_date_styles_are_checked():
    assert Format.date("relative").option("style") == "relative"
    with pytest.raises(ValueError, match="'date', 'datetime', 'time'"):
        Format.date("yesterday")


def test_relative_is_shorthand_for_a_date_style():
    assert Format.relative() == Format.date("relative")


def test_badge_normalises_labels_from_any_spelling():
    badge = Format.badge({"live": "green"}, labels=["draft", "live"])
    assert badge.option("labels") == {"draft": "Draft", "live": "Live"}


def test_option_falls_back_to_a_default():
    assert Format.text().option("missing", "fallback") == "fallback"


def test_format_repr_hides_empty_options():
    assert repr(Format.text()) == "Format('text', mono=False)"


def test_image_rounding_is_checked():
    with pytest.raises(ValueError, match="'none', 'sm', 'md', 'full'"):
        Format.image(rounded="circle")


def test_duration_units_are_checked():
    with pytest.raises(ValueError, match="'seconds', 'milliseconds'"):
        Format.duration(unit="fortnights")


# ------------------------------------------------------------------------ Widget


def test_a_widget_is_a_kind_and_options():
    assert Widget.markdown(height=400).option("height") == 400


def test_an_unknown_widget_kind_is_refused():
    with pytest.raises(ValueError, match="not valid"):
        Widget("telepathy")


def test_select_normalises_choices():
    assert Widget.select(["a"]).choices == (("a", "A"),)


def test_a_widget_with_no_choices_reports_none():
    assert Widget.text().choices == ()


def test_select_becomes_searchable_past_ten_options():
    assert not Widget.select(range(10)).option("searchable")
    assert Widget.select(range(11)).option("searchable")


def test_searchable_can_be_forced_either_way():
    assert Widget.select(["a"], searchable=True).option("searchable")
    assert not Widget.select(range(20), searchable=False).option("searchable")


def test_relation_carries_its_search_fields():
    widget = Widget.relation(display="email", search=["email", "name"])
    assert widget.option("search") == ("email", "name")


def test_widget_repr_hides_falsey_options():
    assert repr(Widget.hidden()) == "Widget('hidden')"


def test_widgets_compare_by_value():
    assert Widget.textarea(rows=4) == Widget.textarea(rows=4)
    assert Widget.textarea(rows=4) != Widget.textarea(rows=6)
