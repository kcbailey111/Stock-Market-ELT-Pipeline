## Author: Kyler Bailey
## Date: 10/15/2026
## Description: This script is a pipeline for extracting, validating, and loading daily stock
##              data from the Alpha Vantage API into a local DuckDB database. Transformations
##              live in the dbt project under transform/.

# These are the tools this script uses.
# os: read settings like the API key and create the data folder.
# time: pause between API calls so we don't get blocked for calling too fast.
# datetime: record when each row was saved.
# requests: download data from the internet.
# duckdb: the database that stores the prices (see the README for what DuckDB is).
# pandas: holds the downloaded prices in a table in memory before saving them.
import os
import time
import datetime as dt
import requests
import duckdb
import pandas as pd

# A .env file is a text file that holds secrets, like the API key, on your own computer.
# GitHub Actions has no .env file; it passes the key in a different way.
# If python-dotenv isn't installed, skip this instead of crashing.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# The whole database is one file. DuckDB creates it the first time we connect.
DB_PATH = "data/data.duckdb"
# One ticker from each of five industries, so the sample isn't all tech stocks.
# If you add one here, also add it to transform/seeds/symbols.csv.
SYMBOLS = ["KO", "AAPL", "MSFT", "JPM", "XOM"]
# The free Alpha Vantage plan allows 5 calls per minute. Waiting 15 seconds
# between calls keeps us under that limit.
SECONDS_BETWEEN_REQUESTS = 15


def extract_data(symbol):
    """Download the recent daily prices for one stock ticker.

    Returns a pandas table with one row per trading day.
    """
    # os.environ is the list of settings for this program. Locally those come
    # from the .env file. On GitHub they come from the repository secret.
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is missing!")

    # The API answers a web address. symbol and the key are filled in here.
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"

    # timeout=10 means give up if the site doesn't answer within 10 seconds.
    response = requests.get(url, timeout=10)
    # Stop here if the site returned an error (like "page not found").
    response.raise_for_status()
    data = response.json()

    # A normal reply contains "Time Series (Daily)". If it's missing, the reply
    # is an error message instead, usually because we called too often.
    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        raise ValueError(f"API Error or Rate Limit Reached for {symbol}: {data}")

    # The free plan sends about the last 100 trading days. Keep all of them.
    # Each day arrives as text, so float() and int() turn prices and volume
    # into real numbers.
    records = [
        {
            "date": date,
            "symbol": symbol,
            "open_price": float(day_data["1. open"]),
            "high_price": float(day_data["2. high"]),
            "low_price": float(day_data["3. low"]),
            "close_price": float(day_data["4. close"]),
            "volume": int(day_data["5. volume"]),
        }
        for date, day_data in time_series.items()
    ]
    df = pd.DataFrame(records)
    # Store the date as a date, not as text like "2026-10-16".
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def validate_data(df):
    """Refuse to save the data if it looks wrong.

    Each check stops the function with an error. The caller catches that error
    and skips this one stock instead of saving bad rows.
    """
    if df.empty:
        raise ValueError("Extracted dataframe is empty.")

    # A blank price or date would break the averages later.
    if df.isnull().any().any():
        raise AssertionError("Data Quality Failure: Null values found.")

    # A price of zero or less can't be a real trade.
    price_cols = ["open_price", "high_price", "low_price", "close_price"]
    if (df[price_cols] <= 0).any().any():
        raise AssertionError("Data Quality Failure: Non-positive price found.")

    # The highest price of the day can't be lower than the lowest price.
    if (df["high_price"] < df["low_price"]).any():
        raise AssertionError("Data Quality Failure: High price below low price.")

    # Volume is a count of shares, so it can't be negative.
    if (df["volume"] < 0).any():
        raise AssertionError("Data Quality Failure: Negative volume found.")

    # The same stock on the same day should appear once, not twice.
    if df.duplicated(subset=["date", "symbol"]).any():
        raise AssertionError("Data Quality Failure: Duplicate (date, symbol) rows.")

    print(f"Validation Check: Passed for {len(df)} rows.")


def load_data(conn, df):
    """Save the table into DuckDB, skipping days we already have."""
    # CREATE TABLE IF NOT EXISTS means "make this table, unless it already exists."
    # PRIMARY KEY (date, symbol) means that pair must be unique, which is what
    # lets the insert below skip rows we've saved before.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_metrics (
            date DATE,
            symbol VARCHAR,
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            volume BIGINT,
            loaded_at TIMESTAMP,
            PRIMARY KEY (date, symbol)
        )
    """)

    # Stamp every row with the current UTC time, then drop the timezone info
    # because this column is stored as a plain timestamp.
    df["loaded_at"] = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

    before = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]

    # Insert the new rows. ON CONFLICT DO NOTHING means: if this stock and date
    # are already in the table, skip that row instead of saving it twice.
    # Running the pipeline again is therefore safe.
    conn.execute("""
        INSERT INTO stock_metrics
            (date, symbol, open_price, high_price, low_price, close_price, volume, loaded_at)
        SELECT date, symbol, open_price, high_price, low_price, close_price, volume, loaded_at
        FROM df
        ON CONFLICT (date, symbol) DO NOTHING
    """)

    after = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]
    print(f"Load Check: {after - before} new rows. Total rows in warehouse: {after}")


# This block only runs when you start the file directly with `python pipeline.py`.
# It does not run when another file imports one of the functions above.
if __name__ == "__main__":
    print(f"Starting Stock ELT pipeline for {', '.join(SYMBOLS)}...")
    # Make the data folder if this is the first run.
    os.makedirs("data", exist_ok=True)
    # Opening the file starts DuckDB. conn is our handle for sending it SQL.
    conn = duckdb.connect(DB_PATH)
    failed = []

    try:
        for i, symbol in enumerate(SYMBOLS):
            # The first stock runs immediately; each one after it waits.
            if i > 0:
                time.sleep(SECONDS_BETWEEN_REQUESTS)
            print(f"\n--- {symbol} ---")
            try:
                df = extract_data(symbol)
                validate_data(df)
                load_data(conn, df)
            except Exception as e:
                # One broken stock should not throw away the others.
                print(f"Skipping {symbol}: {e}")
                failed.append(symbol)
    finally:
        # Always close the database, even if something above crashed.
        conn.close()

    # If every stock failed, tell GitHub Actions the run failed so it doesn't
    # commit an unchanged database and report success.
    if len(failed) == len(SYMBOLS):
        raise SystemExit("Every symbol failed; nothing was loaded.")
    print(f"\nStock ELT pipeline completed. Failed symbols: {failed or 'none'}")
