"""The two kinds of wrong, and how they read."""

from __future__ import annotations

import pytest

from warder.errors import ActionFailed, DeclarationError, Denied, WarderError


def test_a_declaration_error_leads_with_what_is_wrong():
    error = DeclarationError("column 'titel' is not a field of Post.")
    assert str(error) == "column 'titel' is not a field of Post."


def test_a_near_miss_becomes_a_suggestion():
    error = DeclarationError("Bad column.", got="titel", options=["title", "body"])
    assert "Did you mean 'title'?" in str(error)


def test_a_distant_miss_lists_the_options_when_there_are_few():
    error = DeclarationError("Bad column.", got="zzzz", options=["title", "body"])
    assert "Available: 'body', 'title'" in str(error)


def test_a_long_option_list_is_not_dumped():
    error = DeclarationError("Bad.", got="zzz", options=[f"f{n}" for n in range(20)])
    assert "Available" not in str(error)


def test_no_suggestion_without_something_to_compare():
    assert DeclarationError("Bad.", options=["title"]).hint is None


def test_an_explicit_hint_wins_over_a_suggestion():
    error = DeclarationError("Bad.", hint="Try harder.", got="titel", options=["title"])
    assert "Try harder." in str(error)
    assert "Did you mean" not in str(error)


def test_the_location_is_the_last_line():
    error = DeclarationError("Bad.", where="app/admin.py:24")
    assert str(error).endswith("Declared at app/admin.py:24")


def test_all_three_parts_together():
    error = DeclarationError(
        "Resource(Post).list column 'titel' is not a field of Post.",
        got="titel",
        options=["title"],
        where="app/admin.py:24",
    )
    assert str(error).splitlines() == [
        "Resource(Post).list column 'titel' is not a field of Post.",
        "  Did you mean 'title'?",
        "  Declared at app/admin.py:24",
    ]


def test_denied_defaults_to_forbidden():
    denied = Denied()
    assert denied.status == 403
    assert str(denied) == "Forbidden"


def test_denied_can_say_who_are_you_instead():
    # 401 is only correct when nobody is signed in; sending it to a signed-in
    # user starts a login loop.
    assert Denied("Sign in", status=401).status == 401


def test_an_action_can_stop_itself_with_a_message():
    failure = ActionFailed("Nothing to publish.")
    assert failure.status == 400
    assert str(failure) == "Nothing to publish."


def test_everything_shares_one_base():
    for error in (DeclarationError("x"), Denied(), ActionFailed("x")):
        assert isinstance(error, WarderError)


def test_the_base_can_be_caught_alone():
    with pytest.raises(WarderError):
        raise Denied()
