"""Defaults derived from a model's name, and the choice lists people write."""

from __future__ import annotations

import pytest
from fakes import model

from warder.naming import (
    coerce_choices,
    label_for,
    permission,
    plural_of,
    slug,
    slug_for,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Post", "post"),
        ("BlogPost", "blog-post"),
        ("OrderItem", "order-item"),
        ("HTTPRequest", "http-request"),
        ("Order2Item", "order2-item"),
    ],
)
def test_slug_splits_on_case_boundaries(name, expected):
    assert slug_for(model(name)) == expected


def test_slug_of_arbitrary_text():
    assert slug("Order Item!") == "order-item"


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Post", "Post"), ("BlogPost", "Blog post"), ("HTTPRequest", "Http request")],
)
def test_label_capitalises_only_the_first_word(name, expected):
    assert label_for(model(name)) == expected


@pytest.mark.parametrize(
    ("singular", "plural"),
    [
        ("Post", "Posts"),
        ("Category", "Categories"),
        ("Box", "Boxes"),
        ("Match", "Matches"),
        ("Dish", "Dishes"),
        ("Quiz", "Quizzes"),
        ("Day", "Days"),
        ("Person", "People"),
        ("Child", "Children"),
        ("Analysis", "Analyses"),
        ("Blog post", "Blog posts"),
        ("Order item", "Order items"),
    ],
)
def test_pluralisation(singular, plural):
    assert plural_of(singular) == plural


def test_pluralisation_carries_capitalisation():
    assert plural_of("PERSON") == "PEOPLE"
    assert plural_of("person") == "people"


def test_pluralisation_of_nothing_is_nothing():
    assert plural_of("") == ""


def test_permission_names():
    assert permission("post", "change") == "post.change"


def test_choices_from_a_flat_list():
    assert coerce_choices(["draft", "live"]) == (("draft", "Draft"), ("live", "Live"))


def test_choices_from_pairs():
    assert coerce_choices([("draft", "Not published")]) == (("draft", "Not published"),)


def test_choices_from_a_mapping():
    assert coerce_choices({"draft": "Draft"}) == (("draft", "Draft"),)


def test_choices_humanise_underscores():
    assert coerce_choices(["in_review"]) == (("in_review", "In review"),)


def test_choices_keep_non_string_values():
    assert coerce_choices([1, 2]) == ((1, "1"), (2, "2"))
