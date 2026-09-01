"""Sort: a sequence of terms, and the strings an ORM wants."""

from __future__ import annotations

import pytest

from warder.sorting import Sort, SortTerm


def test_asc_and_desc():
    assert Sort.asc("title").as_terms() == ("title",)
    assert Sort.desc("created_at").as_terms() == ("-created_at",)


def test_several_fields_in_one_call():
    assert Sort.asc("a", "b").as_terms() == ("a", "b")


def test_by_reads_minus_prefixes():
    assert Sort.by("-created_at", "title").as_terms() == ("-created_at", "title")


def test_by_reads_plus_prefixes():
    assert Sort.by("+title").as_terms() == ("title",)


def test_then_chains():
    combined = Sort.desc("published_at").then(Sort.asc("title"))
    assert combined.as_terms() == ("-published_at", "title")


def test_reversed_flips_every_term():
    assert Sort.by("-a", "b").reversed().as_terms() == ("a", "-b")


def test_direction_of_a_sorted_field():
    assert Sort.by("-a").direction_of("a") == "desc"
    assert Sort.by("a").direction_of("a") == "asc"


def test_direction_of_an_unsorted_field():
    assert Sort.by("-a").direction_of("b") is None


def test_none_is_falsy():
    assert not Sort.none()
    assert Sort.asc("a")


def test_terms_accept_tuples():
    assert Sort(("a", True)).as_terms() == ("-a",)


def test_terms_accept_sort_terms():
    assert Sort(SortTerm("a", True)).as_terms() == ("-a",)


def test_a_term_must_be_one_of_the_three_spellings():
    with pytest.raises(TypeError, match="field name, a '-field' string or a SortTerm"):
        Sort(42)


def test_an_empty_field_name_is_refused():
    with pytest.raises(ValueError, match="non-empty field name"):
        Sort.asc("")


def test_repr_reads_like_the_call():
    assert repr(Sort.by("-a", "b")) == "Sort('-a', 'b')"


def test_with_appends_terms():
    assert Sort.desc("a").with_("b").as_terms() == ("-a", "b")
