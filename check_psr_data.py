import duckdb
import pandas as pd

DB_FILE = 'ipo_db/ipo_data.db'
company_nos = ['2064', '2138', '2192', '2146', '2102', '2151', '2048', '2200', '2167', '2162']

with duckdb.connect(DB_FILE, read_only=True) as conn:
    query = f"""SELECT company_no, item, value FROM stock_indicators 
               WHERE company_no IN ({str(company_nos)[1:-1]}) 
               AND item IN ('현재가', 'SPS (주당매출액)')"""
    df = conn.execute(query).fetchdf()

print("--- 유사 기업 10곳의 현재가 및 SPS 데이터 ---")
if df.empty:
    print("조회 결과: PSR 계산에 필요한 '현재가' 또는 'SPS' 데이터가 DB에 존재하지 않습니다.")
else:
    print(df.to_markdown(index=False))
