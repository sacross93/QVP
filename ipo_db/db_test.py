import duckdb

conn = duckdb.connect("./ipo_db/ipo_data.db")

conn.execute("SELECT * FROM companies LIMIT 20")

print(conn.fetch_df())




conn.execute("SELECT * FROM financial_ratios LIMIT 10")

print(conn.fetch_df())


conn.execute("SELECT * FROM stock_indicators LIMIT 10")

print(conn.fetch_df())