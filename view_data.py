import duckdb

conn = duckdb.connect("data/data.duckdb", read_only=True)
conn.sql("SELECT * FROM symbol_summary ORDER BY symbol").show() # One row per stock
conn.sql("SELECT * FROM daily_returns ORDER BY date DESC, symbol LIMIT 20").show() # Latest returns and moving averages
conn.close()
