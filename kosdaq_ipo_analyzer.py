import json
import os
import datetime
import re
from glob import glob
from typing import Dict, Any, List
import requests
from bs4 import BeautifulSoup
import time
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 코스닥 상장 규정 텍스트 (가독성 개선)
KOSDAQ_LISTING_REQUIREMENTS = """
### 1. 기본 요건

#### 1-1. 법인 형태 및 사업 기간
- **법인 형태**: 주식회사여야 함
- **영업활동 기간**: 3년 이상의 계속사업 영위 (단, 기술특례 시 완화 가능)

#### 1-2. 자본 요건
- **납입자본금**: 3억원 이상
- **자기자본**: 10억원 이상

### 2. 주식 분산 요건 (다음 중 1개 충족)
- **트랙 1 (소액주주 기준)**:
  - 소액주주 수: 500명 이상
  - 소액주주 지분율: 25% 이상
- **트랙 2 (대규모 자기자본 기준)**:
  - 자기자본: 500억원 이상
  - 소액주주 수: 500명 이상

### 3. 경영성과 요건 (다음 트랙 중 1개 선택)

#### 3-1. 수익성·매출액 기준 (다음 중 1개 충족)
- **트랙 1**: 법인세 차감전 계속사업이익 20억원 이상 (벤처기업 10억원) + 시가총액 90억원 이상
- **트랙 2**: 법인세 차감전 계속사업이익 20억원 이상 (벤처기업 10억원) + 자기자본 30억원 이상 (벤처기업 15억원)
- **트랙 3**: 법인세 차감전 계속사업이익 양수 + 시가총액 200억원 이상 + 매출액 100억원 이상 (벤처기업 50억원)
- **트랙 4**: 법인세 차감전 계속사업이익 50억원 이상

#### 3-2. 시장평가·성장성 기준 (다음 중 1개 충족)
- **트랙 1**: 시가총액 500억원 이상 + 매출액 30억원 이상 + 최근 2년 평균 매출증가율 20% 이상
- **트랙 2**: 시가총액 300억원 이상 + 매출액 100억원 이상 (벤처기업 50억원)
- **트랙 3**: 시가총액 500억원 이상 + PBR 200% 이상
- **트랙 4**: 시가총액 1,000억원 이상
- **트랙 5**: 자기자본 250억원 이상

### 4. 기술평가 특례 기준 (다음 중 1개 충족)

#### 4-1. 일반 기술평가 특례
- **기술평가**: 전문평가기관 2곳에서 BBB 이상 + A 이상 등급 획득
- **자기자본**: 10억원 이상
- **시가총액**: 90억원 이상

#### 4-2. 첨단기술 단수평가 특례
- **기술평가**: 1개 기관에서 A 이상 등급
- **시가총액**: 1,000억원 이상
- **벤처투자 유치**: 최근 5년간 100억원 이상

### 5. 기타 필수 요건
- **감사의견**: 최근 사업연도 재무제표에 대해 '적정' 의견 필수
- **경영투명성**: 지배구조 투명성 확보 및 내부통제시스템 구축
- **주식양도 제한**: 주식양도에 제한이 없어야 함

### 6. 코스닥 상장 체크리스트 요약
- **1단계: 기본 요건**
  - 주식회사 형태, 3년 이상 영업활동, 납입자본금 3억원 이상, 자기자본 10억원 이상
- **2단계: 주식 분산**
  - 소액주주 500명 + 지분율 25% 이상, 또는 자기자본 500억원 + 소액주주 500명
- **3단계: 경영성과 (택1)**
  - 수익성/매출액 기준 (4개 트랙 중 택1)
  - 시장평가/성장성 기준 (5개 트랙 중 택1)
  - 기술평가 특례 기준
- **4단계: 기타 요건**
  - 최근 사업연도 적정 감사의견, 경영투명성 확보, 주식양도 제한 없음
"""

# LLM 설정 (IPO_deep_research.py에서 가져옴)
def setup_llm():
    """LLM을 초기화합니다."""
    print("LLM을 로드합니다...")
    return ChatOllama(
        model="qwen3:32b",
        base_url="http://192.168.120.102:11434",
        temperature=0
    )

def load_company_data(json_file_path: str) -> Dict[str, Any]:
    """JSON 파일에서 기업 데이터를 로드합니다."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ {data.get('company_name', 'Unknown')} 기업 데이터 로드 완료")
        return data
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"❌ JSON 파일 형식 오류: {json_file_path}")
        return {}

def extract_analysis_data(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """News를 제외하고 상장 분석에 필요한 데이터만 추출합니다."""
    analysis_data = {
        "company_name": company_data.get("company_name", ""),
        "extraction_date": company_data.get("extraction_date", ""),
        "url": company_data.get("url", ""),
        "basic_info": company_data.get("basic_info", {}),
        "overview": company_data.get("overview", {}),
        "keywords": company_data.get("keywords", []),
        "key_info": company_data.get("key_info", {}),
        "products": company_data.get("products", [])
    }
    
    # News 데이터 개수만 포함 (프롬프트 길이 절약)
    news_count = len(company_data.get("news", []))
    analysis_data["news_count"] = news_count
    
    return analysis_data

def extract_article_content(soup):
    """
    뉴스 기사 본문을 추출하는 강화된 함수
    여러 CSS 셀렉터를 시도하여 다양한 뉴스 사이트 구조에 대응
    """
    # 1단계: 구체적인 본문 셀렉터들 (우선순위 높음)
    high_priority_selectors = [
        # 가장 구체적인 기사 본문 클래스들
        '.article-body', '.news-body', '.post-body', '.content-body',
        '.article-content', '.news-content', '.post-content', 
        '.article-text', '.news-text', '.post-text',
        '.view-content', '.view-body', '.view-text',
        
        # 한국 뉴스 사이트 특화 클래스들 (새로 발견된 패턴들 추가)
        '.article-view-content', '.article-veiw-body', '.grid.body',
        '.article_txt', '.news_txt', '.view_txt', '.cont_txt',
        '.article_view', '.news_view', '.view_area',
        '.detail_txt', '.detail_view', '.detail_content',
        
        # ID 기반 (구체적)
        '#articleViewCon', '#article-view-content-div',
        '#article-content', '#news-content', '#article-body', '#news-body',
    ]
    
    # 2단계: 일반적인 셀렉터들 (우선순위 중간)
    medium_priority_selectors = [
        # 속성 기반 (더 구체적인 것부터)
        'div[class*="article"][class*="content"]',
        'div[class*="news"][class*="content"]', 
        'div[class*="article"][class*="body"]',
        'div[class*="news"][class*="body"]',
        'div[class*="content"]', 'div[class*="article"]', 'div[class*="news"]',
        'div[class*="text"]', 'div[class*="body"]', 'div[class*="view"]',
        'section[class*="content"]', 'section[class*="article"]',
        
        # 일반 클래스
        '.content', '.body', '.text',
    ]
    
    # 3단계: 광범위한 셀렉터들 (우선순위 낮음)
    low_priority_selectors = [
        # 시멘틱 태그 (가장 마지막에 시도)
        'main',
        'article',
        
        # 데이터 속성
        '[data-article-body]', '[data-content]', '[data-news-content]'
    ]
    
    all_selectors = high_priority_selectors + medium_priority_selectors + low_priority_selectors
    
    print("    🔍 본문 추출 시도 중...")
    
    for i, selector in enumerate(all_selectors):
        try:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    # 텍스트 추출 및 품질 검증
                    text_content = extract_text_from_element(element)
                    
                    # 텍스트 품질 검증 강화
                    if is_valid_article_content(text_content):
                        print(f"    ✅ 셀렉터 '{selector}'로 본문 추출 성공 (길이: {len(text_content)}자)")
                        return text_content
                        
        except Exception as e:
            print(f"    ⚠️  셀렉터 '{selector}' 처리 중 오류: {e}")
            continue
    
    print("    🔄 기본 셀렉터로 추출 실패, 폴백 방법 시도...")
    
    # 폴백: body 전체에서 p 태그들 수집 (기존 로직)
    if soup.body:
        paragraphs = soup.body.find_all(['p', 'div'], string=True)
        all_text = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 20 and not is_navigation_text(text):
                all_text.append(text)
        
        combined_text = '\n'.join(all_text)
        if len(combined_text.strip()) > 100:
            print(f"    ✅ 폴백 방법으로 본문 추출 성공 (길이: {len(combined_text)}자)")
            return combined_text
    
    print("    ❌ 모든 추출 방법 실패")
    return "본문 내용을 찾을 수 없습니다."

def is_valid_article_content(text):
    """추출된 텍스트가 실제 기사 본문인지 검증합니다."""
    if len(text.strip()) < 100:
        print(f"    ❌ 텍스트 길이 부족: {len(text.strip())}자")
        return False
    
    # 공유/네비게이션 텍스트 비율 검사 (더 관대하게)
    nav_ratio = calculate_navigation_ratio(text)
    print(f"    📊 네비게이션 비율: {nav_ratio:.2%}")
    if nav_ratio > 0.7:  # 70% 이상일 때만 제외 (기존 50%에서 완화)
        print(f"    ❌ 네비게이션 텍스트 비율이 너무 높음: {nav_ratio:.2%}")
        return False
    
    # 실제 기사 내용의 특징들 확인 (더 관대하게)
    article_indicators = [
        '기자', '뉴스', '보도', '발표', 'according to', '에 따르면', '밝혔다', '말했다',
        '회사', '기업', '업계', '시장', '정부', '발표했다', '전했다', '설명했다',
        '서울', '부산', '대구', '인천',  # 지역명 추가
        '올해', '작년', '내년', '최근',  # 시간 표현 추가
        '억원', '조원', '만원', '%',     # 숫자/비율 표현 추가
    ]
    
    indicator_count = sum(1 for indicator in article_indicators if indicator in text)
    print(f"    📊 기사 지표어 개수: {indicator_count}개")
    
    if indicator_count >= 2:  # 기사 지표어가 2개 이상 있으면 유효한 기사로 판단
        print(f"    ✅ 기사 지표어 조건 통과")
        return True
    
    # 문장 구조 검사 (더 관대하게)
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 5]  # 최소 길이 완화
    print(f"    📊 완전한 문장 개수: {len(sentences)}개")
    if len(sentences) >= 3:  # 완전한 문장이 3개 이상 있으면 기사로 판단
        print(f"    ✅ 문장 구조 조건 통과")
        return True
    
    # 한국어 기사 특성 검사 (새로 추가)
    korean_patterns = ['다.', '했다.', '된다.', '있다.', '이다.', '한다.']
    korean_ending_count = sum(1 for pattern in korean_patterns if pattern in text)
    print(f"    📊 한국어 문장 종결 패턴: {korean_ending_count}개")
    if korean_ending_count >= 5:  # 한국어 문장 종결이 5개 이상
        print(f"    ✅ 한국어 문장 패턴 조건 통과")
        return True
    
    # 텍스트 길이가 충분히 길면 기사로 간주 (새로 추가)
    if len(text.strip()) > 500:  # 500자 이상이면 기사로 간주
        print(f"    ✅ 충분한 텍스트 길이 조건 통과: {len(text.strip())}자")
        return True
        
    print(f"    ❌ 모든 유효성 검증 조건 실패")
    print(f"    📄 텍스트 미리보기: {text[:100]}...")
    return False

def calculate_navigation_ratio(text):
    """텍스트에서 네비게이션/공유 요소의 비율을 계산합니다."""
    nav_keywords = [
        '페이스북', '트위터', '카카오톡', 'URL복사', '이메일', '공유', '기사보내기',
        '댓글', '구독', '로그인', '회원가입', '바로가기',
        '본문 글씨', '글씨 키우기', '글씨 줄이기', '기사저장', '스크랩'
        # '홈', '뉴스' 등은 제거 (실제 기사에서도 자주 사용됨)
    ]
    
    nav_text_length = 0
    for keyword in nav_keywords:
        # 키워드가 여러 번 나와도 한 번만 계산 (중복 패널티 방지)
        if keyword in text:
            nav_text_length += len(keyword)
    
    return nav_text_length / len(text) if len(text) > 0 else 0

def extract_text_from_element(element):
    """HTML 요소에서 깔끔한 텍스트를 추출합니다."""
    if not element:
        return ""
    
    # 요소 복사 (원본 수정 방지)
    element_copy = element.__copy__()
    
    # 불필요한 태그들 제거
    unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']
    for tag_name in unwanted_tags:
        for tag in element_copy.find_all(tag_name):
            tag.decompose()
    
    # 공유/소셜 버튼 관련 클래스 제거
    social_classes = ['share', 'social', 'sns', 'facebook', 'twitter', 'kakao', 'url-copy']
    for class_name in social_classes:
        for elem in element_copy.find_all(class_=lambda x: x and any(cls in ' '.join(x).lower() for cls in social_classes)):
            elem.decompose()
    
    # 텍스트 추출
    text_parts = []
    
    # p 태그 우선 추출
    paragraphs = element_copy.find_all('p')
    if paragraphs:
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 15 and not is_navigation_text(text):  # 최소 길이 증가
                text_parts.append(text)
    
    # p 태그가 충분하지 않으면 div 태그도 시도
    if len('\n'.join(text_parts)) < 200:
        divs = element_copy.find_all('div')
        for div in divs:
            text = div.get_text(strip=True)
            if len(text) > 30 and text not in text_parts and not is_navigation_text(text):
                text_parts.append(text)
    
    return '\n'.join(text_parts)

def is_navigation_text(text):
    """네비게이션이나 메뉴 텍스트인지 판단합니다."""
    nav_keywords = [
        '홈', '뉴스', '정치', '경제', '사회', '문화', '스포츠', '연예', '국제',
        '로그인', '회원가입', '구독', '공유', '댓글', '이전', '다음', '목록',
        '카테고리', '태그', '관련기사', '인기기사', '최신기사',
        'Home', 'News', 'Login', 'Subscribe', 'Share', 'Comment',
        '페이스북', '트위터', '카카오톡', 'URL복사', '이메일', '기사보내기',
        '본문 글씨', '글씨 키우기', '글씨 줄이기', '기사저장', '바로가기'
    ]
    
    # 텍스트가 너무 짧으면 네비게이션으로 간주
    if len(text) < 15:
        return True
    
    # 네비게이션 키워드 비율 검사
    keyword_matches = sum(1 for keyword in nav_keywords if keyword in text)
    if keyword_matches >= 3:  # 네비게이션 키워드가 3개 이상이면 네비게이션으로 간주
        return True
    
    # 짧은 텍스트에서 네비게이션 키워드가 있으면 네비게이션으로 간주
    for keyword in nav_keywords:
        if keyword in text and len(text) < 50:
            return True
    
    return False

def crawl_news_articles(news_list: List[Dict[str, Any]], max_articles_to_crawl: int = 3) -> List[Dict[str, Any]]:
    """
    주어진 뉴스 기사 목록에서 URL을 크롤링하여 본문 내용을 가져옵니다.

    Args:
        news_list: 뉴스 기사 딕셔너리 목록. 각 딕셔너리는 'link' 키를 포함해야 합니다.
        max_articles_to_crawl: 크롤링할 최대 기사 수.

    Returns:
        크롤링된 본문('crawled_content')이 추가된 뉴스 기사 딕셔너리 목록.
    """
    crawled_count = 0
    if not news_list:
        return []

    print("\n" + "="*80)
    print("📰 뉴스 데이터 크롤링 시작...")

    for news_item in news_list:
        if crawled_count >= max_articles_to_crawl:
            print(f"\n설정된 최대 기사 수({max_articles_to_crawl}개)까지만 크롤링합니다.")
            break

        if 'link' in news_item and news_item['link']:
            url = news_item['link']
            print(f"\n📰 '{news_item.get('title', '제목 없음')}' 기사 크롤링 시도:")
            print(f"    URL: {url}")
            
            try:
                # 다양한 User-Agent 시도
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                response.encoding = response.apparent_encoding  # 인코딩 자동 감지
                
                print(f"    ✅ HTTP 응답 성공 (상태 코드: {response.status_code})")
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 강화된 본문 추출
                content = extract_article_content(soup)
                
                news_item['crawled_content'] = content
                
                print("    📄 크롤링 결과 미리보기:")
                print("    " + "-" * 50)
                preview = content[:300] + "..." if len(content) > 300 else content
                print("    " + preview.replace('\n', '\n    '))
                print("    " + "-" * 50)

                crawled_count += 1
                time.sleep(2)  # 서버 부하 방지를 위해 대기 시간 증가
                
            except requests.exceptions.RequestException as e:
                print(f"    ❌ HTTP 요청 실패: {e}")
                news_item['crawled_content'] = f"크롤링 실패: {e}"
            except Exception as e:
                print(f"    ❌ 처리 중 오류 발생: {e}")
                news_item['crawled_content'] = f"처리 중 오류 발생: {e}"
        else:
            print(f"🟡 '{news_item.get('title', '제목 없음')}' 기사는 URL 정보가 없어 크롤링을 건너뜁니다.")
            news_item['crawled_content'] = "URL 정보가 없어 크롤링할 수 없습니다."

    print("="*80)
    return news_list

def create_ipo_analysis_prompt():
    """코스닥 상장 가능성 분석을 위한 프롬프트를 생성합니다."""
    template = """당신은 코스닥 상장 전문 애널리스트입니다.

아래 기업 정보를 바탕으로 코스닥 상장 가능성을 분석해주세요.

## 코스닥 상장 기준
{kosdaq_requirements}

## 분석 대상 기업 정보
{company_data}

## 분석 요구사항 및 배점 기준
다음 항목들을 체계적으로 분석하고 **각 항목별 점수**를 명시해주세요:

### 1. 기본 요건 충족도 (25점 만점)
- **영업활동 기간** (5점): 3년 이상 충족 시 5점, 2-3년 3점, 1-2년 1점, 1년 미만 0점
- **납입자본금** (5점): 3억 원 이상 충족 시 5점, 부족 시 0점
- **자기자본** (10점): 10억 원 이상 10점, 5-10억 5점, 3-5억 3점, 3억 미만 0점
- **소액주주 확보 가능성** (5점): 현재 주주 구조 및 확보 가능성 평가

### 2. 경영성과 및 재무 분석 (30점 만점)
- **매출 성장성** (10점): 최근 2년 연속 20% 이상 성장 10점, 10-20% 7점, 0-10% 4점, 마이너스 성장 0점
- **수익성** (10점): 흑자 기업 10점, 손익분기점 근접 5점, 적자 기업 0점
- **재무 안정성** (10점): 부채비율, 유동성 등 종합 평가

### 3. 상장 트랙 적합성 (20점 만점)
- **이익실현 상장요건** (10점): 각 트랙별 요건 충족도 평가
- **이익미실현 상장요건(테슬라 요건)** (10점): 시가총액, 매출 기준 충족도 평가

### 4. 기술성장기업 특례 적용 가능성 (10점 만점)
- **기술 혁신성** (5점): AI, 헬스케어 등 혁신 기술 보유도
- **기술 평가 가능성** (5점): 전문평가기관 A등급 획득 가능성

### 5. 정성적 요소 (10점 만점)
- **시장 성장성** (3점): 반려동물 헬스케어 시장 등 성장 시장 진출
- **경쟁 우위** (3점): 차별화된 기술/서비스 보유
- **경영진 역량** (2점): 대표자 및 경영진의 업계 경험
- **거버넌스** (2점): 투명한 지배구조 및 내부통제

### 6. 정보 충족도 및 준비 상태 (5점 만점)
- **공시 정보 충족도** (3점): 상장에 필요한 정보 공개 수준
- **상장 준비도** (2점): 감사 체계, 내부통제 등 준비 정도

## 답변 형식 (필수)
**반드시 다음 형식으로 답변해주세요:**

### 1. 기본 요건 충족도 (25점 만점)
- 영업활동 기간: X점 (근거)
- 납입자본금: X점 (근거)
- 자기자본: X점 (근거)
- 소액주주 확보: X점 (근거)
**소계: X/25점**

### 2. 경영성과 및 재무 분석 (30점 만점)
- 매출 성장성: X점 (근거)
- 수익성: X점 (근거)
- 재무 안정성: X점 (근거)
**소계: X/30점**

### 3. 상장 트랙 적합성 (20점 만점)
- 이익실현 상장요건: X점 (근거)
- 이익미실현 상장요건: X점 (근거)
**소계: X/20점**

### 4. 기술성장기업 특례 (10점 만점)
- 기술 혁신성: X점 (근거)
- 기술 평가 가능성: X점 (근거)
**소계: X/10점**

### 5. 정성적 요소 (10점 만점)
- 시장 성장성: X점 (근거)
- 경쟁 우위: X점 (근거)
- 경영진 역량: X점 (근거)
- 거버넌스: X점 (근거)
**소계: X/10점**

### 6. 정보 충족도 및 준비 상태 (5점 만점)
- 공시 정보 충족도: X점 (근거)
- 상장 준비도: X점 (근거)
**소계: X/5점**

### 🎯 종합 평가
**총점: X/100점**

**상장 가능성 등급:**
- 90-100점: A등급 (상장 가능성 매우 높음)
- 80-89점: B등급 (상장 가능성 높음)
- 70-79점: C등급 (상장 가능성 보통)
- 60-69점: D등급 (상장 가능성 낮음)
- 60점 미만: F등급 (상장 가능성 매우 낮음)

**예상 상장 타임라인:** X개월~X년 후

**핵심 개선 과제:**
1. 가장 중요한 개선 사항
2. 두 번째 개선 사항
3. 세 번째 개선 사항

점수는 현재 공개된 정보를 바탕으로 객관적이고 보수적으로 평가해주세요."""

    return PromptTemplate.from_template(template)

def analyze_ipo_possibility(company_data: Dict[str, Any], llm) -> str:
    """기업 데이터를 분석하여 코스닥 상장 가능성을 평가합니다."""
    
    # News 제외한 분석 데이터 추출
    analysis_data = extract_analysis_data(company_data)
    
    # 프롬프트 생성
    prompt = create_ipo_analysis_prompt()
    
    # 분석 체인 구성
    analysis_chain = prompt | llm | StrOutputParser()
    
    print(f"🔍 {analysis_data['company_name']} 코스닥 상장 가능성 분석 중...")
    
    try:
        # 분석 실행
        result = analysis_chain.invoke({
            "kosdaq_requirements": KOSDAQ_LISTING_REQUIREMENTS,
            "company_data": json.dumps(analysis_data, ensure_ascii=False, indent=2)
        })
        return result
    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {e}")
        return f"분석 중 오류가 발생했습니다: {str(e)}"

def save_analysis_result(company_name: str, analysis_result: str, output_dir: str = "analysis_results"):
    """분석 결과를 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company_name}_ipo_analysis_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    
    cleaned_result = re.sub(r'<think>.*?</think>', '', analysis_result, flags=re.DOTALL).strip()
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {company_name} 코스닥 상장 가능성 분석 보고서\n")
            f.write(f"분석 일시: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}\n\n")
            f.write(cleaned_result)
        
        print(f"📄 분석 결과 저장: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return None

def process_single_company(json_file_path: str, llm):
    """단일 기업 데이터를 분석합니다."""
    # 기업 데이터 로드
    company_data = load_company_data(json_file_path)
    if not company_data:
        return None
    
    # 상장 가능성 분석
    analysis_result = analyze_ipo_possibility(company_data, llm)
    
    # 결과 출력
    print("\n" + "="*80)
    print(f"📊 {company_data.get('company_name', 'Unknown')} 분석 결과")
    print("="*80)
    print(analysis_result)
    print("="*80 + "\n")
    
    # 결과 저장
    company_name = company_data.get('company_name', 'Unknown')
    save_analysis_result(company_name, analysis_result)
    
    return analysis_result

def process_multiple_companies(data_directory: str, llm):
    """디렉토리 내 모든 기업 데이터를 분석합니다."""
    json_files = glob(os.path.join(data_directory, "*.json"))
    
    if not json_files:
        print(f"❌ {data_directory}에서 JSON 파일을 찾을 수 없습니다.")
        return
    
    print(f"📁 {len(json_files)}개의 기업 데이터 파일을 발견했습니다.")
    
    results = {}
    for json_file in json_files:
        print(f"\n🏢 처리 중: {os.path.basename(json_file)}")
        try:
            result = process_single_company(json_file, llm)
            if result:
                company_data = load_company_data(json_file)
                company_name = company_data.get('company_name', os.path.basename(json_file))
                results[company_name] = result
        except Exception as e:
            print(f"❌ {json_file} 처리 중 오류: {e}")
    
    print(f"\n✅ 총 {len(results)}개 기업 분석 완료")
    return results

def main():
    """메인 실행 함수"""
    print("🚀 코스닥 IPO 가능성 분석기를 시작합니다...")
    
    # LLM 초기화
    llm = setup_llm()
    
    # 사용법 안내
    print("\n📋 사용 방법:")
    print("1. 단일 파일 분석: python kosdaq_ipo_analyzer.py --file <JSON_파일_경로>")
    print("2. 디렉토리 일괄 분석: python kosdaq_ipo_analyzer.py --directory <디렉토리_경로>")
    print("3. 현재 디렉토리 크롤링 데이터 분석: python kosdaq_ipo_analyzer.py --crawling")
    print("4. 뉴스 크롤링만 실행: python kosdaq_ipo_analyzer.py --crawl-news <JSON_파일_경로>")
    
    import sys
    
    if len(sys.argv) < 2:
        # 기본값: 현재 디렉토리의 크롤링 데이터 분석
        print("\n🔍 현재 디렉토리에서 크롤링 데이터를 찾아 분석합니다...")
        crawling_files = glob("crawlling_data/company_data_*.json")
        if crawling_files:
            print(f"📊 {len(crawling_files)}개의 크롤링 데이터 파일을 발견했습니다.")
            for file in crawling_files:
                process_single_company(file, llm)
        else:
            print("❌ 크롤링 데이터 파일을 찾을 수 없습니다.")
            print("예시 파일로 십일리터 데이터를 분석해보세요:")
            print("python kosdaq_ipo_analyzer.py --file crawlling_data/company_data_십일리터_20250630_173418.json")
    
    elif sys.argv[1] == "--file" and len(sys.argv) > 2:
        # 단일 파일 분석
        file_path = sys.argv[2]
        print(f"\n📄 단일 파일 분석: {file_path}")
        process_single_company(file_path, llm)
    
    elif sys.argv[1] == "--directory" and len(sys.argv) > 2:
        # 디렉토리 일괄 분석
        directory_path = sys.argv[2]
        print(f"\n📁 디렉토리 일괄 분석: {directory_path}")
        process_multiple_companies(directory_path, llm)
    
    elif sys.argv[1] == "--crawling":
        # 크롤링 데이터 분석
        print("\n🔍 크롤링 데이터 분석...")
        process_multiple_companies("crawlling_data", llm)
    
    elif sys.argv[1] == "--crawl-news" and len(sys.argv) > 2:
        # 뉴스 크롤링만 실행
        file_path = sys.argv[2]
        print(f"\n📰 뉴스 크롤링만 실행: {file_path}")
        company_data = load_company_data(file_path)
        if company_data and "news" in company_data and company_data["news"]:
            crawled_news = crawl_news_articles(company_data["news"])
            print("\n" + "="*80)
            print(f"📊 {company_data.get('company_name', 'Unknown')} 최종 크롤링 결과")
            print("="*80)
            for i, news_item in enumerate(crawled_news):
                print(f"\n--- {i+1}. {news_item.get('title')} ---")
                print(f"URL: {news_item.get('link')}")
                print(f"Crawled Content:\n{news_item.get('crawled_content', '내용 없음')[:500]}...")
            print("="*80 + "\n")
        else:
            print("❌ 뉴스 데이터가 없거나 파일을 불러오는 데 실패했습니다.")
    
    else:
        print("❌ 잘못된 인수입니다. 사용법을 확인하세요.")

if __name__ == "__main__":
    main() 