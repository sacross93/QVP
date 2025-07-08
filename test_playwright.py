#!/usr/bin/env python3
"""
Playwright 기본 동작 테스트 스크립트
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def test_playwright_basic():
    """Playwright 기본 동작 테스트"""
    print("🔍 Playwright 기본 동작 테스트 시작...")
    
    try:
        with sync_playwright() as p:
            print("✅ Playwright 초기화 성공")
            
            browser = p.chromium.launch(headless=True)
            print("✅ Chromium 브라우저 실행 성공")
            
            page = browser.new_page()
            print("✅ 새 페이지 생성 성공")
            
            # 간단한 테스트 페이지 접속
            print("🌐 Google 접속 테스트...")
            page.goto("https://www.google.com", timeout=30000)
            print("✅ Google 접속 성공")
            
            # 페이지 제목 확인
            title = page.title()
            print(f"📄 페이지 제목: {title}")
            
            browser.close()
            print("✅ 브라우저 종료 성공")
            
        print("🎉 Playwright 기본 동작 테스트 완료 - 모든 기능 정상!")
        return True
        
    except PlaywrightTimeoutError as e:
        print(f"❌ Playwright 타임아웃 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ Playwright 오류: {e}")
        return False

def test_whoogle_access():
    """Whoogle 접속 테스트"""
    print("\n🔍 Whoogle 접속 테스트 시작...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Whoogle 메인 페이지 접속
            whoogle_url = "http://192.168.110.102:5000"
            print(f"🌐 Whoogle 메인 페이지 접속: {whoogle_url}")
            page.goto(whoogle_url, timeout=30000)
            print("✅ Whoogle 메인 페이지 접속 성공")
            
            # 페이지 제목 확인
            title = page.title()
            print(f"📄 페이지 제목: {title}")
            
            # 검색 폼이 있는지 확인
            search_input = page.query_selector('input[name="q"]')
            if search_input:
                print("✅ 검색 입력 폼 발견")
            else:
                print("❌ 검색 입력 폼을 찾을 수 없음")
            
            browser.close()
            print("✅ Whoogle 접속 테스트 완료")
            return True
            
    except PlaywrightTimeoutError as e:
        print(f"❌ Whoogle 접속 타임아웃: {e}")
        return False
    except Exception as e:
        print(f"❌ Whoogle 접속 오류: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Playwright 진단 테스트")
    print("=" * 50)
    
    # 1. 기본 동작 테스트
    basic_ok = test_playwright_basic()
    
    # 2. Whoogle 접속 테스트
    if basic_ok:
        whoogle_ok = test_whoogle_access()
        
        if not whoogle_ok:
            print("\n💡 결론: Playwright는 정상이지만 Whoogle과의 호환성 문제가 있습니다.")
    else:
        print("\n💡 결론: Playwright 자체에 문제가 있습니다.") 