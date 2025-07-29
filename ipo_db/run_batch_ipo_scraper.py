"""
[Optimized] IPO 데이터 대량 수집 스크립트 (1 ~ 5000)

동시성(Concurrency)을 활용하여 스크래핑 속도를 대폭 개선한 버전입니다.
`asyncio.Semaphore`를 사용하여 동시에 실행할 작업 수를 제어함으로써,
대상 서버의 부하를 줄이고 안정적으로 데이터를 수집합니다.

[주요 기능]
- 여러 기업 정보를 동시에 스크래핑하여 작업 시간을 단축합니다.
- DB에 이미 존재하는 기업 정보는 건너뜁니다.
- 스크래핑 시 필수 데이터가 없으면 저장하지 않습니다.
- 진행 상황과 최종 결과를 요약하여 보여줍니다.
"""
import asyncio
import duckdb
from playwright.async_api import async_playwright, Browser
import tqdm
import time
from collections import Counter

# 다른 파일에서 함수 임포트
from save_ipo_data_to_db import create_tables, scrape_company_data, save_data_to_db

# --- 설정 ---
DB_FILE = "ipo_db/ipo_data.db"
START_NO = 1
END_NO = 5000
# 동시에 실행할 최대 작업 수. 너무 높게 설정하면 서버에 부담을 주거나 차단될 수 있습니다. (5 ~ 10 권장)
CONCURRENCY_LIMIT = 10 

async def worker(semaphore: asyncio.Semaphore, browser: Browser, company_no: str):
    """
    세마포어로 제어되는 작업자 함수.
    독립적인 브라우저 컨텍스트에서 단일 기업 정보를 처리합니다.
    """
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # with-as 구문으로 DB 연결을 작업 단위로 관리
            with duckdb.connect(DB_FILE) as conn:
                data = await scrape_company_data(page, company_no)
                if data:
                    save_data_to_db(conn, company_no, **data)
                    return "저장 완료"
                else:
                    return "필수 정보 없음"
        except TimeoutError:
            return "타임아웃"
        except Exception as e:
            error_message = str(e).replace('\n', ' ')
            return f"오류: {error_message[:70]}"
        finally:
            await context.close()

async def main():
    """메인 실행 함수"""
    start_time = time.time()
    print(f"--- IPO 데이터 대량 수집 시작 (동시 작업 수: {CONCURRENCY_LIMIT}) ---")
    
    with duckdb.connect(DB_FILE) as conn:
        create_tables(conn)
        try:
            existing_nos_df = conn.execute("SELECT company_no FROM companies").fetchdf()
            existing_nos = set(existing_nos_df['company_no'].astype(str).tolist())
            print(f"현재 DB에 저장된 기업 수: {len(existing_nos)}")
        except duckdb.CatalogException:
            existing_nos = set()
            print("신규 DB. 처음부터 수집을 시작합니다.")

    # 처리해야 할 기업 번호 목록 준비
    numbers_to_process = [str(i) for i in range(START_NO, END_NO + 1) if str(i) not in existing_nos]
    
    if not numbers_to_process:
        print("새롭게 처리할 기업이 없습니다. 작업을 종료합니다.")
        return

    print(f"총 {len(numbers_to_process)}개의 신규 기업 정보를 수집합니다.")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        tasks = [worker(semaphore, browser, num) for num in numbers_to_process]
        
        results = []
        # tqdm을 사용하여 실시간 진행률 표시
        for f in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="수집 진행률"):
            results.append(await f)
            
        await browser.close()

    end_time = time.time()
    
    # --- 최종 결과 출력 ---
    counts = Counter(results)
    
    print("\n" + "="*50)
    print("          최종 수집 결과 요약")
    print("="*50)
    print(f"총 실행 시간: {time.strftime('%H시간 %M분 %S초', time.gmtime(end_time - start_time))}")
    print(f"총 시도한 신규 기업 수: {len(numbers_to_process)}개")
    print("-" * 50)
    print(f"성공 (신규 추가): {counts['저장 완료']} 건")
    print(f"실패 (필수 정보 없음): {counts['필수 정보 없음']} 건")
    print(f"실패 (타임아웃): {counts['타임아웃']} 건")
    # 기타 오류 상세 출력
    error_count = sum(1 for r in results if r.startswith("오류"))
    print(f"실패 (기타 오류): {error_count} 건")
    print("="*50)
    print("--- 모든 작업 완료 ---")

if __name__ == "__main__":
    try:
        import tqdm
    except ImportError:
        print("tqdm 라이브러리가 필요합니다. 'pip install tqdm' 명령어로 설치해주세요.")
        exit()
        
    asyncio.run(main())