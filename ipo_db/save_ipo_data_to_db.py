"""
[Refactored]
38커뮤니케이션즈(38.co.kr)의 IPO 기업 정보를 스크래핑하고 DuckDB에 저장합니다.
이 모듈은 다른 스크립트에서 가져와 사용할 수 있도록 함수 단위로 분리되었습니다.
"""

import asyncio
import argparse
from playwright.async_api import async_playwright, Page, TimeoutError
import pandas as pd
import io
import duckdb
from datetime import datetime
import re
import json

# --- 데이터베이스 관련 함수 ---

def clean_text(text):
    """비-ASCII 문자를 정규화하고 불필요한 공백을 제거합니다."""
    if not isinstance(text, str):
        return text
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def create_tables(conn):
    """DuckDB에 필요한 테이블들을 생성합니다."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        company_no VARCHAR PRIMARY KEY,
        company_name VARCHAR,
        business_summary TEXT,
        data_payload JSON,
        last_updated TIMESTAMP
    );
    """)
    conn.execute("CREATE SEQUENCE IF NOT EXISTS financial_ratios_id_seq START 1;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS financial_ratios (
        id INTEGER PRIMARY KEY DEFAULT nextval('financial_ratios_id_seq'),
        company_no VARCHAR,
        category VARCHAR,
        item VARCHAR,
        period VARCHAR,
        value VARCHAR,
        last_updated TIMESTAMP,
        UNIQUE(company_no, category, item, period)
    );
    """)
    conn.execute("CREATE SEQUENCE IF NOT EXISTS stock_indicators_id_seq START 1;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS stock_indicators (
        id INTEGER PRIMARY KEY DEFAULT nextval('stock_indicators_id_seq'),
        company_no VARCHAR,
        item VARCHAR,
        period VARCHAR,
        value VARCHAR,
        last_updated TIMESTAMP,
        UNIQUE(company_no, item, period)
    );
    """)

def save_data_to_db(conn, company_no, company_name, company_overview, offering_info, subscription_schedule, business_summary, financial_ratios_df, stock_indicators_df):
    """추출된 모든 데이터를 DuckDB에 저장합니다."""
    now = datetime.now()
    
    # payload에는 모든 텍스트 데이터를 포함시키고, business_summary는 별도 컬럼에도 저장
    payload = {
        "business_summary": clean_text(business_summary), 
        **(company_overview or {}), 
        **(offering_info or {}), 
        **(subscription_schedule or {})
    }
    cleaned_payload = {clean_text(k): clean_text(v) for k, v in payload.items()}
    json_payload = json.dumps(cleaned_payload, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO companies (company_no, company_name, business_summary, data_payload, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (company_no) DO UPDATE SET
            company_name = EXCLUDED.company_name,
            business_summary = EXCLUDED.business_summary,
            data_payload = EXCLUDED.data_payload,
            last_updated = EXCLUDED.last_updated;
        """,
        (company_no, clean_text(company_name), clean_text(business_summary), json_payload, now)
    )

    if financial_ratios_df is not None and not financial_ratios_df.empty:
        conn.execute("DELETE FROM financial_ratios WHERE company_no = ?", (company_no,))
        df_melted = financial_ratios_df.melt(id_vars=['구분', '항목'], var_name='period', value_name='value')
        df_melted.rename(columns={'구분': 'category', '항목': 'item'}, inplace=True)
        df_melted['company_no'] = company_no
        df_melted['last_updated'] = now
        df_melted['value'] = df_melted['value'].astype(str)
        conn.execute("INSERT INTO financial_ratios (company_no, category, item, period, value, last_updated) SELECT company_no, category, item, period, value, last_updated FROM df_melted")

    if stock_indicators_df is not None and not stock_indicators_df.empty:
        conn.execute("DELETE FROM stock_indicators WHERE company_no = ?", (company_no,))
        df_melted = stock_indicators_df.melt(id_vars=['항목'], var_name='period', value_name='value')
        df_melted.rename(columns={'항목': 'item'}, inplace=True)
        df_melted['company_no'] = company_no
        df_melted['last_updated'] = now
        df_melted['value'] = df_melted['value'].astype(str)
        conn.execute("INSERT INTO stock_indicators (company_no, item, period, value, last_updated) SELECT company_no, item, period, value, last_updated FROM df_melted")

# --- 스크래핑 함수 ---

async def extract_key_value_table(page: Page, summary_title):
    try:
        table_element = await page.wait_for_selector(f"//table[@summary='{summary_title}']", timeout=3000)
        data = {}
        rows = await table_element.query_selector_all("tr")
        for row in rows:
            cells = await row.query_selector_all("th, td")
            if len(cells) >= 2:
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        key = (await cells[i].inner_text()).strip()
                        value = (await cells[i+1].inner_text()).strip()
                        if key: data[key] = value
        return data
    except TimeoutError: return None
    except Exception: return None

async def find_and_extract_df_table(page_or_element, title_pattern):
    """
    주어진 페이지나 요소 내에서 제목 패턴을 포함하는 테이블을 찾고,
    그 바로 다음 형제 테이블을 데이터 테이블로 간주하여 DataFrame으로 반환합니다.
    """
    try:
        title_table_selector = f"//table[.//b[contains(text(), '{title_pattern}')] or .//font[contains(text(), '{title_pattern}')]]"
        title_table = await page_or_element.wait_for_selector(f"xpath={title_table_selector}", timeout=3000)

        if not title_table:
            return None

        data_table_selector = f"xpath={title_table_selector}/following-sibling::table[1]"
        data_table = await page_or_element.wait_for_selector(data_table_selector, timeout=3000)

        if not data_table:
            return None
        
        html_content = await data_table.inner_html()
        df_list = pd.read_html(io.StringIO(html_content), header=0, flavor='html5lib')

        if not df_list or df_list[0].empty:
            return None

        df = df_list[0]
        df = df.dropna(how='all').reset_index(drop=True)
        df = df.dropna(axis=1, how='all')

        if "재 무 비 율" in title_pattern:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
            if df.iloc[:, 0].isnull().any():
                df.iloc[:, 0] = df.iloc[:, 0].ffill()
            if len(df.columns) > 1:
                df.rename(columns={df.columns[0]: '구분', df.columns[1]: '항목'}, inplace=True)
        
        elif "주 가 지 표" in title_pattern:
            if len(df.columns) > 0:
                df.rename(columns={df.columns[0]: '항목'}, inplace=True)
        
        return df

    except Exception:
        return None

async def extract_business_summary(page: Page):
    """'1.사업현황' 섹션의 텍스트를 안정적으로 추출합니다."""
    try:
        # '1.사업현황' 텍스트를 포함하는 font 태그가 있는 td 요소를 찾습니다.
        container_td_selector = "xpath=//td[.//font[contains(text(), '1.사업현황')]]"
        container_td = await page.query_selector(container_td_selector)

        if not container_td:
            return None

        full_text = await container_td.inner_text()
        
        # '1.사업현황'과 '2.매출현황' 또는 '3.재무현황' 사이의 텍스트를 추출합니다.
        summary_text = None
        if '1.사업현황' in full_text:
            parts = full_text.split('1.사업현황', 1)
            if len(parts) > 1:
                content_after_start = parts[1]
                if '2.매출현황' in content_after_start:
                    summary_text = content_after_start.split('2.매출현황')[0].strip()
                elif '3.재무현황' in content_after_start:
                    summary_text = content_after_start.split('3.재무현황')[0].strip()
                else:
                    summary_text = content_after_start.strip()
        
        return summary_text

    except Exception:
        return None


async def scrape_company_data(page: Page, company_no: str):
    """주어진 Playwright 페이지 객체를 사용하여 특정 기업의 모든 데이터를 스크래핑합니다."""
    url = f"https://www.38.co.kr/html/fund/?o=v&no={company_no}&l=&page=1"
    await page.goto(url, wait_until="domcontentloaded", timeout=10000)
    
    company_overview = await extract_key_value_table(page, "기업개요")
    if not company_overview or not company_overview.get('종목명'):
        return None # 필수 데이터 없으면 None 반환

    company_name = company_overview.pop('종목명')
    offering_info = await extract_key_value_table(page, "공모정보")
    subscription_schedule = await extract_key_value_table(page, "공모청약일정")
    business_summary = await extract_business_summary(page)

    financial_ratios_df, stock_indicators_df = None, None
    try:
        main_container = await page.wait_for_selector("//td[.//img[@alt='본질가치분석']]", timeout=3000)
        financial_ratios_df = await find_and_extract_df_table(main_container, "재 무 비 율")
        stock_indicators_df = await find_and_extract_df_table(main_container, "주 가 지 표")
    except TimeoutError:
        pass # 재무 정보는 선택 사항

    return {
        "company_name": company_name, "company_overview": company_overview,
        "offering_info": offering_info, "subscription_schedule": subscription_schedule,
        "business_summary": business_summary, "financial_ratios_df": financial_ratios_df,
        "stock_indicators_df": stock_indicators_df
    }

# --- 단일 실행을 위한 Main 함수 ---
async def main(company_no, db_file="ipo_db/ipo_data.db"):
    with duckdb.connect(db_file) as conn:
        create_tables(conn)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                print(f"--- 단일 기업 정보 추출 시작 (No: {company_no}) ---")
                data = await scrape_company_data(page, company_no)
                if data:
                    save_data_to_db(conn, company_no, **data)
                    print(f"--- (No: {company_no}) 정보 저장 완료 ---")
                else:
                    print(f"--- (No: {company_no}) 필수 정보가 없어 저장하지 않음 ---")
            except Exception as e:
                print(f"스크립트 실행 중 오류가 발생했습니다: {e}")
            finally:
                await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="38커뮤니케이션즈에서 IPO 기업 정보를 추출하여 DB에 저장합니다.")
    parser.add_argument("--no", required=True, help="38커뮤니케이션즈의 기업 고유 번호")
    args = parser.parse_args()
    asyncio.run(main(args.no))
