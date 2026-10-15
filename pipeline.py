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

DB_Path = "data/data.duckdb"

def extract_data():
    # Extract data from the API will need to change to URL API to something more desired
    url = "https://api.open-meteo.com/v1/forecast?latitude=34.9496&longitude=-81.9199&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    ####Definitely will have to go in and change some code here that involves temperature, humidity, and wind speed.
    
    current = data.get("current", {})
    record = {
        "timestamp": current.get("time", dt.utcnow().isoformat()),
        "temperature_c": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m")
    }
    return pd.DataFrame([record])

def validate_data(df):
    if df.empty:
        raise ValueError("Extracted dataframe is empty.")
    
    if df["timestamp"].isnull().any():
        raise AssertionError("Data Quality Failure: Null values found in timestamp primary key.")
    
    temp = df["temperature_c"].iloc[0]
    if temp is not None and not (-50 <= temp <= 60):
        raise AssertionError(f"Data Quality Failure: Temperature {temp}°C is out of realistic bounds.")
    
    print("Validation Check: Passed successfully.")

def load_data(df):
    os.makedirs("data", exist_ok=True)
    conn = duckdb.connect(DB_Path)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather_metrics (
            timestamp TIMESTAMP PRIMARY KEY,
            temperature_c DOUBLE,
            humidity DOUBLE,
            wind_speed DOUBLE,
            loaded_at TIMESTAMP
        )
    """)
    
    df["loaded_at"] = dt.utcnow()
    
    # Incremental load (Upsert pattern)
    conn.execute("""
        INSERT INTO weather_metrics 
        SELECT * FROM df 
        ON CONFLICT(timestamp) DO NOTHING
    """)
    
    count = conn.execute("SELECT COUNT(*) FROM weather_metrics").fetchone()[0]
    print(f"Load Check: Success. Total rows in warehouse: {count}")
    conn.close()

if __name__ == "__main__":
    print("Starting ELT pipeline execution...")
    df = extract_data()
    validate_data(df)
    load_data(df)
    print("ELT pipeline completed.")