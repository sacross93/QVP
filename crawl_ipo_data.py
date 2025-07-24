import asyncio
import sys
import json
from playwright.async_api import async_playwright

async def crawl_ipo_data(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)

        data = {}

        # Helper function to extract table data
        async def extract_table_data(table_element):
            rows = await table_element.query_selector_all("tr")
            table_data = {}
            for row in rows:
                cols = await row.query_selector_all("td")
                if len(cols) >= 2:
                    key = (await cols[0].inner_text()).strip()
                    value = (await cols[1].inner_text()).strip()
                    table_data[key] = value
            return table_data

        # Helper function to extract data from a section identified by its header
        async def extract_section_data(section_title_text):
            # Find the td element containing the section title
            section_title_td = await page.query_selector(f"td:has-text(\"{section_title_text}\")")
            
            if section_title_td:
                # Get the closest parent table of this td
                header_table = await section_title_td.evaluate_handle('(element) => element.closest("table")');
                
                if header_table:
                    # Start from the next sibling of the header table
                    current_element = await header_table.evaluate_handle('(element) => element.nextElementSibling');
                    
                    while current_element: # Loop only if current_element is not null
                        tag_name = await current_element.evaluate('(element) => element.tagName');
                        if tag_name == 'TABLE':
                            # Check if this table contains actual data rows (more than just headers)
                            rows = await current_element.query_selector_all("tr")
                            if len(rows) > 1: # Assuming data tables have more than one row (header + data)
                                return await extract_table_data(current_element)
                        
                        # Move to the next sibling
                        current_element = await current_element.evaluate_handle('(element) => element.nextElementSibling');
            return {}

        # Extract 기업개요
        data['기업개요'] = await extract_section_data('기업개요')

        # Extract 공모 정보
        data['공모 정보'] = await extract_section_data('공모정보')

        # Extract 청약일정
        data['청약일정'] = await extract_section_data('공모청약일정')

        # Extract 재무비율
        data['재무비율'] = await extract_section_data('재 무 비 율')

        # Extract 주가지표
        data['주가지표'] = await extract_section_data('주 가 지 표')

        # Extract 공모분석 - 사업현황
        business_status_text = []
        # Find the paragraph containing '1.사업현황'
        business_status_heading = await page.query_selector("p:has-text(\"1.사업현황\")")
        if business_status_heading:
            current_element = await business_status_heading.evaluate_handle('(element) => element.nextElementSibling');
            while current_element: # Loop only if current_element is not null
                tag_name = await current_element.evaluate('(element) => element.tagName');
                text_content = await current_element.evaluate('(element) => element.textContent.trim()');
                # Stop when the next section starts (e.g., '2.매출현황') or if it's not a paragraph
                if tag_name == 'P' and not text_content.startswith('2.매출현황') and not text_content.startswith('3.재무현황') and not text_content.startswith('4.공모후 유통가능 물량') and not text_content.startswith('5.요약재무제표') and not text_content.startswith('6.동종업체와의 재무정보 비교'):
                    business_status_text.append(text_content)
                elif text_content.startswith('2.매출현황') or text_content.startswith('3.재무현황') or text_content.startswith('4.공모후 유통가능 물량') or text_content.startswith('5.요약재무제표') or text_content.startswith('6.동종업체와의 재무정보 비교'):
                    break
                current_element = await current_element.evaluate_handle('(element) => element.nextElementSibling');
        data['공모분석_사업현황'] = "\n".join(business_status_text)

        await browser.close()
        return data

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ipo_no = sys.argv[1]
    else:
        ipo_no = "2194" # Default IPO number

    url = f"https://www.38.co.kr/html/fund/?o=v&no={ipo_no}&l=&page=1"
    extracted_data = asyncio.run(crawl_ipo_data(url))
    print(json.dumps(extracted_data, ensure_ascii=False, indent=4))