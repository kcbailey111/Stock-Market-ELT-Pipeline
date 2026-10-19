# Tests for load_data in pipeline.py.
#
# Each test gets its own temporary DuckDB file, so nothing here touches
# data/data.duckdb or calls the Alpha Vantage API.
#
# The behavior we care about: loading the same day twice does not create a
# second row, and a new day does get added.

import datetime as dt

import pandas as pd

from sample_data import good_row
from pipeline import load_data


def test_first_load_inserts_every_row(conn, good_df):
    """Two new days should both land in the table."""
    load_data(conn, good_df)

    count = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]
    assert count == 2


def test_loading_the_same_rows_twice_does_not_duplicate(conn, good_df):
    """Running the pipeline again for days we already have must not add rows.

    This is the ON CONFLICT DO NOTHING rule. The row count stays at 2.
    """
    load_data(conn, good_df.copy())
    load_data(conn, good_df.copy())

    count = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]
    assert count == 2


def test_a_new_day_is_inserted_beside_existing_rows(conn):
    """A day we have not saved yet should be added, and the old day left alone."""
    first = pd.DataFrame([good_row()])
    second = pd.DataFrame([
        good_row(),
        good_row(date=dt.date(2026, 10, 17), close_price=94.10),
    ])

    load_data(conn, first)
    load_data(conn, second)

    rows = conn.execute(
        "SELECT date, close_price FROM stock_metrics ORDER BY date"
    ).fetchall()
    assert rows == [(dt.date(2026, 10, 16), 93.86), (dt.date(2026, 10, 17), 94.10)]


def test_loaded_at_is_filled_in(conn, good_df):
    """Every saved row should have a timestamp saying when it was loaded."""
    load_data(conn, good_df)

    missing = conn.execute(
        "SELECT COUNT(*) FROM stock_metrics WHERE loaded_at IS NULL"
    ).fetchone()[0]
    assert missing == 0
