"""``warder`` — checking an admin, and creating the account that opens it.

Four commands, and all four work against a ``module:attribute`` target — the
same spelling ASGI servers use.

``warder check app.admin:admin``
    Resolve every declaration against its models, exactly as ``mount()`` does,
    and exit non-zero on the first problem. No server, no port, no database:
    a misspelled column fails in CI rather than in production.

``warder create-admin app.admin:admin``
    The account you sign in with. Prompts for anything you do not pass, refuses
    a blank or duplicated one, and hashes through ``sillo.hashing`` — the
    password is never printed, echoed or stored.

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
    create.set_defaults(run=_create_admin)

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

    email = (args.email or _ask("Email: ")).strip()
    if not email:
        print("An email address is required.", file=sys.stderr)
        return 1
    username = (args.username or email.split("@")[0]).strip()

    if await users.filter(email=email).exists():
        print(f"{email} already has an account.", file=sys.stderr)
        return 1
    if await users.filter(username=username).exists():
        print(f"The username {username!r} is taken.", file=sys.stderr)
        return 1

    password = args.password or _ask_secret()
    if password is None:
        return 1

    user = users(
        email=email,
        username=username,
        is_active=True,
        is_staff=True,
        is_superuser=not args.staff,
    )
    if args.name and "name" in users._meta.fields_map:
        user.name = args.name
    user.set_password(password)
    await user.save()

    role = "staff" if args.staff else "superuser"
    print(f"Created {role} {email} (username {username}).")
    print(f"Sign in at {admin.prefix}/login")
    return 0


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


def _ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ""


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
