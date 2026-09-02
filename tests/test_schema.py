"""Reading a model: what Warder needs from the ORM, and nothing more."""

from __future__ import annotations

import pytest
from orm import Author, Comment, Post, Required, Tag

from warder.schema import ModelField, Schema


def test_a_schema_needs_a_record_model():
    with pytest.raises(TypeError, match=r"is not a sillo\.record model"):
        Schema(type("Plain", (), {}))


def test_schemas_are_cached_per_model():
    assert Schema.of(Post) is Schema.of(Post)


def test_the_cache_can_be_dropped():
    first = Schema.of(Tag)
    Schema.forget(Tag)
    assert Schema.of(Tag) is not first
    Schema.forget()


def test_the_primary_key_is_found():
    assert Schema.of(Post).pk == "id"


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("title", "text"),
        ("slug", "slug"),
        ("body", "longtext"),
        ("words", "integer"),
        ("price", "decimal"),
        ("live", "boolean"),
        ("meta", "json"),
        ("secret", "password"),
        ("published_at", "datetime"),
        ("author", "relation"),
        ("id", "integer"),
    ],
)
def test_kinds_are_read_off_the_column(name, kind):
    assert Schema.of(Post).get(name).kind == kind


def test_a_subclass_of_a_known_field_keeps_its_kind():
    # SlugField subclasses CharField; the MRO walk is what makes that work.
    assert Schema.of(Post).get("slug").kind == "slug"


def test_a_password_field_is_recognised():
    assert Schema.of(Post).get("secret").kind == "password"


def test_a_reverse_relation_is_a_backward_kind():
    assert Schema.of(Author).get("posts").kind == "backward"


def test_relations_resolve_to_classes():
    assert Schema.of(Post).get("author").related is Author


def test_nullability_is_read():
    assert Schema.of(Post).get("body").null
    assert not Schema.of(Post).get("title").null


def test_defaults_are_read():
    status = Schema.of(Post).get("status")
    assert status.has_default
    assert status.default == "draft"


def test_a_column_without_a_default_says_so():
    assert not Schema.of(Post).get("title").has_default


def test_max_length_is_read():
    assert Schema.of(Post).get("title").max_length == 200


def test_a_description_is_carried():
    assert Schema.of(Post).get("title").description == "The headline"


def test_uniqueness_is_read():
    assert Schema.of(Author).get("email").unique


def test_the_generated_key_is_not_editable():
    assert not Schema.of(Post).get("id").editable


def test_the_managed_timestamps_are_not_editable():
    for name in ("created_at", "updated_at", "deleted_at"):
        assert not Schema.of(Post).get(name).editable


def test_a_foreign_keys_shadow_column_is_marked():
    # `author` and `author_id` are both real; a form offering both offers two
    # ways to write one value, and they disagree.
    assert Schema.of(Post).get("author_id").shadow
    assert not Schema.of(Post).get("author").shadow


def test_shadows_are_not_editable():
    assert not Schema.of(Post).get("author_id").editable


def test_shadows_are_listed():
    assert Schema.of(Post).shadows == ("author_id",)


def test_editable_is_what_a_form_may_write():
    names = [f.name for f in Schema.of(Post).editable]
    assert names == [
        "title",
        "slug",
        "body",
        "status",
        "words",
        "price",
        "live",
        "meta",
        "secret",
        "published_at",
        "author",
    ]


def test_relations_are_listed():
    assert "author" in Schema.of(Post).relations


def test_has_and_get():
    schema = Schema.of(Post)
    assert schema.has("title")
    assert not schema.has("titel")
    assert schema.get("titel") is None


def test_names_are_available_for_a_suggestion():
    assert "title" in Schema.of(Post).names


def test_resolve_follows_a_traversal():
    assert Schema.of(Post).resolve("author__email").name == "email"


def test_resolve_follows_two_hops():
    assert Schema.of(Comment).resolve("post__author__email").name == "email"


def test_resolve_returns_none_for_a_missing_field():
    assert Schema.of(Post).resolve("titel") is None


def test_resolve_returns_none_for_a_missing_far_field():
    assert Schema.of(Post).resolve("author__nope") is None


def test_resolve_finds_a_plain_field():
    assert Schema.of(Post).resolve("title").name == "title"


def test_a_required_column_with_no_default_cannot_be_left_blank():
    assert not Schema.of(Required).get("code").writable_when_blank


def test_a_nullable_column_can():
    assert Schema.of(Post).get("body").writable_when_blank


def test_a_defaulted_column_can():
    assert Schema.of(Post).get("status").writable_when_blank


def test_an_unresolved_relation_is_not_a_missing_one():
    field = ModelField(name="owner", kind="relation", related=None)
    assert field.unresolved
    assert field.relational


def test_a_resolved_relation_is_not_unresolved():
    assert not Schema.of(Post).get("author").unresolved


def test_repr_counts_the_fields():
    assert repr(Schema.of(Tag)).startswith("Schema(Tag, ")
