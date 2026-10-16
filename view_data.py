import duckdb

conn = duckdb.connect("data/data.duckdb")
conn.sql("SELECT * FROM stock_metrics ORDER BY date DESC").show() # Show the data in a table format
conn.close()