"""
IPO 기업 데이터 벡터 인덱스 빌더

`ipo_data.db`에서 모든 기업의 'business_summary' (사업 개요)를 읽어,
Sentence-BERT 모델을 사용하여 의미 벡터(Embedding)로 변환하고,
FAISS를 이용해 빠른 검색을 위한 벡터 인덱스 파일을 생성합니다.

[생성되는 파일]
1. `ipo_vectors.index`: FAISS 벡터 인덱스 파일
2. `company_mapping.json`: 인덱스 순서와 `company_no`를 매핑하는 파일

이 스크립트는 DB에 중요한 변경이 있을 때마다 한 번씩 실행해주면 됩니다.
"""
import duckdb
import pandas as pd
import numpy as np
import json
import faiss
from sentence_transformers import SentenceTransformer
import time
import os
from dotenv import load_dotenv

# --- 설정 ---
DB_FILE = "ipo_db/ipo_data.db"
INDEX_FILE = "ipo_db/ipo_vectors.index"
MAPPING_FILE = "ipo_db/company_mapping.json"
# 한국어 문장 임베딩에 특화된 모델 사용 (오타 수정)
MODEL_NAME = 'jhgan/ko-sroberta-multitask'

def build_index():
    """DB에서 데이터를 읽어 FAISS 인덱스를 구축하고 저장합니다."""
    start_time = time.time()
    
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")

    # 1. 데이터베이스에서 데이터 로드
    print(f"'{DB_FILE}'에서 기업 데이터를 로드하는 중...")
    try:
        conn = duckdb.connect(DB_FILE, read_only=True)
        # 사업 개요가 비어있지 않은 기업만 대상으로 함
        df = conn.execute("""
            SELECT company_no, company_name, business_summary
            FROM companies
            WHERE business_summary IS NOT NULL AND business_summary != ''
        """).fetchdf()
        conn.close()
    except Exception as e:
        print(f"DB 연결 또는 쿼리 중 오류 발생: {e}")
        return

    if df.empty:
        print("오류: 벡터로 변환할 사업 개요 데이터가 DB에 없습니다.")
        return

    print(f"총 {len(df)}개의 기업 개요를 벡터로 변환합니다.")

    # 2. 문장 임베딩 모델 로드
    print(f"'{MODEL_NAME}' 임베딩 모델을 로드하는 중... (최초 실행 시 시간이 소요될 수 있습니다)")
    try:
        model = SentenceTransformer(MODEL_NAME, use_auth_token=hf_token)
    except Exception as e:
        print(f"모델 로드 중 오류 발생: {e}")
        print("인터넷 연결을 확인하거나, 'pip install -U sentence-transformers'로 라이브러리를 업데이트해보세요.")
        return
        
    # 3. 텍스트를 벡터로 변환 (임베딩)
    print("사업 개요 텍스트를 임베딩 벡터로 변환하는 중...")
    # 모델의 최대 시퀀스 길이에 맞춰 텍스트 자르기 (안정성 확보)
    max_seq_length = model.get_max_seq_length()
    summaries = df['business_summary'].str.slice(0, max_seq_length).tolist()
    
    embeddings = model.encode(summaries, show_progress_bar=True, convert_to_numpy=True)
    
    # 벡터 차원 확인
    d = embeddings.shape[1]
    print(f"임베딩 벡터 생성 완료. 벡터 차원: {d}")

    # 4. FAISS 인덱스 구축
    print("FAISS 인덱스를 구축하는 중...")
    index = faiss.IndexFlatL2(d)  # L2 거리(유클리드 거리)를 사용하는 기본 인덱스
    index.add(embeddings.astype('float32')) # FAISS는 float32 타입을 사용

    # 5. 인덱스 및 매핑 파일 저장
    print(f"'{INDEX_FILE}' 파일에 인덱스를 저장하는 중...")
    faiss.write_index(index, INDEX_FILE)

    # 인덱스 순서에 맞는 company_no 매핑 정보 저장
    mapping = {i: row['company_no'] for i, row in df.iterrows()}
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f)
        
    end_time = time.time()
    print("\n" + "="*50)
    print("      벡터 인덱스 생성 완료!")
    print("="*50)
    print(f"  - 처리한 기업 수: {index.ntotal}개")
    print(f"  - 총 소요 시간: {time.strftime('%M분 %S초', time.gmtime(end_time - start_time))}")
    print(f"  - 인덱스 파일: '{INDEX_FILE}'")
    print(f"  - 매핑 파일: '{MAPPING_FILE}'")
    print("="*50)

if __name__ == "__main__":
    # 필수 라이브러리 확인
    try:
        import sentence_transformers
        import faiss
    except ImportError as e:
        print(f"오류: 필수 라이브러리가 설치되지 않았습니다 - {e.name}")
        print("'pip install sentence-transformers faiss-cpu' 명령어로 설치해주세요.")
        exit()
        
    build_index()
