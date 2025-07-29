import duckdb
import pandas as pd
import numpy as np
import json
import faiss
from sentence_transformers import SentenceTransformer
import re
import os
from dotenv import load_dotenv
import argparse

# --- 분석 설정 ---
DB_FILE = "ipo_db/ipo_data.db"
INDEX_FILE = "ipo_db/ipo_vectors.index"
MAPPING_FILE = "ipo_db/company_mapping.json"
MODEL_NAME = 'jhgan/ko-sroberta-multitask'
TOP_K = 50  # 필터링을 고려하여 검색 대상을 늘림

def generate_business_summary(data):
    """종합 데이터 JSON에서 비즈니스 요약 텍스트를 생성합니다."""
    summary_parts = []
    company_name = data.get("company_name", "알 수 없음")
    summary_parts.append(f"기업명: {company_name}")

    if data.get("thevc_data") and data["thevc_data"].get("company_info"):
        info = data["thevc_data"]["company_info"]
        summary_parts.append(f"주요 서비스/제품: {info.get('product_service', 'N/A')}")
        summary_parts.append(f"본사: {info.get('headquarters', 'N/A')}")

    if data.get("innoforest_data"):
        inno_main = data["innoforest_data"].get("main_info", {})
        summary_parts.append(f"기술 등급: {inno_main.get('기술등급', 'N/A')}")
        news_titles = [news['title'] for news in data["innoforest_data"].get("news", [])[:3]]
        if news_titles:
            summary_parts.append(f"최신 뉴스: {', '.join(news_titles)}")

    if data.get("thevc_data"):
        thevc_main = data["thevc_data"].get("business_info", {})
        summary_parts.append(f"누적 투자 유치: {thevc_main.get('투자', 'N/A')}")
        keywords = data["thevc_data"].get("related_keywords", [])
        if keywords:
            summary_parts.append(f"관련 키워드: {', '.join(keywords)}")
        patents = [p['title'] for p in data["thevc_data"].get("patents", {}).get("details", [])[:3]]
        if patents:
            summary_parts.append(f"주요 특허: {', '.join(patents)}")

    return "\n".join(summary_parts)

def parse_financial_value(value_str):
    """'억', '만' 등의 단위를 포함하는 재무 문자열을 숫자로 변환합니다."""
    if isinstance(value_str, (int, float)): return value_str
    if not isinstance(value_str, str): return 0
    value_str = value_str.replace(',', '').strip()
    if '억' in value_str: return float(re.sub(r'[^\d.]', '', value_str)) * 1e8
    if '만' in value_str: return float(re.sub(r'[^\d.]', '', value_str)) * 1e4
    return pd.to_numeric(value_str, errors='coerce')

def get_listed_company_nos(conn):
    """PBR 또는 PSR 데이터가 있는 상장 기업의 company_no 목록을 반환합니다."""
    query = """
    SELECT DISTINCT company_no
    FROM stock_indicators
    WHERE item IN ('PBR (주가순자산비율)', 'SPS (주당매출액)') AND value IS NOT NULL
    """
    return conn.execute(query).fetchdf()['company_no'].tolist()

def find_similar_companies_by_vector(target_summary, model, listed_nos_set):
    """FAISS로 유사 기업을 찾고, 상장 기업만 필터링하여 상위 10개를 반환합니다."""
    try:
        index = faiss.read_index(INDEX_FILE)
        with open(MAPPING_FILE, 'r') as f:
            mapping = json.load(f)
    except Exception as e:
        print(f"오류: 인덱스 또는 매핑 파일을 로드할 수 없습니다. '{e}'")
        return [], []

    target_vector = model.encode([target_summary])
    faiss.normalize_L2(target_vector)

    distances, indices = index.search(target_vector, TOP_K)
    
    results = []
    for i, idx in enumerate(indices[0]):
        company_no = mapping.get(str(idx))
        if company_no and company_no in listed_nos_set:
            similarity = 1 - distances[0][i]
            results.append({'company_no': company_no, 'similarity': similarity})

    # 유사도 기준으로 정렬 후 상위 10개 선택
    results = sorted(results, key=lambda x: x['similarity'], reverse=True)[:10]
    
    similar_nos = [r['company_no'] for r in results]
    similarities = [r['similarity'] for r in results]
    
    return similar_nos, similarities

def get_valuation_multiples(conn, company_nos):
    """주어진 기업 목록의 PBR, PSR 지표를 계산하여 반환합니다."""
    if not company_nos: return pd.DataFrame()
    placeholders = ', '.join(['?'] * len(company_nos))
    query = f"""
        SELECT c.company_no, c.company_name, c.data_payload,
               (SELECT si.value FROM stock_indicators si WHERE si.company_no = c.company_no AND si.item = 'PBR (주가순자산비율)' LIMIT 1) AS pbr_value,
               (SELECT si.value FROM stock_indicators si WHERE si.company_no = c.company_no AND si.item = 'SPS (주당매출액)' LIMIT 1) AS sps_value
        FROM companies c WHERE c.company_no IN ({placeholders})
    """
    df = conn.execute(query, company_nos).fetchdf()

    df['pbr'] = pd.to_numeric(df['pbr_value'].str.extract(r'([-]?\d+\.?\d*)')[0], errors='coerce')
    df['sps'] = pd.to_numeric(df['sps_value'].str.replace(',', '').str.extract(r'(\d+)')[0], errors='coerce')
    
    def extract_price(payload):
        try:
            price_str = json.loads(payload).get('확정공모가', '0')
            return float(re.sub(r'[^\d.]', '', price_str))
        except: return 0

    df['offering_price'] = df['data_payload'].apply(extract_price)
    df['psr'] = df.apply(lambda row: row['offering_price'] / row['sps'] if row['sps'] and row['sps'] > 0 else np.nan, axis=1)

    return df[['company_no', 'company_name', 'pbr', 'psr']].dropna(subset=['pbr', 'psr'], how='all')

def format_currency(value):
    if pd.isna(value): return "N/A"
    if abs(value) >= 1e8: return f"{value / 1e8:.2f}억 원"
    return f"{value / 1e4:.0f}만 원"

def main(target_file_path):
    try:
        with open(target_file_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError: print(f"오류: 파일을 찾을 수 없습니다 - {target_file_path}"); return
    except json.JSONDecodeError: print(f"오류: JSON 파싱 실패 - {target_file_path}"); return

    target_company_name = data.get("company_name", "알 수 없는 기업")
    business_summary = generate_business_summary(data)

    financials = {}
    if data.get("innoforest_data"):
        financial_data = data["innoforest_data"].get("financial", {})
        profit_loss_data = data["innoforest_data"].get("profit_loss", {})
        financials['latest_equity'] = parse_financial_value(financial_data.get("자본", {}).get("2024년 (개별)"))
        financials['latest_revenue'] = parse_financial_value(profit_loss_data.get("매출액", {}).get("2024년 (개별)"))
    else:
        financials['latest_equity'] = 0
        financials['latest_revenue'] = 0

    print("="*60 + f"\n     '{target_company_name}' 예상 시가총액 분석 (벡터 검색 기반)\n" + "="*60)
    print("\n[0] 생성된 비즈니스 요약:\n" + business_summary)

    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")

    print("\n[1] 유사 기업 그룹(Comparable Companies) 선정 중...")
    conn = duckdb.connect(DB_FILE, read_only=True)
    listed_nos_set = set(get_listed_company_nos(conn))
    print(f"▶ 총 {len(listed_nos_set)}개의 상장기업을 대상으로 검색합니다.")

    print("임베딩 모델을 로드합니다...")
    try:
        model = SentenceTransformer(MODEL_NAME, use_auth_token=hf_token)
    except Exception as e:
        print(f"모델 로드 실패: {e}"); conn.close(); return

    similar_nos, similarities = find_similar_companies_by_vector(business_summary, model, listed_nos_set)
    
    if not similar_nos:
        print("▶ 의미적으로 유사한 상장 기업을 찾을 수 없습니다."); conn.close(); return

    print(f"▶ 총 {len(similar_nos)}개의 의미적으로 유사한 상장 기업을 찾았습니다.")
    similar_df = conn.execute(f"SELECT company_no, company_name FROM companies WHERE company_no IN ({', '.join(['?']*len(similar_nos))})", similar_nos).fetchdf()
    sim_score_map = {no: score for no, score in zip(similar_nos, similarities)}
    similar_df['similarity'] = similar_df['company_no'].map(sim_score_map)
    print(similar_df.sort_values(by='similarity', ascending=False).to_string(index=False))

    print("\n[2] 유사 기업 그룹의 가치평가 지표(Valuation Multiples) 계산 중...")
    multiples_df = get_valuation_multiples(conn, similar_nos)

    if multiples_df.empty:
        print("유사 기업의 가치평가 지표를 계산할 수 없습니다."); conn.close(); return

    metrics = {
        "PBR_avg": multiples_df['pbr'].mean(), "PBR_median": multiples_df['pbr'].median(),
        "PSR_avg": multiples_df['psr'].mean(), "PSR_median": multiples_df['psr'].median(),
    }
    
    print("\n▶ 요약 지표:")
    print(f"  - 평균 PBR: {metrics['PBR_avg']:.2f}x | 중앙값 PBR: {metrics['PBR_median']:.2f}x")
    print(f"  - 평균 PSR: {metrics['PSR_avg']:.2f}x | 중앙값 PSR: {metrics['PSR_median']:.2f}x")

    print(f"\n[3] '{target_company_name}'의 예상 시가총액 추정...")
    pbr_est_median = financials['latest_equity'] * metrics['PBR_median']
    psr_est_median = financials['latest_revenue'] * metrics['PSR_median']

    print(f"\n▶ '{target_company_name}' 재무 정보:")
    print(f"  - 최근 자본: {format_currency(financials['latest_equity'])}")
    print(f"  - 최근 매출: {format_currency(financials['latest_revenue'])}")

    print("\n▶ 예상 시가총액 (중앙값 기반):")
    print(f"  - PBR 기반 추정: {format_currency(pbr_est_median)}")
    print(f"  - PSR 기반 추정: {format_currency(psr_est_median)}")

    print("\n" + "-"*60 + "\n[주의사항]\n- 본 분석은 DB 데이터와 의미 유사도에 기반한 개략적인 추정치입니다.\n- 실제 기업 가치는 시장 상황, 성장 잠재력 등 여러 요인에 따라 달라질 수 있습니다.\n" + "="*60)
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IPO 예정 기업의 예상 시가총액을 분석합니다.")
    parser.add_argument("target_file", help="분석할 기업의 종합 데이터 JSON 파일 경로")
    args = parser.parse_args()

    try:
        import sentence_transformers, faiss, dotenv
    except ImportError as e:
        print(f"오류: 필수 라이브러리가 설치되지 않았습니다 - {e.name}")
        print("uv pip install sentence-transformers faiss-cpu python-dotenv' 명령어로 설치해주세요.")
        exit()
        
    main(args.target_file)