## Author: Kyler Bailey
## Date: 10/15/2026
## Description: This script is a pipeline for extracting, validating, and loading data from an API into a local DuckDB database.

# 1. Import the necessary libraries
import os
import datetime as dt
import requests
import duckdb
import pandas as pd
import pytest

# Try to load local .env file if it exists (won't crash if running on GitHub Actions)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = "data/data.duckdb"
SYMBOL = "AAPL"

def extract_data():
    # This checks os.environ, which will find the .env file locally 
    # OR the GitHub Repository Secret in production!
    api_key = os.environ.get("STOCK_API_KEY")
    
    if not api_key:
        raise ValueError("STOCK_API_KEY environment variable is missing!")
        
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={SYMBOL}&apikey={api_key}"
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        raise ValueError(f"API Error or Rate Limit Reached: {data}")
    
    latest_date = sorted(time_series.keys())[-1]
    day_data = time_series[latest_date]
    
    record = {
        "date": latest_date,
        "symbol": SYMBOL,
        "open_price": float(day_data.get("1. open")),
        "high_price": float(day_data.get("2. high")),
        "low_price": float(day_data.get("3. low")),
        "close_price": float(day_data.get("4. close")),
        "volume": int(day_data.get("5. volume"))
    }
    return pd.DataFrame([record])

# (validate_data and load_data remain the same)

def validate_data(df):
    if df.empty:
        raise ValueError("Extracted dataframe is empty.")
    
    # Data quality check: Stock price cannot be 0 or negative
    close_val = df["close_price"].iloc[0]
    if close_val <= 0:
        raise AssertionError(f"Data Quality Failure: Close price {close_val} is invalid.")
        
    print("Validation Check: Passed successfully.")

def load_data(df):
    os.makedirs("data", exist_ok=True)
    conn = duckdb.connect(DB_PATH)
    
    # Updated schema for financial metrics with a composite primary key (date + symbol)
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
    
    df["loaded_at"] = dt.utcnow()
    
    # Incremental load (Upsert pattern)
    conn.execute("""
        INSERT INTO stock_metrics 
        SELECT * FROM df 
        ON CONFLICT(date, symbol) DO NOTHING
    """)
    
    count = conn.execute("SELECT COUNT(*) FROM stock_metrics").fetchone()[0]
    print(f"Load Check: Success. Total rows in warehouse: {count}")
    conn.close()

if __name__ == "__main__":
    print(f"Starting Stock ELT pipeline for {SYMBOL}...")
    df = extract_data()
    validate_data(df)
    load_data(df)
    print("Stock ELT pipeline completed.")