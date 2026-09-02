"""``warder check`` and ``warder permissions``.

The point of the CLI is that a broken column reference fails in CI rather than
in production, so what matters here is the exit status as much as the output.
"""

from __future__ import annotations

import pytest

from warder.console import main


def test_a_clean_admin_passes(capsys):
    assert main(["check", "demo_admin:admin"]) == 0
    assert "Every reference resolves." in capsys.readouterr().out


def test_the_summary_counts_what_is_registered(capsys):
    main(["check", "demo_admin:admin"])
    assert "2 resources, 0 pages" in capsys.readouterr().out


def test_a_broken_reference_fails(capsys):
    assert main(["check", "demo_admin:broken"]) == 1
    assert "is not a field of Post" in capsys.readouterr().err


def test_a_broken_reference_reports_where_it_was_written(capsys):
    main(["check", "demo_admin:broken"])
    assert "Declared at" in capsys.readouterr().err


def test_only_the_first_problem_is_shown_by_default(capsys):
    assert main(["check", "demo_admin:declaration_problems"]) == 1
    err = capsys.readouterr().err
    assert "1 more; pass --all to see them." in err


def test_all_shows_every_problem(capsys):
    assert main(["check", "demo_admin:declaration_problems", "--all"]) == 1
    err = capsys.readouterr().err
    assert "two columns keyed 'title'" in err
    assert "totals 'nope'" in err
    assert "pass --all" not in err


def test_permissions_are_printed(capsys):
    assert main(["permissions", "demo_admin:admin"]) == 0
    printed = capsys.readouterr().out.split()
    assert "post.view" in printed
    assert "author.delete" in printed


def test_a_target_without_an_attribute_is_explained(capsys):
    assert main(["check", "demo_admin"]) == 2
    assert "Write module:attribute" in capsys.readouterr().err


def test_a_module_that_will_not_import_is_reported(capsys):
    assert main(["check", "nosuchmodule:admin"]) == 2
    assert "Cannot import 'nosuchmodule'" in capsys.readouterr().err


def test_a_missing_attribute_is_reported(capsys):
    assert main(["check", "demo_admin:missing"]) == 2
    assert "has no attribute 'missing'" in capsys.readouterr().err


def test_something_that_is_not_an_admin_is_reported(capsys):
    assert main(["check", "demo_admin:not_an_admin"]) == 2
    assert "is a int, not an Admin" in capsys.readouterr().err


def test_no_command_prints_the_help(capsys):
    assert main([]) == 0
    assert "Check and inspect a Warder admin." in capsys.readouterr().out


def test_version_is_reported(capsys):
    from warder import __version__

    with pytest.raises(SystemExit) as exit_:
        main(["--version"])
    assert exit_.value.code == 0
    assert __version__ in capsys.readouterr().out
