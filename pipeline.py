## Author: Kyler Bailey
## Date: 10/15/2026
## Description: This script is a pipeline for extracting, validating, loading, and transforming
##              daily stock data from the Alpha Vantage API into a local DuckDB database.

# 1. Import the necessary libraries
import os
import time
import datetime as dt
import requests
import duckdb
import pandas as pd

# Try to load local .env file if it exists (won't crash if running on GitHub Actions)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = "data/data.duckdb"
# Stock symbols to extract data for (spread across sectors)
SYMBOLS = ["KO", "AAPL", "MSFT", "JPM", "XOM"]
# Alpha Vantage free tier allows 5 requests per minute and 25 per day
SECONDS_BETWEEN_REQUESTS = 15


# Extract data from the API
def extract_data(symbol):
    # This checks os.environ, which will find the .env file locally
    # OR the GitHub Repository Secret in production!
    api_key = os.environ.get("STOCK_API_KEY")

    if not api_key:
        raise ValueError("STOCK_API_KEY environment variable is missing!")

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        raise ValueError(f"API Error or Rate Limit Reached for {symbol}: {data}")

    # The compact response holds the last ~100 trading days; keep all of them
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
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def validate_data(df):
    if df.empty:
        raise ValueError("Extracted dataframe is empty.")

    if df.isnull().any().any():
        raise AssertionError("Data Quality Failure: Null values found.")

    price_cols = ["open_price", "high_price", "low_price", "close_price"]
    if (df[price_cols] <= 0).any().any():
        raise AssertionError("Data Quality Failure: Non-positive price found.")

    if (df["high_price"] < df["low_price"]).any():
        raise AssertionError("Data Quality Failure: High price below low price.")

    if (df["volume"] < 0).any():
        raise AssertionError("Data Quality Failure: Negative volume found.")

    if df.duplicated(subset=["date", "symbol"]).any():
        raise AssertionError("Data Quality Failure: Duplicate (date, symbol) rows.")

    print(f"Validation Check: Passed for {len(df)} rows.")


def load_data(conn, df):
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

    df["loaded_at"] = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

    before = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]

    # Incremental load (Upsert pattern)
    conn.execute("""
        INSERT INTO stock_metrics
            (date, symbol, open_price, high_price, low_price, close_price, volume, loaded_at)
        SELECT date, symbol, open_price, high_price, low_price, close_price, volume, loaded_at
        FROM df
        ON CONFLICT (date, symbol) DO NOTHING
    """)

    after = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]
    print(f"Load Check: {after - before} new rows. Total rows in warehouse: {after}")


def transform_data(conn):
    # Analytics layer built on top of the raw table
    conn.execute("""
        CREATE OR REPLACE VIEW daily_returns AS
        SELECT
            date,
            symbol,
            close_price,
            volume,
            close_price / LAG(close_price) OVER w - 1 AS daily_return,
            AVG(close_price) OVER (w ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d,
            AVG(close_price) OVER (w ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS moving_avg_30d
        FROM stock_metrics
        WINDOW w AS (PARTITION BY symbol ORDER BY date)
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW symbol_summary AS
        SELECT
            symbol,
            MIN(date) AS first_date,
            MAX(date) AS last_date,
            COUNT(*) AS trading_days,
            ARG_MAX(close_price, date) AS latest_close,
            MIN(low_price) AS period_low,
            MAX(high_price) AS period_high,
            AVG(volume)::BIGINT AS avg_volume
        FROM stock_metrics
        GROUP BY symbol
    """)
    print("Transform Check: Views daily_returns and symbol_summary refreshed.")


if __name__ == "__main__":
    print(f"Starting Stock ELT pipeline for {', '.join(SYMBOLS)}...")
    os.makedirs("data", exist_ok=True)
    conn = duckdb.connect(DB_PATH)
    failed = []

    try:
        for i, symbol in enumerate(SYMBOLS):
            if i > 0:
                time.sleep(SECONDS_BETWEEN_REQUESTS)
            print(f"\n--- {symbol} ---")
            try:
                df = extract_data(symbol)
                validate_data(df)
                load_data(conn, df)
            except Exception as e:
                print(f"Skipping {symbol}: {e}")
                failed.append(symbol)

        transform_data(conn)
    finally:
        conn.close()

    if len(failed) == len(SYMBOLS):
        raise SystemExit("Every symbol failed; nothing was loaded.")
    print(f"\nStock ELT pipeline completed. Failed symbols: {failed or 'none'}")
