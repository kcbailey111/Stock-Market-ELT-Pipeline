# Prints the two finished dbt tables so you can eyeball the pipeline output.
# Run `dbt build` inside transform/ first, or these tables will not exist.
import duckdb

# read_only=True means this script can look but cannot change anything.
conn = duckdb.connect("data/data.duckdb", read_only=True)
conn.sql("SELECT * FROM mart_symbol_summary ORDER BY symbol").show()  # One row per stock
conn.sql("SELECT * FROM fct_daily_prices ORDER BY trade_date DESC, symbol LIMIT 20").show()  # Latest days
conn.close()
