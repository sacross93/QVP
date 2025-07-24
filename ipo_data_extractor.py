"""
38커뮤니케이션즈(38.co.kr)의 IPO 기업 정보 페이지에서 데이터를 추출하는 비동기 스크레이퍼입니다.
Playwright를 사용하여 웹 페이지와 동적으로 상호작용하고, Pandas를 이용해
'기업개요', '재무비율', '주가지표' 테이블 데이터를 추출하고 정제합니다.

이 스크립트는 복잡하고 중첩된 HTML 구조를 안정적으로 파싱하기 위해,
먼저 큰 섹션을 찾고 그 안에서 세부 데이터를 검색하는 방식을 사용합니다.

사용법:
uv run python ipo_data_extractor.py --no <기업코드>

예시:
uv run python ipo_data_extractor.py --no 2204
"""

import asyncio
import argparse
from playwright.async_api import async_playwright
import pandas as pd
import io
import re

async def find_and_extract_table(page_or_element, title_pattern):
    """
    주어진 페이지나 요소 내에서 제목 패턴을 포함하는 테이블을 찾고,
    그 바로 다음 형제 테이블을 데이터 테이블로 간주하여 DataFrame으로 반환합니다.
    """
    print(f"--- '{title_pattern}' 테이블 검색 중 ---")
    try:
        # 제목 텍스트를 포함하는 테이블을 찾음
        title_table_selector = f"//table[.//b[contains(text(), '{title_pattern}')]]"
        title_table = await page_or_element.wait_for_selector(title_table_selector, timeout=5000)

        if not title_table:
            print(f"'{title_pattern}' 제목 테이블을 찾을 수 없습니다.")
            return None

        # 제목 테이블 바로 다음에 오는 형제 테이블(데이터 테이블)을 선택
        data_table_selector = f"{title_table_selector}/following-sibling::table[1]"
        data_table = await page_or_element.wait_for_selector(data_table_selector, timeout=5000)

        if not data_table:
            print(f"'{title_pattern}'에 해당하는 데이터 테이블을 찾을 수 없습니다.")
            return None
        
        html_content = await data_table.inner_html()
        df_list = pd.read_html(io.StringIO(html_content), header=0, flavor='html5lib')

        if not df_list or df_list[0].empty:
            print(f"'{title_pattern}' 테이블에서 데이터를 파싱할 수 없습니다.")
            return None

        df = df_list[0]
        
        # --- 데이터 정제 ---
        df = df.dropna(how='all').reset_index(drop=True)
        df = df.dropna(axis=1, how='all')

        # 각 테이블에 맞는 특화된 정제 로직
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

    except Exception as e:
        print(f"'{title_pattern}' 테이블 추출 중 오류 발생: {e}")
        return None

async def extract_company_overview(page):
    """'기업개요' 테이블에서 회사 정보를 추출하여 딕셔너리로 반환합니다."""
    print("--- 기업개요 정보 추출 중 ---")
    overview_data = {}
    try:
        table_selector = "//table[@summary='기업개요']"
        table_element = await page.wait_for_selector(table_selector, timeout=5000)
        
        rows = await table_element.query_selector_all("tr")
        for row in rows:
            cells = await row.query_selector_all("th, td")
            if len(cells) >= 2:
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        key = (await cells[i].inner_text()).strip()
                        value = (await cells[i+1].inner_text()).strip()
                        if key:
                            overview_data[key] = value
        
        title_element = await page.query_selector("td > font > b")
        if title_element:
            full_title = await title_element.inner_text()
            overview_data['회사명'] = full_title.split('(')[0].strip()

        return overview_data
    except Exception as e:
        print(f"기업개요 추출 중 오류 발생: {e}")
        return overview_data

async def main(company_no):
    """Playwright를 실행하여 지정된 기업의 IPO 정보를 스크레이핑합니다."""
    url = f"https://www.38.co.kr/html/fund/?o=v&no={company_no}&l=&page=1"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        company_name = "알 수 없음"
        try:
            print(f"페이지 로딩 중: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            print("페이지 로딩 완료.")
            
            company_overview = await extract_company_overview(page)
            if company_overview and '회사명' in company_overview:
                company_name = company_overview.pop('회사명')

            # 재무정보 섹션을 포함하는 더 큰 컨테이너를 먼저 찾음
            main_container_selector = "//td[.//img[@alt='본질가치분석']]"
            main_container = await page.wait_for_selector(main_container_selector, timeout=5000)

            if main_container:
                # 컨테이너 내부에서 각 테이블을 검색
                financial_ratios_df = await find_and_extract_table(main_container, "재 무 비 율")
                stock_indicators_df = await find_and_extract_table(main_container, "주 가 지 표")
            else:
                print("재무정보 컨테이너를 찾을 수 없습니다.")
                financial_ratios_df = None
                stock_indicators_df = None

            # --- 결과 출력 ---
            print("\n\n" + "="*60)
            print(f"          {company_name} (종목코드: {company_no}) IPO 데이터 추출 결과")
            print("="*60 + "\n")

            if company_overview:
                print("1. 기업개요")
                items = list(company_overview.items())
                for i in range(0, len(items), 2):
                    col1 = f"- {items[i][0]}: {items[i][1]}"
                    col2 = ""
                    if i + 1 < len(items):
                        col2 = f"- {items[i+1][0]}: {items[i+1][1]}"
                    print(f"{col1:<40}{col2}")
            else:
                print("1. 기업개요: 데이터를 추출하지 못했습니다.")

            if financial_ratios_df is not None and not financial_ratios_df.empty:
                print("\n2. 재무비율")
                print(financial_ratios_df.to_string(index=False))
            else:
                print("\n2. 재무비율: 데이터를 추출하지 못했습니다.")

            if stock_indicators_df is not None and not stock_indicators_df.empty:
                print("\n3. 주가지표")
                print(stock_indicators_df.to_string(index=False))
            else:
                print("\n3. 주가지표: 데이터를 추출하지 못했습니다.")
            
            print("\n" + "="*60)

        except Exception as e:
            print(f"스크립트 실행 중 오류가 발생했습니다: {e}")
        finally:
            await browser.close()
            print("\n브라우저를 종료했습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="38커뮤니케이션즈에서 IPO 기업 정보를 추출합니다.")
    parser.add_argument("--no", required=True, help="38커뮤니케이션즈의 기업 고유 번호 (URL의 no= 값)")
    args = parser.parse_args()
    
    asyncio.run(main(args.no))