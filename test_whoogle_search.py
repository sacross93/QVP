#!/usr/bin/env python3
"""
Whoogle 검색 기능 상세 테스트 스크립트
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth.stealth import Stealth
import time

def test_whoogle_search_detailed():
    """Whoogle 검색 상세 테스트"""
    print("🔍 Whoogle 검색 상세 테스트 시작...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 스텔스 모드 적용
            stealth = Stealth()
            stealth.apply_stealth_sync(page)
            print("✅ 스텔스 모드 적용 완료")
            
            # 검색 URL 직접 접속
            search_url = "http://192.168.110.102:5000/search?q=test"
            print(f"🌐 검색 URL 접속: {search_url}")
            
            # 페이지 이동 시간 측정
            start_time = time.time()
            page.goto(search_url, timeout=60000, wait_until='domcontentloaded')
            load_time = time.time() - start_time
            print(f"✅ 페이지 로딩 완료 (소요시간: {load_time:.2f}초)")
            
            # 페이지 제목 확인
            title = page.title()
            print(f"📄 페이지 제목: {title}")
            
            # 페이지 내용 일부 확인
            body_text = page.locator('body').text_content()
            if body_text:
                print(f"📝 페이지 내용 길이: {len(body_text)} 문자")
                if "test" in body_text.lower():
                    print("✅ 검색어 'test'가 페이지에 포함됨")
                else:
                    print("❌ 검색어 'test'가 페이지에 없음")
            
            # 검색 결과 컨테이너 찾기
            print("🔍 검색 결과 컨테이너 찾는 중...")
            
            # 여러 가능한 선택자 시도
            selectors_to_try = [
                'div.results',
                '.results',
                'div[class*="result"]',
                'div[class*="ezO2md"]',  # curl 결과에서 본 클래스
                '.ezO2md'
            ]
            
            found_results = False
            for selector in selectors_to_try:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        print(f"✅ '{selector}' 선택자로 {len(elements)}개 요소 발견")
                        found_results = True
                        break
                    else:
                        print(f"❌ '{selector}' 선택자로 요소 없음")
                except Exception as e:
                    print(f"❌ '{selector}' 선택자 오류: {e}")
            
            if not found_results:
                print("❌ 검색 결과 컨테이너를 찾을 수 없음")
                # HTML 내용 일부 출력
                html_content = page.content()
                print(f"📄 HTML 길이: {len(html_content)} 문자")
                print("📄 HTML 앞부분 (500자):")
                print(html_content[:500])
                print("...")
                print("📄 HTML 뒷부분 (500자):")
                print(html_content[-500:])
            
            browser.close()
            return found_results
            
    except PlaywrightTimeoutError as e:
        print(f"❌ 타임아웃 오류 (60초): {e}")
        return False
    except Exception as e:
        print(f"❌ 기타 오류: {e}")
        return False

def test_whoogle_search_simple():
    """간단한 검색 테스트 (스텔스 모드 없이)"""
    print("\n🔍 간단한 검색 테스트 (스텔스 모드 없이)...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 검색 URL 직접 접속
            search_url = "http://192.168.110.102:5000/search?q=test"
            print(f"🌐 검색 URL 접속: {search_url}")
            
            start_time = time.time()
            page.goto(search_url, timeout=30000)
            load_time = time.time() - start_time
            print(f"✅ 페이지 로딩 완료 (소요시간: {load_time:.2f}초)")
            
            title = page.title()
            print(f"📄 페이지 제목: {title}")
            
            browser.close()
            return True
            
    except PlaywrightTimeoutError as e:
        print(f"❌ 타임아웃 오류 (30초): {e}")
        return False
    except Exception as e:
        print(f"❌ 기타 오류: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Whoogle 검색 기능 상세 진단")
    print("=" * 60)
    
    # 1. 스텔스 모드 포함 상세 테스트
    detailed_ok = test_whoogle_search_detailed()
    
    # 2. 간단한 테스트 (스텔스 모드 없이)
    simple_ok = test_whoogle_search_simple()
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"상세 테스트 (스텔스 모드): {'✅ 성공' if detailed_ok else '❌ 실패'}")
    print(f"간단 테스트 (스텔스 없음): {'✅ 성공' if simple_ok else '❌ 실패'}")
    
    if simple_ok and not detailed_ok:
        print("\n💡 결론: 스텔스 모드가 문제를 일으키고 있습니다.")
    elif not simple_ok and not detailed_ok:
        print("\n💡 결론: 검색 요청 자체에 문제가 있습니다.")
    elif detailed_ok:
        print("\n💡 결론: 모든 기능이 정상입니다. 원래 스크립트의 다른 부분에 문제가 있을 수 있습니다.") 