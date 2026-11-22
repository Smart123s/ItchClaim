# The MIT License (MIT)
#
# Copyright (c) 2022-2026 Péter Tombor.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

import pytest
import ItchClaim.ItchGame  # Ensures SQLAlchemy declarative mappers (ItchGame & ItchSale) are registered
from ItchClaim.database import _engines


@pytest.fixture(autouse=True)
def clean_engine_cache():
    """Ensure engine cache is cleared between tests to prevent file locking or state leakage."""
    _engines.clear()
    yield
    for engine in list(_engines.values()):
        try:
            engine.dispose()
        except Exception:
            pass
    _engines.clear()


@pytest.fixture
def temp_db_path(tmp_path):
    """Provides a fresh isolated SQLite database path."""
    return str(tmp_path / "test_data.db")
