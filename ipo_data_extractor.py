
"""
38커뮤니케이션즈(38.co.kr)의 IPO 기업 정보 페이지에서 데이터를 추출하는 비동기 스크레이퍼입니다.
Playwright를 사용하여 웹 페이지와 동적으로 상호작용하고, Pandas를 이용해
'기업개요', '공모정보', '공모청약일정', '재무비율', '주가지표' 테이블 데이터를 추출하고, '사업현황' 텍스트를 추출합니다.

이 스크립트는 복잡하고 중첩된 HTML 구조를 안정적으로 파싱하기 위해,
각 정보 섹션의 특성에 맞는 맞춤형 추출 함수를 사용합니다.

사용법:
uv run python ipo_data_extractor.py --no <기업코드>

예시:
uv run python ipo_data_extractor.py --no 2194
"""

import asyncio
import argparse
from playwright.async_api import async_playwright, TimeoutError
import pandas as pd
import io

async def extract_key_value_table(page, summary_title):
    """'summary' 속성을 기준으로 테이블을 찾아 key-value 쌍의 딕셔너리로 반환합니다."""
    print(f"--- '{summary_title}' 정보 추출 중 ---")
    try:
        table_selector = f"//table[@summary='{summary_title}']"
        table_element = await page.wait_for_selector(f"xpath={table_selector}", timeout=5000)
        
        data = {}
        rows = await table_element.query_selector_all("tr")
        for row in rows:
            cells = await row.query_selector_all("th, td")
            if len(cells) >= 2:
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        key = (await cells[i].inner_text()).strip()
                        value = (await cells[i+1].inner_text()).strip()
                        if key:
                            # 복잡한 '공모사항' 키의 중복을 피하고 내용을 합칩니다.
                            if "공모사항" in key and "공모사항" in data:
                                data["공모사항"] += "\n" + value
                            else:
                                data[key] = value
        return data
    except TimeoutError:
        print(f"'{summary_title}' 테이블을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"'{summary_title}' 정보 추출 중 오류 발생: {e}")
        return None

async def find_and_extract_df_table(page_or_element, title_pattern):
    """
    주어진 페이지나 요소 내에서 제목 패턴을 포함하는 테이블을 찾고,
    그 바로 다음 형제 테이블을 데이터 테이블로 간주하여 DataFrame으로 반환합니다.
    """
    print(f"--- '{title_pattern}' 테이블 검색 중 ---")
    try:
        title_table_selector = f"//table[.//b[contains(text(), '{title_pattern}')] or .//font[contains(text(), '{title_pattern}')]]"
        title_table = await page_or_element.wait_for_selector(f"xpath={title_table_selector}", timeout=5000)

        if not title_table:
            print(f"'{title_pattern}' 제목 테이블을 찾을 수 없습니다.")
            return None

        data_table_selector = f"xpath={title_table_selector}/following-sibling::table[1]"
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

    except Exception as e:
        print(f"'{title_pattern}' 테이블 추출 중 오류 발생: {e}")
        return None

async def extract_business_summary(page):
    """'사업현황' 정보를 추출하여 텍스트로 반환합니다."""
    print("--- 사업현황 정보 추출 중 ---")
    try:
        # '1.사업현황' 텍스트를 포함하는 strong 태그를 찾습니다.
        summary_element = await page.query_selector("xpath=//strong[contains(text(), '1.사업현황')]")
        if not summary_element:
             print("'사업현황' 정보를 찾을 수 없습니다.")
             return None

        # strong 태그의 부모의 부모인 td 요소에서 전체 텍스트를 가져옵니다.
        parent_td = await summary_element.query_selector("xpath=./../..")
        full_text = await parent_td.inner_text()
        
        # '1.사업현황' 부터 '2.매출현황' 전까지의 텍스트를 추출합니다.
        summary_text = full_text.split('1.사업현황')[1].split('2.매출현황')[0].strip()
        return summary_text
    except TimeoutError:
        print("'사업현황' 정보를 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"사업현황 추출 중 오류 발생: {e}")
        return None

def print_dict_data(title, data):
    """딕셔너리 형태의 데이터를 2열로 예쁘게 출력합니다."""
    if data:
        print(f"\n{title}")
        items = list(data.items())
        for i in range(0, len(items), 2):
            val1 = str(items[i][1]).replace('\n', ' ').replace('\t', ' ')
            col1 = f"- {items[i][0]}: {val1}"
            
            col2 = ""
            if i + 1 < len(items):
                val2 = str(items[i+1][1]).replace('\n', ' ').replace('\t', ' ')
                col2 = f"- {items[i+1][0]}: {val2}"
            print(f"{col1:<45}{col2}")
    else:
        print(f"\n{title}: 데이터를 추출하지 못했습니다.")

async def main(company_no):
    url = f"https://www.38.co.kr/html/fund/?o=v&no={company_no}&l=&page=1"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        company_name = "알 수 없음"
        try:
            print(f"페이지 로딩 중: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            print("페이지 로딩 완료.")

            # --- 데이터 추출 ---
            company_overview = await extract_key_value_table(page, "기업개요")
            if company_overview and '종목명' in company_overview:
                company_name = company_overview.pop('종목명')
            
            offering_info = await extract_key_value_table(page, "공모정보")
            subscription_schedule = await extract_key_value_table(page, "공모청약일정")
            business_summary = await extract_business_summary(page)

            financial_ratios_df = None
            stock_indicators_df = None
            try:
                main_container_selector = "//td[.//img[@alt='본질가치분석']]"
                main_container = await page.wait_for_selector(f"xpath={main_container_selector}", timeout=5000)
                if main_container:
                    financial_ratios_df = await find_and_extract_df_table(main_container, "재 무 비 율")
                    stock_indicators_df = await find_and_extract_df_table(main_container, "주 가 지 표")
            except TimeoutError:
                print("본질가치분석 테이블을 찾을 수 없어 재무정보 추출을 건너뜁니다.")

            # --- 결과 출력 ---
            print("\n\n" + "="*60)
            print(f"          {company_name} (종목코드: {company_no}) IPO 데이터 추출 결과")
            print("="*60)

            print_dict_data("1. 기업개요", company_overview)
            print_dict_data("2. 공모정보", offering_info)
            print_dict_data("3. 공모청약일정", subscription_schedule)

            if business_summary:
                print("\n4. 사업현황")
                print(business_summary)
            else:
                print("\n4. 사업현황: 데이터를 추출하지 못했습니다.")

            if financial_ratios_df is not None and not financial_ratios_df.empty:
                print("\n5. 재무비율")
                print(financial_ratios_df.to_string(index=False))
            else:
                print("\n5. 재무비율: 데이터를 추출하지 못했습니다.")

            if stock_indicators_df is not None and not stock_indicators_df.empty:
                print("\n6. 주가지표")
                print(stock_indicators_df.to_string(index=False))
            else:
                print("\n6. 주가지표: 데이터를 추출하지 못했습니다.")
            
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
