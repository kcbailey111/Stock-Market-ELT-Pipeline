# Tests for validate_data in pipeline.py.
#
# validate_data does not return anything when the data is fine. It raises an
# error when the data is not. So each test below either checks that a good
# table gets through, or checks that a specific kind of bad table is rejected.
#
# These tests never call the Alpha Vantage API. They build small tables in memory.

import datetime as dt

import pandas as pd
import pytest

from sample_data import good_row
from pipeline import validate_data


def test_valid_table_is_accepted(good_df):
    """A normal two-day table should not raise any error."""
    validate_data(good_df)


def test_empty_table_is_rejected():
    """An empty download is not usable, so validation stops immediately."""
    empty = pd.DataFrame(columns=["date", "symbol", "open_price", "high_price", "low_price", "close_price", "volume"])

    with pytest.raises(ValueError, match="empty"):
        validate_data(empty)


def test_missing_price_is_rejected():
    """A blank close price would break the return and moving-average math later."""
    df = pd.DataFrame([good_row(close_price=None)])

    with pytest.raises(AssertionError, match="Null values"):
        validate_data(df)


def test_zero_price_is_rejected():
    """A price of zero is not a real trade."""
    df = pd.DataFrame([good_row(open_price=0)])

    with pytest.raises(AssertionError, match="Non-positive price"):
        validate_data(df)


def test_negative_price_is_rejected():
    """A negative price is not a real trade either."""
    df = pd.DataFrame([good_row(low_price=-5)])

    with pytest.raises(AssertionError, match="Non-positive price"):
        validate_data(df)


def test_high_below_low_is_rejected():
    """The day's highest price cannot be lower than its lowest price."""
    df = pd.DataFrame([good_row(high_price=90.0, low_price=92.81)])

    with pytest.raises(AssertionError, match="High price below low price"):
        validate_data(df)


def test_negative_volume_is_rejected():
    """Volume counts shares traded, so it cannot be negative."""
    df = pd.DataFrame([good_row(volume=-1)])

    with pytest.raises(AssertionError, match="Negative volume"):
        validate_data(df)


def test_duplicate_day_is_rejected():
    """The same stock on the same day must appear only once."""
    df = pd.DataFrame([
        good_row(),
        good_row(),
    ])

    with pytest.raises(AssertionError, match="Duplicate"):
        validate_data(df)


def test_same_day_for_two_symbols_is_allowed():
    """KO and AAPL can both have a row on the same date. That is not a duplicate."""
    df = pd.DataFrame([
        good_row(symbol="KO"),
        good_row(symbol="AAPL", date=dt.date(2026, 10, 16)),
    ])

    validate_data(df)
