"""Column: what a cell shows, how it sorts, and which join it needs."""

from __future__ import annotations

import pytest

from warder.columns import Column
from warder.formats import Format


def test_a_column_needs_a_name_or_a_derivation():
    with pytest.raises(TypeError, match="field name, or a derive="):
        Column()


def test_a_derived_column_needs_a_label():
    with pytest.raises(TypeError, match="computed column needs a label"):
        Column(derive=lambda row: 1)


def test_a_derivation_must_be_callable():
    with pytest.raises(TypeError, match="must be callable"):
        Column.compute("Words", "not a function")


def test_the_key_of_a_named_column_is_its_name():
    assert Column("title").key == "title"


def test_the_key_of_a_computed_column_is_its_slugged_label():
    assert Column.compute("Word count", lambda row: 1).key == "word-count"


def test_the_heading_humanises_the_name():
    assert Column("published_at").heading == "Published at"


def test_the_heading_drops_an_id_suffix():
    assert Column("author_id").heading == "Author"


def test_the_heading_uses_the_last_segment_of_a_traversal():
    assert Column("author__email").heading == "Email"


def test_an_explicit_label_wins():
    assert Column("published_at", label="Published").heading == "Published"


def test_alignment_comes_from_the_format():
    assert Column.money("total").alignment == "right"


def test_an_explicit_alignment_wins():
    assert Column.money("total", align="left").alignment == "left"


def test_an_unknown_alignment_is_refused():
    with pytest.raises(ValueError, match="'left', 'center', 'right'"):
        Column("a", align="middle")


def test_a_plain_column_sorts_on_itself():
    assert Column("title").sort_field == "title"


def test_a_relation_column_sorts_by_what_it_shows():
    # Ordering by the foreign key gives insertion order under a column of
    # email addresses, which looks like a bug and is one.
    assert Column.relation("author", display="email").sort_field == "author__email"


def test_sorting_can_be_redirected():
    assert (
        Column.compute("Words", lambda r: 1, sort="word_count").sort_field
        == "word_count"
    )


def test_a_computed_column_without_a_sort_is_not_sortable():
    column = Column.compute("Words", lambda r: 1)
    assert not column.sortable
    assert column.sort_field is None


def test_a_traversal_contributes_its_relation():
    assert Column("author__email").relation_path == "author"


def test_a_deep_traversal_contributes_the_whole_prefix():
    assert Column("author__team__name").relation_path == "author__team"


def test_a_relation_column_contributes_itself():
    assert Column.relation("author", display="email").relation_path == "author"


def test_a_relation_column_contributes_a_join_without_a_display():
    # Column.relation("author") and Column("author") look identical from the
    # outside; only the marker tells the resolver to join.
    assert Column.relation("author").relation_path == "author"
    assert Column("author").relation_path is None


def test_a_relation_column_without_a_display_sorts_on_the_key():
    assert Column.relation("author").sort_field == "author"


def test_a_plain_column_contributes_no_join():
    assert Column("title").relation_path is None


def test_traversal_splits_the_name():
    assert Column("author__email").traversal == ("author", "email")


def test_computed_columns_report_themselves():
    assert Column.compute("X", lambda r: 1).computed
    assert not Column("title").computed


def test_shorthands_fill_in_a_format():
    assert Column.badge("status").format.kind == "badge"
    assert Column.date("at", "relative").format.option("style") == "relative"
    assert Column.money("total", "GBP").format.option("currency") == "GBP"
    assert Column.bytes("size").format.kind == "bytes"
    assert Column.percent("rate").format.kind == "percent"
    assert Column.progress("done").format.kind == "progress"
    assert Column.tags("labels").format.kind == "tags"
    assert Column.avatar("user").format.kind == "avatar"
    assert Column.code("body").format.kind == "code"
    assert Column.duration("took").format.kind == "duration"
    assert Column.boolean("live").format.kind == "bool"
    assert Column.text("title", truncate=20).format.option("truncate") == 20
    assert Column.number("n", precision=2).format.option("precision") == 2


def test_images_and_json_are_not_sortable_by_default():
    assert not Column.image("photo").sortable
    assert not Column.json("meta").sortable


def test_a_url_column_is_derived_and_unsortable():
    column = Column.url("Invoice", to=lambda row: "/x")
    assert column.computed
    assert not column.sortable
    assert column.format.kind == "link"


def test_a_url_column_can_take_derived_text():
    column = Column.url("Invoice", to=lambda row: "/x", text=lambda row: row.number)
    row = type("Row", (), {"number": "INV-1"})()
    assert column.derive(row) == "INV-1"


def test_a_url_column_defaults_to_fixed_text():
    column = Column.url("Invoice", to=lambda row: "/x")
    assert column.derive(object()) == "Open"


def test_columns_extend_without_mutating():
    base = Column("title")
    assert base.with_(link=True).link
    assert not base.link


def test_repr_names_a_computed_column_by_its_label():
    assert repr(Column.compute("Words", lambda r: 1)) == "Column('Words', sort=False)"


def test_repr_shows_the_flags_that_were_set():
    assert repr(Column("title", link=True)) == "Column('title', link=True)"


def test_a_format_survives_the_repr():
    assert "Format" in repr(Column("x", format=Format.money()))


def test_a_width_must_be_positive_when_numeric():
    with pytest.raises(ValueError, match="positive integer"):
        Column("a", width=0)


def test_a_width_may_be_a_css_length():
    assert Column("a", width="12rem").width == "12rem"
