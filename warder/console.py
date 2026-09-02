"""``warder`` — checking an admin without starting the application.

Two commands, and both of them do something today.

``warder check app.admin:admin``
    Import an admin and resolve every declaration against its models, exactly
    as ``mount()`` would. It exits non-zero on the first problem, so a broken
    column reference fails in CI rather than in production, and it needs no
    server, no port and no database connection — only the models importable.

``warder permissions app.admin:admin``
    Print the permissions the site declares. What a deployment can grant is
    derived from what is registered, and this is how you read it: to seed a
    fixtures file, to write a role, or to see what a new resource added.

Both take a ``module:attribute`` target, the same spelling ASGI servers use.
"""

from __future__ import annotations

import argparse
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
        prog="warder", description="Check and inspect a Warder admin."
    )
    parser.add_argument("--version", action="version", version=f"warder {__version__}")
    commands = parser.add_subparsers(dest="command")

    check = commands.add_parser(
        "check", help="Resolve every declaration against its models."
    )
    check.add_argument("target", help="module:attribute, e.g. app.admin:admin")
    check.add_argument(
        "--all",
        action="store_true",
        help="Report every problem rather than stopping at the first.",
    )
    check.set_defaults(run=_check)

    permissions = commands.add_parser(
        "permissions", help="Print the permissions this site declares."
    )
    permissions.add_argument("target", help="module:attribute, e.g. app.admin:admin")
    permissions.set_defaults(run=_permissions)

    return parser


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
