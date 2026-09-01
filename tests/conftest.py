"""Fixtures over the fakes in :mod:`tests.fakes`.

The fakes live in their own module rather than here because an editable
install of the framework puts *its* ``tests`` package on ``sys.path``, and
``from tests.conftest import ...`` then resolves to the wrong project. ``tests/``
has no ``__init__.py``, so pytest puts it on the path and ``from fakes import
Ctx`` finds this one.
"""

from __future__ import annotations

import pytest
from fakes import Ctx, Rows, User


@pytest.fixture
def rows() -> Rows:
    return Rows()


@pytest.fixture
def anyone() -> Ctx:
    return Ctx(User())


@pytest.fixture
def nobody() -> Ctx:
    return Ctx(None)
