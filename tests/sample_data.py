# Small fake price rows used by the tests.
# Kept in their own file so the tests can import them. pytest does not like
# tests importing from conftest.py.

import datetime as dt

import pandas as pd


def good_row(**overrides):
    """One valid trading day. Pass a column name to break it on purpose.

    Example: good_row(close_price=-1) builds a row that should fail validation.
    """
    row = {
        "date": dt.date(2026, 10, 16),
        "symbol": "KO",
        "open_price": 93.12,
        "high_price": 93.885,
        "low_price": 92.81,
        "close_price": 93.86,
        "volume": 22417720,
    }
    row.update(overrides)
    return row


def good_df():
    """A two-day table that passes every check in validate_data."""
    return pd.DataFrame([
        good_row(),
        good_row(date=dt.date(2026, 10, 17), close_price=94.10),
    ])
