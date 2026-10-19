# Tests for extract_data that do not call Alpha Vantage.
#
# The real download needs a network call and an API key, and the free plan only
# allows 25 calls a day. These tests check the guard that runs before any call:
# if the key is missing, the function stops with a clear error.

import pytest

from pipeline import extract_data


def test_missing_api_key_raises(monkeypatch):
    """Deleting the key from the environment should fail before any download.

    monkeypatch changes the environment for this test only, then puts it back.
    """
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)

    with pytest.raises(ValueError, match="ALPHA_VANTAGE_API_KEY"):
        extract_data("KO")
