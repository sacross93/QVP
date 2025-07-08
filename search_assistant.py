#!/usr/bin/env python3
"""
Whoogle 기반 검색 정보 정리 도구
내부 Whoogle 인스턴스(http://192.168.110.102:5000)를 사용하여 웹 검색을 수행하고, 
그 결과를 Local LLM으로 정리합니다.

**사용법:**
uv run search_assistant.py "검색어"

**사용 예시:**
uv run search_assistant.py "파이썬 FastAPI"
uv run search_assistant.py "AI 최신 동향" --num-results 15
"""

import sys
import json
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth.stealth import Stealth
from bs4 import BeautifulSoup
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


def setup_llm():
    """Local LLM 설정"""
    return ChatOllama(
        model="qwen3:32b",
        base_url="http://192.168.120.102:11434",
        temperature=0.3
    )


def search_web(query: str, num_results: int = 1):
    """
    Whoogle 인스턴스를 Playwright를 사용하여 검색하고 결과를 파싱합니다.
    (고정된 주소: http://192.168.110.102:5000)

    Args:
        query: 검색어
        num_results: 가져올 검색 결과의 수

    Returns:
        (list, str): 검색 결과 리스트와 성공한 검색 타입 ('whoogle')
    """
    whoogle_url = "http://192.168.110.102:5000"
    search_url = f"{whoogle_url}/search?q={query}"
    
    print(f"ℹ️ Playwright로 Whoogle 검색을 시도합니다: {search_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 스텔스 모드 적용 (클래스 기반)
            stealth = Stealth()
            stealth.apply_stealth_sync(page)
            
            # 페이지로 이동하고, 타임아웃을 20초로 설정
            page.goto(search_url, timeout=20000, wait_until='domcontentloaded')
            
            # 검색 결과 컨테이너가 나타날 때까지 최대 10초 대기
            page.wait_for_selector('div[class*="ezO2md"]', timeout=10000)
            
            html_content = page.content()
            browser.close()

        soup = BeautifulSoup(html_content, 'html.parser')
        
        results = []
        # 실제 Whoogle HTML 구조에 맞는 선택자 사용
        result_nodes = soup.select('div[class*="ezO2md"]')

        if not result_nodes:
            print("⚠️ Playwright로 페이지를 로드했지만, 검색 결과를 찾을 수 없습니다.")
            return [], None

        for i, node in enumerate(result_nodes):
            if i >= num_results:
                break
            
            # 실제 Whoogle HTML 구조에 맞는 파싱
            title_tag = node.find('a', class_='fuLhoc ZWRArf')
            if not title_tag:
                title_tag = node.find('a')
            
            link_tag = title_tag
            snippet_tag = node.find('span', class_='fYyStc')

            title = title_tag.get_text(strip=True) if title_tag else "제목을 찾을 수 없음"
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
            
            if link and not link.startswith('http'):
                from urllib.parse import urljoin
                link = urljoin(whoogle_url, link)

            if link and '/url?q=' in link:
                from urllib.parse import unquote, urlparse, parse_qs
                parsed_link = urlparse(link)
                link = parse_qs(parsed_link.query).get('q', [""])[0]

            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "요약을 찾을 수 없음"

            results.append({'title': title, 'snippet': snippet, 'link': link})
        
        print(f"✅ Playwright를 통해 Whoogle에서 {len(results)}개의 결과 획득")
        return results, "whoogle"

    except PlaywrightTimeoutError:
        print("❌ Whoogle 페이지 로딩 시간 초과 (20초). 서버가 응답하지 않거나, Whoogle의 봇 탐지에 의해 차단되었을 수 있습니다.")
        return [], None
    except Exception as e:
        print(f"❌ Playwright 실행 중 오류 발생: {e}")
        return [], None


def create_summary_prompt():
    """검색 결과 정리용 프롬프트 템플릿 생성"""
    
    prompt_template = """
당신은 전문적인 정보 분석가입니다. 주어진 검색 결과를 바탕으로 검색어에 대한 포괄적이고 정확한 정보를 한국어로 정리해주세요.

검색어: {query}

검색 결과:
{search_results}

다음 형식으로 정리해주세요:

# {query}에 대한 정보 정리

## 📋 요약
(핵심 내용을 2-3줄로 요약)

## 🔍 주요 정보
(가장 중요한 정보들을 불릿 포인트로 정리)

## 📊 세부 내용
(구체적인 데이터, 사실, 배경 정보 등을 자세히 설명)

## 🔗 참고 자료
(검색 결과에서 유용한 링크들을 제공)

**주의사항:**
- 검색 결과에 기반한 정확한 정보만 제공하세요
- 추측이나 가정은 피하고 사실만 기술하세요
- 출처가 명확한 정보를 우선적으로 사용하세요
- 한국어로 자연스럽게 작성하세요
"""
    
    return PromptTemplate.from_template(prompt_template)


def format_search_results(results):
    """검색 결과를 텍스트 형태로 포맷팅"""
    formatted_results = []
    
    for i, result in enumerate(results, 1):
        formatted_result = f"""
--- 결과 {i} ---
제목: {result.get('title', 'N/A')}
내용: {result.get('snippet', 'N/A')}
링크: {result.get('link', 'N/A')}
"""
        formatted_results.append(formatted_result)
    
    return "\n".join(formatted_results)


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="DuckDuckGo 검색 결과를 LLM으로 정리해주는 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  uv run search_assistant.py "파이썬 FastAPI"
  uv run search_assistant.py "AI 뉴스" --search-type simple --num-results 5
  uv run search_assistant.py "코로나 백신" --region kr-ko --time-range week
  uv run search_assistant.py "기술 동향" --search-type api --safesearch off

검색 타입:
  detailed: 상세한 JSON 결과 (제목, 요약, 링크) - 기본값
  simple: 간단한 텍스트 결과
  api: API 래퍼를 통한 고급 검색

지역 설정:
  wt-wt: 전 세계 (기본값)
  us-en: 미국 (영어)
  kr-ko: 한국 (한국어)
  jp-jp: 일본 (일본어)
  gb-en: 영국 (영어)

시간 범위:
  day: 최근 하루
  week: 최근 일주일
  month: 최근 한 달
  year: 최근 일년
  (빈 값): 모든 시간 - 기본값
        """
    )
    
    parser.add_argument("query", help="검색할 키워드")
    parser.add_argument("--num-results", type=int, default=1, 
                       help="가져올 검색 결과의 수 (기본값: 1)")
    
    args = parser.parse_args()
    
    if not args.query:
        print("❌ 검색어를 입력해주세요.")
        print("사용법: uv run search_assistant.py \"검색어\"")
        return
    
    # 검색 설정 정보 출력
    print(f"🔍 '{args.query}' 검색 중...")
    print(f"📊 검색 설정:")
    print(f"   - Whoogle URL: http://192.168.110.102:5000")
    print(f"   - 결과 개수: {args.num_results}")
    
    # 웹 검색 수행
    search_results, successful_type = search_web(
        args.query,
        args.num_results
    )
    
    if not search_results:
        print("❌ 최종적으로 검색 결과를 찾을 수 없습니다.")
        print("💡 해결 방법:")
        print("   1. Whoogle 컨테이너가 http://192.168.110.102:5000 에서 정상적으로 실행 중인지 확인하세요.")
        print("   2. 검색어를 변경해보세요.")
        print("   3. `playwright install --with-deps`가 제대로 실행되었는지 확인하세요.")
        return
    
    if successful_type != "whoogle":
        print(f"\nℹ️ 참고: 요청하신 'whoogle' 타입 검색에 실패하여 '{successful_type}' 타입으로 결과를 가져왔습니다.")

    print(f"\n✅ {len(search_results)}개의 검색 결과를 바탕으로 LLM 정리 시작...")
    
    # LLM 설정
    try:
        llm = setup_llm()
    except Exception as e:
        print(f"❌ LLM 연결 오류: {e}")
        print("Local LLM 서버가 실행 중인지 확인해주세요.")
        return
    
    # 검색 결과 정리 (성공한 타입 기준으로 프롬프트 생성)
    formatted_results = format_search_results(search_results)
    prompt = create_summary_prompt()
    
    chain = prompt | llm | StrOutputParser()
    
    try:
        summary = chain.invoke({
            "query": args.query,
            "search_results": formatted_results
        })
        
        print("\n" + "=" * 50)
        print("📝 정리된 정보")
        print("=" * 50)
        print(summary)
        
    except Exception as e:
        print(f"❌ 정보 정리 중 오류 발생: {e}")
        print("\n📋 원시 검색 결과:")
        for i, result in enumerate(search_results, 1):
            print(f"\n--- 결과 {i} ---")
            print(f"제목: {result.get('title', 'N/A')}")
            print(f"내용: {result.get('snippet', 'N/A')}")
            print(f"링크: {result.get('link', 'N/A')}")


if __name__ == "__main__":
    main() 