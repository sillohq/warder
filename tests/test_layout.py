"""Sections, panels and the empty state."""

from __future__ import annotations

import pytest
from fakes import Comment, Post

from warder.fields import Field
from warder.layout import Empty, Panel, Section
from warder.sorting import Sort


def test_a_section_keys_off_its_title():
    assert Section("Publishing details").key == "publishing-details"


def test_an_unnamed_section_keys_as_main():
    assert Section("").key == "main"


def test_a_section_holds_its_fields_in_order():
    section = Section("Content", Field("title"), Field("body"))
    assert [f.name for f in section.fields] == ["title", "body"]


def test_extending_a_section_appends():
    base = Section("Content", Field("title"))
    extended = base.with_(Field("body"), collapsed=True)
    assert [f.name for f in extended.fields] == ["title", "body"]
    assert extended.collapsed
    assert len(base.fields) == 1


def test_section_columns_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        Section("X", columns=0)


def test_panel_kinds_are_checked():
    with pytest.raises(ValueError, match="not valid"):
        Panel("hologram", "X")


def test_a_fields_panel_carries_names():
    assert Panel.fields("Overview", "title", "author").target == ("title", "author")


def test_a_fields_panel_rejects_an_empty_name():
    with pytest.raises(ValueError, match="non-empty field name"):
        Panel.fields("Overview", "")


def test_an_inline_panel_carries_its_model_and_options():
    panel = Panel.inline("Sections", Post, extra=2, sort=Sort.asc("position"))
    assert panel.target is Post
    assert panel.option("extra") == 2
    assert panel.option("sort").as_terms() == ("position",)


def test_inline_extra_cannot_be_negative():
    with pytest.raises(ValueError, match="zero or more"):
        Panel.inline("X", Post, extra=-1)


def test_a_related_panel_limits_its_rows():
    assert Panel.related("Comments", Comment, limit=5).option("limit") == 5


def test_a_related_panel_limit_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        Panel.related("Comments", Comment, limit=0)


def test_a_custom_panel_names_a_component():
    assert Panel.custom("Chart", "acme/Revenue").target == "acme/Revenue"


def test_a_text_panel_checks_its_format():
    with pytest.raises(ValueError, match="'text', 'markdown', 'html'"):
        Panel.text("Summary", lambda row: "", format="rtf")


def test_panel_spans_are_checked():
    with pytest.raises(ValueError, match="'main', 'side', 'full'"):
        Panel.fields("X", "a", span="left")


def test_a_panel_keys_off_its_title():
    assert Panel.fields("Overview", "a").key == "overview"


def test_an_untitled_panel_keys_off_its_kind():
    assert Panel.custom("", "acme/X").key == "custom"


def test_panel_repr_names_the_model():
    assert repr(Panel.inline("Sections", Post)) == "Panel.inline('Sections', Post)"


def test_panel_repr_without_a_model():
    assert repr(Panel.fields("Overview", "a")) == "Panel.fields('Overview')"


def test_an_empty_state_carries_a_message():
    assert Empty("No posts yet").title == "No posts yet"
    assert repr(Empty("No posts yet")) == "Empty('No posts yet')"


def test_the_default_empty_state_says_something():
    assert Empty().title
