"""Declarations are values: frozen, comparable, extendable, and locatable."""

from __future__ import annotations

import pytest

from warder.base import Declaration, freeze, origin


class Demo(Declaration):
    __slots__ = ("items", "label", "per_page")
    _fields = ("items", "per_page", "label")
    _parts = "items"

    def __init__(self, *items, per_page=25, label=None):
        self._init(items=items, per_page=per_page, label=label)


class Headed(Declaration):
    __slots__ = ("note", "parts", "title")
    _fields = ("title", "parts", "note")
    _parts = "parts"
    _head = ("title",)

    def __init__(self, title, *parts, note=None):
        self._init(title=title, parts=parts, note=note)


class Plain(Declaration):
    __slots__ = ("a", "b")
    _fields = ("a", "b")

    def __init__(self, a=1, b=2):
        self._init(a=a, b=b)


def test_attributes_cannot_be_set():
    demo = Demo("a")
    with pytest.raises(AttributeError, match="cannot be modified"):
        demo.per_page = 50


def test_attributes_cannot_be_deleted():
    demo = Demo("a")
    with pytest.raises(AttributeError, match="cannot be modified"):
        del demo.per_page


def test_the_error_names_the_way_out():
    with pytest.raises(AttributeError, match=r"\.with_\(per_page=\.\.\.\)"):
        Demo().per_page = 50


def test_with_appends_parts():
    base = Demo("a", "b")
    assert base.with_("c").items == ("a", "b", "c")


def test_with_replaces_keywords():
    assert Demo(per_page=25).with_(per_page=50).per_page == 50


def test_with_leaves_the_original_alone():
    base = Demo("a", per_page=25)
    base.with_("b", per_page=50)
    assert base.items == ("a",)
    assert base.per_page == 25


def test_with_passes_leading_positionals_positionally():
    # Without _head the first part would bind to `title`.
    extended = Headed("Content", "a").with_("b")
    assert extended.title == "Content"
    assert extended.parts == ("a", "b")


def test_with_rejects_unknown_keywords():
    with pytest.raises(TypeError, match="unexpected keyword 'nope'"):
        Demo().with_(nope=1)


def test_with_lists_what_it_accepts():
    with pytest.raises(TypeError, match="Accepts: items, per_page, label"):
        Demo().with_(nope=1)


def test_with_pluralises_several_unknown_keywords():
    with pytest.raises(TypeError, match="unexpected keywords 'one', 'two'"):
        Demo().with_(one=1, two=2)


def test_with_rejects_parts_where_there_are_none():
    with pytest.raises(TypeError, match="takes no positional parts"):
        Plain().with_("a")


def test_equality_is_by_value():
    assert Demo("a", per_page=25) == Demo("a", per_page=25)
    assert Demo("a") != Demo("b")


def test_equality_against_another_type_is_not_implemented():
    assert Demo().__eq__(Plain()) is NotImplemented
    assert Demo() != Plain()


def test_declarations_are_not_hashable():
    # Fields hold callables, lists and mappings; a hash would be a lie about
    # what can be compared.
    with pytest.raises(TypeError):
        hash(Demo())


def test_repr_hides_defaults():
    assert repr(Demo("a")) == "Demo('a')"


def test_repr_shows_what_was_asked_for():
    assert repr(Demo("a", per_page=50)) == "Demo('a', per_page=50)"


def test_repr_does_not_report_frozen_collections_as_changed():
    # freeze() turns [] into (), so a naive default comparison would print
    # every collection on every declaration.
    class WithList(Declaration):
        __slots__ = ("names",)
        _fields = ("names",)

        def __init__(self, names=()):
            self._init(names=names)

    assert repr(WithList()) == "WithList()"


def test_where_records_the_calling_line():
    demo = Demo("a")
    assert demo.where is not None
    assert demo.where.endswith(
        f":{test_where_records_the_calling_line.__code__.co_firstlineno + 1}"
    )


def test_where_points_outside_the_package():
    # Built through with_, which is warder's own code; the location should
    # still be the caller's line, not the frame inside the package.
    where = Demo("a").with_("b").where or ""
    assert "warder/base.py" not in where
    assert where.startswith("tests/")


def test_freeze_copies_sequences():
    source = ["a"]
    frozen = freeze(source)
    source.append("b")
    assert frozen == ("a",)


def test_freeze_makes_mappings_read_only():
    frozen = freeze({"a": 1})
    with pytest.raises(TypeError):
        frozen["b"] = 2  # type: ignore[index]


def test_freeze_copies_sets():
    assert freeze({"a"}) == frozenset({"a"})


def test_freeze_leaves_other_values_alone():
    def handler():
        return None

    assert freeze(handler) is handler
    assert freeze("text") == "text"


def test_origin_returns_a_location():
    assert origin() is not None
