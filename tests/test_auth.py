"""Sessions, logins, second factors, impersonation and the audit trail."""

from __future__ import annotations

import pytest
from fakes import Ctx, User, model

from warder._time import parse_duration, parse_rate
from warder.access import Gate, Role
from warder.auth import MFA, Audit, Auth, Impersonation, Login, Session


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("30s", 30),
        ("30m", 1800),
        ("12h", 43200),
        ("7d", 604800),
        ("1w", 604800),
        ("1y", 31_536_000),
        ("1.5h", 5400),
    ],
)
def test_durations(text, seconds):
    assert parse_duration(text) == seconds


def test_a_bare_number_is_already_seconds():
    assert parse_duration(90) == 90.0


def test_no_duration_stays_none():
    assert parse_duration(None) is None


def test_a_compound_duration_is_refused():
    # One unit per value, deliberately: '90m' says the same thing.
    with pytest.raises(ValueError, match="not a duration"):
        parse_duration("1h30m")


def test_an_unknown_unit_is_refused():
    with pytest.raises(ValueError, match="not a duration"):
        parse_duration("3 fortnights")


def test_rates():
    assert parse_rate("5/15m") == (5, 900.0)


def test_no_rate_stays_none():
    assert parse_rate(None) is None


def test_a_malformed_rate_is_refused():
    with pytest.raises(ValueError, match="not a rate"):
        parse_rate("5 per 15m")


# ------------------------------------------------------------------- Session


def test_session_lifetimes_are_parsed():
    session = Session(idle="30m", absolute="12h")
    assert (session.idle, session.absolute) == (1800.0, 43200.0)


def test_lifetimes_can_be_switched_off():
    assert Session(idle=None, absolute=None).idle is None


def test_a_concurrent_cap_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        Session(concurrent=0)


def test_same_site_is_checked():
    with pytest.raises(ValueError, match="'lax', 'strict', 'none'"):
        Session(same_site="always")


def test_session_defaults_are_conservative():
    session = Session()
    assert session.secure
    assert session.revoke_on_password_change


# --------------------------------------------------------------------- Login


def test_login_throttling_is_parsed():
    login = Login(throttle="5/15m")
    assert (login.attempts, login.window) == (5, 900.0)


def test_throttling_can_be_switched_off():
    assert Login(throttle=None).attempts is None


def test_remember_may_be_a_duration():
    assert Login(remember="30d").remember == 2_592_000.0


def test_remember_may_be_a_flag():
    assert Login(remember=True).remember is True


# ----------------------------------------------------------------------- MFA


def test_totp_is_the_default_method():
    assert MFA.totp().method == "totp"


def test_webauthn_is_offered():
    assert MFA.webauthn().method == "webauthn"


def test_an_unknown_method_is_refused():
    with pytest.raises(ValueError, match="not valid"):
        MFA("sms-please")


def test_recovery_codes_must_be_positive():
    with pytest.raises(ValueError, match="positive integer"):
        MFA.totp(recovery_codes=0)


async def test_mfa_can_be_demanded_of_everyone():
    assert await MFA.totp(required=True).demanded_of(Ctx(User()))


async def test_mfa_is_optional_by_default():
    assert not await MFA.totp().demanded_of(Ctx(User(is_superuser=True)))


async def test_mfa_can_be_demanded_of_a_role_only():
    # Rolling it out to everyone at once is the version switched off on day two.
    mfa = MFA.totp(required=Gate.role("owner"))
    assert await mfa.demanded_of(Ctx(User(groups=["owner"])))
    assert not await mfa.demanded_of(Ctx(User(groups=["support"])))


# ------------------------------------------------------------- Impersonation


def test_impersonation_is_gated_to_superusers_by_default():
    assert Impersonation().gate == Gate.superuser()


def test_impersonation_expires_by_default():
    assert Impersonation().maximum == 3600.0


def test_impersonation_can_be_open_ended():
    assert Impersonation(maximum=None).maximum is None


# --------------------------------------------------------------------- Audit


def test_redaction_matches_a_substring_of_the_field_name():
    audit = Audit(redact=["token"])
    assert audit.redacted({"api_token": "x", "token_hash": "y", "email": "z"}) == {
        "api_token": "[redacted]",
        "token_hash": "[redacted]",
        "email": "z",
    }


def test_redaction_is_case_insensitive():
    assert Audit(redact=["secret"]).redacted({"API_SECRET": "x"}) == {
        "API_SECRET": "[redacted]"
    }


def test_the_default_redactions_cover_the_obvious():
    assert set(Audit().redact) == {"password", "token", "secret", "key"}


def test_retention_is_parsed():
    assert Audit(retain="1y").retain == 31_536_000.0


# ---------------------------------------------------------------------- Auth


def test_auth_defaults_to_staff_only():
    assert Auth().gate == Gate.staff()


def test_auth_brings_a_session_and_a_login_by_default():
    auth = Auth()
    assert isinstance(auth.session, Session)
    assert isinstance(auth.login, Login)


def test_a_user_model_must_be_a_class():
    with pytest.raises(TypeError, match="takes a model class"):
        Auth(users=model("User")())


def test_the_permission_source_is_checked():
    with pytest.raises(ValueError, match="'records', 'none'"):
        Auth(permissions="ldap")


def test_roles_are_indexed_by_name():
    auth = Auth(roles=[Role("support"), Role("editor")])
    assert sorted(auth.role_map) == ["editor", "support"]


def test_grants_follow_inheritance():
    auth = Auth(
        roles=[
            Role("support", grants=["order.view"]),
            Role("editor", grants=["post.add"], inherits=["support"]),
        ]
    )
    assert auth.grants_of("editor") == frozenset({"post.add", "order.view"})


def test_grants_of_an_unknown_role_are_empty():
    assert Auth().grants_of("ghost") == frozenset()


async def test_may_enter_asks_the_gate():
    auth = Auth(gate=Gate.staff())
    assert await auth.may_enter(Ctx(User(is_staff=True)))
    assert not await auth.may_enter(Ctx(User()))


def test_repr_says_whose_users_these_are():
    assert "users=bundled" in repr(Auth())
    assert "users=User" in repr(Auth(users=model("User")))
