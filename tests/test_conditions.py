"""When: a form condition the browser and the server both evaluate."""

from __future__ import annotations

import pytest

from warder.conditions import When


def test_equals():
    condition = When("status", equals="live")
    assert condition.holds({"status": "live"})
    assert not condition.holds({"status": "draft"})


def test_not_equals():
    assert When("status", not_equals="live").holds({"status": "draft"})


def test_any_of():
    condition = When("status", any_of=["rejected", "held"])
    assert condition.holds({"status": "held"})
    assert not condition.holds({"status": "live"})


def test_none_of():
    assert When("status", none_of=["live"]).holds({"status": "draft"})


def test_is_true():
    assert When("business", is_true=True).holds({"business": True})
    assert not When("business", is_true=True).holds({"business": False})


def test_is_false():
    assert When("business", is_false=True).holds({"business": False})


def test_filled_is_the_default_test():
    assert When("note").holds({"note": "something"})
    assert not When("note").holds({"note": ""})


def test_empty():
    assert When("note", empty=True).holds({"note": None})
    assert not When("note", empty=True).holds({"note": "x"})


def test_a_missing_key_reads_as_absent():
    assert not When("note").holds({})
    assert When("note", empty=True).holds({})


def test_all_requires_every_condition():
    condition = When.all(When("country", equals="GB"), When("business", is_true=True))
    assert condition.holds({"country": "GB", "business": True})
    assert not condition.holds({"country": "GB", "business": False})


def test_any_needs_only_one():
    condition = When.any(When("a", equals=1), When("b", equals=2))
    assert condition.holds({"b": 2})


def test_negation():
    assert (~When("status", equals="live")).holds({"status": "draft"})


def test_operators_compose():
    both = When("a", equals=1) & When("b", equals=2)
    either = When("a", equals=1) | When("b", equals=2)
    assert both.holds({"a": 1, "b": 2})
    assert either.holds({"a": 1})


def test_fields_reports_everything_watched():
    condition = When.all(When("a", equals=1), When.any(When("b"), When("c")))
    assert condition.fields() == frozenset({"a", "b", "c"})


def test_a_leaf_condition_needs_a_field():
    with pytest.raises(ValueError, match="needs a field name"):
        When(test="equals")


def test_an_unknown_test_is_refused():
    with pytest.raises(ValueError, match="not one of"):
        When("a", test="rhymes_with")


def test_repr_reads_like_the_call():
    assert repr(When("status", equals="live")) == "When('status', equals='live')"
    assert repr(When("note")) == "When('note', test='filled')"
    assert repr(~When("a")).startswith("When.not(")
