"""Deriving screens from a model, and checking the ones that were written."""

from __future__ import annotations

import pytest
from orm import Author, Comment, Post, Required, Tag, Wide

from warder import (
    Access,
    Admin,
    Column,
    Detail,
    Field,
    Filter,
    Form,
    List,
    Panel,
    Resource,
    Section,
    Sort,
)
from warder.errors import DeclarationError
from warder.resolve import (
    bind,
    check,
    derive_detail,
    derive_form,
    derive_list,
    display_for,
    format_for,
    widget_for,
)
from warder.schema import Schema

# ---------------------------------------------------------------- deriving


def test_a_bare_resource_gets_a_working_list():
    screen = derive_list(Schema.of(Post))
    assert screen.columns
    assert screen.link_column is not None


def test_the_key_comes_first_and_is_monospaced():
    screen = derive_list(Schema.of(Post))
    assert screen.columns[0].key == "id"
    assert screen.columns[0].format.option("mono")


def test_the_second_column_is_the_link():
    # The key is not what anyone clicks; the first identifying column is.
    screen = derive_list(Schema.of(Post))
    assert screen.link_column.key == "title"


def test_a_derived_list_stops_before_it_scrolls_sideways():
    from warder.resolve import LIST_WIDTH

    assert len(derive_list(Schema.of(Post)).columns) <= LIST_WIDTH


def test_prose_is_not_given_a_column():
    keys = {c.key for c in derive_list(Schema.of(Post)).columns}
    assert "body" not in keys


def test_a_password_is_never_listed():
    keys = {c.key for c in derive_list(Schema.of(Post)).columns}
    assert "secret" not in keys


def test_a_relation_column_is_derived_with_a_display():
    column = next(c for c in derive_list(Schema.of(Post)).columns if c.key == "author")
    assert column.related
    assert column.display == "name"


def test_a_derived_list_is_ordered():
    # An unordered page two repeats a row from page one and skips another,
    # which reads as data loss.
    assert derive_list(Schema.of(Post)).sort.as_terms() == ("-created_at",)


def test_a_model_without_timestamps_falls_back_to_the_key():
    from warder.resolve import _default_sort

    schema = Schema.of(Post)
    assert _default_sort(schema).as_terms() == ("-created_at",)


def test_a_derived_list_has_a_search_box():
    assert derive_list(Schema.of(Post)).search is not None


def test_the_search_box_covers_the_text_columns():
    assert "title" in derive_list(Schema.of(Post)).search.fields


def test_booleans_become_filters():
    keys = set(derive_list(Schema.of(Post)).filter_map)
    assert "live" in keys


def test_a_date_range_filter_is_offered():
    filters = derive_list(Schema.of(Post)).filters
    assert any(f.kind == "date_range" for f in filters)


def test_a_derived_form_offers_every_writable_column():
    names = {f.name for f in derive_form(Schema.of(Post)).fields}
    assert "title" in names
    assert "author" in names


def test_a_derived_form_does_not_offer_the_key():
    assert "id" not in {f.name for f in derive_form(Schema.of(Post)).fields}


def test_a_derived_form_does_not_offer_a_shadow_column():
    assert "author_id" not in {f.name for f in derive_form(Schema.of(Post)).fields}


def test_the_timestamps_are_readonly_and_collapsed():
    form = derive_form(Schema.of(Post))
    audit = form.sections[-1]
    assert audit.title == "Audit"
    assert audit.collapsed
    assert all(not f.editable for f in audit.fields)


def test_a_derived_detail_shows_the_form_fields():
    detail = derive_detail(Schema.of(Post), derive_form(Schema.of(Post)))
    assert detail.panels[0].kind == "fields"


def test_a_derived_detail_windows_onto_child_tables():
    detail = derive_detail(Schema.of(Post), derive_form(Schema.of(Post)))
    assert any(p.kind == "related" for p in detail.panels)


def test_a_child_panel_is_labelled_in_the_plural():
    detail = derive_detail(Schema.of(Post), derive_form(Schema.of(Post)))
    assert any(p.title == "Comments" for p in detail.panels)


# ------------------------------------------------------------------ widgets


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("title", "text"),
        ("body", "textarea"),
        ("slug", "slug"),
        ("secret", "password"),
        ("live", "switch"),
        ("meta", "json"),
        ("words", "number"),
        ("price", "number"),
        ("published_at", "datetime"),
        ("author", "relation"),
    ],
)
def test_widgets_are_read_off_the_column(name, kind):
    assert widget_for(Schema.of(Post).get(name)).kind == kind


def test_a_relation_widget_carries_a_display():
    assert widget_for(Schema.of(Post).get("author")).option("display") == "name"


def test_a_conventional_display_name_wins():
    assert display_for(Author) == "name"


def test_a_model_without_a_conventional_name_uses_its_unique_text_column():
    assert display_for(Tag) == "label"


def test_an_unresolved_relation_has_no_display():
    assert display_for(None) is None


# ---------------------------------------------------------------- checking


def test_a_clean_resource_reports_nothing():
    assert check(Resource(Post, list=List(Column("title")))) == []


def test_a_misspelled_column_is_caught():
    problems = check(Resource(Post, list=List(Column("titel"))))
    assert str(problems[0]).splitlines()[0] == (
        "Resource(Post).list column 'titel' is not a field of Post."
    )


def test_a_misspelled_column_gets_a_suggestion():
    problems = check(Resource(Post, list=List(Column("titel"))))
    assert "Did you mean 'title'?" in str(problems[0])


def test_a_misspelled_column_carries_its_line():
    problems = check(Resource(Post, list=List(Column("titel"))))
    assert "Declared at tests/test_resolve.py:" in str(problems[0])


def test_a_traversal_is_followed():
    assert check(Resource(Post, list=List(Column("author__email")))) == []


def test_a_broken_traversal_is_caught():
    problems = check(Resource(Post, list=List(Column("author__nope"))))
    assert "not a field of Post" in str(problems[0])


def test_a_relation_column_over_a_plain_column_is_caught():
    problems = check(Resource(Post, list=List(Column.relation("title"))))
    assert "is a text column, not a relation" in str(problems[0])


def test_a_display_that_is_not_on_the_far_side_is_caught():
    problems = check(
        Resource(Post, list=List(Column.relation("author", display="nope")))
    )
    assert "not a field of Author" in str(problems[0])


def test_a_valid_display_passes():
    assert (
        check(Resource(Post, list=List(Column.relation("author", display="email"))))
        == []
    )


def test_a_sort_over_a_missing_column_is_caught():
    problems = check(
        Resource(Post, list=List(Column.compute("X", lambda r: 1, sort="nope")))
    )
    assert "sorts by 'nope'" in str(problems[0])


def test_a_filter_over_a_missing_field_is_caught():
    problems = check(Resource(Post, list=List(filters=[Filter.text("nope")])))
    assert "names 'nope'" in str(problems[0])


def test_select_related_over_a_plain_column_is_caught():
    problems = check(Resource(Post, list=List(select_related=["title"])))
    assert "not a relation" in str(problems[0])


def test_select_related_over_a_missing_relation_is_caught():
    problems = check(Resource(Post, list=List(select_related=["nope"])))
    assert "names 'nope'" in str(problems[0])


def test_a_total_over_a_text_column_is_caught():
    problems = check(
        Resource(Post, list=List(Column("title"), totals={"title": "sum"}))
    )
    assert "which is a text column" in str(problems[0])


def test_counting_a_text_column_is_fine():
    assert (
        check(Resource(Post, list=List(Column("title"), totals={"title": "count"})))
        == []
    )


def test_summing_a_number_is_fine():
    assert (
        check(Resource(Post, list=List(Column("words"), totals={"words": "sum"}))) == []
    )


def test_a_group_by_over_a_missing_column_is_caught():
    problems = check(Resource(Post, list=List(group_by="nope")))
    assert "group_by names 'nope'" in str(problems[0])


def test_a_list_sort_over_a_missing_column_is_caught():
    problems = check(Resource(Post, list=List(sort=Sort.desc("nope"))))
    assert "sort names 'nope'" in str(problems[0])


def test_a_form_field_that_is_not_a_column_is_caught():
    problems = check(Resource(Post, form=Form(Field("nope"))))
    assert "form field 'nope' is not a field of Post" in str(problems[0])


def test_a_reverse_relation_on_a_form_is_caught():
    problems = check(Resource(Author, form=Form(Field("posts"))))
    assert "reverse relation, which a form cannot write" in str(problems[0])


def test_a_readonly_required_field_would_make_the_form_unsubmittable():
    problems = check(Resource(Required, form=Form(Field.readonly("code"))))
    assert "could never be saved" in str(problems[0])


def test_a_readonly_field_with_a_default_is_fine():
    assert check(Resource(Post, form=Form(Field.readonly("status")))) == []


def test_a_readonly_nullable_field_is_fine():
    assert check(Resource(Post, form=Form(Field.readonly("body")))) == []


def test_a_readonly_required_field_with_a_declared_default_is_fine():
    assert (
        check(Resource(Required, form=Form(Field.readonly("code", default="X")))) == []
    )


def test_a_fields_panel_naming_a_missing_column_is_caught():
    problems = check(Resource(Post, detail=Detail(Panel.fields("Overview", "nope"))))
    assert "names 'nope'" in str(problems[0])


def test_a_fields_panel_may_take_whole_columns():
    detail = Detail(Panel.fields("Overview", Column("title")))
    assert check(Resource(Post, detail=detail)) == []


def test_an_ambiguous_inline_panel_asks_for_via():
    # Comment has two foreign keys to Author. Picking the first would be wrong
    # half the time and silent both halves.
    problems = check(Resource(Author, detail=Detail(Panel.inline("C", Comment))))
    assert "Pass via= to say which one" in str(problems[0])
    assert "author, reviewer" in str(problems[0])
    assert "2 relations" in str(problems[0])


def test_naming_via_resolves_the_ambiguity():
    detail = Detail(Panel.inline("C", Comment, via="author"))
    assert check(Resource(Author, detail=detail)) == []


def test_a_via_that_is_not_a_field_is_caught():
    detail = Detail(Panel.related("C", Comment, via="nope"))
    problems = check(Resource(Author, detail=detail))
    assert "names 'nope'" in str(problems[0])


def test_an_unambiguous_child_needs_no_via():
    assert check(Resource(Post, detail=Detail(Panel.related("C", Comment)))) == []


def test_a_child_with_no_way_back_is_caught():
    from orm import Required

    problems = check(Resource(Required, detail=Detail(Panel.related("C", Comment))))
    assert "no relation from Comment back to Required" in str(problems[0])


def test_a_related_panel_may_follow_a_many_to_many():
    # A class's subjects is a many-to-many, and is exactly as much "the rows
    # belonging to this one" as a post's comments are.
    from orm import Wide

    assert check(Resource(Tag, detail=Detail(Panel.related("Wides", Wide)))) == []


def test_a_panel_over_something_that_is_not_a_model_is_caught():
    detail = Detail(Panel.inline("C", type("Plain", (), {})))
    problems = check(Resource(Post, detail=detail))
    assert "takes a model class" in str(problems[0])


def test_resource_search_is_checked():
    problems = check(Resource(Post, search=["nope"]))
    assert "search names 'nope'" in str(problems[0])


def test_resource_sort_is_checked():
    problems = check(Resource(Post, sort="-nope"))
    assert "sort names 'nope'" in str(problems[0])


# ------------------------------------------------------------------ binding


def test_binding_derives_what_was_left_out():
    bound = bind(Resource(Post))
    assert bound.list.columns
    assert bound.form.fields
    assert bound.detail.panels


def test_binding_keeps_what_was_declared():
    declared = List(Column("title"), per_page=7, sort=Sort.asc("title"))
    bound = bind(Resource(Post, list=declared)).list
    assert [c.key for c in bound.columns] == ["title"]
    assert bound.per_page == 7
    assert bound.sort == declared.sort


def test_a_declared_relation_column_learns_that_it_is_one():
    # Column("author") and Column.relation("author") must not behave
    # differently when the model says the same thing about both: without the
    # marker the list joins nothing and every row costs a query.
    bound = bind(Resource(Post, list=List(Column("author")))).list
    assert bound.columns[0].related
    assert bound.columns[0].display == "name"
    assert bound.joins == ("author",)


def test_a_declared_many_to_many_column_is_prefetched():
    from orm import Wide

    bound = bind(Resource(Wide, list=List(Column("tags")))).list
    assert bound.columns[0].multiple
    assert bound.prefetches == ("tags",)
    # Never joined: one row with four tags is four rows.
    assert bound.joins == ()


def test_a_many_to_many_column_is_not_sortable():
    from orm import Wide

    bound = bind(Resource(Wide, list=List(Column("tags")))).list
    assert not bound.columns[0].sortable


def test_a_derived_list_includes_a_many_to_many():
    from orm import Wide

    keys = {c.key for c in derive_list(Schema.of(Wide)).columns}
    assert "tags" in keys


def test_an_explicit_display_survives_dressing():
    bound = bind(
        Resource(Post, list=List(Column.relation("author", display="email")))
    ).list
    assert bound.columns[0].display == "email"


def test_a_resource_sort_reaches_a_derived_list():
    bound = bind(Resource(Post, sort="-words"))
    assert bound.list.sort.as_terms() == ("-words",)


def test_a_declared_list_sort_wins_over_the_resource():
    bound = bind(Resource(Post, sort="-words", list=List(sort=Sort.asc("title"))))
    assert bound.list.sort.as_terms() == ("title",)


def test_resource_search_becomes_a_search_filter():
    bound = bind(Resource(Post, search=["title", "body"], list=List(Column("title"))))
    assert bound.list.search.fields == ("title", "body")


def test_bound_knows_its_model():
    assert bind(Resource(Post)).model is Post


def test_bound_prints_its_model():
    assert repr(bind(Resource(Post))) == "Bound(Post)"


# ------------------------------------------------------------- through Admin


def test_admin_bind_resolves_every_resource():
    admin = Admin().add(Resource(Post), Resource(Author))
    bound = admin.bind()
    assert sorted(bound) == ["author", "post"]


def test_admin_bind_raises_on_the_first_problem():
    admin = Admin().add(Resource(Post, list=List(Column("titel"))))
    with pytest.raises(DeclarationError, match="not a field of Post"):
        admin.bind()


def test_admin_bind_refuses_something_that_is_not_a_model():
    admin = Admin().add(Resource(type("Plain", (), {})))
    with pytest.raises(DeclarationError, match="has no _meta"):
        admin.bind()


def test_admin_check_still_needs_no_orm():
    # The declaration-only checks are what a test without models can call.
    assert Admin().add(Resource(type("Plain", (), {}))).check() == []


def test_a_real_admin_binds_end_to_end():
    admin = Admin(title="Acme Ops", groups=["Content"])
    admin.add(
        Resource(
            Post,
            group="Content",
            list=List(
                Column("title", link=True),
                Column.relation("author", display="email"),
                Column.badge("status", colors={"live": "green"}),
                filters=[Filter.search("title", "body"), Filter.boolean("live")],
                select_related=["author"],
                sort=Sort.desc("published_at"),
            ),
            form=Form(
                Section("Content", Field("title"), Field("body")),
                Section("Publishing", Field("status"), Field("published_at")),
            ),
            detail=Detail(
                Panel.fields("Overview", "title", "status"),
                Panel.related("Comments", Comment, limit=5),
            ),
            access=Access(view=True, add="post.add", delete=False),
        )
    )
    admin.add(Resource(Author), Resource(Tag))
    assert admin.check() == []
    bound = admin.bind()
    assert bound["post"].list.joins == ("author",)
    assert bound["author"].list.columns
    assert bound["tag"].form.fields


def test_resource_search_replaces_a_derived_search_box():
    # Otherwise a derived list would carry two search filters, both keyed "q".
    bound = bind(Resource(Post, search=["title"]))
    assert len([f for f in bound.list.filters if f.kind == "search"]) == 1
    assert bound.list.search.fields == ("title",)


def test_a_declared_search_filter_wins_over_the_resource():
    declared = List(Column("title"), filters=[Filter.search("body")])
    bound = bind(Resource(Post, search=["title"], list=declared))
    assert bound.list.search.fields == ("body",)


# The kinds the Post model does not have. Inference with a blind spot is
# inference that surprises you on the model you did not think about.


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("id", "uuid"),
        ("kind", "enum"),
        ("rank", "enum"),
        ("ratio", "float"),
        ("on", "date"),
        ("at", "time"),
        ("blob", "binary"),
        ("prose", "text"),
        ("tags", "m2m"),
    ],
)
def test_the_remaining_kinds_are_read(name, kind):
    assert Schema.of(Wide).get(name).kind == kind


@pytest.mark.parametrize(
    ("name", "widget"),
    [
        ("kind", "select"),
        ("rank", "select"),
        ("ratio", "number"),
        ("on", "date"),
        ("at", "time"),
        ("blob", "text"),
        ("prose", "textarea"),
        ("tags", "relation"),
    ],
)
def test_the_remaining_widgets(name, widget):
    assert widget_for(Schema.of(Wide).get(name)).kind == widget


def test_an_enum_column_offers_its_members():
    assert widget_for(Schema.of(Wide).get("kind")).choices == (
        ("alpha", "Alpha"),
        ("beta", "Beta"),
    )


def test_a_many_to_many_widget_takes_several():
    assert widget_for(Schema.of(Wide).get("tags")).option("multiple")


def test_a_long_char_column_is_prose_in_a_short_columns_clothing():
    assert widget_for(Schema.of(Wide).get("prose")).kind == "textarea"


def test_a_binary_column_is_monospaced():
    assert widget_for(Schema.of(Wide).get("blob")).option("mono")


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("kind", "badge"),
        ("ratio", "number"),
        ("on", "date"),
        ("at", "date"),
        ("blob", "text"),
    ],
)
def test_the_remaining_formats(name, kind):
    assert format_for(Schema.of(Wide).get(name)).kind == kind


def test_a_plain_text_column_needs_no_format():
    assert format_for(Schema.of(Post).get("title")) is None


def test_prose_is_truncated_when_it_is_shown():
    assert format_for(Schema.of(Post).get("body")).option("truncate") == 80


def test_a_managed_timestamp_reads_as_relative():
    assert format_for(Schema.of(Post).get("created_at")).option("style") == "relative"


def test_an_ordinary_timestamp_reads_in_full():
    assert format_for(Schema.of(Post).get("published_at")).option("style") == "datetime"


def test_a_json_column_gets_a_json_format():
    assert format_for(Schema.of(Post).get("meta")).kind == "json"


def test_a_uuid_key_is_monospaced():
    assert format_for(Schema.of(Wide).get("id")).option("mono")


def test_a_wide_model_derives_a_usable_list():
    screen = derive_list(Schema.of(Wide))
    assert screen.link_column is not None
    assert screen.sort


def test_enum_columns_become_choice_filters():
    assert "kind" in derive_list(Schema.of(Wide)).filter_map


def test_a_nullable_choice_is_clearable():
    from warder.schema import ModelField

    field = ModelField(name="x", kind="text", choices=(("a", "A"),), null=True)
    assert widget_for(field).option("clearable")


def test_a_computed_column_may_name_a_column_to_sort_by():
    # The check for "computed, so nothing to sort by" fired on exactly the
    # declaration that answers it, because sort_field resolves to the named
    # column while the column's own name is still None.
    screen = List(Column.compute("Read", lambda row: 1, sort="words"))
    assert check(Resource(Post, list=screen)) == []


def test_a_computed_column_without_a_sort_is_not_an_error():
    screen = List(Column.compute("Read", lambda row: 1))
    assert check(Resource(Post, list=screen)) == []
    assert screen.columns[0].sort_field is None


# A declared form gets the same inference a derived one does. Otherwise
# Field("published_at") renders as a text box inside a Section you wrote and as
# a date picker when the form was derived — the same declaration behaving
# differently depending on how much of the screen you spelled out.


def test_a_declared_field_gets_a_widget_from_its_column():
    bound = bind(Resource(Post, form=Form(Section("", Field("published_at")))))
    assert bound.form.fields[0].widget.kind == "datetime"


def test_a_named_widget_always_wins():
    from warder import Widget

    form = Form(Section("", Field("published_at", widget=Widget.text())))
    assert bind(Resource(Post, form=form)).form.fields[0].widget.kind == "text"


def test_required_is_read_off_the_column():
    bound = bind(Resource(Post, form=Form(Section("", Field("title"), Field("body")))))
    required = {field.name: field.required for field in bound.form.fields}
    assert required == {"title": True, "body": False}


def test_an_explicit_required_wins():
    form = Form(Section("", Field("title", required=False)))
    assert bind(Resource(Post, form=form)).form.fields[0].required is False


def test_a_column_description_becomes_the_help_text():
    bound = bind(Resource(Post, form=Form(Section("", Field("title")))))
    assert bound.form.fields[0].help == "The headline"


def test_declared_help_wins_over_the_column():
    form = Form(Section("", Field("title", help="Ours")))
    assert bind(Resource(Post, form=form)).form.fields[0].help == "Ours"


def test_dressing_keeps_the_sections_and_their_settings():
    form = Form(
        Section("Content", Field("title")),
        Section("Audit", Field("published_at"), collapsed=True),
        submit="Publish",
        width="wide",
    )
    dressed = bind(Resource(Post, form=form)).form
    assert [s.title for s in dressed.sections] == ["Content", "Audit"]
    assert dressed.sections[1].collapsed
    assert dressed.submit == "Publish"
    assert dressed.width == "wide"


def test_dressing_leaves_an_unresolvable_field_alone():
    # The error should be about the reference, not about a widget nobody asked
    # for; `check` is what reports it.
    from warder.resolve import dress

    form = dress(Form(Section("", Field("nope"))), Schema.of(Post))
    assert form.fields[0].widget is None
