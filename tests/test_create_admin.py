"""``warder create-admin`` and ``warder users``.

The command has to be right about three situations that are not the happy path,
because each of them is a thing somebody will hit on their first afternoon and
each has a database error that says nothing useful on its own:

* the user model is not registered with the ORM;
* the table has not been migrated in;
* nobody is at a terminal to answer a prompt.
"""

from __future__ import annotations

import argparse

import pytest
from orm import Author, Person
from tortoise import Tortoise

from warder import Admin, Auth, Gate
from warder.console import _missing_table, _unregistered, _write
from warder.models import AdminUser


@pytest.fixture
async def database():
    await Tortoise.init(
        db_url="sqlite://:memory:", modules={"models": ["orm", "warder.models"]}
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


def options(**overrides) -> argparse.Namespace:
    """The parsed arguments, with everything the command reads defaulted."""
    return argparse.Namespace(
        **{
            "email": None,
            "username": None,
            "name": None,
            "password": None,
            "staff": False,
            "set": [],
            **overrides,
        }
    )


def admin(**auth) -> Admin:
    return Admin(title="Ops", auth=Auth(gate=Gate.staff(), **auth))


# ------------------------------------------------------------ the happy path


async def test_it_creates_a_superuser(database, capsys):
    code = await _write(admin(), options(email="ada@acme.com", password="secret123"))
    assert code == 0
    user = await AdminUser.get(email="ada@acme.com")
    assert user.is_superuser and user.is_staff and user.is_active
    assert "Created superuser" in capsys.readouterr().out


async def test_the_username_is_derived_from_the_email(database):
    await _write(admin(), options(email="ada@acme.com", password="secret123"))
    assert (await AdminUser.get(email="ada@acme.com")).username == "ada"


async def test_an_explicit_username_wins(database):
    await _write(
        admin(), options(email="ada@acme.com", username="lovelace", password="x1")
    )
    assert (await AdminUser.get(email="ada@acme.com")).username == "lovelace"


async def test_staff_creates_a_non_superuser(database):
    await _write(admin(), options(email="bob@acme.com", password="x1", staff=True))
    user = await AdminUser.get(email="bob@acme.com")
    assert user.is_staff and not user.is_superuser


async def test_the_password_is_hashed_never_stored(database):
    await _write(admin(), options(email="ada@acme.com", password="secret123"))
    user = await AdminUser.get(email="ada@acme.com")
    assert user.password != "secret123"
    assert user.check_password("secret123")


async def test_the_name_is_set_when_the_model_has_one(database):
    await _write(
        admin(), options(email="ada@acme.com", password="x1", name="Ada Lovelace")
    )
    assert (await AdminUser.get(email="ada@acme.com")).name == "Ada Lovelace"


async def test_it_can_write_to_your_own_user_model(database):
    # Auth(users=...) is the whole point: the command writes wherever the admin
    # authenticates from.
    code = await _write(admin(users=Person), options(email="x@y.z", password="x1"))
    assert code == 0
    user = await Person.get(email="x@y.z")
    assert user.is_staff and user.check_password("x1")


async def test_a_model_that_cannot_hash_a_password_is_refused(database, capsys):
    # Author is an ordinary model, not a user model.
    code = await _write(admin(users=Author), options(email="x@y.z", password="x1"))
    assert code == 1
    assert "cannot hash a password" in capsys.readouterr().err
    assert not await Author.filter(email="x@y.z").exists()


async def test_a_model_without_the_login_column_is_refused(database, capsys):
    from warder import Login

    code = await _write(
        admin(users=Person, login=Login(field="staff_number")),
        options(email="1234", password="x1"),
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "has no 'staff_number' column" in err
    assert "Its columns are:" in err


async def test_the_login_column_is_the_column_it_writes(database):
    # They have to be the same one, or the account is created and cannot sign
    # in with it.
    from warder import Login

    code = await _write(
        admin(users=Person, login=Login(field="username")),
        options(email="ada", password="x1", set=["email=ada@acme.com"]),
    )
    assert code == 0
    assert await Person.filter(username="ada").exists()


async def test_a_column_this_model_needs_is_named(database, capsys):
    # Somebody's own user model may require an email even when sign-in is by
    # username. Without this the insert fails on a validation error naming a
    # column the command never mentioned.
    from warder import Login

    code = await _write(
        admin(users=Person, login=Login(field="username")),
        options(email="ada", password="x1"),
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "also needs 'email'" in err
    assert "--set email=..." in err


async def test_set_takes_column_equals_value(database):
    await _write(
        admin(users=Person),
        options(email="a@b.c", password="x1", set=["display=Ada L"]),
    )
    assert (await Person.get(email="a@b.c")).display == "Ada L"


async def test_a_malformed_set_is_refused(database, capsys):
    code = await _write(
        admin(), options(email="a@b.c", password="x1", set=["nonsense"])
    )
    assert code == 1
    assert "--set takes column=value" in capsys.readouterr().err


async def test_a_model_without_a_staff_flag_is_still_created(database):
    from orm import Sparse

    assert await _write(admin(users=Sparse), options(email="a@b.c", password="x1")) == 0
    assert await Sparse.filter(email="a@b.c").exists()


# ------------------------------------------------------------- what it refuses


async def test_a_duplicate_email_is_refused(database, capsys):
    await _write(admin(), options(email="ada@acme.com", password="x1"))
    code = await _write(admin(), options(email="ada@acme.com", password="x1"))
    assert code == 1
    assert "already has an account" in capsys.readouterr().err


async def test_a_taken_username_is_refused(database, capsys):
    await _write(admin(), options(email="ada@acme.com", password="x1"))
    code = await _write(
        admin(), options(email="other@acme.com", username="ada", password="x1")
    )
    assert code == 1
    assert "is taken" in capsys.readouterr().err


async def test_something_that_is_not_an_email_is_refused(database, capsys):
    code = await _write(admin(), options(email="nope", password="x1"))
    assert code == 1
    assert "does not look like an email address" in capsys.readouterr().err


async def test_no_email_and_no_terminal_says_what_to_pass(database, capsys):
    # Prompting is for a person. In a script there is nobody to answer, and a
    # command that waits forever is worse than one that says what it needs.
    code = await _write(admin(), options(password="x1"))
    assert code == 1
    assert "Pass --email" in capsys.readouterr().err


async def test_no_password_and_no_terminal_says_what_to_pass(database, capsys):
    code = await _write(admin(), options(email="a@b.c"))
    assert code == 1
    assert "Pass --password" in capsys.readouterr().err


async def test_nothing_is_written_when_it_refuses(database):
    await _write(admin(), options(email="a@b.c"))
    assert await AdminUser.all().count() == 0


# --------------------------------------------------------------- diagnostics


def test_an_unregistered_model_is_explained():
    # Tortoise's own answer is "default_connection ... cannot be None", which
    # says nothing about what to do.
    class Loose(AdminUser):
        class Meta:
            table = "loose_users"

    message = _unregistered(Loose)
    assert message is not None
    assert "not registered with the database" in message
    assert "model_modules" in message


def test_a_registered_model_reports_no_problem(database):
    assert _unregistered(AdminUser) is None


def test_something_that_is_not_a_model_is_reported():
    assert "not a sillo.record model" in (_unregistered(type("Plain", (), {})) or "")


def test_a_missing_table_is_recognised():
    message = _missing_table(AdminUser, Exception("no such table: warder_users"))
    assert message is not None
    assert "warder_users" in message
    assert "sillo record migrate" in message


def test_a_missing_table_on_postgres_is_recognised():
    assert _missing_table(AdminUser, Exception('relation "x" does not exist'))


def test_any_other_error_is_not_swallowed():
    # Reporting an unrelated failure as "the table is missing" would send
    # somebody to write a migration for a table that already exists.
    assert _missing_table(AdminUser, Exception("connection refused")) is None


async def test_an_unregistered_model_stops_before_writing(database, capsys):
    class Loose(AdminUser):
        class Meta:
            table = "loose_users_2"

    code = await _write(admin(users=Loose), options(email="a@b.c", password="x1"))
    assert code == 1
    assert "model_modules" in capsys.readouterr().err
