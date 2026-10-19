# pytest loads this file automatically. Fixtures defined here are available
# to every test in this folder without an import.

import duckdb
import pytest

from sample_data import good_df as build_good_df


@pytest.fixture
def good_df():
    """A fresh valid two-day table for each test."""
    return build_good_df()


@pytest.fixture
def conn(tmp_path):
    """A temporary DuckDB file that is closed when the test finishes.

    tmp_path is a folder pytest creates for this one test and deletes afterward.
    Using it keeps the tests away from data/data.duckdb.
    """
    connection = duckdb.connect(str(tmp_path / "test.duckdb"))
    yield connection
    connection.close()
