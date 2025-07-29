import duckdb

DB_FILE = 'ipo_db/ipo_data.db'

with duckdb.connect(DB_FILE, read_only=True) as conn:
    try:
        per_count_query = "SELECT count(*) FROM stock_indicators WHERE item LIKE '%PER%' AND value IS NOT NULL AND value != '-'"
        per_count = conn.execute(per_count_query).fetchone()[0]
        print(f"데이터베이스에 저장된 유효한 PER 데이터 수: {per_count}개")
        
        if per_count > 0:
            print("\n--- PER 데이터 샘플 (상위 10개) ---")
            per_sample_query = "SELECT company_no, item, value FROM stock_indicators WHERE item LIKE '%PER%' AND value IS NOT NULL AND value != '-' LIMIT 10"
            df = conn.execute(per_sample_query).fetchdf()
            print(df.to_markdown(index=False))
            
    except Exception as e:
        print(f"DB 조회 중 오류 발생: {e}")

