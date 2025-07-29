
'''
IPO 예정 기업 분석 리포트 생성기

특정 비상장 기업의 종합 데이터(JSON)를 입력받아,
유사 상장 기업 그룹을 찾고, 가치평가 지표를 계산하여
최종적으로 예상 시가총액 분석 리포트를 Markdown 형식으로 출력합니다.

사용법:
uv run python ipo_db/generate_ipo_analysis_report.py <분석할 JSON 파일 경로>

예시:
uv run python ipo_db/generate_ipo_analysis_report.py company_summary/comprehensive_integrated_data_십일리터_20250728_114921.json
'''
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
import warnings

# 경고 메시지 숨기기
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 분석 설정 ---
DB_FILE = "ipo_db/ipo_data.db"
INDEX_FILE = "ipo_db/ipo_vectors.index"
MAPPING_FILE = "ipo_db/company_mapping.json"
MODEL_NAME = 'jhgan/ko-sroberta-multitask'
TOP_K = 50  # 필터링을 고려하여 검색 대상을 늘림

def generate_business_summary(data):
    '''종합 데이터 JSON에서 비즈니스 요약 텍스트를 생성합니다.'''
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
    ''''억', '만' 등의 단위를 포함하는 재무 문자열을 숫자로 변환합니다.'''
    if isinstance(value_str, (int, float)): return value_str
    if not isinstance(value_str, str): return 0
    value_str = value_str.replace(',', '').strip()
    if '억' in value_str:
        num_part = re.search(r'[-]?\d+\.?\d*', value_str)
        return float(num_part.group()) * 1e8 if num_part else 0
    if '만' in value_str:
        num_part = re.search(r'[-]?\d+\.?\d*', value_str)
        return float(num_part.group()) * 1e4 if num_part else 0
    return pd.to_numeric(value_str, errors='coerce')

def get_listed_company_nos(conn):
    '''PBR, PSR, PER 데이터 중 하나라도 있는 상장 기업의 company_no 목록을 반환합니다.'''
    query = '''
    SELECT DISTINCT company_no
    FROM stock_indicators
    WHERE item IN ('PBR (주가수익비율)', 'SPS (주당매출액)', 'PER (주가수익비율)  공모가 대비') AND value IS NOT NULL AND value != '-'
    '''
    try:
        return conn.execute(query).fetchdf()['company_no'].tolist()
    except Exception:
        return []

def find_similar_companies_by_vector(target_summary, model, listed_nos_set):
    '''FAISS로 유사 기업을 찾고, 상장 기업만 필터링하여 상위 10개를 반환합니다.'''
    try:
        index = faiss.read_index(INDEX_FILE)
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    except Exception as e:
        print(f"오류: 인덱스 또는 매핑 파일을 로드할 수 없습니다. '{e}'")
        return [], []

    target_vector = model.encode([target_summary])
    
    distances, indices = index.search(target_vector.astype('float32'), TOP_K)
    
    results = []
    for i, idx in enumerate(indices[0]):
        company_no = mapping.get(str(idx))
        if company_no and company_no in listed_nos_set:
            results.append({'company_no': company_no, 'distance': distances[0][i]})

    results = sorted(results, key=lambda x: x['distance'])[:10]
    
    similar_nos = [r['company_no'] for r in results]
    similarities = [r['distance'] for r in results]
    
    return similar_nos, similarities

def get_valuation_multiples(conn, company_nos):
    '''주어진 기업 목록의 PBR, PSR, PER 지표를 계산하여 반환합니다.'''
    if not company_nos: return pd.DataFrame()
    placeholders = ', '.join(['?'] * len(company_nos))
    
    # 가능한 모든 지표 항목명 조회하여 실제 존재하는 것 찾기
    check_query = '''
    SELECT DISTINCT item 
    FROM stock_indicators 
    WHERE value IS NOT NULL AND value != '-' AND item LIKE '%PBR%' OR item LIKE '%PER%' OR item LIKE '%SPS%' OR item LIKE '%현재가%' OR item LIKE '%주가%'
    '''
    available_items = conn.execute(check_query).fetchdf()['item'].tolist()
    
    # PBR 관련 항목 찾기
    pbr_items = [item for item in available_items if 'PBR' in item or '주가순자산비율' in item]
    per_items = [item for item in available_items if 'PER' in item or '주가수익비율' in item]
    sps_items = [item for item in available_items if 'SPS' in item or '주당매출' in item]
    price_items = [item for item in available_items if '현재가' in item or '주가' in item]
    
    # 첫 번째로 찾은 항목 사용 (없으면 원래 항목명 유지)
    pbr_item = pbr_items[0] if pbr_items else 'PBR (주가수익비율)'
    per_item = per_items[0] if per_items else 'PER (주가수익비율)  공모가 대비'
    sps_item = sps_items[0] if sps_items else 'SPS (주당매출액)'
    price_item = price_items[0] if price_items else '현재가'
    
    query = f'''
        SELECT
            c.company_no,
            c.company_name,
            (SELECT si.value FROM stock_indicators si WHERE si.company_no = c.company_no AND si.item = '{pbr_item}' AND si.value IS NOT NULL AND si.value != '-' LIMIT 1) AS pbr_str,
            (SELECT si.value FROM stock_indicators si WHERE si.company_no = c.company_no AND si.item = '{per_item}' AND si.value IS NOT NULL AND si.value != '-' LIMIT 1) AS per_str,
            (SELECT si.value FROM stock_indicators si WHERE si.company_no = c.company_no AND si.item = '{sps_item}' AND si.value IS NOT NULL AND si.value != '-' LIMIT 1) AS sps_str,
            (SELECT si.value FROM stock_indicators si WHERE si.company_no = c.company_no AND si.item = '{price_item}' AND si.value IS NOT NULL AND si.value != '-' LIMIT 1) AS price_str
        FROM companies c
        WHERE c.company_no IN ({placeholders})
    '''
    df = conn.execute(query, company_nos).fetchdf()

    # 데이터 클리닝 및 숫자 변환 (null 체크 추가)
    def safe_extract_numeric(series, pattern=r'([-]?\d+\.?\d*)'):
        if series is None:
            return pd.Series([np.nan] * len(df))
        return pd.to_numeric(series.fillna('').str.replace(',', '').str.extract(pattern)[0], errors='coerce')
    
    df['pbr'] = safe_extract_numeric(df['pbr_str'])
    df['per'] = safe_extract_numeric(df['per_str'])
    df['sps'] = safe_extract_numeric(df['sps_str'], r'(\d+\.?\d*)')
    df['price'] = safe_extract_numeric(df['price_str'], r'(\d+\.?\d*)')

    # PSR 계산 (안전한 계산)
    df['psr'] = df.apply(lambda row: row['price'] / row['sps'] if pd.notna(row['sps']) and row['sps'] > 0 and pd.notna(row['price']) else np.nan, axis=1)

    # 최소한 하나의 유효한 지표라도 있는 기업만 반환
    result_df = df[['company_no', 'company_name', 'pbr', 'psr', 'per']]
    return result_df[result_df[['pbr', 'psr', 'per']].notna().any(axis=1)]

def format_currency(value):
    if pd.isna(value) or not np.isfinite(value): return "N/A"
    if abs(value) >= 1e8: return f"{value / 1e8:.2f}억 원"
    return f"{value / 1e4:.0f}만 원"

def main(target_file_path):
    try:
        with open(target_file_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError: print(f"오류: 파일을 찾을 수 없습니다 - {target_file_path}"); return
    except json.JSONDecodeError: print(f"오류: JSON 파싱 실패 - {target_file_path}"); return

    target_company_name = data.get("company_name", "알 수 없는 기업")
    
    financials = {}
    if data.get("innoforest_data"):
        financial_data = data["innoforest_data"].get("financial", {})
        profit_loss_data = data["innoforest_data"].get("profit_loss", {})
        
        latest_equity_val = next((v for k, v in reversed(financial_data.get("자본", {}).items()) if v and v != '-'), None)
        latest_revenue_val = next((v for k, v in reversed(profit_loss_data.get("매출액", {}).items()) if v and v != '-'), None)
        latest_profit_val = next((v for k, v in reversed(profit_loss_data.get("순이익", {}).items()) if v and v != '-'), None)

        financials['latest_equity'] = parse_financial_value(latest_equity_val)
        financials['latest_revenue'] = parse_financial_value(latest_revenue_val)
        financials['latest_profit'] = parse_financial_value(latest_profit_val)
    else:
        financials['latest_equity'] = 0
        financials['latest_revenue'] = 0
        financials['latest_profit'] = 0

    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")

    conn = duckdb.connect(DB_FILE, read_only=True)
    listed_nos_set = set(get_listed_company_nos(conn))
    
    if not listed_nos_set:
        print("오류: DB에 유효한 재무 지표를 가진 상장 기업 데이터가 없습니다.")
        conn.close()
        return

    model = SentenceTransformer(MODEL_NAME, use_auth_token=hf_token)
    
    business_summary = generate_business_summary(data)
    similar_nos, similarities = find_similar_companies_by_vector(business_summary, model, listed_nos_set)
    
    if not similar_nos:
        print(f"'{target_company_name}'과(와) 의미적으로 유사한 상장 기업을 찾을 수 없습니다."); conn.close(); return

    similar_df_from_db = conn.execute(f"SELECT company_no, company_name FROM companies WHERE company_no IN ({', '.join(['?']*len(similar_nos))})", similar_nos).fetchdf()
    sim_score_map = {no: score for no, score in zip(similar_nos, similarities)}
    similar_df_from_db['distance'] = similar_df_from_db['company_no'].map(sim_score_map)
    similar_df_from_db = similar_df_from_db.sort_values(by='distance')

    multiples_df = get_valuation_multiples(conn, similar_nos)

    if multiples_df.empty:
        print("유사 기업의 가치평가 지표를 계산할 수 없습니다."); conn.close(); return

    # nan이 아닌 값들만으로 중앙값 계산
    metrics = {
        "PBR_median": multiples_df['pbr'].dropna().median() if not multiples_df['pbr'].dropna().empty else np.nan,
        "PSR_median": multiples_df['psr'].dropna().median() if not multiples_df['psr'].dropna().empty else np.nan,
        "PER_median": multiples_df['per'].dropna().median() if not multiples_df['per'].dropna().empty else np.nan,
    }
    
    # 유효한 지표가 있을 때만 시가총액 추정
    pbr_est_median = financials['latest_equity'] * metrics['PBR_median'] if not pd.isna(metrics['PBR_median']) else np.nan
    psr_est_median = financials['latest_revenue'] * metrics['PSR_median'] if not pd.isna(metrics['PSR_median']) else np.nan
    per_est_median = financials['latest_profit'] * metrics['PER_median'] if not pd.isna(metrics['PER_median']) else np.nan

    # --- 리포트 출력 ---
    print(f"### '{target_company_name}' 시가총액 분석 최종 결과")
    print("\n**1. 유사 기업 그룹 (Comparable Companies)**")
    print(f"'{target_company_name}'의 사업 개요와 의미적으로 가장 유사하다고 판단된 상장 기업 {len(similar_df_from_db)}곳은 다음과 같습니다.")
    
    report_df = similar_df_from_db[['company_no', 'company_name', 'distance']].copy()
    report_df.rename(columns={'distance': '유사도(거리)'}, inplace=True)
    print(report_df.to_markdown(index=False))
    print("\n*   **분석**: AI, 기술, 서비스 등 관련 키워드를 기반으로 유사 기업을 선정했습니다. `유사도(거리)`는 낮을수록 사업 연관성이 높음을 의미합니다.")

    print("\n**2. 가치평가 지표 (Valuation Multiples)**")
    print(f"*   **PBR 중앙값**: {metrics['PBR_median']:.2f}x" if not pd.isna(metrics['PBR_median']) else "*   **PBR 중앙값**: N/A (데이터 없음)")
    print(f"*   **PSR 중앙값**: {metrics['PSR_median']:.2f}x" if not pd.isna(metrics['PSR_median']) else "*   **PSR 중앙값**: N/A (데이터 없음)")
    print(f"*   **PER 중앙값**: {metrics['PER_median']:.2f}x" if not pd.isna(metrics['PER_median']) else "*   **PER 중앙값**: N/A (데이터 없음)")
    print("*   **분석**: 유사 기업 그룹의 가치평가 지표 중앙값을 사용하여, 시장이 유사 비즈니스 모델을 어떻게 평가하는지에 대한 기준을 설정합니다. 'N/A'로 표시된 지표는 해당 데이터를 가진 유사 기업이 없음을 의미합니다.")

    print(f"\n**3. '{target_company_name}' 예상 시가총액**")
    
    if not pd.isna(metrics['PBR_median']):
        print(f"*   **PBR 기반 추정**: **{format_currency(pbr_est_median)}** (최근 자본 {format_currency(financials['latest_equity'])} × PBR {metrics['PBR_median']:.2f}x)")
    else:
        print(f"*   **PBR 기반 추정**: **N/A** (PBR 데이터 없음)")
    
    if not pd.isna(metrics['PSR_median']):
        print(f"*   **PSR 기반 추정**: **{format_currency(psr_est_median)}** (최근 매출 {format_currency(financials['latest_revenue'])} × PSR {metrics['PSR_median']:.2f}x)")
    else:
        print(f"*   **PSR 기반 추정**: **N/A** (PSR 데이터 없음)")
    
    if not pd.isna(metrics['PER_median']):
        print(f"*   **PER 기반 추정**: **{format_currency(per_est_median)}** (최근 순이익 {format_currency(financials['latest_profit'])} × PER {metrics['PER_median']:.2f}x)")
    else:
        print(f"*   **PER 기반 추정**: **N/A** (PER 데이터 없음)")

    print("\n### 종합 결론 및 추가 분석 제안")
    print("*   **분석 요약**: PBR, PSR, PER 등 다양한 지표를 통해 가치를 추정했습니다. 각 지표는 기업의 다른 측면(자산, 매출, 수익)을 반영하므로 종합적으로 고려해야 합니다.")
    print("*   **한계점**: 이 분석은 제한된 데이터에 기반한 추정치이며, 실제 기업 가치는 시장 상황, 성장 잠재력, 경영진 능력 등 다양한 요인에 따라 달라질 수 있습니다. 특히 순이익이 적자인 경우 PER 기반 추정은 의미가 없을 수 있습니다.")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IPO 예정 기업의 예상 시가총액 분석 리포트를 생성합니다.")
    parser.add_argument("target_file", help="분석할 기업의 종합 데이터 JSON 파일 경로")
    args = parser.parse_args()

    try:
        import sentence_transformers, faiss, dotenv
    except ImportError as e:
        print(f"오류: 필수 라이브러리가 설치되지 않았습니다 - {e.name}")
        print("uv pip install sentence-transformers faiss-cpu python-dotenv' 명령어로 설치해주세요.")
        exit()
        
    main(args.target_file)
