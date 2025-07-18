#!/usr/bin/env python3
"""
Innoforest Stealth 크롤러
https://www.innoforest.co.kr/ 사이트 크롤링용

기능:
- Stealth 모드 브라우저 초기화
- 사이트 접속 및 기본 정보 수집
- Human 탐지 우회 기능
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('innoforest_stealth_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InnoforestStealthCrawler:
    """
    Innoforest Stealth 크롤러 클래스
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.session_file = "innoforest_stealth_browser_state.json"
        self.cookies_file = "innoforest_stealth_cookies.json"
        
    def _generate_random_headers(self):
        """
        랜덤 브라우저 헤더 생성 (Human 탐지 우회)
        """
        chrome_versions = [
            "126.0.0.0", "127.0.0.0", "128.0.0.0", 
            "129.0.0.0", "130.0.0.0", "131.0.0.0"
        ]
        
        os_list = [
            "Windows NT 10.0; Win64; x64",
            "Macintosh; Intel Mac OS X 10_15_7",
            "X11; Linux x86_64"
        ]
        
        chrome_version = random.choice(chrome_versions)
        os_info = random.choice(os_list)
        
        user_agent = f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': f'"Chromium";v="{chrome_version.split(".")[0]}", "Google Chrome";v="{chrome_version.split(".")[0]}", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{os_info.split(";")[0] if ";" in os_info else "Windows"}"'
        }
        
        logger.info(f"🎭 랜덤 헤더 생성: Chrome {chrome_version}, OS: {os_info.split(';')[0] if ';' in os_info else os_info}")
        return headers

    async def _simulate_human_behavior(self):
        """
        인간 행동 시뮬레이션
        """
        try:
            # 1. 마우스 움직임 시뮬레이션
            await self._simulate_mouse_movement()
            
            # 2. 스크롤 시뮬레이션
            await self._simulate_scroll()
            
            # 3. 페이지 읽기 시뮬레이션
            await self._simulate_page_reading()
            
        except Exception as e:
            logger.warning(f"인간 행동 시뮬레이션 실패: {e}")

    async def _simulate_scroll(self):
        """
        자연스러운 스크롤 시뮬레이션
        """
        try:
            logger.info("📜 스크롤 시뮬레이션 시작")
            
            # 페이지 높이 확인
            page_height = await self.page.evaluate("document.body.scrollHeight")
            viewport_height = await self.page.evaluate("window.innerHeight")
            
            if page_height > viewport_height:
                # 3-5번의 랜덤 스크롤
                scroll_count = random.randint(3, 5)
                
                for i in range(scroll_count):
                    # 랜덤한 스크롤 거리
                    scroll_distance = random.randint(200, 500)
                    
                    await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                    
                    # 스크롤 후 대기 (1-2초)
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # 맨 위로 돌아가기
                await self.page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                
            logger.info("📜 스크롤 시뮬레이션 완료")
            
        except Exception as e:
            logger.warning(f"스크롤 시뮬레이션 실패: {e}")

    async def _simulate_mouse_movement(self):
        """
        자연스러운 마우스 움직임 시뮬레이션
        """
        try:
            logger.info("🖱️ 마우스 움직임 시뮬레이션")
            
            # 뷰포트 크기 가져오기
            viewport_size = self.page.viewport_size
            width = viewport_size['width']
            height = viewport_size['height']
            
            # 3-5회 랜덤 마우스 움직임
            move_count = random.randint(3, 5)
            
            for i in range(move_count):
                x = random.randint(50, width - 50)
                y = random.randint(50, height - 50)
                
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            logger.warning(f"마우스 움직임 시뮬레이션 실패: {e}")

    async def _simulate_page_reading(self):
        """
        페이지 읽기 시뮬레이션 (체류 시간)
        """
        try:
            # 3-7초 체류
            reading_time = random.uniform(3.0, 7.0)
            logger.info(f"📖 페이지 읽기 시뮬레이션: {reading_time:.1f}초")
            
            await asyncio.sleep(reading_time)
            
        except Exception as e:
            logger.warning(f"페이지 읽기 시뮬레이션 실패: {e}")

    async def initialize(self, headless=True, use_saved_state=True):
        """
        Stealth 브라우저 초기화
        """
        try:
            logger.info("🥷 Innoforest Stealth 모드로 브라우저 초기화 중...")
            
            # 랜덤 헤더 생성
            headers = self._generate_random_headers()
            
            playwright = await async_playwright().start()
            
            # 강화된 브라우저 인수 (탐지 우회)
            browser_args = [
                '--no-zygote',
                '--single-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-popup-blocking',
                '--disable-translate',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-device-discovery-notifications',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--enable-features=NetworkService,NetworkServiceLogging',
                '--disable-background-networking',
                '--disable-sync',
                '--disable-extensions',
                '--disable-component-extensions-with-background-pages',
                '--disable-component-update',
                '--disable-client-side-phishing-detection',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-domain-reliability',
                '--disable-features=VizDisplayCompositor',
                '--user-agent=' + headers['User-Agent']
            ]
            
            self.browser = await playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )
            
            # 브라우저 컨텍스트 생성
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': headers['User-Agent'],
                'extra_http_headers': headers,
                'java_script_enabled': True,
                'accept_downloads': True,
                'ignore_https_errors': True,
                'permissions': ['geolocation']
            }
            
            # 저장된 세션 복원 시도
            if use_saved_state and Path(self.session_file).exists():
                try:
                    logger.info("저장된 Innoforest Stealth 세션 발견 - 복원 중...")
                    context_options['storage_state'] = self.session_file
                    self.context = await self.browser.new_context(**context_options)
                    logger.info("✅ Innoforest Stealth 세션 복원 완료")
                except Exception as e:
                    logger.warning(f"세션 복원 실패: {e} - 새 세션 생성")
                    self.context = await self.browser.new_context(**context_options)
            else:
                self.context = await self.browser.new_context(**context_options)
            
            # 새 페이지 생성
            self.page = await self.context.new_page()
            
            # 강화된 탐지 우회 스크립트 주입
            await self.page.add_init_script("""
                // WebDriver 탐지 제거
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Chrome 자동화 객체 삭제
                delete window.chrome.runtime;
                
                // Permissions API 조작
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Plugin 배열 조작
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Languages 배열 조작
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                });
                
                // WebGL 벤더 정보 조작
                const getParameter = WebGLRenderingContext.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel(R) Iris(TM) Graphics 6100';
                    }
                    return getParameter(parameter);
                };
                
                // Console.debug 숨기기
                const originalLog = console.log;
                console.log = function() {
                    if (arguments[0] && arguments[0].includes && arguments[0].includes('DevTools')) {
                        return;
                    }
                    originalLog.apply(console, arguments);
                };
            """)
            
            logger.info("✅ Innoforest Stealth 브라우저 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ Innoforest 브라우저 초기화 실패: {e}")
            return False

    async def navigate_to_innoforest(self):
        """
        Innoforest 사이트 접속
        """
        try:
            logger.info("🥷 Stealth 모드로 Innoforest 사이트 접속: https://www.innoforest.co.kr/")
            
            # Referer 설정 (구글에서 온 것처럼)
            await self.page.set_extra_http_headers({
                'Referer': 'https://www.google.com/search?q=innoforest'
            })
            logger.info("🔗 Referer 설정: https://www.google.com/search?q=innoforest")
            
            # 접속 전 랜덤 대기 (2-5초)
            wait_time = random.uniform(2.0, 5.0)
            logger.info(f"🤔 접속 전 대기 시간: {wait_time:.1f}초")
            await asyncio.sleep(wait_time)
            
            # 사이트 접속 시도 (최대 3회)
            for attempt in range(1, 4):
                try:
                    logger.info(f"Innoforest 접속 시도 {attempt}/3")
                    
                    response = await self.page.goto(
                        "https://www.innoforest.co.kr/",
                        wait_until="domcontentloaded",
                        timeout=30000
                    )
                    
                    if response and response.status < 400:
                        logger.info("✅ Innoforest Stealth 모드 접속 성공!")
                        break
                    else:
                        logger.warning(f"⚠️ 접속 응답 상태: {response.status if response else 'None'}")
                        
                except Exception as e:
                    logger.warning(f"❌ 접속 시도 {attempt} 실패: {e}")
                    if attempt < 3:
                        await asyncio.sleep(random.uniform(3.0, 6.0))
                    else:
                        raise e
            
            # 페이지 로딩 대기
            logger.info("Innoforest 페이지 로딩 대기 중...")
            await asyncio.sleep(3)
            
            # 인간 행동 시뮬레이션
            await self._simulate_human_behavior()
            
            # 페이지 정보 확인
            title = await self.page.title()
            url = self.page.url
            
            logger.info(f"📄 페이지 제목: {title}")
            logger.info(f"🌐 현재 URL: {url}")
            
            # 초기 접속 후 팝업 확인 및 닫기
            await self.close_popup_if_exists()
            
            # 스크린샷 저장
            await self.take_screenshot("innoforest_stealth_initial.png")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Innoforest 사이트 접속 실패: {e}")
            return False

    async def check_stealth_effectiveness(self):
        """
        Stealth 모드 효과 확인
        """
        try:
            logger.info("🔍 Innoforest Stealth 모드 효과 확인 중...")
            
            # WebDriver 탐지 확인
            webdriver_detected = await self.page.evaluate("navigator.webdriver")
            logger.info(f"🤖 WebDriver 탐지: {webdriver_detected}")
            
            # User Agent 확인
            user_agent = await self.page.evaluate("navigator.userAgent")
            logger.info(f"👤 User Agent: {user_agent}")
            
            # 플러그인 수 확인
            plugins_length = await self.page.evaluate("navigator.plugins.length")
            logger.info(f"🔌 플러그인 개수: {plugins_length}")
            
            # 언어 설정 확인
            languages = await self.page.evaluate("navigator.languages")
            logger.info(f"🌍 언어 설정: {languages}")
            
            return {
                "webdriver_detected": webdriver_detected,
                "user_agent": user_agent,
                "plugins_count": plugins_length,
                "languages": languages
            }
            
        except Exception as e:
            logger.error(f"❌ Stealth 효과 확인 실패: {e}")
            return None

    async def save_stealth_session(self):
        """
        현재 세션 상태 저장
        """
        try:
            await self.context.storage_state(path=self.session_file)
            logger.info(f"💾 Innoforest Stealth 세션 저장: {self.session_file}")
            
            # 쿠키도 별도 저장
            cookies = await self.context.cookies()
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"🍪 Innoforest 쿠키 저장: {self.cookies_file}")
            
        except Exception as e:
            logger.error(f"❌ Innoforest 세션 저장 실패: {e}")

    async def take_screenshot(self, filename="innoforest_stealth_screenshot.png"):
        """
        스크린샷 저장
        """
        try:
            await self.page.screenshot(path=filename)
            logger.info(f"📸 Innoforest Stealth 스크린샷 저장: {filename}")
        except Exception as e:
            logger.error(f"❌ 스크린샷 저장 실패: {e}")

    async def close_popup_if_exists(self):
        """
        팝업이 있으면 닫기 (상시 확인용)
        """
        try:
            logger.info("🔍 팝업 확인 중...")
            
            # 팝업 닫기 버튼 찾기 (SVG path를 포함한 버튼)
            popup_close_selectors = [
                # SVG path를 포함한 다양한 선택자들
                'svg path[d="M17 17L1 1"]',
                'button svg path[d="M17 17L1 1"]',
                'div svg path[d="M17 17L1 1"]',
                # 상위 요소들도 확인
                'svg:has(path[d="M17 17L1 1"])',
                'button:has(svg path[d="M17 17L1 1"])',
                'div:has(svg path[d="M17 17L1 1"])',
                # 일반적인 팝업 닫기 버튼들
                'button[aria-label*="close"]',
                'button[aria-label*="닫기"]',
                '[class*="close"]',
                '[class*="modal"] button',
                '.modal-close',
                '.popup-close',
                # X 버튼 관련
                'button:has(svg)',
                '[role="dialog"] button',
                '.dialog button'
            ]
            
            popup_closed = False
            for selector in popup_close_selectors:
                try:
                    close_button = self.page.locator(selector)
                    button_count = await close_button.count()
                    
                    if button_count > 0:
                        # 버튼이 보이는지 확인
                        is_visible = await close_button.first.is_visible()
                        if is_visible:
                            logger.info(f"🔍 팝업 닫기 버튼 발견: {selector}")
                            await close_button.first.click()
                            logger.info("✅ 팝업 닫기 버튼 클릭 완료")
                            await asyncio.sleep(1)
                            popup_closed = True
                            break
                except Exception as e:
                    logger.debug(f"팝업 버튼 확인 중 오류 ({selector}): {e}")
                    continue
            
            if popup_closed:
                logger.info("🎯 팝업이 성공적으로 닫혔습니다")
                return True
            else:
                logger.debug("ℹ️ 팝업이 없거나 이미 닫혀있습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 팝업 확인 중 오류: {e}")
            return False

    async def check_if_logged_in(self):
        """
        로그인 상태 확인
        """
        try:
            logger.info("🔍 Innoforest 로그인 상태 확인 중...")
            
            # 먼저 팝업 확인 및 닫기
            await self.close_popup_if_exists()
            
            # 로그인 버튼이 있는지 확인 (로그인 안된 상태)
            login_button_exists = await self.page.locator('a[href="/login"]').count() > 0
            
            if login_button_exists:
                logger.info("❌ 로그인이 필요합니다")
                return False
            else:
                logger.info("✅ 이미 로그인된 상태입니다")
                return True
                
        except Exception as e:
            logger.error(f"❌ 로그인 상태 확인 실패: {e}")
            return False

    async def perform_login(self, email="jgpark@jch.kr", password="jch2025@#"):
        """
        Innoforest 로그인 수행
        """
        try:
            logger.info("🔐 Innoforest 로그인 시작...")
            
            # 1. 로그인 버튼 클릭 (로그인 페이지로 이동)
            logger.info("👆 로그인 버튼 클릭 중...")
            login_link = self.page.locator('a[href="/login"]')
            
            if await login_link.count() > 0:
                await login_link.click()
                logger.info("✅ 로그인 페이지로 이동 완료")
                
                # 페이지 로딩 대기
                await asyncio.sleep(2)
                
                # 로그인 폼 확인
                await self.page.wait_for_selector('input[name="email"]', timeout=10000)
                logger.info("📋 로그인 폼 로딩 완료")
            else:
                logger.warning("⚠️ 로그인 버튼을 찾을 수 없습니다")
                return False
            
            # 2. 이메일 입력
            logger.info(f"📧 이메일 입력: {email}")
            email_input = self.page.locator('input[name="email"]')
            await email_input.clear()
            await email_input.fill(email)
            await asyncio.sleep(1)
            
            # 3. 비밀번호 입력
            logger.info("🔑 비밀번호 입력...")
            password_input = self.page.locator('input[name="password"]')
            await password_input.clear()
            await password_input.fill(password)
            await asyncio.sleep(1)
            
            # 4. 로그인 버튼 클릭
            logger.info("🚀 로그인 버튼 클릭...")
            login_submit_button = self.page.locator('#__next > main > div.css-10ieela > div > div > form > div.css-2banuq > button')
            
            if await login_submit_button.count() > 0:
                await login_submit_button.click()
                logger.info("✅ 로그인 버튼 클릭 완료")
            else:
                logger.warning("⚠️ 로그인 제출 버튼을 찾을 수 없습니다")
                return False
            
            # 5. 로그인 결과 확인
            logger.info("⏳ 로그인 처리 대기 중...")
            await asyncio.sleep(3)
            
            # 로그인 성공 확인 (로그인 버튼이 사라졌는지 확인)
            login_button_still_exists = await self.page.locator('a[href="/login"]').count() > 0
            
            if not login_button_still_exists:
                logger.info("🎉 Innoforest 로그인 성공!")
                
                # 6. 팝업 확인 및 닫기
                logger.info("🔍 로그인 후 팝업 확인 중...")
                await asyncio.sleep(2)  # 팝업이 나타날 시간 대기
                
                # 팝업 닫기 함수 호출
                await self.close_popup_if_exists()
                
                # 로그인 후 스크린샷 (팝업 처리 후)
                await self.take_screenshot("innoforest_after_login.png")
                
                # 세션 저장
                await self.save_stealth_session()
                
                return True
            else:
                logger.error("❌ Innoforest 로그인 실패")
                
                # 실패 스크린샷
                await self.take_screenshot("innoforest_login_failed.png")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Innoforest 로그인 중 오류 발생: {e}")
            
            # 오류 스크린샷
            await self.take_screenshot("innoforest_login_error.png")
            
            return False

    def get_search_keyword_from_user(self):
        """
        사용자로부터 검색할 회사 이름 입력받기 (동기 함수)
        """
        try:
            print("\n" + "="*50)
            print("🔍 Innoforest 스타트업 검색")
            print("="*50)
            print("검색할 스타트업/기업명을 입력해주세요.")
            print("예시: 로보스, 십일리터, 토스, 카카오 등")
            print("-"*50)
            
            while True:
                keyword = input("🏢 검색할 스타트업 이름: ").strip()
                
                if not keyword:
                    print("❌ 검색어를 입력해주세요!")
                    continue
                
                if len(keyword) > 60:
                    print("❌ 검색어는 60자 이하로 입력해주세요!")
                    continue
                
                # 확인
                print(f"\n📝 입력된 검색어: '{keyword}'")
                confirm = input("이 검색어로 검색하시겠습니까? (y/n): ").strip().lower()
                
                if confirm in ['y', 'yes', '예', 'ㅇ']:
                    return keyword
                elif confirm in ['n', 'no', '아니오', 'ㄴ']:
                    continue
                else:
                    print("y 또는 n을 입력해주세요.")
                    continue
                    
        except KeyboardInterrupt:
            print("\n❌ 사용자에 의해 취소되었습니다.")
            return None

    async def search_startup(self, keyword):
        """
        Innoforest에서 스타트업 검색
        """
        try:
            logger.info(f"🔍 '{keyword}' 검색 시작...")
            
            # 팝업 확인 및 닫기
            await self.close_popup_if_exists()
            
            # 검색창 찾기 및 클릭
            search_selectors = [
                'input[placeholder="검색어를 입력해 보세요"]',
                'input[type="text"][placeholder*="검색"]',
                'input[placeholder*="검색"]',
                '.search-input',
                '[class*="search"] input'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    input_element = self.page.locator(selector)
                    if await input_element.count() > 0:
                        is_visible = await input_element.first.is_visible()
                        if is_visible:
                            search_input = input_element.first
                            logger.info(f"✅ 검색창 발견: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"검색창 찾기 실패 ({selector}): {e}")
                    continue
            
            if not search_input:
                logger.error("❌ 검색창을 찾을 수 없습니다")
                return False
            
            # 검색창 클릭 및 포커스
            await search_input.click()
            await asyncio.sleep(2)  # 1초 -> 2초로 증가
            
            # 기존 내용 지우기
            await search_input.clear()
            await asyncio.sleep(1)  # 0.5초 -> 1초로 증가
            
            # 검색어 입력
            logger.info(f"⌨️ 검색어 입력: '{keyword}'")
            await search_input.fill(keyword)
            await asyncio.sleep(2)  # 1초 -> 2초로 증가
            
            # Enter 키로 검색 실행
            logger.info("🚀 Enter 키로 검색 실행...")
            await search_input.press('Enter')
            
            # 검색 결과 로딩 대기 (더 긴 시간)
            logger.info("⏳ 검색 결과 로딩 대기 중...")
            await asyncio.sleep(5)  # 3초 -> 5초로 증가
            
            # 추가 대기 시간 (페이지 완전 로딩)
            logger.info("⏳ 페이지 완전 로딩을 위한 추가 대기...")
            await asyncio.sleep(3)  # 3초 추가 대기
            
            # 팝업 다시 확인 (검색 후 팝업이 나타날 수 있음)
            await self.close_popup_if_exists()
            
            # 검색 결과 스크린샷
            await self.take_screenshot(f"innoforest_search_results_{keyword.replace(' ', '_')}.png")
            
            logger.info(f"✅ '{keyword}' 검색 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ '{keyword}' 검색 실패: {e}")
            
            # 오류 스크린샷
            await self.take_screenshot(f"innoforest_search_error_{keyword.replace(' ', '_')}.png")
            
            return False

    async def check_search_results(self, keyword):
        """
        검색 결과 확인
        """
        try:
            logger.info(f"🔍 '{keyword}' 검색 결과 확인 중...")
            
            # 검색 결과 로딩 완료를 위한 추가 대기
            logger.info("⏳ 검색 결과 완전 로딩 대기 중... (3초)")
            await asyncio.sleep(3.0)
            
            # 네트워크 요청 완료 대기
            try:
                await self.page.wait_for_load_state('networkidle', timeout=5000)
                logger.info("✅ 네트워크 요청 완료 확인")
            except Exception as e:
                logger.info(f"⏳ 네트워크 대기 시간 초과 (계속 진행): {e}")
                await asyncio.sleep(2.0)  # 네트워크 대기 실패 시 추가 대기
            
            # 검색 결과 관련 선택자들
            result_selectors = [
                '.search-result',
                '[class*="result"]',
                '[class*="company"]',
                '.startup-card',
                '.company-card',
                'ul li',
                '[role="listitem"]'
            ]
            
            total_results = 0
            for selector in result_selectors:
                try:
                    results = self.page.locator(selector)
                    count = await results.count()
                    if count > 0:
                        logger.info(f"📊 검색 결과 발견: {selector} - {count}개")
                        total_results = max(total_results, count)
                        break
                except Exception as e:
                    logger.debug(f"검색 결과 확인 실패 ({selector}): {e}")
                    continue
            
            if total_results > 0:
                logger.info(f"✅ 총 {total_results}개의 검색 결과 발견")
                return True
            else:
                logger.warning("⚠️ 검색 결과를 찾을 수 없습니다")
                
                # 검색 결과가 없는 경우 추가 진단
                try:
                    page_content = await self.page.content()
                    
                    # "검색 결과 없음" 관련 메시지 확인
                    no_results_messages = [
                        "검색 결과가 없습니다",
                        "검색된 결과가 없습니다", 
                        "결과를 찾을 수 없습니다",
                        "No results found",
                        "검색어와 일치하는",
                        "해당하는 기업이 없습니다",
                        "검색 결과 0건",
                        "조회된 결과가 없습니다"
                    ]
                    
                    if any(msg in page_content for msg in no_results_messages):
                        logger.info(f"📋 페이지에서 '검색 결과 없음' 메시지 확인됨")
                    else:
                        logger.info(f"📋 검색 결과 페이지 구조를 파악하지 못했습니다")
                        
                        # 검색이 제대로 실행되었는지 확인
                        if keyword.lower() in page_content.lower():
                            logger.info(f"📋 페이지에 검색어 '{keyword}'가 포함되어 있습니다")
                        else:
                            logger.warning(f"📋 페이지에 검색어 '{keyword}'가 없습니다 - 검색이 제대로 실행되지 않았을 수 있습니다")
                    
                    # 검색 결과 없음 스크린샷 저장
                    await self.take_screenshot(f"innoforest_no_search_results_{keyword.replace(' ', '_')}.png")
                    logger.info(f"📸 검색 결과 없음 스크린샷 저장")
                
                except Exception as e:
                    logger.debug(f"페이지 내용 분석 실패: {e}")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ 검색 결과 확인 실패: {e}")
            return False

    async def click_first_search_result(self, keyword):
        """
        검색 결과에서 첫 번째 회사 클릭하여 상세 페이지로 이동
        """
        try:
            logger.info(f"🖱️ '{keyword}' 검색 결과 첫 번째 회사 클릭...")
            
            # 검색 결과 테이블 완전 로딩 대기
            logger.info("⏳ 검색 결과 테이블 로딩 대기 중... (2초)")
            await asyncio.sleep(2.0)
            
            # 팝업 확인 및 닫기
            await self.close_popup_if_exists()
            
            # 첫 번째 검색 결과 클릭 선택자들
            first_result_selectors = [
                '#__next > main > div > div.css-7kga4p > div > div:nth-child(1) > table > tbody > tr > td.css-17ct3ww > a',
                '#__next > main > div > div > div > div:nth-child(1) > table > tbody > tr > td > a',
                'table tbody tr:first-child td a',
                'table tbody tr:first-child a',
                '.css-17ct3ww a',
                'tbody tr:first-child td a'
            ]
            
            first_result_link = None
            for selector in first_result_selectors:
                try:
                    link_element = self.page.locator(selector)
                    if await link_element.count() > 0:
                        is_visible = await link_element.first.is_visible()
                        if is_visible:
                            first_result_link = link_element.first
                            logger.info(f"✅ 첫 번째 검색 결과 링크 발견: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"첫 번째 결과 링크 찾기 실패 ({selector}): {e}")
                    continue
            
            if not first_result_link:
                logger.error("❌ 첫 번째 검색 결과 링크를 찾을 수 없습니다")
                
                # 검색 결과가 실제로 있는지 다시 확인
                try:
                    # 검색 결과 테이블이나 리스트가 있는지 확인
                    result_indicators = [
                        'table tbody tr',
                        'ul li',
                        '.search-result',
                        '[class*="result"]',
                        '[class*="company"]'
                    ]
                    
                    has_results = False
                    for indicator in result_indicators:
                        try:
                            elements = self.page.locator(indicator)
                            count = await elements.count()
                            if count > 0:
                                has_results = True
                                logger.info(f"📊 검색 결과 요소 발견: {indicator} - {count}개")
                                break
                        except Exception as e:
                            logger.debug(f"결과 확인 실패 ({indicator}): {e}")
                            continue
                    
                    if not has_results:
                        logger.warning(f"⚠️ '{keyword}'에 대한 검색 결과가 없는 것으로 보입니다")
                    else:
                        logger.warning(f"⚠️ '{keyword}' 검색 결과는 있지만 클릭 가능한 링크를 찾을 수 없습니다")
                        
                        # 페이지 내용에서 "결과 없음" 메시지 확인
                        page_content = await self.page.content()
                        no_results_messages = [
                            "검색 결과가 없습니다",
                            "검색된 결과가 없습니다", 
                            "결과를 찾을 수 없습니다",
                            "No results found",
                            "검색어와 일치하는",
                            "해당하는 기업이 없습니다"
                        ]
                        
                        if any(msg in page_content for msg in no_results_messages):
                            logger.warning(f"⚠️ 페이지에서 '검색 결과 없음' 메시지 발견")
                        else:
                            logger.info(f"📄 페이지에 검색 결과가 있는 것으로 보이지만 구조 파악 실패")
                
                except Exception as content_e:
                    logger.debug(f"검색 결과 재확인 실패: {content_e}")
                
                # 오류 스크린샷 저장
                try:
                    await self.take_screenshot(f"innoforest_no_result_{keyword.replace(' ', '_')}.png")
                    logger.info(f"📸 검색 결과 없음 스크린샷 저장: innoforest_no_result_{keyword.replace(' ', '_')}.png")
                except Exception as screenshot_e:
                    logger.debug(f"스크린샷 저장 실패: {screenshot_e}")
                
                return False
            
            # 링크 텍스트 확인 (회사명 로깅용)
            try:
                link_text = await first_result_link.text_content()
                if link_text:
                    logger.info(f"🏢 클릭할 회사명: '{link_text.strip()}'")
            except Exception as e:
                logger.debug(f"링크 텍스트 확인 실패: {e}")
            
            # 첫 번째 검색 결과 클릭
            logger.info("👆 첫 번째 검색 결과 클릭 중...")
            await first_result_link.click()
            
            # 페이지 로딩 대기 (더 긴 시간)
            logger.info("⏳ 회사 상세 페이지 로딩 대기 중...")
            await asyncio.sleep(5)  # 3초 -> 5초로 증가
            
            # 추가 대기 시간 (상세 페이지 완전 로딩)
            logger.info("⏳ 상세 페이지 완전 로딩을 위한 추가 대기...")
            await asyncio.sleep(3)  # 3초 추가 대기
            
            # 팝업 다시 확인 (상세 페이지 진입 후 팝업이 나타날 수 있음)
            await self.close_popup_if_exists()
            
            # 상세 페이지 진입 확인
            current_url = self.page.url
            logger.info(f"🌐 현재 URL: {current_url}")
            
            # 상세 페이지 스크린샷
            await self.take_screenshot(f"innoforest_company_detail_{keyword.replace(' ', '_')}.png")
            
            logger.info(f"✅ '{keyword}' 첫 번째 검색 결과 클릭 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ '{keyword}' 첫 번째 검색 결과 클릭 실패: {e}")
            
            # 오류 스크린샷
            await self.take_screenshot(f"innoforest_click_error_{keyword.replace(' ', '_')}.png")
            
            return False

    async def extract_company_info(self, keyword):
        """
        회사 상세 페이지에서 정보 추출 (주요정보 포함)
        """
        try:
            logger.info(f"📊 '{keyword}' 회사 정보 추출 중...")
            
            # 페이지 안정화를 위한 추가 대기
            logger.info("⏳ 페이지 안정화를 위한 대기...")
            await asyncio.sleep(3)
            
            # 팝업 확인 및 닫기
            await self.close_popup_if_exists()
            
            company_info = {
                'keyword': keyword,
                'url': self.page.url,
                'extracted_at': datetime.now().isoformat()
            }
            
            # 회사명 추출
            company_name_selectors = [
                'h1',
                '.company-name',
                '[class*="company"] h1',
                '[class*="title"] h1',
                'header h1'
            ]
            
            for selector in company_name_selectors:
                try:
                    name_element = self.page.locator(selector)
                    if await name_element.count() > 0:
                        company_name = await name_element.first.text_content()
                        if company_name and company_name.strip():
                            company_info['company_name'] = company_name.strip()
                            logger.info(f"🏢 회사명: {company_name.strip()}")
                            break
                except Exception as e:
                    logger.debug(f"회사명 추출 실패 ({selector}): {e}")
                    continue
            
            # 페이지 제목 확인
            try:
                page_title = await self.page.title()
                if page_title:
                    company_info['page_title'] = page_title
                    logger.info(f"📄 페이지 제목: {page_title}")
            except Exception as e:
                logger.debug(f"페이지 제목 확인 실패: {e}")
            
            # 주요정보 추출
            main_info = await self.extract_main_info()
            if main_info:
                company_info['main_info'] = main_info
                logger.info(f"📈 주요정보 추출 성공: {len(main_info)}개 항목")
            
            # 손익 정보 추출 (예외처리 강화)
            try:
                profit_loss_info = await self.extract_profit_loss_info()
                if profit_loss_info:
                    company_info['profit_loss'] = profit_loss_info
                    logger.info(f"💰 손익정보 추출 성공: {len(profit_loss_info)}개 항목")
                else:
                    company_info['profit_loss'] = None
                    logger.warning("⚠️ 손익정보가 없거나 추출할 수 없습니다")
            except Exception as e:
                company_info['profit_loss'] = None
                logger.error(f"❌ 손익정보 추출 중 오류: {e}")
            
            # 재무 정보 추출 (예외처리 강화)
            try:
                financial_info = await self.extract_financial_info()
                if financial_info:
                    company_info['financial'] = financial_info
                    logger.info(f"💼 재무정보 추출 성공: {len(financial_info)}개 항목")
                else:
                    company_info['financial'] = None
                    logger.warning("⚠️ 재무정보가 없거나 추출할 수 없습니다")
            except Exception as e:
                company_info['financial'] = None
                logger.error(f"❌ 재무정보 추출 중 오류: {e}")
            
            # 투자유치 정보 추출 (예외처리 강화)
            try:
                investment_info = await self.extract_investment_info()
                if investment_info:
                    company_info['investment'] = investment_info
                    logger.info(f"💰 투자유치정보 추출 성공: 요약 {len(investment_info.get('summary', {}))}개 항목, 상세 {len(investment_info.get('details', []))}건")
                else:
                    company_info['investment'] = None
                    logger.warning("⚠️ 투자유치정보가 없거나 추출할 수 없습니다")
            except Exception as e:
                company_info['investment'] = None
                logger.error(f"❌ 투자유치정보 추출 중 오류: {e}")
            
            # 보도자료 정보 추출 (예외처리 강화)
            try:
                news_info = await self.extract_news_info()
                if news_info:
                    company_info['news'] = news_info
                    logger.info(f"📰 보도자료 추출 성공: {len(news_info)}건")
                else:
                    company_info['news'] = None
                    logger.warning("⚠️ 보도자료가 없거나 추출할 수 없습니다")
            except Exception as e:
                company_info['news'] = None
                logger.error(f"❌ 보도자료 추출 중 오류: {e}")
            
            logger.info(f"✅ '{keyword}' 회사 정보 추출 완료")
            return company_info
            
        except Exception as e:
            logger.error(f"❌ '{keyword}' 회사 정보 추출 실패: {e}")
            return None

    async def extract_main_info(self):
        """
        주요정보 섹션에서 상세 데이터 추출
        """
        try:
            logger.info("📊 주요정보 섹션 추출 중...")
            
            # 주요정보 섹션 찾기 (더 정확한 selector 사용)
            main_info_selectors = [
                '.css-1s5aaxq',  # dl 컨테이너 (제공된 HTML 기준)
                '.css-17jidve',  # dl 요소 직접
                'dl.css-17jidve',
                'div:has(h2:has-text("주요정보")) + div dl',
                'div:has(h2:has-text("주요정보")) dl',
                '.css-vfwno5 dl'
            ]
            
            main_info_dl = None
            for selector in main_info_selectors:
                try:
                    dl_element = self.page.locator(selector)
                    if await dl_element.count() > 0:
                        main_info_dl = dl_element.first
                        logger.info(f"✅ 주요정보 DL 요소 발견: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"주요정보 DL 찾기 실패 ({selector}): {e}")
                    continue
            
            if not main_info_dl:
                logger.warning("⚠️ 주요정보 DL 요소를 찾을 수 없습니다")
                return None
            
            main_info_data = {}
            
            # 방법 1: .css-198bnr5 클래스로 각 정보 항목 추출
            info_items = main_info_dl.locator('.css-198bnr5')
            item_count = await info_items.count()
            
            logger.info(f"📋 정보 항목 발견: {item_count}개")
            
            if item_count > 0:
                for i in range(item_count):
                    try:
                        item = info_items.nth(i)
                        
                        # dt (제목) - 첫 번째 텍스트만 추출
                        dt = item.locator('dt.css-0')
                        if await dt.count() > 0:
                            dt_text = await dt.first.text_content()
                            # 첫 줄만 가져오기 (설명 텍스트 제거)
                            key = dt_text.strip().split('\n')[0].strip() if dt_text else None
                        else:
                            key = None
                        
                        # dd (값)
                        dd = item.locator('dd.css-3qsen1')
                        if await dd.count() > 0:
                            dd_text = await dd.first.text_content()
                            value = dd_text.strip() if dd_text else None
                        else:
                            value = None
                        
                        if key and value:
                            main_info_data[key] = value
                            logger.info(f"  📌 {key}: {value}")
                    
                    except Exception as e:
                        logger.debug(f"항목 {i} 추출 실패: {e}")
                        continue
            
            # 방법 2: 전체 페이지에서 특정 키워드로 검색
            if not main_info_data or len(main_info_data) < 6:
                logger.info("📊 추가 방법으로 주요정보 추출 시도...")
                
                # 특정 정보 항목들을 직접 찾기
                info_keys = ["자본금", "고용인원", "누적투자유치금액", "투자유치건수", "연매출", "기술등급"]
                
                for key in info_keys:
                    try:
                        # dt에서 키워드를 포함하는 요소 찾기
                        dt_with_key = self.page.locator(f'dt:has-text("{key}")')
                        
                        if await dt_with_key.count() > 0:
                            # 해당 dt의 부모 요소에서 dd 찾기
                            parent_div = dt_with_key.first.locator('..')
                            dd_element = parent_div.locator('dd')
                            
                            if await dd_element.count() > 0:
                                value = await dd_element.first.text_content()
                                if value:
                                    main_info_data[key] = value.strip()
                                    logger.info(f"  📌 {key}: {value.strip()}")
                    
                    except Exception as e:
                        logger.debug(f"키워드 '{key}' 검색 실패: {e}")
                        continue
            
            # 방법 3: XPath를 사용한 추출
            if not main_info_data or len(main_info_data) < 6:
                logger.info("📊 XPath 방법으로 주요정보 추출 시도...")
                
                try:
                    # XPath로 dt/dd 쌍 찾기
                    dt_elements = self.page.locator('//dt[contains(@class, "css-0")]')
                    dt_count = await dt_elements.count()
                    
                    for i in range(dt_count):
                        try:
                            dt = dt_elements.nth(i)
                            dt_text = await dt.text_content()
                            
                            if dt_text:
                                key = dt_text.strip().split('\n')[0].strip()
                                
                                # 해당 dt의 형제 dd 찾기
                                dd = dt.locator('+ dd')
                                if await dd.count() > 0:
                                    dd_text = await dd.first.text_content()
                                    if dd_text and key:
                                        value = dd_text.strip()
                                        main_info_data[key] = value
                                        logger.info(f"  📌 {key}: {value}")
                        
                        except Exception as e:
                            logger.debug(f"XPath 항목 {i} 추출 실패: {e}")
                            continue
                
                except Exception as e:
                    logger.debug(f"XPath 방법 실패: {e}")
            
            if main_info_data:
                logger.info(f"✅ 주요정보 추출 완료: {len(main_info_data)}개 항목")
                return main_info_data
            else:
                logger.warning("⚠️ 주요정보 데이터를 추출할 수 없습니다")
                
                # 디버깅을 위한 페이지 소스 일부 확인
                try:
                    page_content = await self.page.content()
                    if "주요정보" in page_content:
                        logger.info("📄 페이지에 '주요정보' 텍스트가 존재합니다")
                    if "자본금" in page_content:
                        logger.info("📄 페이지에 '자본금' 텍스트가 존재합니다")
                except Exception as e:
                    logger.debug(f"페이지 내용 확인 실패: {e}")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ 주요정보 추출 실패: {e}")
            return None

    async def extract_profit_loss_info(self):
        """
        손익 정보 테이블 추출
        """
        try:
            logger.info("💰 손익정보 섹션 추출 중...")
            
            # 손익 테이블 찾기
            profit_loss_selectors = [
                '#dataroom14 > div > div > div:nth-child(1) > div > div.css-1s5aaxq > div.css-6y0nmk',
                '#dataroom14 div:nth-child(1) .css-6y0nmk',
                'div:has(table) .css-6y0nmk:first-of-type',
                '.css-6y0nmk table:has(td:has-text("매출액"))',
                'table:has(td:has-text("매출액"))'
            ]
            
            profit_loss_table = None
            for selector in profit_loss_selectors:
                try:
                    table_element = self.page.locator(selector)
                    if await table_element.count() > 0:
                        profit_loss_table = table_element.first
                        logger.info(f"✅ 손익 테이블 발견: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"손익 테이블 찾기 실패 ({selector}): {e}")
                    continue
            
            if not profit_loss_table:
                logger.warning("⚠️ 손익 테이블을 찾을 수 없습니다")
                
                # 페이지에 손익 관련 텍스트가 있는지 확인
                try:
                    page_content = await self.page.content()
                    if any(keyword in page_content for keyword in ["매출액", "영업이익", "순이익"]):
                        logger.info("📄 페이지에 손익 관련 텍스트는 존재하지만 테이블을 찾지 못했습니다")
                    else:
                        logger.info("📄 페이지에 손익 관련 데이터가 없는 것으로 보입니다")
                except Exception as e:
                    logger.debug(f"페이지 내용 확인 실패: {e}")
                
                return None
            
            # 테이블 데이터 추출
            profit_loss_data = {}
            
            try:
                # 헤더 추출 (년도 정보)
                headers = []
                try:
                    header_cells = profit_loss_table.locator('thead tr th')
                    header_count = await header_cells.count()
                    
                    if header_count == 0:
                        logger.warning("⚠️ 손익 테이블 헤더를 찾을 수 없습니다")
                        return None
                    
                    for i in range(header_count):
                        try:
                            header_text = await header_cells.nth(i).text_content()
                            if header_text:
                                headers.append(header_text.strip())
                        except Exception as e:
                            logger.debug(f"헤더 {i} 추출 실패: {e}")
                            headers.append(f"헤더{i}")
                    
                    logger.info(f"📋 손익 테이블 헤더: {headers}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 손익 테이블 헤더 추출 실패: {e}")
                    headers = ["구분", "연도1", "연도2", "연도3"]  # 기본값
                
                # 데이터 행 추출
                try:
                    rows = profit_loss_table.locator('tbody tr')
                    row_count = await rows.count()
                    
                    if row_count == 0:
                        logger.warning("⚠️ 손익 테이블에 데이터 행이 없습니다")
                        return None
                    
                    for i in range(row_count):
                        try:
                            row = rows.nth(i)
                            cells = row.locator('td')
                            cell_count = await cells.count()
                            
                            if cell_count > 0:
                                # 첫 번째 셀은 항목명
                                try:
                                    item_name = await cells.nth(0).text_content()
                                    if item_name and item_name.strip():
                                        item_name = item_name.strip()
                                        profit_loss_data[item_name] = {}
                                        
                                        # 나머지 셀들은 년도별 데이터
                                        for j in range(1, min(cell_count, len(headers))):
                                            try:
                                                year_header = headers[j] if j < len(headers) else f"연도{j}"
                                                cell_value = await cells.nth(j).text_content()
                                                if cell_value and cell_value.strip():
                                                    profit_loss_data[item_name][year_header] = cell_value.strip()
                                                else:
                                                    profit_loss_data[item_name][year_header] = "-"
                                            except Exception as e:
                                                logger.debug(f"셀 {j} 추출 실패: {e}")
                                                profit_loss_data[item_name][f"연도{j}"] = "-"
                                        
                                        logger.info(f"  📌 {item_name}: {profit_loss_data[item_name]}")
                                    
                                except Exception as e:
                                    logger.debug(f"항목명 추출 실패 (행 {i}): {e}")
                                    continue
                            
                        except Exception as e:
                            logger.debug(f"행 {i} 처리 실패: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ 손익 테이블 데이터 행 처리 실패: {e}")
                    return None
                
                if profit_loss_data:
                    logger.info(f"✅ 손익정보 추출 완료: {len(profit_loss_data)}개 항목")
                    return profit_loss_data
                else:
                    logger.warning("⚠️ 손익 데이터를 추출할 수 없습니다")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ 손익 테이블 파싱 실패: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 손익정보 추출 실패: {e}")
            return None

    async def extract_financial_info(self):
        """
        재무 정보 테이블 추출
        """
        try:
            logger.info("💼 재무정보 섹션 추출 중...")
            
            # 재무 테이블 찾기
            financial_selectors = [
                '#dataroom14 > div > div > div:nth-child(2) > div > div.css-1s5aaxq > div.css-6y0nmk',
                '#dataroom14 div:nth-child(2) .css-6y0nmk',
                'div:has(table) .css-6y0nmk:nth-of-type(2)',
                '.css-6y0nmk table:has(td:has-text("자산"))',
                'table:has(td:has-text("자산"))'
            ]
            
            financial_table = None
            for selector in financial_selectors:
                try:
                    table_element = self.page.locator(selector)
                    if await table_element.count() > 0:
                        financial_table = table_element.first
                        logger.info(f"✅ 재무 테이블 발견: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"재무 테이블 찾기 실패 ({selector}): {e}")
                    continue
            
            if not financial_table:
                logger.warning("⚠️ 재무 테이블을 찾을 수 없습니다")
                
                # 페이지에 재무 관련 텍스트가 있는지 확인
                try:
                    page_content = await self.page.content()
                    if any(keyword in page_content for keyword in ["자산", "부채", "자본"]):
                        logger.info("📄 페이지에 재무 관련 텍스트는 존재하지만 테이블을 찾지 못했습니다")
                    else:
                        logger.info("📄 페이지에 재무 관련 데이터가 없는 것으로 보입니다")
                except Exception as e:
                    logger.debug(f"페이지 내용 확인 실패: {e}")
                
                return None
            
            # 테이블 데이터 추출
            financial_data = {}
            
            try:
                # 헤더 추출 (년도 정보)
                headers = []
                try:
                    header_cells = financial_table.locator('thead tr th')
                    header_count = await header_cells.count()
                    
                    if header_count == 0:
                        logger.warning("⚠️ 재무 테이블 헤더를 찾을 수 없습니다")
                        return None
                    
                    for i in range(header_count):
                        try:
                            header_text = await header_cells.nth(i).text_content()
                            if header_text:
                                headers.append(header_text.strip())
                        except Exception as e:
                            logger.debug(f"헤더 {i} 추출 실패: {e}")
                            headers.append(f"헤더{i}")
                    
                    logger.info(f"📋 재무 테이블 헤더: {headers}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 재무 테이블 헤더 추출 실패: {e}")
                    headers = ["구분", "연도1", "연도2", "연도3"]  # 기본값
                
                # 데이터 행 추출
                try:
                    rows = financial_table.locator('tbody tr')
                    row_count = await rows.count()
                    
                    if row_count == 0:
                        logger.warning("⚠️ 재무 테이블에 데이터 행이 없습니다")
                        return None
                    
                    for i in range(row_count):
                        try:
                            row = rows.nth(i)
                            cells = row.locator('td')
                            cell_count = await cells.count()
                            
                            if cell_count > 0:
                                # 첫 번째 셀은 항목명
                                try:
                                    item_name = await cells.nth(0).text_content()
                                    if item_name and item_name.strip():
                                        item_name = item_name.strip()
                                        financial_data[item_name] = {}
                                        
                                        # 나머지 셀들은 년도별 데이터
                                        for j in range(1, min(cell_count, len(headers))):
                                            try:
                                                year_header = headers[j] if j < len(headers) else f"연도{j}"
                                                cell_value = await cells.nth(j).text_content()
                                                if cell_value and cell_value.strip():
                                                    financial_data[item_name][year_header] = cell_value.strip()
                                                else:
                                                    financial_data[item_name][year_header] = "-"
                                            except Exception as e:
                                                logger.debug(f"셀 {j} 추출 실패: {e}")
                                                financial_data[item_name][f"연도{j}"] = "-"
                                        
                                        logger.info(f"  📌 {item_name}: {financial_data[item_name]}")
                                    
                                except Exception as e:
                                    logger.debug(f"항목명 추출 실패 (행 {i}): {e}")
                                    continue
                            
                        except Exception as e:
                            logger.debug(f"행 {i} 처리 실패: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ 재무 테이블 데이터 행 처리 실패: {e}")
                    return None
                
                if financial_data:
                    logger.info(f"✅ 재무정보 추출 완료: {len(financial_data)}개 항목")
                    return financial_data
                else:
                    logger.warning("⚠️ 재무 데이터를 추출할 수 없습니다")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ 재무 테이블 파싱 실패: {e}")
                return None
        
        except Exception as e:
            logger.error(f"❌ 재무정보 추출 실패: {e}")
            return None
    
    async def extract_investment_info(self):
        """투자유치 정보 추출"""
        logger.info("🔍 투자유치 정보 추출 시작...")
        
        investment_data = {
            'summary': {},
            'details': []
        }
        
        try:
            # 투자유치 요약 정보 추출 (최종투자단계, 누적투자유치금액, 투자유치건수)
            await self.page.wait_for_timeout(2000)
            
            # 투자유치 요약 정보 섹션 찾기
            summary_selectors = [
                'div.css-1s5aaxq dl.css-3k8w26',  # 주어진 구조
                'div.css-1s5aaxq dl',
                'dl.css-3k8w26',
                'div[class*="css-"] dl[class*="css-"]'
            ]
            
            summary_section = None
            for selector in summary_selectors:
                try:
                    summary_section = self.page.locator(selector).first
                    if await summary_section.count() > 0:
                        logger.info(f"📋 투자유치 요약 섹션 발견: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"요약 섹션 selector {selector} 실패: {e}")
                    continue
            
            if summary_section and await summary_section.count() > 0:
                try:
                    # 요약 정보의 각 항목 추출
                    summary_items = summary_section.locator('div')
                    item_count = await summary_items.count()
                    
                    for i in range(item_count):
                        try:
                            item = summary_items.nth(i)
                            dt_element = item.locator('dt')
                            dd_element = item.locator('dd')
                            
                            if await dt_element.count() > 0 and await dd_element.count() > 0:
                                key = await dt_element.text_content()
                                value = await dd_element.text_content()
                                
                                if key and value:
                                    key = key.strip()
                                    value = value.strip()
                                    investment_data['summary'][key] = value
                                    logger.info(f"  📌 {key}: {value}")
                        
                        except Exception as e:
                            logger.debug(f"요약 항목 {i} 추출 실패: {e}")
                            continue
                
                except Exception as e:
                    logger.warning(f"⚠️ 투자유치 요약 정보 파싱 실패: {e}")
            
            else:
                logger.warning("⚠️ 투자유치 요약 섹션을 찾을 수 없습니다")
            
            # 투자유치 상세 테이블 추출
            table_selectors = [
                'div.css-1ipakji table.css-deqyqf',  # 주어진 구조
                'table.css-deqyqf',
                'div.css-1ipakji table',
                'div[class*="css-"] table[class*="css-"]',
                'table'
            ]
            
            investment_table = None
            for selector in table_selectors:
                try:
                    investment_table = self.page.locator(selector).first
                    if await investment_table.count() > 0:
                        logger.info(f"📋 투자유치 테이블 발견: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"테이블 selector {selector} 실패: {e}")
                    continue
            
            if not investment_table or await investment_table.count() == 0:
                logger.warning("⚠️ 투자유치 테이블을 찾을 수 없습니다")
                
                # 페이지에 투자 관련 텍스트가 있는지 확인
                try:
                    page_content = await self.page.content()
                    if any(keyword in page_content for keyword in ["투자단계", "투자유치금액", "투자사"]):
                        logger.info("📄 페이지에 투자 관련 텍스트는 존재하지만 테이블을 찾지 못했습니다")
                    else:
                        logger.info("📄 페이지에 투자 관련 데이터가 없는 것으로 보입니다")
                except Exception as e:
                    logger.debug(f"페이지 내용 확인 실패: {e}")
            
            else:
                try:
                    # 테이블 헤더 추출
                    headers = []
                    try:
                        header_cells = investment_table.locator('thead tr th')
                        header_count = await header_cells.count()
                        
                        if header_count == 0:
                            logger.warning("⚠️ 투자유치 테이블 헤더를 찾을 수 없습니다")
                        else:
                            for i in range(header_count):
                                try:
                                    header_text = await header_cells.nth(i).text_content()
                                    if header_text:
                                        headers.append(header_text.strip())
                                except Exception as e:
                                    logger.debug(f"헤더 {i} 추출 실패: {e}")
                                    headers.append(f"헤더{i}")
                            
                            logger.info(f"📋 투자유치 테이블 헤더: {headers}")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ 투자유치 테이블 헤더 추출 실패: {e}")
                        headers = ["날짜", "투자단계", "투자유치금액", "투자사"]  # 기본값
                    
                    # 테이블 데이터 행 추출
                    try:
                        rows = investment_table.locator('tbody tr')
                        row_count = await rows.count()
                        
                        if row_count == 0:
                            logger.warning("⚠️ 투자유치 테이블에 데이터 행이 없습니다")
                        else:
                            for i in range(row_count):
                                try:
                                    row = rows.nth(i)
                                    cells = row.locator('td')
                                    cell_count = await cells.count()
                                    
                                    if cell_count > 0:
                                        row_data = {}
                                        
                                        for j in range(cell_count):
                                            try:
                                                header_key = headers[j] if j < len(headers) else f"컬럼{j+1}"
                                                cell_value = await cells.nth(j).text_content()
                                                
                                                if cell_value and cell_value.strip():
                                                    # 투자사 컬럼의 경우 링크 텍스트만 추출
                                                    if "투자사" in header_key:
                                                        # 링크가 있는 경우 텍스트만 추출
                                                        links = cells.nth(j).locator('a')
                                                        link_count = await links.count()
                                                        if link_count > 0:
                                                            investor_names = []
                                                            for k in range(link_count):
                                                                link_text = await links.nth(k).text_content()
                                                                if link_text and link_text.strip():
                                                                    investor_names.append(link_text.strip())
                                                            
                                                            # 링크가 아닌 텍스트도 포함
                                                            full_text = cell_value.strip()
                                                            # 쉼표와 공백으로 분리하여 정리
                                                            row_data[header_key] = full_text
                                                        else:
                                                            row_data[header_key] = cell_value.strip()
                                                    else:
                                                        row_data[header_key] = cell_value.strip()
                                                else:
                                                    row_data[header_key] = "-"
                                            
                                            except Exception as e:
                                                logger.debug(f"셀 {j} 추출 실패: {e}")
                                                row_data[f"컬럼{j+1}"] = "-"
                                        
                                        investment_data['details'].append(row_data)
                                        logger.info(f"  📌 투자 {i+1}: {row_data}")
                                
                                except Exception as e:
                                    logger.debug(f"행 {i} 처리 실패: {e}")
                                    continue
                    
                    except Exception as e:
                        logger.error(f"❌ 투자유치 테이블 데이터 행 처리 실패: {e}")
                
                except Exception as e:
                    logger.error(f"❌ 투자유치 테이블 파싱 실패: {e}")
            
            # 결과 확인
            if investment_data['summary'] or investment_data['details']:
                logger.info(f"✅ 투자유치정보 추출 완료: 요약 {len(investment_data['summary'])}개 항목, 상세 {len(investment_data['details'])}건")
                return investment_data
            else:
                logger.warning("⚠️ 투자유치 데이터를 추출할 수 없습니다")
                return None
        
        except Exception as e:
            logger.error(f"❌ 투자유치 정보 추출 실패: {e}")
            return None
    
    async def extract_news_info(self):
        """보도자료 정보 추출"""
        logger.info("🔍 보도자료 정보 추출 시작...")
        
        news_data = []
        
        try:
            # 보도자료 섹션 대기
            await self.page.wait_for_timeout(2000)
            
            # 보도자료 리스트 찾기
            news_selectors = [
                'div.css-1s5aaxq ul.css-1nx5s0',  # 주어진 구조
                'ul.css-1nx5s0',
                'div.css-1s5aaxq ul',
                'div[class*="css-"] ul[class*="css-"]',
                'ul li dl'
            ]
            
            news_list = None
            for selector in news_selectors:
                try:
                    news_element = self.page.locator(selector).first
                    if await news_element.count() > 0:
                        news_list = news_element
                        logger.info(f"📋 보도자료 리스트 발견: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"보도자료 리스트 selector {selector} 실패: {e}")
                    continue
            
            if not news_list or await news_list.count() == 0:
                logger.warning("⚠️ 보도자료 리스트를 찾을 수 없습니다")
                
                # 페이지에 보도자료 관련 텍스트가 있는지 확인
                try:
                    page_content = await self.page.content()
                    if any(keyword in page_content for keyword in ["보도자료", "뉴스", "기사"]):
                        logger.info("📄 페이지에 보도자료 관련 텍스트는 존재하지만 리스트를 찾지 못했습니다")
                    else:
                        logger.info("📄 페이지에 보도자료 관련 데이터가 없는 것으로 보입니다")
                except Exception as e:
                    logger.debug(f"페이지 내용 확인 실패: {e}")
                
                return None
            
            # 뉴스 항목들 추출
            try:
                # li 요소들 찾기
                news_items = news_list.locator('li')
                item_count = await news_items.count()
                
                if item_count == 0:
                    logger.warning("⚠️ 보도자료 항목이 없습니다")
                    return None
                
                logger.info(f"📰 발견된 보도자료 항목: {item_count}개")
                
                for i in range(item_count):
                    try:
                        item = news_items.nth(i)
                        dl_element = item.locator('dl')
                        
                        if await dl_element.count() > 0:
                            news_item = {}
                            
                            # 링크와 제목 추출
                            try:
                                link_element = dl_element.locator('a').first
                                if await link_element.count() > 0:
                                    # 링크 URL 추출
                                    news_item['link'] = await link_element.get_attribute('href')
                                    
                                    # 카테고리 추출 (투자/일반)
                                    try:
                                        category_element = link_element.locator('div').first
                                        if await category_element.count() > 0:
                                            category_text = await category_element.text_content()
                                            if category_text and category_text.strip():
                                                news_item['category'] = category_text.strip()
                                        else:
                                            news_item['category'] = "일반"
                                    except Exception as e:
                                        logger.debug(f"카테고리 추출 실패: {e}")
                                        news_item['category'] = "일반"
                                    
                                    # 제목 추출
                                    try:
                                        title_element = link_element.locator('dt').first
                                        if await title_element.count() > 0:
                                            title_text = await title_element.text_content()
                                            if title_text and title_text.strip():
                                                news_item['title'] = title_text.strip()
                                        else:
                                            news_item['title'] = "제목 없음"
                                    except Exception as e:
                                        logger.debug(f"제목 추출 실패: {e}")
                                        news_item['title'] = "제목 없음"
                                
                                else:
                                    logger.debug(f"항목 {i}: 링크를 찾을 수 없습니다")
                                    continue
                            
                            except Exception as e:
                                logger.debug(f"링크/제목 추출 실패 (항목 {i}): {e}")
                                continue
                            
                            # 날짜와 출처 추출
                            try:
                                date_element = dl_element.locator('dd').first
                                if await date_element.count() > 0:
                                    date_text = await date_element.text_content()
                                    if date_text and date_text.strip():
                                        date_info = date_text.strip()
                                        # "출처 | 날짜" 형식으로 분리
                                        if ' | ' in date_info:
                                            parts = date_info.split(' | ')
                                            news_item['source'] = parts[0].strip()
                                            news_item['date'] = parts[1].strip()
                                        else:
                                            # 날짜만 있는 경우
                                            news_item['source'] = "출처 없음"
                                            news_item['date'] = date_info
                                    else:
                                        news_item['source'] = "출처 없음"
                                        news_item['date'] = "날짜 없음"
                                else:
                                    news_item['source'] = "출처 없음"
                                    news_item['date'] = "날짜 없음"
                            
                            except Exception as e:
                                logger.debug(f"날짜/출처 추출 실패 (항목 {i}): {e}")
                                news_item['source'] = "출처 없음"
                                news_item['date'] = "날짜 없음"
                            
                            # 필수 정보가 있는 경우에만 추가
                            if news_item.get('title') and news_item.get('link'):
                                news_data.append(news_item)
                                logger.info(f"  📌 뉴스 {i+1}: [{news_item.get('category', '일반')}] {news_item['title'][:50]}...")
                            else:
                                logger.debug(f"항목 {i}: 필수 정보 부족으로 제외")
                        
                        else:
                            logger.debug(f"항목 {i}: dl 요소를 찾을 수 없습니다")
                    
                    except Exception as e:
                        logger.debug(f"뉴스 항목 {i} 처리 실패: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"❌ 보도자료 항목 처리 실패: {e}")
                return None
            
            # 결과 확인
            if news_data:
                logger.info(f"✅ 보도자료 추출 완료: {len(news_data)}건")
                return news_data
            else:
                logger.warning("⚠️ 보도자료 데이터를 추출할 수 없습니다")
                return None
        
        except Exception as e:
            logger.error(f"❌ 보도자료 정보 추출 실패: {e}")
            return None

    async def save_company_data_to_json(self, company_info, keyword):
        """
        추출된 회사 정보를 JSON 파일로 저장
        """
        try:
            if not company_info:
                logger.warning("⚠️ 저장할 회사 정보가 없습니다")
                return False
            
            # 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"innoforest_company_data_{keyword.replace(' ', '_')}_{timestamp}.json"
            
            # JSON 파일로 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(company_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 회사 정보 JSON 저장 완료: {filename}")
            logger.info(f"📊 저장된 데이터: {json.dumps(company_info, ensure_ascii=False, indent=2)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ JSON 저장 실패: {e}")
            return False

    async def close(self):
        """
        브라우저 종료 - 강화된 정리 로직
        """
        try:
            logger.info("🔚 Innoforest Stealth 브라우저 종료 중...")
            
            if self.page:
                try:
                    await self.page.close()
                    await asyncio.sleep(0.3)  # 페이지 정리 대기
                    logger.info("Innoforest 페이지 종료 완료")
                except Exception as e:
                    logger.warning(f"페이지 종료 중 오류: {e}")
                    
            if self.context:
                try:
                    await self.context.close()
                    await asyncio.sleep(0.3)  # 컨텍스트 정리 대기
                    logger.info("Innoforest 컨텍스트 종료 완료")
                except Exception as e:
                    logger.warning(f"컨텍스트 종료 중 오류: {e}")
                    
            if self.browser:
                try:
                    await self.browser.close()
                    await asyncio.sleep(0.5)  # 브라우저 정리 대기
                    logger.info("Innoforest 브라우저 종료 완료")
                except Exception as e:
                    logger.warning(f"브라우저 종료 중 오류: {e}")
                    
            # 추가 정리 시간
            await asyncio.sleep(0.5)
            logger.info("✅ Innoforest Stealth 모드 완전 종료")
            
        except Exception as e:
            logger.warning(f"Innoforest 브라우저 종료 중 오류: {e}")
            # 예외 발생 시에도 정리 시간 확보
            await asyncio.sleep(1.0)

async def run_innoforest_stealth_crawler():
    """
    Innoforest Stealth 크롤러 실행 (검색 기능 포함)
    """
    crawler = None
    
    try:
        logger.info("🚀 Innoforest Stealth 크롤러 시작")
        
        # 크롤러 초기화
        crawler = InnoforestStealthCrawler()
        
        # 브라우저 초기화
        if not await crawler.initialize(headless=False):  # 개발용으로 headless=False
            logger.error("❌ Innoforest 브라우저 초기화 실패")
            return
        
        # 사이트 접속
        if not await crawler.navigate_to_innoforest():
            logger.error("❌ Innoforest 사이트 접속 실패")
            return
        
        # Stealth 효과 확인
        stealth_info = await crawler.check_stealth_effectiveness()
        if stealth_info:
            logger.info(f"🥷 Stealth 정보: {stealth_info}")
        
        # 로그인 상태 확인 및 로그인 수행
        is_logged_in = await crawler.check_if_logged_in()
        
        if not is_logged_in:
            logger.info("🔐 로그인이 필요합니다. 로그인을 시도합니다...")
            login_success = await crawler.perform_login()
            
            if not login_success:
                logger.error("❌ Innoforest 로그인 실패")
                return
            else:
                logger.info("✅ Innoforest 로그인 완료!")
        else:
            logger.info("✅ 이미 로그인된 상태입니다")
        
        # 세션 저장
        await crawler.save_stealth_session()
        
        # 최종 팝업 확인 (혹시 다시 나타날 수 있음)
        await crawler.close_popup_if_exists()
        
        # 검색어 입력받기
        keyword = crawler.get_search_keyword_from_user()
        if not keyword:
            logger.warning("⚠️ 검색어 입력이 취소되었습니다.")
            return
        
        # 스타트업 검색
        search_success = await crawler.search_startup(keyword)
        if not search_success:
            logger.error(f"❌ '{keyword}' 검색 실패")
            return
        
        # 검색 결과 확인
        results_found = await crawler.check_search_results(keyword)
        if results_found:
            logger.info(f"✅ '{keyword}' 검색 결과를 성공적으로 찾았습니다!")
            
            # 첫 번째 검색 결과 클릭
            click_success = await crawler.click_first_search_result(keyword)
            if click_success:
                logger.info(f"✅ '{keyword}' 첫 번째 검색 결과 클릭 성공!")
                
                # 회사 정보 추출
                company_info = await crawler.extract_company_info(keyword)
                if company_info:
                    logger.info(f"📊 '{keyword}' 회사 정보 추출 성공!")
                    
                    # JSON 파일로 저장
                    save_success = await crawler.save_company_data_to_json(company_info, keyword)
                    if save_success:
                        logger.info(f"💾 '{keyword}' 회사 데이터 JSON 저장 완료!")
                    else:
                        logger.warning(f"⚠️ '{keyword}' JSON 저장 실패")
                else:
                    logger.warning(f"⚠️ '{keyword}' 회사 정보 추출 실패")
                
                # 상세 페이지 확인 시간 (더 긴 시간)
                logger.info("⏳ 20초 대기 - 상세 페이지 확인 시간")
                await asyncio.sleep(20)  # 15초 -> 20초로 증가
            else:
                logger.error(f"❌ '{keyword}' 첫 번째 검색 결과 클릭 실패")
                logger.info(f"💡 '{keyword}' 검색어를 다시 확인하거나 다른 키워드로 시도해보세요.")
        else:
            logger.warning(f"⚠️ '{keyword}' 검색 결과가 없거나 구조를 파악하지 못했습니다.")
            logger.info(f"💡 가능한 원인:")
            logger.info(f"   1. '{keyword}' 기업이 Innoforest 데이터베이스에 없을 수 있습니다")
            logger.info(f"   2. 검색어 철자가 틀렸을 수 있습니다")
            logger.info(f"   3. 정확한 회사명이 아닐 수 있습니다")
            logger.info(f"💡 해결 방법:")
            logger.info(f"   - 다른 키워드로 다시 시도해보세요")
            logger.info(f"   - 회사명의 일부만 입력해보세요")
            logger.info(f"   - 영어명 또는 한글명으로 바꿔서 시도해보세요")
        
        logger.info("🎉 Innoforest Stealth 크롤러 완료")
        
    except KeyboardInterrupt:
        logger.info("❌ 사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"❌ Innoforest Stealth 크롤러 실행 중 오류: {e}")
    finally:
        if crawler:
            await crawler.close()

if __name__ == "__main__":
    asyncio.run(run_innoforest_stealth_crawler()) 