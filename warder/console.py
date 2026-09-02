"""``warder`` — checking an admin, and creating the account that opens it.

Four commands, and all four work against a ``module:attribute`` target — the
same spelling ASGI servers use.

``warder check app.admin:admin``
    Resolve every declaration against its models, exactly as ``mount()`` does,
    and exit non-zero on the first problem. No server, no port, no database:
    a misspelled column fails in CI rather than in production.

``warder create-admin app.admin:admin``
    The account you sign in with. Prompts for anything you do not pass — but
    only at a terminal, so a script gets an error rather than a hang. It writes
    the column the *sign-in form* asks for, sets only the flags the model
    actually has, and hashes through ``sillo.hashing``: the password is never
    printed, echoed or stored. ``--set column=value`` fills in anything your own
    user model requires that Warder cannot know about.

``warder users app.admin:admin``
    Who can already sign in, and when they last did.

``warder permissions app.admin:admin``
    What the site declares. Derived from what is registered, so it is how you
    seed a fixtures file or write a role against what exists rather than what
    you remember.

``warder routes app.admin:admin``
    Every URL the admin serves, so you can see what mounting it added.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import importlib
import sys
import typing

from warder import __version__
from warder.errors import DeclarationError

__all__ = ["main"]


def main(argv: typing.Sequence[str] | None = None) -> int:
    """Run the CLI. Returns the exit status rather than calling ``sys.exit``."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return typing.cast(int, args.run(args))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warder", description="Check, inspect and open a Warder admin."
    )
    parser.add_argument("--version", action="version", version=f"warder {__version__}")
    commands = parser.add_subparsers(dest="command")

    def target(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
        sub.add_argument("target", help="module:attribute, e.g. app.admin:admin")
        return sub

    check = target(
        commands.add_parser(
            "check", help="Resolve every declaration against its models."
        )
    )
    check.add_argument(
        "--all",
        action="store_true",
        help="Report every problem rather than stopping at the first.",
    )
    check.set_defaults(run=_check)

    target(
        commands.add_parser(
            "permissions", help="Print the permissions this site declares."
        )
    ).set_defaults(run=_permissions)

    target(
        commands.add_parser("routes", help="Print every URL the admin serves.")
    ).set_defaults(run=_routes)

    create = target(
        commands.add_parser(
            "create-admin", help="Create an account that can sign in to the admin."
        )
    )
    create.add_argument("--email", help="Email address. Prompted for if omitted.")
    create.add_argument(
        "--username", help="Username. Defaults to the email's local part."
    )
    create.add_argument("--name", help="Display name.")
    create.add_argument(
        "--password",
        help="Prompted for, twice and without echo, if omitted. Passing it here "
        "puts it in your shell history.",
    )
    create.add_argument(
        "--staff",
        action="store_true",
        help="Create a staff account rather than a superuser.",
    )
    create.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="COLUMN=VALUE",
        help="Set another column on the new row. Repeatable. For a user model "
        "of your own that requires something Warder cannot know about.",
    )
    create.set_defaults(run=_create_admin)

    target(
        commands.add_parser(
            "users", help="List the accounts that can sign in to the admin."
        )
    ).set_defaults(run=_users)

    return parser


# ------------------------------------------------------------------ commands


def _check(args: argparse.Namespace) -> int:
    admin = _load(args.target)
    if admin is None:
        return 2

    problems = list(admin.check())
    if not problems:
        try:
            admin.bind()
        except DeclarationError as failure:
            problems = [failure]

    if not problems:
        print(
            f"{admin.title}: {len(admin.resources)} resources, "
            f"{len(admin.pages)} pages, {len(admin.permissions)} permissions. "
            "Every reference resolves."
        )
        return 0

    shown = problems if args.all else problems[:1]
    for problem in shown:
        print(problem, file=sys.stderr)
        print(file=sys.stderr)
    remaining = len(problems) - len(shown)
    if remaining > 0:
        print(f"{remaining} more; pass --all to see them.", file=sys.stderr)
    return 1


def _permissions(args: argparse.Namespace) -> int:
    admin = _load(args.target)
    if admin is None:
        return 2
    for name in admin.permissions:
        print(name)
    return 0


def _routes(args: argparse.Namespace) -> int:
    admin = _load(args.target)
    if admin is None:
        return 2
    try:
        admin.bind()
    except DeclarationError as failure:
        print(failure, file=sys.stderr)
        return 1
    from warder.routes import routes as build_routes

    for route in build_routes(admin):
        methods = ",".join(sorted(route.methods or ["GET"]))
        print(f"{methods:22} {route.raw_path:44} {route.name or ''}")
    return 0


def _create_admin(args: argparse.Namespace) -> int:
    admin = _load(args.target)
    if admin is None:
        return 2
    try:
        return asyncio.run(_create(admin, args))
    except KeyboardInterrupt:  # pragma: no cover - interactive
        print("\nCancelled.", file=sys.stderr)
        return 130


def _users(args: argparse.Namespace) -> int:
    admin = _load(args.target)
    if admin is None:
        return 2
    return asyncio.run(_show_users(admin))


async def _create(admin: typing.Any, args: argparse.Namespace) -> int:
    manager = await _database(admin)
    if manager is None:
        return 2
    try:
        return await _write(admin, args)
    finally:
        # `aiosqlite`'s worker thread is not a daemon, so a command that leaves
        # the connection open prints its result and then never exits.
        await _close(manager)


async def _write(admin: typing.Any, args: argparse.Namespace) -> int:
    users = admin.auth.resolve().users

    unregistered = _unregistered(users)
    if unregistered is not None:
        print(unregistered, file=sys.stderr)
        return 1

    # The column the sign-in form asks for is the column this writes. They have
    # to be the same one, or the account is created and cannot sign in.
    identity = admin.auth.login.field
    columns = set(typing.cast(typing.Any, users)._meta.fields_map)
    unusable = _unusable(users, identity, columns)
    if unusable is not None:
        print(unusable, file=sys.stderr)
        return 1

    # Prompting is for a person at a terminal. Piped into a script or run in
    # CI there is nobody to answer, and a command that waits forever for an
    # answer that will never come is worse than one that says what it needs.
    asking = _interactive()
    label = identity.replace("_", " ")

    value = (args.email or (_ask(f"{label.capitalize()}: ") if asking else "")).strip()
    if not value:
        print(
            f"A{'n' if label[0] in 'aeiou' else ''} {label} is required."
            + ("" if asking else " Pass --email."),
            file=sys.stderr,
        )
        return 1
    if identity == "email" and "@" not in value:
        print(f"{value!r} does not look like an email address.", file=sys.stderr)
        return 1

    fields: dict[str, typing.Any] = {identity: value}
    username = None
    if "username" in columns and identity != "username":
        derived = value.split("@")[0]
        username = (
            args.username or (_ask_default("Username", derived) if asking else derived)
        ).strip()
        fields["username"] = username

    try:
        if await users.filter(**{identity: value}).exists():
            print(f"{value} already has an account.", file=sys.stderr)
            return 1
        if username and await users.filter(username=username).exists():
            print(f"The username {username!r} is taken.", file=sys.stderr)
            return 1
    except Exception as unreachable:
        missing = _missing_table(users, unreachable)
        if missing is None:
            raise
        print(missing, file=sys.stderr)
        return 1

    password = args.password or (_ask_secret() if asking else None)
    if password is None:
        if not asking:
            print(
                "A password is required. Pass --password, or run this in a "
                "terminal to be prompted for one without echo.",
                file=sys.stderr,
            )
        return 1

    # Only what this model actually has. Somebody's own user model may have no
    # `is_superuser`, and setting an attribute the table does not have fails at
    # the insert with a message about SQL.
    for name, given in (
        ("is_active", True),
        ("is_staff", True),
        ("is_superuser", not args.staff),
        ("name", args.name),
    ):
        if name in columns and given is not None:
            fields[name] = given

    extra, bad = _extra(args)
    if bad is not None:
        print(bad, file=sys.stderr)
        return 1
    fields.update(extra)

    unmet = _unmet(users, fields)
    if unmet is not None:
        print(unmet, file=sys.stderr)
        return 1

    user = users(**fields)
    user.set_password(password)
    await user.save()

    role = "staff account" if args.staff else "superuser"
    named = f" (username {username})" if username else ""
    print(f"Created {role} {value}{named}.")
    if "is_staff" not in columns:
        print(
            f"  Note: {users.__name__} has no is_staff column, so the default "
            "Gate.staff() will admit nobody. Use a different gate.",
            file=sys.stderr,
        )
    print(f"Sign in at {admin.prefix}/login")
    return 0


def _extra(args: argparse.Namespace) -> tuple[dict[str, typing.Any], str | None]:
    """The ``--set column=value`` pairs, or a message about a malformed one."""
    values: dict[str, typing.Any] = {}
    for pair in getattr(args, "set", []) or []:
        name, sep, value = str(pair).partition("=")
        if not sep or not name.strip():
            return {}, f"--set takes column=value, got {pair!r}."
        values[name.strip()] = value
    return values, None


def _unmet(users: type, fields: typing.Mapping[str, typing.Any]) -> str | None:
    """A message naming columns this row needs and does not have, else ``None``.

    Somebody's own user model may require a tenant, a display name or an email
    even when sign-in is by username. Without this the insert fails on a
    validation error naming a column the command never mentioned.
    """
    meta = typing.cast(typing.Any, users)._meta
    missing = [
        name
        for name, column in meta.fields_map.items()
        if _needs_a_value(name, column, fields)
    ]
    if not missing:
        return None
    pairs = " ".join(f"--set {name}=..." for name in missing)
    return (
        f"{users.__name__} also needs {', '.join(repr(n) for n in missing)}, "
        "which this command does not know how to fill in.\n\n"
        f"  Pass them:\n\n      {pairs}"
    )


def _needs_a_value(
    name: str, column: typing.Any, fields: typing.Mapping[str, typing.Any]
) -> bool:
    """Whether this column will be empty and the database will mind.

    Everything the ORM fills in for itself is excluded — the key, the
    ``auto_now`` timestamps, anything with a default — because listing those
    would send somebody to pass a value the ORM is about to overwrite.
    """
    if name in fields or name == "password":
        return False
    if getattr(column, "null", False) or getattr(column, "generated", False):
        return False
    if getattr(column, "pk", False) or getattr(column, "primary_key", False):
        return False
    if getattr(column, "auto_now", False) or getattr(column, "auto_now_add", False):
        return False
    if getattr(column, "default", None) is not None:
        return False
    if getattr(column, "related_model", None) is not None:
        return False
    return bool(getattr(column, "required", False))


def _unusable(users: type, identity: str, columns: set[str]) -> str | None:
    """A message when this model cannot back a sign-in, else ``None``.

    Two things are genuinely required: the column the login form asks for, and
    a way to hash a password. Everything else is optional and simply not set.
    """
    if identity not in columns:
        usable = ", ".join(sorted(name for name in columns if not name.startswith("_")))
        return (
            f"{users.__name__} has no {identity!r} column, but the sign-in form "
            f"asks for one.\n\n"
            f"  Either point the form at a column this model has:\n\n"
            f"      Auth(users={users.__name__}, login=Login(field='username'))\n\n"
            f"  Its columns are: {usable}"
        )
    if not callable(getattr(users, "set_password", None)):
        return (
            f"{users.__name__} cannot hash a password.\n\n"
            "  A user model for the admin has to subclass "
            "sillo.users.UserBaseModel,\n"
            "  which is where set_password and check_password come from."
        )
    return None


async def _show_users(admin: typing.Any) -> int:
    users = admin.auth.resolve().users
    manager = await _database(admin)
    if manager is None:
        return 2
    try:
        unregistered = _unregistered(users)
        if unregistered is not None:
            print(unregistered, file=sys.stderr)
            return 1
        try:
            rows = await users.all().limit(200)
        except Exception as unreachable:
            missing = _missing_table(users, unreachable)
            if missing is None:
                raise
            print(missing, file=sys.stderr)
            return 1
        if not rows:
            print("No accounts yet. Create one with: warder create-admin <target>")
            return 0
        print(f"{'EMAIL':34} {'USERNAME':20} {'ROLE':11} {'ACTIVE':7} LAST SIGN-IN")
        for row in rows:
            role = (
                "superuser"
                if getattr(row, "is_superuser", False)
                else "staff"
                if getattr(row, "is_staff", False)
                else "-"
            )
            seen = getattr(row, "last_login", None)
            print(
                f"{getattr(row, 'email', '')!s:34} "
                f"{getattr(row, 'username', '')!s:20} "
                f"{role:11} "
                f"{('yes' if getattr(row, 'is_active', True) else 'no'):7} "
                f"{seen.strftime('%Y-%m-%d %H:%M') if seen else 'never'}"
            )
        return 0
    finally:
        await _close(manager)


def _unregistered(users: type) -> str | None:
    """A message when the user model is not registered with the ORM, else None.

    This is the mistake everybody makes once, and Tortoise's own answer to it —
    ``default_connection for the model ... cannot be None`` — says nothing
    about what to do. Warder ships its models but does not register them:
    model discovery scans a module's namespace, so importing them would put
    ``warder_users`` into the database of every project that installed the
    package.
    """
    meta = getattr(users, "_meta", None)
    if meta is None:
        return f"{users.__name__} is not a sillo.record model."
    try:
        if meta.db is not None:
            return None
    except Exception:
        pass
    module = users.__module__
    return (
        f"{users.__name__} is not registered with the database.\n\n"
        f"  Add {module!r} to the model modules:\n\n"
        f"      setup_record(app, config, model_modules=[..., {module!r}])\n\n"
        "  Warder ships its user model but does not register it for you: model\n"
        "  discovery scans a module's namespace, so importing it would create\n"
        "  warder_users in the database of every project that installs Warder."
    )


def _missing_table(users: type, error: Exception) -> str | None:
    """A message when the table does not exist yet, else None."""
    text = str(error).lower()
    if "no such table" not in text and "does not exist" not in text:
        return None
    table = getattr(getattr(users, "_meta", None), "db_table", users.__name__.lower())
    module = users.__module__
    return (
        f"The table {table!r} does not exist yet.\n\n"
        "  This project builds its schema from migrations rather than on\n"
        "  start-up, so the table has to be migrated in:\n\n"
        f"      sillo record make add_{table}\n"
        "      sillo record migrate\n\n"
        f"  Make sure {module!r} is in the model modules first, or the\n"
        "  migration will not include it."
    )


async def _close(manager: typing.Any) -> None:
    shutdown = getattr(manager, "shutdown", None)
    if shutdown is not None:
        try:
            await shutdown()
            return
        except Exception:  # pragma: no cover - falls through to the ORM
            pass
    from tortoise import Tortoise

    with contextlib.suppress(Exception):
        await Tortoise.close_connections()


# ------------------------------------------------------------------ plumbing


def _interactive() -> bool:
    """Whether there is a person at a terminal to answer a question."""
    try:
        return bool(sys.stdin.isatty())
    except (AttributeError, ValueError):  # pragma: no cover - detached stdin
        return False


def _ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ""


def _ask_default(prompt: str, fallback: str) -> str:
    """Ask, showing the default, and take the default on an empty answer."""
    return _ask(f"{prompt} [{fallback}]: ").strip() or fallback


def _ask_secret() -> str | None:
    """Read a password twice, without echo.

    Twice because a typo in a password you cannot see locks you out of the
    thing you just created, and the fix is a database edit.
    """
    for _ in range(3):
        first = getpass.getpass("Password: ")
        if not first:
            print("A password is required.", file=sys.stderr)
            continue
        if first != getpass.getpass("Password again: "):
            print("They did not match. Try again.", file=sys.stderr)
            continue
        return first
    return None


async def _database(admin: typing.Any) -> typing.Any:
    """Open the connection the admin's own application configured.

    Rather than asking for a database URL: the application already knows one,
    and a second copy in a shell argument is a second thing to get wrong.
    """
    app = getattr(admin, "mounted", None)
    manager = None
    if app is not None:
        try:
            manager = app.state["record"]
        except (KeyError, TypeError, AttributeError):
            manager = None
    if manager is None:
        print(
            "Could not find the database. The admin has to be mounted on an "
            "application configured with setup_record() for this command to "
            "know where to write.",
            file=sys.stderr,
        )
        return None
    await manager.init()
    return manager


def _load(target: str) -> typing.Any:
    """Import ``module:attribute``, reporting rather than raising.

    A traceback is the right answer for a bug in the admin module and the wrong
    one for a mistyped target, so the two are told apart here.
    """
    module_name, _, attribute = target.partition(":")
    if not attribute:
        print(
            f"{target!r} is not a target. Write module:attribute — "
            "for example app.admin:admin.",
            file=sys.stderr,
        )
        return None
    sys.path.insert(0, "")
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        print(f"Cannot import {module_name!r}: {error}", file=sys.stderr)
        return None
    admin = getattr(module, attribute, None)
    if admin is None:
        print(f"{module_name!r} has no attribute {attribute!r}.", file=sys.stderr)
        return None
    if not hasattr(admin, "check") or not hasattr(admin, "resources"):
        print(f"{target} is a {type(admin).__name__}, not an Admin.", file=sys.stderr)
        return None
    return admin


if __name__ == "__main__":  # pragma: no cover - exercised through the console script
    raise SystemExit(main())
