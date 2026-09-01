"""Field: what an input says about itself."""

from __future__ import annotations

import pytest

from warder.conditions import When
from warder.fields import Field
from warder.widgets import Widget


def test_a_field_needs_a_name():
    with pytest.raises(ValueError, match="non-empty field name"):
        Field("")


def test_the_heading_humanises_the_name():
    assert Field("published_at").heading == "Published at"


def test_the_heading_drops_an_id_suffix():
    assert Field("author_id").heading == "Author"


def test_an_explicit_label_wins():
    assert Field("body", label="Article").heading == "Article"


def test_readonly_is_the_shorthand_for_not_editable():
    assert not Field.readonly("created_at").editable


def test_fields_are_editable_by_default():
    assert Field("title").editable


def test_unset_is_distinguishable_from_a_default_of_none():
    assert not Field("a").has_default
    assert Field("a", default=None).has_default


def test_a_span_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        Field("a", span=0)


def test_validators_must_be_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Field("a", validate=["not a function"])


def test_a_single_validator_need_not_be_wrapped():
    field = Field("a", validate=lambda v: "no" if not v else None)
    assert field.errors("") == ("no",)


def test_every_validator_runs():
    field = Field(
        "email",
        validate=[
            lambda v: "Required" if not v else None,
            lambda v: "Needs an @" if v and "@" not in v else None,
        ],
    )
    assert field.errors("") == ("Required",)
    assert field.errors("nope") == ("Needs an @",)
    assert field.errors("a@b.c") == ()


def test_shorthands_fill_in_a_widget():
    assert Field.markdown("body").widget.kind == "markdown"
    assert Field.password().widget.kind == "password"
    assert Field.select("status", ["a"]).widget.choices == (("a", "A"),)
    assert Field.relation("author", display="email").widget.option("display") == "email"
    assert Field.slug("slug", source="title").widget.option("source") == "title"
    assert Field.textarea("body", rows=8).widget.option("rows") == 8
    assert Field.switch("live").widget.kind == "switch"
    assert Field.tags("labels").widget.kind == "tags"
    assert Field.json("meta").widget.kind == "json"
    assert Field.keyvalue("meta").widget.kind == "keyvalue"
    assert Field.file("doc").widget.kind == "file"
    assert Field.image("photo").widget.kind == "image"
    assert Field.date("on").widget.kind == "date"
    assert Field.datetime("at").widget.kind == "datetime"
    assert Field.number("n", min=1).widget.option("min") == 1
    assert Field.money("total", "GBP").widget.option("currency") == "GBP"
    assert Field.code("config").widget.kind == "code"
    assert Field.rich("body").widget.kind == "rich"
    assert Field.radio("choice", ["a"]).widget.kind == "radio"
    assert Field.text("title", prefix="@").widget.option("prefix") == "@"


def test_the_default_widget_is_left_unset_for_the_resolver_to_pick():
    assert Field("body").widget is None


def test_a_condition_is_carried():
    field = Field("published_at", show=When("status", equals="live"))
    assert field.show.holds({"status": "live"})


def test_password_defaults_to_the_conventional_name():
    assert Field.password().name == "password"


def test_repr_shows_what_was_set():
    assert repr(Field.readonly("created_at")) == "Field('created_at', editable=False)"


def test_fields_extend_without_mutating():
    base = Field("title")
    assert base.with_(label="Headline").label == "Headline"
    assert base.label is None


def test_a_widget_can_be_replaced_by_extension():
    assert Field("body").with_(widget=Widget.markdown()).widget.kind == "markdown"
