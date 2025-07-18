"""
TheVC 크롤러 - Stealth 라이브러리 버전 (비상시 백업용)
playwright-stealth 라이브러리를 사용한 강화된 탐지 우회 버전
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime

# Stealth 라이브러리 import (설치 필요: pip install playwright-stealth)
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    print("⚠️ playwright-stealth 라이브러리가 설치되지 않았습니다.")
    print("설치 명령어: pip install playwright-stealth")

from playwright.async_api import async_playwright

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('thevc_stealth_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TheVCStealthCrawler:
    """
    TheVC 크롤러 - Stealth 라이브러리 버전
    기존 버전이 차단당했을 때 사용하는 백업 버전
    """
    
    def __init__(self):
        self.base_url = "https://thevc.kr/"
        self.browser = None
        self.context = None
        self.page = None
        self.state_file = "thevc_stealth_browser_state.json"
        self.cookies_file = "thevc_stealth_cookies.json"
        self.stealth = None
        
    def _generate_random_headers(self):
        """
        매번 다른 랜덤 헤더 생성 (실제 브라우저 패턴 모방)
        """
        
        # 다양한 Chrome 버전들 (실제 사용되는 버전들)
        chrome_versions = [
            "131.0.0.0", "130.0.0.0", "129.0.0.0", "128.0.0.0", "127.0.0.0",
            "126.0.0.0", "125.0.0.0", "124.0.0.0", "123.0.0.0", "122.0.0.0"
        ]
        
        # 다양한 WebKit 버전들
        webkit_versions = [
            "537.36", "537.37", "537.38", "537.39", "537.40"
        ]
        
        # 다양한 운영체제 패턴들
        os_patterns = [
            "Windows NT 10.0; Win64; x64",
            "Windows NT 11.0; Win64; x64", 
            "Windows NT 10.0; WOW64",
            "Macintosh; Intel Mac OS X 10_15_7",
            "Macintosh; Intel Mac OS X 10_14_6",
            "X11; Linux x86_64"
        ]
        
        # 언어 설정 패턴들
        language_patterns = [
            "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "ko-KR,ko;q=0.9,en;q=0.8",
            "ko,en-US;q=0.9,en;q=0.8",
            "ko-KR,ko;q=0.8,en-US;q=0.7,en;q=0.6",
            "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6"
        ]
        
        # 랜덤 선택
        chrome_version = random.choice(chrome_versions)
        webkit_version = random.choice(webkit_versions)
        os_pattern = random.choice(os_patterns)
        language = random.choice(language_patterns)
        
        # User-Agent 생성
        user_agent = f"Mozilla/5.0 ({os_pattern}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}"
        
        # 다양한 Accept 헤더 패턴들
        accept_patterns = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        ]
        
        # Sec-Ch-Ua 브랜드 패턴들
        brand_patterns = [
            f'"Google Chrome";v="{chrome_version.split(".")[0]}", "Chromium";v="{chrome_version.split(".")[0]}", "Not_A Brand";v="24"',
            f'"Google Chrome";v="{chrome_version.split(".")[0]}", "Chromium";v="{chrome_version.split(".")[0]}", "Not)A;Brand";v="99"',
            f'"Chromium";v="{chrome_version.split(".")[0]}", "Google Chrome";v="{chrome_version.split(".")[0]}", "Not-A.Brand";v="24"'
        ]
        
        # 캐시 제어 패턴들
        cache_patterns = [
            "max-age=0",
            "no-cache",
            "no-store",
            "must-revalidate"
        ]
        
        headers = {
            'User-Agent': user_agent,
            'Accept': random.choice(accept_patterns),
            'Accept-Language': language,
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': random.choice(cache_patterns),
            'Sec-Ch-Ua': random.choice(brand_patterns),
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': f'"{os_pattern.split(";")[0].split("NT")[0].strip() if "NT" in os_pattern else os_pattern.split(";")[0]}"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Dnt': random.choice(['1', '0']),
            'Connection': 'keep-alive',
        }
        
        # 가끔 추가 헤더들 (실제 브라우저처럼)
        if random.random() < 0.3:  # 30% 확률
            headers['Pragma'] = 'no-cache'
        
        if random.random() < 0.2:  # 20% 확률
            headers['X-Requested-With'] = 'XMLHttpRequest'
        
        if random.random() < 0.4:  # 40% 확률  
            headers['Referer'] = random.choice([
                'https://www.google.com/',
                'https://www.naver.com/',
                'https://www.google.co.kr/search?q=thevc',
                'https://search.naver.com/search.naver?query=thevc'
            ])
        
        logger.info(f"🎭 랜덤 헤더 생성: Chrome {chrome_version}, OS: {os_pattern.split(';')[0]}")
        return headers
    
    async def _simulate_scroll(self):
        """
        인간처럼 스크롤하는 행동 시뮬레이션
        """
        try:
            logger.info("📜 스크롤 시뮬레이션 시작")
            
            # 랜덤한 스크롤 패턴
            scroll_patterns = [
                # 천천히 아래로
                [(0, 300), (0, 600), (0, 300)],
                # 빠르게 아래로 갔다가 다시 위로
                [(0, 800), (0, -400), (0, 200)],
                # 조금씩 여러 번
                [(0, 200), (0, 150), (0, 100), (0, -200)],
            ]
            
            pattern = random.choice(scroll_patterns)
            for x, y in pattern:
                await self.page.mouse.wheel(x, y)
                await asyncio.sleep(random.uniform(0.5, 2))
                
            logger.info("✅ 스크롤 시뮬레이션 완료")
        except Exception as e:
            logger.debug(f"스크롤 시뮬레이션 실패: {e}")
    
    async def _simulate_mouse_movement(self):
        """
        인간처럼 마우스 움직이는 행동 시뮬레이션
        """
        try:
            logger.info("🖱️ 마우스 움직임 시뮬레이션 시작")
            
            # 화면 크기 가져오기
            viewport = await self.page.viewport_size()
            width = viewport['width']
            height = viewport['height']
            
            # 랜덤한 마우스 움직임
            for _ in range(random.randint(2, 5)):
                x = random.randint(50, width - 50)
                y = random.randint(50, height - 50)
                
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.3, 1.5))
                
                # 가끔 클릭하지 않고 호버만
                if random.random() < 0.3:
                    await asyncio.sleep(random.uniform(0.5, 1))
                    
            logger.info("✅ 마우스 움직임 시뮬레이션 완료")
        except Exception as e:
            logger.debug(f"마우스 움직임 시뮬레이션 실패: {e}")
    
    async def _simulate_page_reading(self):
        """
        인간처럼 페이지를 읽는 행동 시뮬레이션
        """
        try:
            logger.info("👀 페이지 읽기 시뮬레이션 시작")
            
            # 텍스트 요소들을 찾아서 집중하는 시간
            text_selectors = ['h1', 'h2', 'h3', 'p', 'div', 'span']
            
            for selector in random.sample(text_selectors, random.randint(2, 4)):
                try:
                    elements = await self.page.locator(selector).all()
                    if elements:
                        element = random.choice(elements)
                        
                        # 요소로 스크롤해서 보기
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(random.uniform(1, 3))
                        
                        # 가끔 텍스트 선택하기
                        if random.random() < 0.2:
                            await element.click(click_count=2)  # 더블클릭으로 텍스트 선택
                            await asyncio.sleep(random.uniform(0.5, 1))
                            
                except:
                    continue
                    
            logger.info("✅ 페이지 읽기 시뮬레이션 완료")
        except Exception as e:
            logger.debug(f"페이지 읽기 시뮬레이션 실패: {e}")

    async def initialize(self, headless=True, use_saved_state=True):
        """
        Stealth 라이브러리를 사용한 브라우저 초기화 (랜덤 헤더 적용)
        """
        try:
            if not STEALTH_AVAILABLE:
                logger.error("❌ playwright-stealth 라이브러리가 필요합니다")
                logger.info("설치 명령어: pip install playwright-stealth")
                return False
            
            logger.info("🥷 Stealth 모드로 브라우저 초기화 중...")
            
            # 랜덤 헤더 생성
            random_headers = self._generate_random_headers()
            
            # 저장된 상태 파일 검증
            valid_state = False
            if use_saved_state and os.path.exists(self.state_file):
                try:
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content and content.startswith('{'):
                            json.loads(content)
                            valid_state = True
                            logger.info("저장된 Stealth 세션 발견 - 복원 중...")
                        else:
                            logger.warning("저장된 상태 파일이 손상됨 - 새 세션으로 시작")
                except Exception as e:
                    logger.warning(f"상태 파일 검증 실패: {e}")
                    valid_state = False
            
            # Playwright 시작
            playwright = await async_playwright().start()
            
            # 강화된 브라우저 인수들 (Human 에러 방지)
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--disable-ipc-flooding-protection',
                f'--user-agent={random_headers["User-Agent"]}',
            ]
            
            # 가끔 추가 인수들 (무작위성 증가)
            if random.random() < 0.3:
                browser_args.append('--mute-audio')
            
            # 브라우저 실행
            self.browser = await playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )
            
            # 뷰포트 크기도 랜덤하게
            viewport_options = [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
                {'width': 1440, 'height': 900},
                {'width': 1536, 'height': 864},
                {'width': 1600, 'height': 900},
            ]
            selected_viewport = random.choice(viewport_options)
            
            # 지역 정보도 약간 랜덤하게
            seoul_coords = [
                {'latitude': 37.5665, 'longitude': 126.9780},  # 서울 중심
                {'latitude': 37.5519, 'longitude': 126.9918},  # 강남
                {'latitude': 37.5795, 'longitude': 126.9768},  # 종로
                {'latitude': 37.5172, 'longitude': 127.0473},  # 잠실
                {'latitude': 37.5664, 'longitude': 126.9997},  # 명동
            ]
            
            # 강화된 컨텍스트 옵션 (Human 에러 방지)
            context_options = {
                'user_agent': random_headers["User-Agent"],
                'viewport': selected_viewport,
                'screen': selected_viewport,
                'device_scale_factor': random.choice([1, 1.25, 1.5]),
                'is_mobile': False,
                'has_touch': False,
                'locale': 'ko-KR',
                'timezone_id': 'Asia/Seoul',
                'geolocation': random.choice(seoul_coords),
                'permissions': ['geolocation'],
                'extra_http_headers': {
                    'Accept': random_headers.get('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'),
                    'Accept-Language': random_headers.get('Accept-Language', 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'),
                    'Accept-Encoding': random_headers.get('Accept-Encoding', 'gzip, deflate, br, zstd'),
                    'Cache-Control': random_headers.get('Cache-Control', 'max-age=0'),
                    'Sec-Ch-Ua': random_headers.get('Sec-Ch-Ua', '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'),
                    'Sec-Ch-Ua-Mobile': random_headers.get('Sec-Ch-Ua-Mobile', '?0'),
                    'Sec-Ch-Ua-Platform': random_headers.get('Sec-Ch-Ua-Platform', '"Windows"'),
                    'Sec-Fetch-Dest': random_headers.get('Sec-Fetch-Dest', 'document'),
                    'Sec-Fetch-Mode': random_headers.get('Sec-Fetch-Mode', 'navigate'),
                    'Sec-Fetch-Site': random_headers.get('Sec-Fetch-Site', 'none'),
                    'Sec-Fetch-User': random_headers.get('Sec-Fetch-User', '?1'),
                    'Upgrade-Insecure-Requests': random_headers.get('Upgrade-Insecure-Requests', '1'),
                    'Dnt': random_headers.get('Dnt', '1'),
                    'Connection': random_headers.get('Connection', 'keep-alive')
                }
            }
            
            # 유효한 상태 파일이 있으면 로드
            if valid_state:
                context_options['storage_state'] = self.state_file
            
            # 브라우저 컨텍스트 생성
            self.context = await self.browser.new_context(**context_options)
            
            # 새 페이지 생성
            self.page = await self.context.new_page()
            
            # Stealth 라이브러리 적용
            stealth = Stealth()
            await stealth.apply_stealth_async(self.context)
            
            # 강화된 탐지 우회 스크립트 (Human 에러 방지)
            await self.page.add_init_script("""
                // 강화된 탐지 우회 스크립트
                console.log('🥷 Enhanced Stealth Mode Activated');
                
                // WebDriver 탐지 완전 제거
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Chrome 자동화 객체 삭제
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Permissions API 완전 우회
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Chrome runtime 우회
                Object.defineProperty(window, 'chrome', {
                    value: {
                        runtime: {
                            onConnect: undefined,
                            onMessage: undefined,
                        },
                    },
                    writable: false,
                    enumerable: true,
                    configurable: false,
                });
                
                // 플러그인 리스트 정상화
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: ""},
                            description: "",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }
                    ],
                });
                
                // 언어 리스트 정상화
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                });
                
                // 하드웨어 동시성 정상화
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8,
                });
                
                console.log('✅ Human Detection Bypass Complete');
            """)
            
            if valid_state:
                logger.info("✅ Stealth 세션 복원 완료")
            else:
                logger.info("🆕 새로운 Stealth 세션 시작")
            
            return True
                
        except Exception as e:
            logger.error(f"Stealth 브라우저 초기화 실패: {e}")
            # 손상된 상태 파일 삭제
            if use_saved_state and os.path.exists(self.state_file):
                try:
                    os.remove(self.state_file)
                    logger.info("손상된 Stealth 상태 파일 삭제 완료")
                except:
                    pass
            return False
    
    async def navigate_to_thevc(self):
        """
        TheVC 사이트로 이동 (Stealth 모드)
        """
        try:
            logger.info(f"🥷 Stealth 모드로 사이트 접속: {self.base_url}")
            
            # 매번 새로운 랜덤 헤더 생성
            
            # 접속 시 추가 랜덤 헤더들
            referer_options = [
                'https://www.google.com/search?q=thevc',
                'https://www.google.co.kr/search?q=더브이씨',
                'https://search.naver.com/search.naver?query=thevc',
                'https://www.google.com/search?q=startup+database',
                'https://www.google.com/search?q=korean+startups',
                'https://www.naver.com/',
                'https://www.google.com/',
                None  # 가끔 Referer 없이
            ]
            
            cache_options = [
                'no-cache',
                'max-age=0',
                'no-store',
                'must-revalidate'
            ]
            
            # 랜덤 헤더 설정
            extra_headers = {
                'Cache-Control': random.choice(cache_options),
            }
            
            selected_referer = random.choice(referer_options)
            if selected_referer:
                extra_headers['Referer'] = selected_referer
                logger.info(f"🔗 Referer 설정: {selected_referer}")
            else:
                logger.info("🔗 Referer 없이 접속")
            
            # 가끔 추가 헤더들
            if random.random() < 0.3:
                extra_headers['Pragma'] = 'no-cache'
            
            if random.random() < 0.2:
                extra_headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            
            if random.random() < 0.4:
                extra_headers['X-Real-IP'] = f"210.{random.randint(90,99)}.{random.randint(1,255)}.{random.randint(1,255)}"  # 한국 IP 대역
            
            await self.page.set_extra_http_headers(extra_headers)
            
            # 인간처럼 접속 패턴 모방
            # 첫 접속 전 생각하는 시간
            thinking_time = random.uniform(2, 8)
            logger.info(f"🤔 접속 전 대기 시간: {thinking_time:.1f}초")
            await asyncio.sleep(thinking_time)
            
            # 사이트 접속 (여러 번 시도)
            max_attempts = 5  # Stealth 모드에서는 더 많이 시도
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Stealth 접속 시도 {attempt + 1}/{max_attempts}")
                    
                    # 시도 간격도 랜덤하게 (실패 시 점점 더 기다림)
                    if attempt > 0:
                        retry_delay = random.uniform(3, 10) + (attempt * 2)  # 재시도할수록 더 기다림
                        logger.info(f"⏳ 재시도 전 대기: {retry_delay:.1f}초")
                        await asyncio.sleep(retry_delay)
                    else:
                        # 첫 시도 전 짧은 대기
                        await asyncio.sleep(random.uniform(1, 3))
                    
                    response = await self.page.goto(
                        self.base_url,
                        wait_until='domcontentloaded',
                        timeout=60000  # 더 긴 타임아웃
                    )
                    
                    if response and response.status == 200:
                        logger.info("✅ Stealth 모드 접속 성공!")
                        break
                    elif response:
                        logger.warning(f"HTTP {response.status} - Stealth 재시도 중...")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(random.uniform(5, 10))
                            continue
                    
                except Exception as e:
                    logger.warning(f"Stealth 접속 시도 {attempt + 1} 실패: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(random.uniform(5, 10))
                        continue
                    else:
                        raise e
            
            # 페이지 로딩 완료 대기
            try:
                logger.info("Stealth 페이지 로딩 대기 중...")
                await self.page.wait_for_load_state('networkidle', timeout=20000)
            except:
                logger.info("네트워크 대기 시간 초과 - 계속 진행")
                await asyncio.sleep(random.uniform(3, 7))
            
            # 인간처럼 페이지 확인하는 행동들
            human_actions = [
                self._simulate_scroll,
                self._simulate_mouse_movement, 
                self._simulate_page_reading
            ]
            
            # 랜덤하게 1-2개 액션 수행
            selected_actions = random.sample(human_actions, random.randint(1, 2))
            for action in selected_actions:
                try:
                    await action()
                except Exception as e:
                    logger.debug(f"인간 행동 시뮬레이션 실패: {e}")
            
            # 페이지 확인 후 추가 대기
            reading_time = random.uniform(3, 8)
            logger.info(f"📖 페이지 읽는 시간: {reading_time:.1f}초")
            await asyncio.sleep(reading_time)
            
            # 페이지 정보 확인
            try:
                title = await self.page.title()
                url = self.page.url
                
                logger.info(f"Stealth 페이지 제목: {title}")
                logger.info(f"Stealth 현재 URL: {url}")
                
                # 차단 감지
                blocked_keywords = ['blocked', 'forbidden', 'access denied', '차단', '접근 거부', 'cloudflare']
                if any(keyword in title.lower() for keyword in blocked_keywords):
                    logger.error("⚠️ Stealth 모드에서도 접근이 차단되었습니다")
                    return False
                
                if 'thevc' in url.lower() or 'the vc' in title.lower():
                    logger.info("🎉 Stealth 모드로 TheVC 접속 성공!")
                    return True
                else:
                    logger.warning("⚠️ 예상과 다른 페이지 - 하지만 진행")
                    return True
                    
            except Exception as e:
                logger.warning(f"페이지 정보 확인 실패: {e}")
                return True
                
        except Exception as e:
            logger.error(f"Stealth 사이트 접속 실패: {e}")
            return False
    
    async def check_stealth_effectiveness(self):
        """
        Stealth 모드 효과 확인
        """
        try:
            logger.info("🔍 Stealth 모드 효과 검증 중...")
            
            # 다양한 탐지 포인트 체크
            checks = {
                'webdriver': await self.page.evaluate("navigator.webdriver"),
                'plugins_length': await self.page.evaluate("navigator.plugins.length"),
                'languages': await self.page.evaluate("navigator.languages"),
                'platform': await self.page.evaluate("navigator.platform"),
                'vendor': await self.page.evaluate("navigator.vendor"),
                'chrome_present': await self.page.evaluate("!!window.chrome"),
                'permissions_query': await self.page.evaluate("typeof navigator.permissions.query"),
                'hardwareConcurrency': await self.page.evaluate("navigator.hardwareConcurrency"),
            }
            
            logger.info("🥷 Stealth 효과 검증 결과:")
            for key, value in checks.items():
                logger.info(f"  {key}: {value}")
            
            # 성공 지표
            success_indicators = [
                checks['webdriver'] is None or checks['webdriver'] == False,
                checks['plugins_length'] > 0,
                checks['chrome_present'] == True,
                len(checks['languages']) > 0,
            ]
            
            success_rate = sum(success_indicators) / len(success_indicators)
            logger.info(f"🎯 Stealth 성공률: {success_rate*100:.1f}%")
            
            return success_rate > 0.7  # 70% 이상이면 성공
            
        except Exception as e:
            logger.error(f"Stealth 효과 검증 실패: {e}")
            return False
    
    async def save_stealth_session(self):
        """
        Stealth 세션 상태 저장
        """
        try:
            logger.info("💾 Stealth 세션 저장 중...")
            
            # 브라우저 상태 저장
            await self.context.storage_state(path=self.state_file)
            logger.info(f"✅ Stealth 브라우저 상태 저장: {self.state_file}")
            
            # 쿠키 저장
            cookies = await self.context.cookies()
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Stealth 쿠키 저장: {self.cookies_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Stealth 세션 저장 실패: {e}")
            return False
    
    async def take_screenshot(self, filename="thevc_stealth_screenshot.png"):
        """
        스크린샷 저장
        """
        try:
            await self.page.screenshot(path=filename, full_page=True)
            logger.info(f"📸 Stealth 스크린샷 저장: {filename}")
            return True
        except Exception as e:
            logger.error(f"스크린샷 저장 실패: {e}")
            return False
    
    async def close(self):
        """
        브라우저 안전 종료
        """
        try:
            logger.info("🔚 Stealth 브라우저 종료 중...")
            
            if self.page:
                await self.page.close()
                logger.info("Stealth 페이지 종료 완료")
            
            if self.context:
                await self.context.close()
                logger.info("Stealth 컨텍스트 종료 완료")
            
            if self.browser:
                await self.browser.close()
                logger.info("Stealth 브라우저 종료 완료")
            
            logger.info("✅ Stealth 모드 완전 종료")
            
        except Exception as e:
            logger.warning(f"Stealth 브라우저 종료 중 오류: {e}")

    async def check_if_logged_in(self):
        """
        현재 로그인 상태 확인 (Stealth 버전)
        """
        try:
            logger.info("🔍 Stealth 모드에서 로그인 상태 확인 중...")
            
            # 1단계: 로그인 필요 지표 확인 (우선순위)
            login_needed_selectors = [
                "div:has-text('가입 / 로그인')",
                "text=가입 / 로그인",
                "[data-v-b3196f07]:has-text('가입 / 로그인')",
            ]
            
            for selector in login_needed_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        logger.info("❌ '가입 / 로그인' 버튼 발견 - 로그인 필요")
                        return False
                except:
                    continue
            
            # 2단계: 로그인 상태 지표 확인
            logged_in_selectors = [
                "div:has-text('로그아웃')",
                "text=로그아웃",
                "div:has-text('마이페이지')",
                "text=마이페이지",
                "[class*='user']",
                "[class*='profile']",
            ]
            
            for selector in logged_in_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        logger.info("✅ 로그인 상태 지표 발견 - 로그인됨")
                        return True
                except:
                    continue
            
            # 3단계: URL 기반 확인
            current_url = self.page.url
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                logger.info("❌ 로그인 페이지 URL 감지 - 로그인 필요")
                return False
            
            # 4단계: 텍스트 기반 확인
            try:
                page_text = await self.page.text_content('body')
                if page_text:
                    if '가입 / 로그인' in page_text:
                        logger.info("❌ 페이지 텍스트에서 '가입 / 로그인' 발견 - 로그인 필요")
                        return False
                    elif '로그아웃' in page_text or '마이페이지' in page_text:
                        logger.info("✅ 페이지 텍스트에서 로그인 지표 발견 - 로그인됨")
                        return True
            except:
                pass
            
            logger.info("⚠️ 로그인 상태를 명확히 판단할 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"로그인 상태 확인 실패: {e}")
            return None

    async def click_login_button(self):
        """
        로그인 버튼 클릭 (Stealth 버전)
        """
        try:
            logger.info("🔑 Stealth 모드에서 로그인 버튼 찾는 중...")
            
            # 다양한 로그인 버튼 선택자들
            login_selectors = [
                "div:has-text('가입 / 로그인')",
                "text=가입 / 로그인",
                "[data-v-b3196f07]:has-text('가입 / 로그인')",
                "div.flex.align-center.justify-center:has-text('가입')",
            ]
            
            for i, selector in enumerate(login_selectors):
                try:
                    logger.info(f"로그인 버튼 시도 {i+1}: {selector}")
                    
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        logger.info(f"✅ 로그인 버튼 발견: {selector}")
                        
                        # 다중 클릭 방법 시도
                        click_methods = [
                            ("일반 클릭", lambda: element.click()),
                            ("강제 클릭", lambda: element.click(force=True)),
                            ("JavaScript 클릭", lambda: element.evaluate("el => el.click()")),
                            ("더블 클릭", lambda: element.dblclick()),
                            ("마우스 클릭", lambda: element.click(button="left")),
                        ]
                        
                        for method_name, click_method in click_methods:
                            try:
                                logger.info(f"🖱️ {method_name} 시도 중...")
                                await click_method()
                                await asyncio.sleep(1)
                                logger.info(f"✅ {method_name} 성공")
                                return True
                            except Exception as click_error:
                                logger.warning(f"❌ {method_name} 실패: {click_error}")
                                continue
                        
                except Exception as e:
                    logger.warning(f"선택자 {i+1} 실패: {e}")
                    continue
            
            logger.error("❌ 모든 로그인 버튼 클릭 시도 실패")
            return False
            
        except Exception as e:
            logger.error(f"로그인 버튼 클릭 실패: {e}")
            return False

    async def wait_for_login_modal(self):
        """
        로그인 창 대기 (Stealth 버전)
        """
        try:
            logger.info("⏳ Stealth 모드에서 로그인 창 대기 중...")
            
            # 3단계 빠른 검색 시스템
            modal_selectors = [
                "input[type='email']",
                "input[placeholder*='이메일']",
                "input[placeholder*='email']",
                "[data-v-b3196f07][type='email']",
                "form input[type='email']",
                ".modal input[type='email']",
                "div[class*='modal'] input",
            ]
            
            # 1단계: 0.5초 빠른 확인
            for selector in modal_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=500)
                    if element:
                        logger.info(f"✅ 로그인 창 즉시 발견: {selector}")
                        return True
                except:
                    continue
            
            # 2단계: 1.5초 추가 대기
            await asyncio.sleep(1.5)
            for selector in modal_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=100)
                    if element:
                        logger.info(f"✅ 로그인 창 발견 (2단계): {selector}")
                        return True
                except:
                    continue
            
            # 3단계: 즉시 확인
            for selector in modal_selectors:
                try:
                    element = self.page.locator(selector)
                    if await element.count() > 0:
                        logger.info(f"✅ 로그인 창 발견 (3단계): {selector}")
                        return True
                except:
                    continue
            
            logger.error("❌ 로그인 창을 찾을 수 없음")
            return False
            
        except Exception as e:
            logger.error(f"로그인 창 대기 실패: {e}")
            return False

    async def perform_login(self):
        """
        실제 로그인 수행 (Stealth 버전)
        """
        try:
            logger.info("🔐 Stealth 모드에서 로그인 수행 중...")
            
            # 이메일 입력
            email_selectors = [
                "input[type='email']",
                "input[placeholder*='이메일']",
                "input[placeholder*='email']",
                "[data-v-b3196f07][type='email']",
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.fill("jgpark@jch.kr")
                        logger.info(f"✅ 이메일 입력 완료: {selector}")
                        email_filled = True
                        break
                except:
                    continue
            
            if not email_filled:
                logger.error("❌ 이메일 입력 필드를 찾을 수 없음")
                return False
            
            # 비밀번호 입력
            password_selectors = [
                "input[type='password']",
                "input[placeholder*='비밀번호']",
                "input[placeholder*='password']",
                "[data-v-b3196f07][type='password']",
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.fill("jch2025")
                        logger.info(f"✅ 비밀번호 입력 완료: {selector}")
                        password_filled = True
                        break
                except:
                    continue
            
            if not password_filled:
                logger.error("❌ 비밀번호 입력 필드를 찾을 수 없음")
                return False
            
            # Enter 키로 로그인 (더 안정적)
            logger.info("🔑 Enter 키로 로그인 시도...")
            
            # 비밀번호 필드에서 Enter 키 누르기 (가장 안정적)
            for selector in password_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.press('Enter')
                        logger.info(f"✅ 비밀번호 필드에서 Enter 키 입력: {selector}")
                        
                        # 로그인 처리 대기
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
            
            # 백업: 이메일 필드에서 Enter 키 시도
            logger.info("🔄 이메일 필드에서 Enter 키 시도...")
            for selector in email_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.press('Enter')
                        logger.info(f"✅ 이메일 필드에서 Enter 키 입력: {selector}")
                        
                        # 로그인 처리 대기
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
            
            # 최후 수단: 로그인 버튼 클릭
            logger.info("🔄 로그인 버튼 클릭 시도...")
            login_button_selectors = [
                "div:has-text('로그인'):not(:has-text('가입'))",
                "button:has-text('로그인')",
                "text=로그인",
                "[data-v-b3196f07]:has-text('로그인')",
            ]
            
            for selector in login_button_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.click()
                        logger.info(f"✅ 로그인 버튼 클릭 완료: {selector}")
                        
                        # 로그인 처리 대기
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
            
            logger.error("❌ 모든 로그인 시도 실패")
            return False
            
        except Exception as e:
            logger.error(f"로그인 수행 실패: {e}")
            return False

    def get_search_keyword_from_user(self):
        """
        사용자로부터 검색어 입력받기 (Stealth 버전) - 환경 변수 지원
        """
        try:
            # 환경 변수에서 검색어 확인 (자동 모드)
            auto_keyword = os.environ.get('STEALTH_SEARCH_KEYWORD')
            auto_mode = os.environ.get('STEALTH_AUTO_MODE', '').lower() == 'true'
            
            if auto_mode and auto_keyword:
                logger.info(f"🤖 자동 모드: 환경 변수에서 검색어 '{auto_keyword}' 받음")
                print(f"🤖 자동 모드로 실행 - 검색어: '{auto_keyword}'")
                return auto_keyword.strip()
            
            print("\n" + "="*50)
            print("🔍 TheVC 스타트업 검색")
            print("="*50)
            print("💡 검색하고 싶은 스타트업 이름을 입력하세요")
            print("   예시: 퓨리오사AI, 로보스, 십일리터 등")
            print("   (Enter만 누르면 검색을 건너뜁니다)")
            print("-"*50)
            
            while True:
                keyword = input("🔍 검색어 입력: ").strip()
                
                if not keyword:
                    print("⏭️ 검색을 건너뜁니다.")
                    return None
                
                if len(keyword) < 2:
                    print("❌ 검색어는 2글자 이상 입력해주세요.")
                    continue
                
                # 확인
                print(f"\n📝 입력하신 검색어: '{keyword}'")
                confirm = input("✅ 맞습니까? (y/n): ").strip().lower()
                
                if confirm in ['y', 'yes', '예', 'ㅇ', '']:
                    print(f"🎯 '{keyword}' 검색을 시작합니다!")
                    return keyword
                else:
                    print("🔄 다시 입력해주세요.")
                    continue
                    
        except KeyboardInterrupt:
            print("\n⏹️ 검색이 취소되었습니다.")
            return None
        except Exception as e:
            logger.error(f"검색어 입력 중 오류: {e}")
            return None

    async def search_startup(self, keyword):
        """
        스타트업 검색 및 상세 페이지 진입 (Stealth 버전)
        """
        try:
            logger.info(f"🔍 Stealth 모드에서 '{keyword}' 검색 시작")
            
            # 검색창 찾기
            search_selectors = [
                'input[data-v-b3196f07][type="search"]',
                'input[placeholder*="기업"]',
                'input[placeholder*="검색"]',
                'input[type="search"]',
                '[data-v-b3196f07] input[type="search"]',
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        search_input = element
                        logger.info(f"✅ 검색창 발견: {selector}")
                        break
                except:
                    continue
            
            if not search_input:
                logger.error("❌ 검색창을 찾을 수 없음")
                await self.take_screenshot(f"thevc_search_error_{keyword.replace(' ', '_')}.png")
                return False
            
            # 검색어 입력 (인간처럼 천천히)
            await search_input.fill("")  # 기존 내용 지우기
            await asyncio.sleep(random.uniform(0.5, 1.5))  # 생각하는 시간
            
            # 글자 하나씩 입력하는 것처럼 (가끔)
            if random.random() < 0.3:  # 30% 확률로 타이핑 시뮬레이션
                logger.info("⌨️ 타이핑 시뮬레이션 모드")
                for char in keyword:
                    await search_input.type(char)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            else:
                await search_input.fill(keyword)
            
            logger.info(f"✅ 검색어 입력 완료: {keyword}")
            
            # 입력 후 잠깐 기다리기 (검토하는 시간)
            await asyncio.sleep(random.uniform(0.8, 2.5))
            
            # Enter 키 누르기
            await search_input.press('Enter')
            logger.info("✅ 검색 실행 (Enter)")
            
            # 검색 결과 대기 (더 긴 대기 시간)
            await asyncio.sleep(3.5)
            
            # 검색 결과 확인
            search_success = await self.check_search_results(keyword)
            
            if search_success:
                logger.info("✅ 검색 결과 확인 완료")
                
                # 검색 결과 스크린샷 저장
                await self.take_screenshot(f"thevc_search_results_{keyword.replace(' ', '_')}.png")
                
                # 첫 번째 검색 결과 클릭
                if await self.click_first_search_result():
                    logger.info("✅ 첫 번째 검색 결과 클릭 성공")
                    
                    # 상세 페이지 로딩 대기
                    await asyncio.sleep(3)
                    
                    # 상세 페이지 스크린샷 저장
                    await self.take_screenshot(f"thevc_company_detail_{keyword.replace(' ', '_')}.png")
                    
                    # 회사 정보 크롤링 및 JSON 저장
                    company_data = await self.extract_company_data(keyword)
                    if company_data:
                        await self.save_company_data_to_json(company_data, keyword)
                        logger.info(f"✅ '{keyword}' 회사 정보 JSON 저장 완료")
                    else:
                        logger.warning(f"⚠️ '{keyword}' 회사 정보 추출 실패")
                    
                    logger.info(f"🎉 '{keyword}' 검색 및 상세 페이지 진입 완료")
                    return True
                else:
                    logger.error("❌ 검색 결과 클릭 실패")
                    return False
            else:
                logger.warning("⚠️ 검색 결과 확인 실패")
                await self.take_screenshot(f"thevc_search_status_{keyword.replace(' ', '_')}.png")
                return None
                
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            await self.take_screenshot(f"thevc_search_error_{keyword.replace(' ', '_')}.png")
            return False

    async def check_search_results(self, keyword):
        """
        검색 결과 확인 (Stealth 버전)
        """
        try:
            logger.info(f"🔍 '{keyword}' 검색 결과 확인 중...")
            
            # 1단계: 텍스트 기반 확인 (가장 정확)
            try:
                page_text = await self.page.text_content('body')
                if page_text:
                    import re
                    # "기업 검색 결과 N개" 패턴 찾기
                    result_pattern = r'기업\s*검색\s*결과\s*(\d+)개'
                    match = re.search(result_pattern, page_text)
                    if match:
                        result_count = int(match.group(1))
                        logger.info(f"✅ 검색 결과 {result_count}개 발견 (텍스트 기반)")
                        return result_count > 0
                    
                    # 기본 검색 결과 텍스트 확인
                    if '기업 검색 결과' in page_text or '검색 결과' in page_text:
                        logger.info("✅ 검색 결과 페이지 확인 (텍스트 기반)")
                        return True
            except Exception as e:
                logger.warning(f"텍스트 기반 확인 실패: {e}")
            
            # 2단계: 요소 기반 확인 (개선된 방식)
            result_selectors = [
                'li[data-v-174ebeb4]',  # 검색 결과 아이템
                'div.item-wrap',        # 아이템 래퍼
                '[data-v-174ebeb4] .item-wrap',
                'ul li',                # 일반적인 리스트 아이템
            ]
            
            for selector in result_selectors:
                try:
                    elements = await self.page.locator(selector).count()
                    if elements > 0:
                        logger.info(f"✅ 검색 결과 {elements}개 발견 (요소 기반): {selector}")
                        return True
                except Exception as e:
                    logger.warning(f"선택자 {selector} 확인 실패: {e}")
                    continue
            
            # 3단계: URL 기반 확인 (백업)
            current_url = self.page.url
            if 'search' in current_url.lower() or '검색' in current_url:
                logger.info("✅ 검색 페이지 URL 확인 (URL 기반)")
                return True
            
            logger.warning("⚠️ 검색 결과를 확인할 수 없음")
            return False
            
        except Exception as e:
            logger.error(f"검색 결과 확인 실패: {e}")
            return False

    async def click_first_search_result(self):
        """
        첫 번째 검색 결과 클릭 (Stealth 버전)
        """
        try:
            logger.info("🖱️ 첫 번째 검색 결과 클릭 시도 중...")
            
            # 클릭 전 대기 (사용자 요청)
            await asyncio.sleep(1.5)
            
            # 정확한 선택자 우선 시도 (사용자 제공)
            precise_selector = "#core-container > div > div > div > div:nth-child(1) > div:nth-child(1) > ul > li:nth-child(1)"
            
            try:
                element = await self.page.wait_for_selector(precise_selector, timeout=5000)
                if element:
                    logger.info("✅ 정확한 선택자로 요소 발견")
                    await element.click()
                    logger.info("✅ 정확한 선택자로 클릭 성공")
                    return True
            except Exception as e:
                logger.warning(f"정확한 선택자 실패: {e}")
            
            # 백업 선택자들
            result_selectors = [
                'li[data-v-174ebeb4]:first-child',
                'div.item-wrap:first-child',
                '[data-v-174ebeb4] .item-wrap:first-child',
                'ul li:first-child',
                'li:first-child',
            ]
            
            for selector in result_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        logger.info(f"✅ 백업 선택자로 요소 발견: {selector}")
                        
                        # 다양한 클릭 방법 시도
                        click_methods = [
                            ("일반 클릭", lambda: element.click()),
                            ("강제 클릭", lambda: element.click(force=True)),
                            ("JavaScript 클릭", lambda: element.evaluate("el => el.click()")),
                            ("더블 클릭", lambda: element.dblclick()),
                            ("마우스 클릭", lambda: element.click(button="left")),
                        ]
                        
                        for method_name, click_method in click_methods:
                            try:
                                logger.info(f"🖱️ {method_name} 시도 중...")
                                await click_method()
                                await asyncio.sleep(2)
                                logger.info(f"✅ {method_name} 성공")
                                return True
                            except Exception as click_error:
                                logger.warning(f"❌ {method_name} 실패: {click_error}")
                                continue
                        
                except Exception as e:
                    logger.warning(f"선택자 {selector} 실패: {e}")
                    continue
            
            logger.error("❌ 모든 클릭 시도 실패")
            return False
            
        except Exception as e:
            logger.error(f"검색 결과 클릭 실패: {e}")
            return False

    async def extract_company_data(self, keyword):
        """
        회사 상세 페이지에서 정보 추출 (Stealth 버전)
        """
        try:
            logger.info(f"📊 '{keyword}' 회사 정보 추출 시작...")
            
            # 페이지 로딩 완료 대기
            await asyncio.sleep(3)
            
            company_data = {
                "company_name": keyword,
                "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "url": self.page.url,
                "basic_info": {},
                "overview": {},
                "keywords": [],
                "key_info": {},
                "products": []
            }
            
            # 1. 기업 개요 추출
            try:
                overview_section = await self.page.wait_for_selector('[data-v-715631b9]', timeout=5000)
                if overview_section:
                    # 회사명 추출
                    company_name_elements = await self.page.locator('mark.bg-none.text-gray-900').all()
                    if company_name_elements:
                        company_data["basic_info"]["company_name"] = await company_name_elements[0].text_content()
                    
                    # 설립일 추출
                    overview_text = await overview_section.text_content()
                    import re
                    
                    # 설립일 패턴 매칭
                    date_pattern = r'(\d{4}년\s*\d{1,2}월)'
                    date_match = re.search(date_pattern, overview_text)
                    if date_match:
                        company_data["basic_info"]["founded_date"] = date_match.group(1)
                    
                    # 회사 유형 추출
                    if "스타트업" in overview_text:
                        company_data["basic_info"]["company_type"] = "스타트업"
                    elif "주식회사" in overview_text:
                        company_data["basic_info"]["company_type"] = "주식회사"
                    
                    # 주요 제품/서비스 추출
                    if "주요 제품/서비스" in overview_text:
                        service_pattern = r'분야의\s*([^이]*?)이\s*주요 제품/서비스'
                        service_match = re.search(service_pattern, overview_text)
                        if service_match:
                            company_data["basic_info"]["main_service"] = service_match.group(1).strip()
                    
                    # 본사 위치 추출
                    location_pattern = r'본사는\s*([^에]*?)에\s*위치'
                    location_match = re.search(location_pattern, overview_text)
                    if location_match:
                        company_data["basic_info"]["headquarters"] = location_match.group(1).strip()
                    
                    # 대표자 추출
                    ceo_pattern = r'현재 대표자는\s*([^입]*?)입니다'
                    ceo_match = re.search(ceo_pattern, overview_text)
                    if ceo_match:
                        company_data["basic_info"]["ceo"] = ceo_match.group(1).strip()
                    
                    # 유사 기업 추출
                    similar_pattern = r'유사 기업은\s*([^등]*?)등'
                    similar_match = re.search(similar_pattern, overview_text)
                    if similar_match:
                        similar_companies = similar_match.group(1).strip().split('∙')
                        company_data["basic_info"]["similar_companies"] = [comp.strip() for comp in similar_companies if comp.strip()]
                    
                    company_data["overview"]["full_text"] = overview_text.strip()
                    logger.info("✅ 기업 개요 추출 완료")
                    
            except Exception as e:
                logger.warning(f"기업 개요 추출 실패: {e}")
            
            # 2. 제품/서비스 정보 추출
            try:
                product_chips = await self.page.locator('[data-v-44e3a713][data-v-069986de]').all()
                for chip in product_chips:
                    try:
                        product_name = await chip.locator('.chip-text').text_content()
                        if product_name:
                            # 제품 이미지 URL 추출
                            img_element = chip.locator('img')
                            img_src = ""
                            if await img_element.count() > 0:
                                img_src = await img_element.get_attribute('src')
                            
                            company_data["products"].append({
                                "name": product_name.strip(),
                                "image_url": img_src
                            })
                    except:
                        continue
                logger.info(f"✅ 제품 정보 {len(company_data['products'])}개 추출 완료")
            except Exception as e:
                logger.warning(f"제품 정보 추출 실패: {e}")
            
            # 3. 연관 키워드 추출
            try:
                keyword_section = await self.page.locator('[data-v-0150772a]').first
                if keyword_section:
                    keyword_chips = await keyword_section.locator('.chip-text').all()
                    chip_count = await keyword_chips.count()
                    for i in range(chip_count):
                        try:
                            chip = keyword_chips.nth(i)
                            keyword_text = await chip.text_content()
                            if keyword_text and keyword_text.strip() != "+5":
                                company_data["keywords"].append(keyword_text.strip())
                        except:
                            continue
                logger.info(f"✅ 연관 키워드 {len(company_data['keywords'])}개 추출 완료")
            except Exception as e:
                logger.warning(f"연관 키워드 추출 실패: {e}")
            
            # 4. 주요 정보 추출
            try:
                # 먼저 정확한 선택자로 투자 유치 금액 추출 시도
                try:
                    investment_element = await self.page.locator('#core-container > div > div > div > div.main-container.between-y-32.mb-32 > div:nth-child(1) > div > div > div:nth-child(1) > div.grid.fill-300.pb-12 > div:nth-child(4) > span:nth-child(2)').first
                    if investment_element:
                        investment_text = await investment_element.text_content()
                        if investment_text and investment_text.strip():
                            company_data["key_info"]["total_investment"] = investment_text.strip()
                            logger.info(f"✅ 정확한 선택자로 투자 금액 추출: {investment_text.strip()}")
                except Exception as e:
                    logger.debug(f"정확한 선택자로 투자 금액 추출 실패: {e}")
                
                # 다른 방법으로 투자 금액 추출 시도 (span 태그에서 직접)
                if not company_data["key_info"].get("total_investment"):
                    try:
                        # 투자 유치 금액이 포함된 span 요소들 검색
                        investment_spans = await self.page.locator('span:has-text("억")').all()
                        for span in investment_spans:
                            try:
                                span_text = await span.text_content()
                                if span_text and re.search(r'\d+억[+]?', span_text):
                                    # 부모 요소에서 "투자 유치" 텍스트 확인
                                    parent = span.locator('..')
                                    parent_text = await parent.text_content()
                                    if "투자 유치" in parent_text:
                                        company_data["key_info"]["total_investment"] = span_text.strip()
                                        logger.info(f"✅ span 태그에서 투자 금액 추출: {span_text.strip()}")
                                        break
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"span 태그에서 투자 금액 추출 실패: {e}")
                
                info_blocks = await self.page.locator('[data-v-d81b7dfa] .important-info-block').all()
                for block in info_blocks:
                    try:
                        block_text = await block.text_content()
                        if not block_text:
                            continue
                        
                        # 상태 정보
                        if "상태" in block_text:
                            status_match = re.search(r'상태.*?(비상장|상장)', block_text)
                            if status_match:
                                company_data["key_info"]["status"] = status_match.group(1)
                        
                        # 업력 정보
                        elif "업력" in block_text:
                            years_match = re.search(r'업력.*?(\d+\.?\d*년)', block_text)
                            if years_match:
                                company_data["key_info"]["business_years"] = years_match.group(1)
                        
                        # 투자 라운드
                        elif "투자 라운드" in block_text:
                            round_match = re.search(r'투자 라운드.*?\((\d+)건\).*?(Series [ABC]|Pre-A|Seed)', block_text)
                            if round_match:
                                company_data["key_info"]["investment_rounds"] = {
                                    "count": round_match.group(1),
                                    "latest_round": round_match.group(2)
                                }
                        
                        # 투자 유치 금액 (정확한 선택자로 이미 추출되지 않은 경우만)
                        elif "투자 유치" in block_text and not company_data["key_info"].get("total_investment"):
                            # 기존 방식으로 먼저 시도
                            investment_match = re.search(r'투자 유치.*?(\d+억?\+?)', block_text)
                            if investment_match:
                                company_data["key_info"]["total_investment"] = investment_match.group(1)
                            else:
                                # 더 포괄적인 패턴으로 재시도
                                investment_match2 = re.search(r'(\d+억[+]?)', block_text)
                                if investment_match2:
                                    company_data["key_info"]["total_investment"] = investment_match2.group(1)
                        
                        # 임직원 수
                        elif "임직원 수" in block_text:
                            employee_match = re.search(r'(\d+)명', block_text)
                            growth_match = re.search(r'YoY\s*(\d+%)', block_text)
                            if employee_match:
                                company_data["key_info"]["employees"] = {
                                    "count": employee_match.group(1) + "명",
                                    "yoy_growth": growth_match.group(1) if growth_match else None
                                }
                        
                        # 특허 정보
                        elif "특허" in block_text:
                            patent_match = re.search(r'(\d+)개', block_text)
                            if patent_match:
                                company_data["key_info"]["patents"] = patent_match.group(1) + "개"
                        
                    except Exception as e:
                        logger.warning(f"주요 정보 블록 처리 실패: {e}")
                        continue
                
                logger.info(f"✅ 주요 정보 {len(company_data['key_info'])}개 추출 완료")
            except Exception as e:
                logger.warning(f"주요 정보 추출 실패: {e}")
            
            # 5. 홈페이지 URL 추출
            try:
                homepage_links = await self.page.locator('a[href*="ref=thevc"]').all()
                if homepage_links:
                    homepage_link = homepage_links[0]
                    homepage_url = await homepage_link.get_attribute('href')
                    if homepage_url:
                        # ref=thevc 제거
                        clean_url = homepage_url.split('?ref=thevc')[0]
                        company_data["basic_info"]["homepage"] = clean_url
                        logger.info("✅ 홈페이지 URL 추출 완료")
            except Exception as e:
                logger.warning(f"홈페이지 URL 추출 실패: {e}")
            
            # 5-1. 특허 정보 추출 (뉴스 전에 추가)
            company_data["patents"] = []
            try:
                logger.info("📜 특허 정보 추출 시작...")
                
                                # 특허 섹션의 "더보기" 버튼 반복 클릭
                more_button_selector = "#core-container > div > div > div > div.main-container.between-y-32.mb-32 > div:nth-child(6) > div.flex.justify-center > button > div:nth-child(2)"
                
                logger.info("🔄 특허 '더보기' 버튼 반복 클릭 시작...")
                click_count = 0
                max_clicks = 20  # 최대 20번까지만 클릭 (무한루프 방지)
                
                while click_count < max_clicks:
                    try:
                        # 더보기 버튼이 존재하는지 확인
                        more_button = self.page.locator(more_button_selector).first
                        button_count = await self.page.locator(more_button_selector).count()
                        
                        if button_count > 0:
                            # 버튼이 보이는지 확인
                            is_visible = await more_button.is_visible()
                            
                            if is_visible:
                                # 버튼 텍스트 확인 ("접기"가 나타나면 중단)
                                try:
                                    button_text = await more_button.text_content()
                                    if button_text and "접기" in button_text:
                                        logger.info(f"🛑 '접기' 버튼 발견: '{button_text.strip()}' - 더보기 클릭 중단")
                                        logger.info("✅ 모든 특허가 완전히 펼쳐졌습니다!")
                                        break
                                    else:
                                        logger.info(f"🔍 버튼 텍스트 확인: '{button_text.strip() if button_text else 'None'}'")
                                except Exception as e:
                                    logger.warning(f"⚠️ 버튼 텍스트 확인 실패: {e}")
                                
                                logger.info(f"🖱️ 특허 '더보기' 버튼 클릭 {click_count + 1}회 시도...")
                                
                                # 버튼으로 스크롤하여 확실히 보이도록 하기
                                await more_button.scroll_into_view_if_needed()
                                await asyncio.sleep(0.5)
                                
                                # 버튼 클릭
                                await more_button.click()
                                click_count += 1
                                
                                logger.info(f"✅ 특허 '더보기' 버튼 {click_count}회 클릭 완료")
                                
                                # 1초 대기 (로딩 시간 및 텍스트 변경 대기)
                                await asyncio.sleep(1)
                                
                                # 클릭 후 다시 버튼 텍스트 확인 (상태 변화 감지)
                                try:
                                    await asyncio.sleep(0.5)  # 텍스트 변경 대기
                                    updated_button_text = await more_button.text_content()
                                    if updated_button_text and "접기" in updated_button_text:
                                        logger.info(f"🛑 클릭 후 '접기' 버튼으로 변경됨: '{updated_button_text.strip()}' - 완료!")
                                        logger.info("✅ 모든 특허가 완전히 펼쳐졌습니다!")
                                        break
                                except Exception as e:
                                    logger.warning(f"⚠️ 클릭 후 버튼 텍스트 확인 실패: {e}")
                                
                            else:
                                logger.info("👁️ 특허 '더보기' 버튼이 더 이상 보이지 않음 - 모든 특허 로드 완료")
                                break
                        else:
                            logger.info("🔍 특허 '더보기' 버튼을 찾을 수 없음 - 모든 특허 로드 완료")
                            break
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 특허 '더보기' 버튼 클릭 중 오류 (시도 {click_count + 1}): {e}")
                        break
                
                # 최종 버튼 상태 확인
                try:
                    final_button = self.page.locator(more_button_selector).first
                    final_button_count = await self.page.locator(more_button_selector).count()
                    
                    if final_button_count > 0:
                        final_button_text = await final_button.text_content()
                        if final_button_text:
                            logger.info(f"🔍 최종 버튼 상태: '{final_button_text.strip()}'")
                            if "접기" in final_button_text:
                                logger.info("🎯 성공: 모든 특허가 완전히 펼쳐진 상태입니다!")
                            elif "더보기" in final_button_text:
                                logger.warning("⚠️ 주의: 아직 '더보기' 상태입니다. 일부 특허가 숨겨져 있을 수 있습니다.")
                except Exception as e:
                    logger.warning(f"⚠️ 최종 버튼 상태 확인 실패: {e}")
                
                if click_count > 0:
                    logger.info(f"🎯 특허 '더보기' 버튼 총 {click_count}회 클릭 완료")
                else:
                    logger.info("ℹ️ 특허 '더보기' 버튼이 없거나 이미 모든 특허가 로드됨")
                
                # 특허 정보 추출 시작
                logger.info("📋 특허 상세 정보 추출 시작...")
                
                # 특허 컨테이너 찾기 (6번째 섹션)
                patent_container_selector = "#core-container > div > div > div > div.main-container.between-y-32.mb-32 > div:nth-child(6)"
                
                try:
                    patent_container = self.page.locator(patent_container_selector).first
                    container_count = await self.page.locator(patent_container_selector).count()
                    
                    if container_count > 0:
                        logger.info("✅ 특허 컨테이너 발견")
                        
                        # 특허 컨테이너로 스크롤
                        await patent_container.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        
                        # 정확한 특허 아이템 선택자 사용 (HTML 구조 기반)
                        patent_items_selector = f"{patent_container_selector} > div.flex.direction-col.gap-16 > a"
                        
                        try:
                            patent_items = await self.page.locator(patent_items_selector).all()
                            item_count = len(patent_items)
                            
                            logger.info(f"🔍 특허 아이템 {item_count}개 발견")
                            
                            patents_found = False
                            
                            for i, item in enumerate(patent_items):
                                try:
                                    logger.info(f"📋 특허 {i+1}번 처리 중...")
                                    
                                    # 특허 정보 초기화
                                    patent_info = {
                                        "title": "",
                                        "date": "",
                                        "status": "",
                                        "patent_url": "",
                                        "abstract": "",
                                        "patent_number": "",
                                        "raw_text": ""
                                    }
                                    
                                    # 특허 URL 추출
                                    try:
                                        patent_url = await item.get_attribute('href')
                                        if patent_url:
                                            patent_info["patent_url"] = patent_url
                                            
                                            # URL에서 특허 번호 추출 (doi 링크에서)
                                            import re
                                            doi_match = re.search(r'doi\.org/10\.8080/(\d+)', patent_url)
                                            if doi_match:
                                                patent_info["patent_number"] = doi_match.group(1)
                                                
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ 특허 {i+1} URL 추출 실패: {e}")
                                    
                                    # 특허 제목 추출 (정확한 선택자 사용)
                                    try:
                                        title_element = item.locator('div.body-1.mb-8').first
                                        title_count = await item.locator('div.body-1.mb-8').count()
                                        
                                        if title_count > 0:
                                            title = await title_element.text_content()
                                            if title:
                                                patent_info["title"] = title.strip()
                                                logger.info(f"  📝 제목: {title.strip()[:40]}...")
                                        else:
                                            logger.warning(f"  ⚠️ 특허 {i+1} 제목 요소를 찾을 수 없음")
                                            
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ 특허 {i+1} 제목 추출 실패: {e}")
                                    
                                    # 날짜 및 상태 추출 (정확한 선택자 사용)
                                    try:
                                        date_element = item.locator('div.text-sub.body-3.mb-4').first
                                        date_count = await item.locator('div.text-sub.body-3.mb-4').count()
                                        
                                        if date_count > 0:
                                            date_text = await date_element.text_content()
                                            if date_text:
                                                date_text = date_text.strip()
                                                logger.info(f"  📅 날짜/상태: {date_text}")
                                                
                                                # 날짜와 상태 분리 (예: "2025-05-13∙등록")
                                                if '∙' in date_text:
                                                    parts = date_text.split('∙')
                                                    if len(parts) == 2:
                                                        patent_info["date"] = parts[0].strip()
                                                        patent_info["status"] = parts[1].strip()
                                                else:
                                                    # 날짜와 상태가 분리되지 않은 경우
                                                    patent_info["date"] = date_text
                                                    
                                                    # 상태 추출
                                                    if "등록" in date_text:
                                                        patent_info["status"] = "등록"
                                                    elif "공개" in date_text:
                                                        patent_info["status"] = "공개"
                                                    elif "출원" in date_text:
                                                        patent_info["status"] = "출원"
                                        else:
                                            logger.warning(f"  ⚠️ 특허 {i+1} 날짜 요소를 찾을 수 없음")
                                            
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ 특허 {i+1} 날짜 추출 실패: {e}")
                                    
                                    # 특허 요약(abstract) 추출
                                    try:
                                        abstract_element = item.locator('p.text-sub.text-truncate-from-2nd').first
                                        abstract_count = await item.locator('p.text-sub.text-truncate-from-2nd').count()
                                        
                                        if abstract_count > 0:
                                            abstract = await abstract_element.text_content()
                                            if abstract:
                                                patent_info["abstract"] = abstract.strip()
                                                logger.info(f"  📄 요약: {abstract.strip()[:50]}...")
                                        else:
                                            logger.warning(f"  ⚠️ 특허 {i+1} 요약 요소를 찾을 수 없음")
                                            
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ 특허 {i+1} 요약 추출 실패: {e}")
                                    
                                    # 전체 텍스트 백업
                                    try:
                                        full_text = await item.text_content()
                                        if full_text:
                                            patent_info["raw_text"] = full_text.strip()
                                    except Exception as e:
                                        logger.warning(f"  ⚠️ 특허 {i+1} 전체 텍스트 추출 실패: {e}")
                                    
                                    # 유효한 특허 정보인지 확인 (제목이나 URL이 있어야 함)
                                    if patent_info["title"] or patent_info["patent_url"]:
                                        company_data["patents"].append(patent_info)
                                        patents_found = True
                                        
                                        # 로그 출력
                                        title_display = patent_info["title"][:30] if patent_info["title"] else "제목 없음"
                                        date_display = patent_info["date"] if patent_info["date"] else "날짜 없음"
                                        status_display = patent_info["status"] if patent_info["status"] else "상태 없음"
                                        
                                        logger.info(f"  ✅ 특허 {i+1} 저장 완료: {title_display} ({date_display}, {status_display})")
                                    else:
                                        logger.warning(f"  ⚠️ 특허 {i+1} 필수 정보 부족 - 저장하지 않음")
                                    
                                except Exception as e:
                                    logger.warning(f"  ❌ 특허 {i+1} 처리 실패: {e}")
                                    continue
                            
                            if patents_found:
                                logger.info(f"🎉 특허 정보 추출 성공! 총 {len(company_data['patents'])}개")
                            else:
                                logger.warning("⚠️ 유효한 특허 정보를 찾을 수 없음")
                                        
                        except Exception as e:
                            logger.warning(f"특허 아이템 추출 실패: {e}")
                            
                            # 대체 방법: 일반적인 선택자들 시도
                            logger.info("🔄 대체 특허 선택자로 재시도...")
                            
                            alternative_selectors = [
                                f"{patent_container_selector} a[data-v-b766f8d4]",  # data-v 속성 기반
                                f"{patent_container_selector} a.block-wrap",       # 클래스 기반
                                f"{patent_container_selector} a[href*='doi.org']", # doi 링크 기반
                            ]
                            
                            for alt_selector in alternative_selectors:
                                try:
                                    alt_items = await self.page.locator(alt_selector).all()
                                    if len(alt_items) > 0:
                                        logger.info(f"✅ 대체 선택자로 특허 {len(alt_items)}개 발견: {alt_selector}")
                                        # 여기서 같은 로직 적용 가능
                                        break
                                except:
                                    continue
                        
                        if not patents_found:
                            logger.warning("⚠️ 특허 정보를 찾을 수 없습니다 - 대체 방법 시도")
                            
                            # 대체 방법: 전체 특허 컨테이너에서 텍스트 추출
                            try:
                                container_text = await patent_container.text_content()
                                if container_text and "특허" in container_text:
                                    logger.info("📄 특허 컨테이너에서 텍스트 발견 - 원시 텍스트로 저장")
                                    
                                    # 간단한 특허 정보라도 저장
                                    patent_info = {
                                        "title": "특허 정보 (상세 추출 실패)",
                                        "patent_number": "",
                                        "application_date": "",
                                        "registration_date": "",
                                        "status": "",
                                        "inventors": [],
                                        "abstract": "",
                                        "raw_text": container_text.strip()
                                    }
                                    
                                    # 특허 개수라도 추출
                                    import re
                                    patent_count_match = re.search(r'(\d+)개', container_text)
                                    if patent_count_match:
                                        patent_info["title"] = f"특허 {patent_count_match.group(1)}개 (상세 정보 추출 필요)"
                                    
                                    company_data["patents"].append(patent_info)
                                    patents_found = True
                                    
                            except Exception as e:
                                logger.warning(f"대체 특허 추출 실패: {e}")
                        
                        logger.info(f"🎉 특허 정보 총 {len(company_data['patents'])}개 추출 완료!")
                        
                        # 특허 요약 출력
                        if company_data["patents"]:
                            logger.info("📜 추출된 특허 목록:")
                            for idx, patent in enumerate(company_data["patents"][:3], 1):  # 처음 3개만 로그에 표시
                                title_display = patent['title'][:40] if patent['title'] else "제목 없음"
                                number_display = f" ({patent['patent_number']})" if patent['patent_number'] else ""
                                logger.info(f"  {idx}. {title_display}{number_display}")
                            if len(company_data["patents"]) > 3:
                                logger.info(f"  ... 외 {len(company_data['patents']) - 3}개 더")
                        else:
                            logger.info("📜 추출된 특허가 없습니다")
                    
                    else:
                        logger.warning("⚠️ 특허 컨테이너를 찾을 수 없습니다")
                
                except Exception as e:
                    logger.error(f"❌ 특허 컨테이너 처리 실패: {e}")
                
            except Exception as e:
                logger.error(f"❌ 특허 정보 추출 실패: {e}")
                # 디버깅을 위한 스크린샷 저장
                try:
                    await self.page.screenshot(path=f"debug_patent_section_{keyword.replace(' ', '_')}.png")
                    logger.info(f"🔍 특허 섹션 디버깅 스크린샷 저장: debug_patent_section_{keyword.replace(' ', '_')}.png")
                except:
                    pass
            
            # 6. 뉴스 정보 추출 (Stealth 버전 - 개선된 버전)
            company_data["news"] = []
            try:
                logger.info("📰 뉴스 정보 추출 시작...")
                
                # 먼저 뉴스 섹션으로 스크롤하는 버튼 클릭
                scroll_button_selector = "#core-container > div > div > div > div.main-container.between-y-32.mb-32 > div:nth-child(1) > div > div > div.py-16.flex.direction-col > div > button > div:nth-child(2)"
                
                logger.info("📍 STEP 1: 뉴스 섹션 스크롤 버튼 찾기 시작")
                logger.info(f"🔍 스크롤 버튼 선택자: {scroll_button_selector}")
                
                try:
                    logger.info("🔄 뉴스 섹션으로 스크롤 버튼 찾는 중...")
                    scroll_button = self.page.locator(scroll_button_selector).first
                    scroll_button_count = await self.page.locator(scroll_button_selector).count()
                    logger.info(f"🔢 스크롤 버튼 개수: {scroll_button_count}")
                    
                    if scroll_button and scroll_button_count > 0:
                        logger.info("✅ 스크롤 버튼 발견 - 클릭 시도")
                        
                        # 버튼이 보이는지 확인
                        is_visible = await scroll_button.is_visible()
                        logger.info(f"👁️ 스크롤 버튼 가시성: {is_visible}")
                        
                        # 버튼으로 스크롤
                        await scroll_button.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        logger.info("📍 스크롤 버튼으로 이동 완료")
                        
                        # 클릭 시도
                        await scroll_button.click()
                        logger.info("🖱️ 스크롤 버튼 클릭 완료")
                        
                        # 스크롤 후 페이지 로딩 대기
                        await asyncio.sleep(3)
                        logger.info("⏳ 뉴스 섹션 로딩 대기 완료")
                    else:
                        logger.warning("⚠️ 스크롤 버튼을 찾을 수 없음 - 직접 스크롤 시도")
                        # 페이지 하단으로 스크롤
                        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                        logger.info("📜 JavaScript로 페이지 하단 스크롤 완료")
                except Exception as e:
                    logger.error(f"❌ 스크롤 버튼 클릭 실패: {e} - 대체 스크롤 방법 시도")
                    # 대체 스크롤 방법들
                    try:
                        # 방법 1: 키보드 End 키
                        logger.info("🔄 대체 방법 1: End 키 사용")
                        await self.page.keyboard.press('End')
                        await asyncio.sleep(2)
                        logger.info("⌨️ End 키로 페이지 하단 이동 완료")
                    except Exception as e2:
                        logger.warning(f"⚠️ End 키 실패: {e2}")
                        try:
                            # 방법 2: JavaScript 스크롤
                            logger.info("🔄 대체 방법 2: JavaScript 스크롤 사용")
                            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await asyncio.sleep(2)
                            logger.info("📜 JavaScript로 페이지 하단 이동 완료")
                        except Exception as e3:
                            logger.error(f"❌ JavaScript 스크롤도 실패: {e3}")
                            logger.warning("⚠️ 모든 스크롤 방법 실패 - 현재 위치에서 뉴스 검색")
                
                logger.info("📍 STEP 2: 뉴스 컨테이너 찾기 시작")
                
                # 뉴스 컨테이너 찾기
                news_container_selector = "#core-container > div > div > div > div.news-container"
                logger.info(f"🔍 뉴스 컨테이너 선택자: {news_container_selector}")
                
                # 뉴스 컨테이너가 로딩될 때까지 잠시 대기
                logger.info("🔍 뉴스 컨테이너 로딩 대기 중...")
                news_container = None
                
                # 최대 10초 동안 뉴스 컨테이너 찾기 시도
                for attempt in range(10):
                    try:
                        logger.info(f"🔄 뉴스 컨테이너 찾기 시도 {attempt + 1}/10")
                        news_container = self.page.locator(news_container_selector).first
                        container_count = await self.page.locator(news_container_selector).count()
                        
                        logger.info(f"🔢 뉴스 컨테이너 개수: {container_count}")
                        
                        if container_count > 0:
                            # 컨테이너가 실제로 존재하는지 확인
                            is_visible = await news_container.is_visible()
                            logger.info(f"👁️ 뉴스 컨테이너 가시성: {is_visible}")
                            
                            # 컨테이너 내용 확인
                            container_text = await news_container.text_content()
                            logger.info(f"📄 뉴스 컨테이너 텍스트 길이: {len(container_text) if container_text else 0}")
                            if container_text:
                                logger.info(f"📄 뉴스 컨테이너 텍스트 샘플 (처음 100자): {container_text[:100]}...")
                            
                            logger.info(f"✅ 뉴스 컨테이너 발견 (시도 {attempt + 1}회)")
                            break
                        else:
                            logger.info(f"⏳ 뉴스 컨테이너 대기 중... (시도 {attempt + 1}/10)")
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning(f"⚠️ 뉴스 컨테이너 찾기 중 오류 (시도 {attempt + 1}): {e}")
                        await asyncio.sleep(1)
                        continue
                
                # 뉴스 컨테이너가 발견되었는지 최종 확인
                final_container_count = await self.page.locator(news_container_selector).count()
                logger.info(f"🔍 최종 뉴스 컨테이너 개수: {final_container_count}")
                
                if final_container_count > 0:
                    news_container = self.page.locator(news_container_selector).first
                    logger.info("✅ 뉴스 컨테이너 발견")
                    
                    # 뉴스 컨테이너로 스크롤하여 확실히 보이도록 하기
                    try:
                        await news_container.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        logger.info("📍 뉴스 컨테이너로 스크롤 완료")
                    except Exception as e:
                        logger.warning(f"뉴스 컨테이너 스크롤 실패: {e}")
                    
                    # 뉴스 섹션 확인을 위한 스크린샷 (디버깅용)
                    try:
                        await self.page.screenshot(path=f"debug_news_section_{keyword.replace(' ', '_')}.png")
                        logger.info(f"🔍 뉴스 섹션 디버깅 스크린샷 저장: debug_news_section_{keyword.replace(' ', '_')}.png")
                    except:
                        pass
                    
                    logger.info("📍 STEP 3: 첫 번째 뉴스 정보 추출 시작")
                    
                    # 🎯 모든 뉴스 정보 추출 (최대 12개)
                    logger.info("🎯 모든 뉴스 정보 추출 시작...")
                    
                    try:
                        # 최대 12개 뉴스 크롤링 (nth-child(2)부터 nth-child(13)까지)
                        max_news_count = 12
                        successful_news = 0
                        
                        for i in range(1, max_news_count + 1):
                            nth_child = i + 1  # 1번째 뉴스 = nth-child(2)
                            
                            logger.info(f"📰 {i}번째 뉴스 추출 시작 (nth-child({nth_child}))")
                            
                            # 뉴스 제목 선택자
                            news_title_selector = f"#core-container > div > div > div > div.news-container > div:nth-child({nth_child}) > div > div.flex-1.overflow-x-hidden > div.text-truncate-from-2nd.text-16.mb-8"
                            
                            # 뉴스 링크 선택자
                            news_link_selector = f"#core-container > div > div > div > div.news-container > div:nth-child({nth_child})"
                            
                            try:
                                # 제목 추출
                                title_element = self.page.locator(news_title_selector).first
                                title_count = await self.page.locator(news_title_selector).count()
                                
                                title = ""
                                if title_count > 0:
                                    is_title_visible = await title_element.is_visible()
                                    if is_title_visible:
                                        title = await title_element.text_content()
                                        if title:
                                            title = title.strip()
                                            logger.info(f"  📝 {i}번째 뉴스 제목: {title[:30]}...")
                                        else:
                                            logger.warning(f"  ⚠️ {i}번째 뉴스 제목이 비어있음")
                                            continue
                                    else:
                                        logger.warning(f"  ⚠️ {i}번째 뉴스 제목이 보이지 않음")
                                        continue
                                else:
                                    logger.warning(f"  ⚠️ {i}번째 뉴스 제목 요소를 찾을 수 없음")
                                    continue
                                
                                # 링크 추출
                                link_element = self.page.locator(news_link_selector).first
                                link_count = await self.page.locator(news_link_selector).count()
                                
                                link = ""
                                if link_count > 0:
                                    is_link_visible = await link_element.is_visible()
                                    if is_link_visible:
                                        link = await link_element.get_attribute('to')
                                        if link:
                                            link = link.strip()
                                            logger.info(f"  🔗 {i}번째 뉴스 링크: {link}")
                                        else:
                                            logger.warning(f"  ⚠️ {i}번째 뉴스 링크가 비어있음")
                                            continue
                                    else:
                                        logger.warning(f"  ⚠️ {i}번째 뉴스 링크가 보이지 않음")
                                        continue
                                else:
                                    logger.warning(f"  ⚠️ {i}번째 뉴스 링크 요소를 찾을 수 없음")
                                    continue
                                
                                # 뉴스 데이터 저장
                                if title and link:
                                    news_data = {
                                        "title": title,
                                        "link": link
                                    }
                                    company_data["news"].append(news_data)
                                    successful_news += 1
                                    logger.info(f"  ✅ {i}번째 뉴스 저장 완료!")
                                else:
                                    logger.warning(f"  ⚠️ {i}번째 뉴스 필수 정보 누락")
                                    
                            except Exception as e:
                                logger.warning(f"  ❌ {i}번째 뉴스 처리 실패: {e}")
                                continue
                        
                        logger.info(f"🎉 뉴스 크롤링 완료: 총 {successful_news}개 성공!")
                        
                        if successful_news == 0:
                            logger.warning(f"  ⚠️ 모든 뉴스 추출 실패")
                            
                            # 상세 디버깅
                            logger.info("🔍 상세 디버깅 정보:")
                            
                            # 1. 뉴스 컨테이너의 자식 요소들 확인
                            try:
                                child_divs = await self.page.locator("#core-container > div > div > div > div.news-container > div").count()
                                logger.info(f"  📂 뉴스 컨테이너 자식 div 개수: {child_divs}")
                                
                                for i in range(min(child_divs, 5)):  # 처음 5개만 확인
                                    child_selector = f"#core-container > div > div > div > div.news-container > div:nth-child({i+1})"
                                    child_element = self.page.locator(child_selector).first
                                    if child_element:
                                        child_text = await child_element.text_content()
                                        logger.info(f"    📄 자식 {i+1}: {child_text[:50] if child_text else 'None'}...")
                            except Exception as e:
                                logger.warning(f"  ❌ 자식 요소 확인 실패: {e}")
                            
                            # 2. 전체 뉴스 컨테이너의 HTML 구조 확인
                            try:
                                container_html = await news_container.inner_html()
                                logger.info(f"  📄 뉴스 컨테이너 HTML (처음 1000자): {container_html[:1000]}...")
                            except Exception as e:
                                logger.warning(f"  ❌ HTML 구조 확인 실패: {e}")
                        
                    except Exception as e:
                        logger.error(f"❌ 첫 번째 뉴스 추출 중 오류 발생: {e}")
                        
                        # 페이지 전체 상태 확인
                        logger.info("🔍 페이지 전체 상태 확인:")
                        try:
                            page_content = await self.page.content()
                            
                            # HTML에서 뉴스 관련 키워드 검색
                            keywords_to_check = [
                                "news-container",
                                "text-truncate-from-2nd.text-16.mb-8",
                                "뉴스",
                                "기사",
                                "뉴스 썸네일"
                            ]
                            
                            for keyword in keywords_to_check:
                                exists = keyword in page_content
                                logger.info(f"  🔍 '{keyword}' 존재: {exists}")
                                
                            # 현재 URL 확인
                            current_url = self.page.url
                            logger.info(f"  🌐 현재 URL: {current_url}")
                            
                        except Exception as e2:
                            logger.error(f"  ❌ 페이지 상태 확인 실패: {e2}")
                    
                    logger.info(f"🎉 뉴스 정보 총 {len(company_data['news'])}개 추출 완료!")
                    
                    # 뉴스 요약 출력
                    if company_data["news"]:
                        logger.info("📰 추출된 뉴스 목록:")
                        for idx, news in enumerate(company_data["news"][:3], 1):  # 처음 3개만 로그에 표시
                            logger.info(f"  {idx}. {news['title'][:50]}... ({news['publisher']})")
                        if len(company_data["news"]) > 3:
                            logger.info(f"  ... 외 {len(company_data['news']) - 3}개 더")
                else:
                    logger.warning("⚠️ 뉴스 컨테이너를 찾을 수 없습니다")
                    # 대체 방법 시도
                    logger.info("🔄 대체 뉴스 선택자로 재시도...")
                    alternative_selectors = [
                        '[data-v-bbc8ac04].news-container',
                        '.news-container',
                        '[class*="news"]',
                    ]
                    
                    for alt_selector in alternative_selectors:
                        try:
                            alt_container = self.page.locator(alt_selector).first
                            if alt_container:
                                logger.info(f"✅ 대체 선택자로 뉴스 컨테이너 발견: {alt_selector}")
                                break
                        except:
                            continue
                    
            except Exception as e:
                logger.error(f"❌ 뉴스 정보 추출 실패: {e}")
                # 디버깅을 위한 페이지 소스 일부 확인
                try:
                    page_text = await self.page.text_content('body')
                    if '뉴스' in page_text:
                        logger.info("📄 페이지에 '뉴스' 텍스트가 존재하지만 추출에 실패했습니다")
                    else:
                        logger.info("📄 페이지에 '뉴스' 텍스트를 찾을 수 없습니다")
                except:
                    pass
            
            logger.info(f"🎉 '{keyword}' 회사 정보 추출 완료")
            return company_data
            
        except Exception as e:
            logger.error(f"회사 정보 추출 실패: {e}")
            return None

    async def save_company_data_to_json(self, company_data, keyword):
        """
        회사 정보를 JSON 파일로 저장
        """
        try:
            # 파일명 생성 (안전한 파일명)
            safe_keyword = keyword.replace(' ', '_').replace('/', '_').replace('\\', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"company_data_{safe_keyword}_{timestamp}.json"
            
            # JSON 파일 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(company_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📁 JSON 파일 저장: {filename}")
            
            # 요약 정보 출력
            print(f"\n📊 '{keyword}' 회사 정보 추출 완료!")
            print("=" * 50)
            
            if company_data.get("basic_info"):
                basic = company_data["basic_info"]
                if basic.get("company_name"):
                    print(f"🏢 회사명: {basic['company_name']}")
                if basic.get("founded_date"):
                    print(f"📅 설립일: {basic['founded_date']}")
                if basic.get("main_service"):
                    print(f"🔧 주요 서비스: {basic['main_service']}")
                if basic.get("headquarters"):
                    print(f"📍 본사: {basic['headquarters']}")
                if basic.get("ceo"):
                    print(f"👤 대표자: {basic['ceo']}")
                if basic.get("homepage"):
                    print(f"🌐 홈페이지: {basic['homepage']}")
            
            if company_data.get("key_info"):
                key = company_data["key_info"]
                if key.get("status"):
                    print(f"📈 상태: {key['status']}")
                if key.get("business_years"):
                    print(f"⏰ 업력: {key['business_years']}")
                if key.get("total_investment"):
                    print(f"💰 총 투자: {key['total_investment']}")
                if key.get("employees"):
                    emp = key["employees"]
                    growth_text = f" (YoY {emp['yoy_growth']})" if emp.get('yoy_growth') else ""
                    print(f"👥 임직원: {emp['count']}{growth_text}")
                if key.get("patents"):
                    print(f"📜 특허: {key['patents']}")
            
            if company_data.get("products"):
                print(f"🛍️ 제품/서비스: {len(company_data['products'])}개")
                for product in company_data["products"][:3]:  # 최대 3개만 표시
                    print(f"   - {product['name']}")
            
            if company_data.get("keywords"):
                print(f"🏷️ 키워드: {', '.join(company_data['keywords'][:5])}")  # 최대 5개만 표시
            
            if company_data.get("patents"):
                print(f"📜 특허: {len(company_data['patents'])}개")
                for patent in company_data["patents"][:2]:  # 최대 2개만 표시
                    title_display = patent['title'][:40] if patent['title'] else "제목 없음"
                    number_display = f" ({patent['patent_number']})" if patent['patent_number'] else ""
                    print(f"   - {title_display}{number_display}")
            
            if company_data.get("news"):
                print(f"📰 뉴스: {len(company_data['news'])}개")
            
            print(f"💾 JSON 파일: {filename}")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"JSON 파일 저장 실패: {e}")
            return False

async def run_stealth_crawler():
    """
    Stealth 모드 완전 크롤러 실행 (로그인 + 검색 포함)
    """
    if not STEALTH_AVAILABLE:
        print("❌ playwright-stealth 라이브러리를 먼저 설치하세요:")
        print("pip install playwright-stealth")
        return
    
    crawler = TheVCStealthCrawler()
    
    try:
        print("🥷 TheVC Stealth 크롤러 시작...")
        print("=" * 50)
        print("💡 Stealth 모드로 탐지를 우회하며 크롤링합니다!")
        print("")
        
        # 초기화 (자동 모드에서는 headless)
        auto_mode = os.environ.get('STEALTH_AUTO_MODE', '').lower() == 'true'
        is_headless = auto_mode  # 자동 모드면 headless
        
        print("📡 Stealth 브라우저 초기화 중...")
        if auto_mode:
            print("🤖 자동 모드: headless 브라우저로 실행")
        
        if not await crawler.initialize(headless=is_headless, use_saved_state=True):
            print("❌ Stealth 초기화 실패")
            return
        
        print("✅ Stealth 브라우저 초기화 완료")
        
        # 사이트 접속
        print("🌐 TheVC 사이트 접속 중...")
        if not await crawler.navigate_to_thevc():
            print("❌ Stealth 사이트 접속 실패")
            return
        
        print("✅ 사이트 접속 성공")
        
        # Stealth 효과 검증
        print("\n🔍 Stealth 효과 검증 중...")
        stealth_success = await crawler.check_stealth_effectiveness()
        if stealth_success:
            print("🎉 Stealth 모드 효과 확인!")
        else:
            print("⚠️ Stealth 모드 효과 제한적 - 하지만 진행")
        
        # 로그인 상태 확인
        print("\n🔍 현재 로그인 상태 확인 중...")
        is_logged_in = await crawler.check_if_logged_in()
        
        if is_logged_in is True:
            print("🎉 이미 로그인된 상태입니다!")
            print("💾 저장된 Stealth 세션이 유효합니다")
            print("📸 현재 상태 스크린샷 저장 중...")
            await crawler.take_screenshot("thevc_stealth_already_logged_in.png")
            print("✅ Stealth 세션 복원 완료!")
            
            # 이미 로그인된 상태에서도 검색 기능 실행
            await perform_stealth_search_process(crawler)
            
        elif is_logged_in is False:
            print("❌ 로그인이 필요합니다")
            print("🔑 Stealth 모드로 자동 로그인을 시작합니다...")
            print("")
            
            # 초기 스크린샷 저장
            print("📸 Stealth 초기 스크린샷 저장 중...")
            await crawler.take_screenshot("thevc_stealth_initial.png")
            print("✅ 초기 스크린샷 저장 완료")
            
            # 전체 로그인 과정 수행
            login_success = await perform_stealth_login_process(crawler)
            
            if login_success:
                print("\n💾 Stealth 세션 상태 저장 중...")
                if await crawler.save_stealth_session():
                    print("✅ Stealth 세션 저장 완료! 다음에는 자동으로 로그인됩니다")
                    print("📸 로그인 완료 스크린샷 저장 중...")
                    await crawler.take_screenshot("thevc_stealth_login_success.png")
                    print("✅ Stealth 로그인 완료!")
                else:
                    print("⚠️ 세션 저장에 실패했지만 로그인은 성공했습니다")
                
                # 로그인 성공 후 검색 기능 실행
                await perform_stealth_search_process(crawler)
            else:
                print("❌ Stealth 로그인에 실패했습니다")
                
        else:
            print("⚠️ 로그인 상태가 불명확합니다")
            print("🔑 안전을 위해 Stealth 로그인을 시도합니다...")
            
            login_success = await perform_stealth_login_process(crawler)
            if login_success:
                await crawler.save_stealth_session()
                print("✅ Stealth 로그인 및 세션 저장 완료!")
                
                # 검색 기능 실행
                await perform_stealth_search_process(crawler)
        
        # 최종 대기
        print("\n⏳ 15초 대기 중... (결과 확인 시간)")
        await asyncio.sleep(15)
        
        print("\n🎉 Stealth 크롤러 실행 완료!")
        print("📋 생성된 파일들을 확인해보세요:")
        print("   - thevc_stealth_browser_state.json (브라우저 상태)")
        print("   - thevc_stealth_cookies.json (쿠키 정보)")
        print("   - 각종 스크린샷 파일들")
        print("   - thevc_stealth_crawler.log (로그 파일)")
        
        return True
        
    except Exception as e:
        print(f"❌ Stealth 크롤러 실행 중 오류: {e}")
        return False
    
    finally:
        # 브라우저 안전 종료
        print("\n🔚 Stealth 브라우저 종료 중...")
        try:
            await crawler.close()
            print("✅ Stealth 브라우저 종료 완료")
        except Exception as e:
            print(f"⚠️ 브라우저 종료 중 오류 (정상적인 경우가 많음): {e}")
        
        # 정리 완료 메시지
        print("🏁 모든 Stealth 작업 완료")

async def perform_stealth_login_process(crawler):
    """
    Stealth 모드 로그인 과정 수행
    """
    try:
        print("\n🔑 Stealth 로그인 과정 시작...")
        print("=" * 40)
        
        if await crawler.click_login_button():
            print("✅ 로그인 버튼 클릭 성공")
            
            # 로그인 창 대기
            print("⏳ 로그인 창 대기 중...")
            if await crawler.wait_for_login_modal():
                print("✅ 로그인 창 확인 완료")
                
                # 로그인 창 스크린샷 저장
                print("📸 Stealth 로그인 창 스크린샷 저장 중...")
                await crawler.take_screenshot("thevc_stealth_login_modal.png")
                print("✅ 로그인 창 스크린샷 저장 완료")
                
                # 실제 로그인 수행
                print("\n🔐 Stealth 자동 로그인 수행 중...")
                print("=" * 30)
                print("📧 이메일: jgpark@jch.kr")
                print("🔑 비밀번호: jch2025")
                
                if await crawler.perform_login():
                    print("✅ Stealth 로그인 폼 작성 완료")
                    
                    # 로그인 성공 여부 확인
                    print("🔍 Stealth 로그인 결과 확인 중...")
                    await asyncio.sleep(3)  # 로그인 처리 대기
                    
                    login_success = await crawler.check_if_logged_in()
                    
                    if login_success is True:
                        print("🎉 Stealth 로그인 성공! 🎉")
                        return True
                    elif login_success is False:
                        print("❌ Stealth 로그인 실패 - 자격 증명을 확인해주세요")
                        return False
                    else:
                        print("⚠️ Stealth 로그인 상태가 불명확합니다")
                        await crawler.take_screenshot("thevc_stealth_login_uncertain.png")
                        return None
                else:
                    print("❌ Stealth 로그인 폼 작성에 실패했습니다")
                    return False
            else:
                print("❌ 로그인 창을 찾을 수 없습니다")
                return False
        else:
            print("❌ 로그인 버튼 클릭에 실패했습니다")
            return False
            
    except Exception as e:
        print(f"❌ Stealth 로그인 과정 중 오류: {e}")
        return False

async def perform_stealth_search_process(crawler):
    """
    Stealth 모드 스타트업 검색 과정 수행
    """
    try:
        print("\n" + "="*50)
        print("🔍 TheVC Stealth 스타트업 검색 시작")
        print("="*50)
        
        # 사용자로부터 검색어 입력받기
        search_keyword = crawler.get_search_keyword_from_user()
        
        if not search_keyword:
            print("❌ 검색어가 입력되지 않았습니다. 검색을 건너뜁니다.")
            return False
        
        print(f"\n🔍 Stealth 모드로 '{search_keyword}' 검색을 시작합니다...")
        print("=" * 40)
        
        # 검색 수행
        search_result = await crawler.search_startup(search_keyword)
        
        if search_result is True:
            print(f"\n🎉 '{search_keyword}' Stealth 검색 및 상세 페이지 진입 완료!")
            print("✅ 검색 결과에서 첫 번째 회사를 클릭했습니다")
            print(f"📸 검색 결과 스크린샷: thevc_search_results_{search_keyword.replace(' ', '_')}.png")
            print(f"📸 회사 상세 스크린샷: thevc_company_detail_{search_keyword.replace(' ', '_')}.png")
            
            # 상세 페이지 확인 시간
            print("\n⏳ 회사 상세 페이지 확인 시간 (15초)...")
            await asyncio.sleep(15)
            
        elif search_result is False:
            print(f"\n❌ '{search_keyword}' Stealth 검색 중 오류가 발생했습니다")
            print("🔧 검색창을 찾을 수 없거나 기술적 문제가 있을 수 있습니다")
            
        else:  # None
            print(f"\n⚠️ '{search_keyword}' Stealth 검색은 완료되었지만 결과 확인이 어렵습니다")
            print("📸 현재 페이지 상태를 스크린샷으로 저장했습니다")
            print(f"🔍 스크린샷 파일: thevc_search_status_{search_keyword.replace(' ', '_')}.png")
        
        return search_result
        
    except Exception as e:
        print(f"❌ Stealth 검색 과정 중 오류: {e}")
        return False

async def test_stealth_mode():
    """
    Stealth 모드 기본 테스트 함수 (간단한 접속 테스트)
    """
    if not STEALTH_AVAILABLE:
        print("❌ playwright-stealth 라이브러리를 먼저 설치하세요:")
        print("pip install playwright-stealth")
        return
    
    crawler = TheVCStealthCrawler()
    
    try:
        print("🥷 Stealth 모드 기본 테스트 시작...")
        print("=" * 50)
        
        # 초기화
        if not await crawler.initialize(headless=False):
            print("❌ Stealth 초기화 실패")
            return
        
        # 사이트 접속
        if not await crawler.navigate_to_thevc():
            print("❌ Stealth 사이트 접속 실패")
            return
        
        # Stealth 효과 검증
        stealth_success = await crawler.check_stealth_effectiveness()
        if stealth_success:
            print("🎉 Stealth 모드 성공!")
        else:
            print("⚠️ Stealth 모드 효과 제한적")
        
        # 스크린샷 저장
        await crawler.take_screenshot("thevc_stealth_test.png")
        
        # 세션 저장
        await crawler.save_stealth_session()
        
        print("\n✅ Stealth 모드 기본 테스트 완료!")
        print("📋 생성된 파일들:")
        print("  - thevc_stealth_test.png")
        print("  - thevc_stealth_browser_state.json")
        print("  - thevc_stealth_cookies.json")
        print("  - thevc_stealth_crawler.log")
        
        # 결과 확인 시간
        await asyncio.sleep(10)
        
    except Exception as e:
        print(f"❌ Stealth 모드 테스트 중 오류: {e}")
        
    finally:
        await crawler.close()

if __name__ == "__main__":
    # Windows 콘솔 인코딩 문제 해결
    import sys
    if sys.platform.startswith('win'):
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass
    
    print("🥷 TheVC Stealth Crawler - 비상시 백업 버전")
    print("=" * 50)
    print("이 버전은 기존 크롤러가 차단당했을 때 사용하세요.")
    print("")
    
    if not STEALTH_AVAILABLE:
        print("❌ 필수 라이브러리 설치 필요:")
        print("pip install playwright-stealth")
    else:
        import sys
        
        # 명령행 인자 확인
        if len(sys.argv) > 1 and sys.argv[1] == "--test-only":
            print("🧪 기본 테스트 모드로 실행합니다...")
            asyncio.run(test_stealth_mode())
        else:
            print("🚀 완전한 Stealth 크롤러 모드로 실행합니다...")
            print("💡 기본 테스트만 원하시면: python main_stealth.py --test-only")
            print("")
            asyncio.run(run_stealth_crawler()) 