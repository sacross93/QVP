"""
코스닥 IPO 가능성 분석기 v2.0
새로운 JSON 구조 (innoforest 데이터)에 최적화된 버전

개발자: AI Assistant
버전: 2.0
날짜: 2025-01-23
"""

import json
import os
import datetime
import re
from glob import glob
from typing import Dict, Any, List, Optional, Tuple
import argparse
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# =============================================================================
# PHASE 1: 데이터 구조 분석 및 파싱
# =============================================================================

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

def parse_amount_string(amount_str: str) -> float:
    """
    '65.5억원', '-3.3억원' 같은 문자열을 숫자로 변환합니다.
    반환값: 억원 단위 (예: -3.3억원 → -3.3)
    """
    if not amount_str or amount_str == "-":
        return 0.0
    
    text = str(amount_str).strip()
    is_negative = text.startswith('-')

    # 숫자와 단위 추출
    match = re.search(r'([0-9,]+\.?[0-9]*)', text)
    if not match:
        return 0.0
    
    number_str = match.group(1).replace(',', '')
    try:
        number = float(number_str)
    except ValueError:
        return 0.0
    
    # 단위 확인
    if '조원' in text:
        number *= 10000  # 조 → 억 변환
    elif '만원' in text:
        number /= 10000  # 만 → 억 변환
    
    return -number if is_negative else number

def extract_basic_info(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """기본 기업 정보를 추출합니다."""
    basic_info = {
        'company_name': company_data.get('company_name', ''),
        'capital': 0.0,  # 자본금 (억원)
        'employees': 0,
        'total_investment': 0.0,
        'annual_revenue': 0.0,
        'latest_equity': 0.0,  # 최신 자기자본
        'business_years': 0  # 추정 영업년수
    }
    
    if 'main_info' in company_data:
        main_info = company_data['main_info']
        
        # 자본금
        if '자본금' in main_info:
            basic_info['capital'] = parse_amount_string(main_info['자본금'])
        
        # 직원수
        if '고용인원' in main_info:
            emp_str = main_info['고용인원']
            emp_match = re.search(r'(\d+)', str(emp_str))
            if emp_match:
                basic_info['employees'] = int(emp_match.group(1))
        
        # 누적투자유치금액
        if '누적투자유치금액' in main_info:
            basic_info['total_investment'] = parse_amount_string(main_info['누적투자유치금액'])
        
        # 연매출
        if '연매출' in main_info:
            basic_info['annual_revenue'] = parse_amount_string(main_info['연매출'])
    
    # 최신 자기자본 추출
    if 'financial' in company_data and '자본' in company_data['financial']:
        equity_data = company_data['financial']['자본']
        latest_equity = 0.0
        latest_year = 0
        
        for period, amount in equity_data.items():
            year_match = re.search(r'(\d{4})년', period)
            if year_match:
                year = int(year_match.group(1))
                if year > latest_year:
                    latest_year = year
                    latest_equity = parse_amount_string(amount)
        
        basic_info['latest_equity'] = latest_equity
    
    # 영업년수 추정
    if 'profit_loss' in company_data and '매출액' in company_data['profit_loss']:
        years = []
        for period in company_data['profit_loss']['매출액'].keys():
            year_match = re.search(r'(\d{4})년', period)
            if year_match:
                years.append(int(year_match.group(1)))
        
        if years:
            min_year = min(years)
            max_year = max(years)
            basic_info['business_years'] = max_year - min_year + 1
    
    return basic_info

def extract_financial_data(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """재무 데이터를 추출하고 파싱합니다."""
    financial_data = {
        'profit_loss': {},
        'financial_position': {},
        'latest_year': None,
        'revenue_trend': [],
        'profit_trend': [],
        'growth_rates': {}
    }
    
    # Profit & Loss 데이터 추출
    if 'profit_loss' in company_data:
        pl_data = company_data['profit_loss']
        financial_data['profit_loss'] = pl_data
        
        # 연도별 매출 추이 계산
        if '매출액' in pl_data:
            revenue_by_year = {}
            for period, amount in pl_data['매출액'].items():
                year = re.search(r'(\d{4})년', period)
                if year:
                    year_int = int(year.group(1))
                    revenue_by_year[year_int] = parse_amount_string(amount)
            
            financial_data['revenue_trend'] = sorted(revenue_by_year.items())
            financial_data['latest_year'] = max(revenue_by_year.keys()) if revenue_by_year else None
            
            # 매출 성장률 계산
            if len(revenue_by_year) >= 2:
                years = sorted(revenue_by_year.keys())
                growth_rates = []
                for i in range(1, len(years)):
                    prev_year = years[i-1]
                    curr_year = years[i]
                    prev_revenue = revenue_by_year[prev_year]
                    curr_revenue = revenue_by_year[curr_year]
                    
                    if prev_revenue > 0:
                        growth_rate = ((curr_revenue - prev_revenue) / prev_revenue) * 100
                        growth_rates.append((curr_year, growth_rate))
                
                financial_data['growth_rates']['revenue'] = growth_rates
    
    # 재무상태 데이터 추출
    if 'financial' in company_data:
        financial_data['financial_position'] = company_data['financial']
    
    return financial_data

def extract_investment_data(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """투자 관련 데이터를 추출합니다."""
    investment_data = {
        'total_investment': 0.0,
        'investment_count': 0,
        'latest_investment': None,
        'patents': 0,
        'patent_grade': 0.0,
        'technology_grade': 0.0
    }
    
    if 'investment' in company_data:
        inv_data = company_data['investment']
        
        # 투자 상세 정보
        if 'details' in inv_data and inv_data['details']:
            investment_data['investment_count'] = len(inv_data['details'])
            # 최신 투자 정보
            latest_inv = max(inv_data['details'], key=lambda x: x.get('날짜', ''))
            investment_data['latest_investment'] = latest_inv
            
            # 총 투자금액 계산
            total_inv = 0.0
            for inv in inv_data['details']:
                amount = parse_amount_string(inv.get('투자유치금액', '0'))
                total_inv += amount
            investment_data['total_investment'] = total_inv
        
        # 특허 정보
        if 'summary' in inv_data:
            summary = inv_data['summary']
            for key, value in summary.items():
                if '특허' in key and '수' in key:
                    investment_data['patents'] = int(value) if value.isdigit() else 0
                elif '특허' in key and '등급' in key:
                    try:
                        investment_data['patent_grade'] = float(value)
                    except:
                        investment_data['patent_grade'] = 0.0
    
    # 메인 정보에서 기술등급 추출
    if 'main_info' in company_data:
        main_info = company_data['main_info']
        if '기술등급' in main_info:
            try:
                investment_data['technology_grade'] = float(main_info['기술등급'])
            except:
                investment_data['technology_grade'] = 0.0
    
    return investment_data

# =============================================================================
# PHASE 2: 코스닥 상장 요건 체크 로직
# =============================================================================

def check_basic_requirements(basic_info: Dict[str, Any]) -> Dict[str, Any]:
    """기본 요건 충족도를 체크합니다."""
    results = {
        'capital_requirement': False,
        'equity_requirement': False,  
        'business_period_requirement': False,
        'scores': {
            'capital': 0,
            'equity': 0,
            'business_period': 0
        },
        'details': {}
    }
    
    # 자본금 요건 (3억원 이상)
    capital = basic_info['capital']
    if capital >= 3.0:
        results['capital_requirement'] = True
        results['scores']['capital'] = 5
    results['details']['capital'] = f"자본금: {capital:.1f}억원 (기준: 3억원 이상)"
    
    # 자기자본 요건 (10억원 이상)
    equity = basic_info['latest_equity']
    if equity >= 10.0:
        results['equity_requirement'] = True
        results['scores']['equity'] = 10
    elif equity >= 5.0:
        results['scores']['equity'] = 5
    elif equity >= 3.0:
        results['scores']['equity'] = 3
    results['details']['equity'] = f"자기자본: {equity:.1f}억원 (기준: 10억원 이상)"
    
    # 영업활동 기간 요건 (3년 이상)
    business_years = basic_info['business_years']
    if business_years >= 3:
        results['business_period_requirement'] = True
        results['scores']['business_period'] = 5
    elif business_years >= 2:
        results['scores']['business_period'] = 3
    results['details']['business_period'] = f"영업활동기간: {business_years}년 (기준: 3년 이상)"
    
    return results

def check_financial_requirements(financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """재무 성과 요건을 체크합니다."""
    results = {
        'revenue_scale': 0,
        'profitability': 0,
        'financial_stability': 0,
        'scores': {
            'revenue': 0,
            'profit': 0,
            'stability': 0
        },
        'details': {}
    }
    
    # 최신년도 매출액 평가
    if financial_data['revenue_trend']:
        latest_revenue = financial_data['revenue_trend'][-1][1]  # (year, revenue)
        
        if latest_revenue >= 100:
            results['scores']['revenue'] = 10
        elif latest_revenue >= 50:
            results['scores']['revenue'] = 7
        elif latest_revenue >= 30:
            results['scores']['revenue'] = 5
        elif latest_revenue >= 10:
            results['scores']['revenue'] = 3
        
        results['details']['revenue'] = f"연매출: {latest_revenue:.1f}억원"
    
    # 수익성 평가 (최신년도 영업이익, 순이익)
    if 'profit_loss' in financial_data:
        pl_data = financial_data['profit_loss']
        
        # 최신년도 영업이익 확인
        operating_profit = 0.0
        net_profit = 0.0
        
        if '영업이익' in pl_data:
            latest_op_profit = None
            latest_year = 0
            for period, amount in pl_data['영업이익'].items():
                year_match = re.search(r'(\d{4})년', period)
                if year_match and int(year_match.group(1)) > latest_year:
                    latest_year = int(year_match.group(1))
                    latest_op_profit = amount
            
            if latest_op_profit:
                operating_profit = parse_amount_string(latest_op_profit)
        
        if '순이익' in pl_data:
            latest_net_profit = None
            latest_year = 0
            for period, amount in pl_data['순이익'].items():
                year_match = re.search(r'(\d{4})년', period)
                if year_match and int(year_match.group(1)) > latest_year:
                    latest_year = int(year_match.group(1))
                    latest_net_profit = amount
            
            if latest_net_profit:
                net_profit = parse_amount_string(latest_net_profit)
        
        # 수익성 점수 계산
        if operating_profit > 0 and net_profit > 0:
            results['scores']['profit'] = 15  # 완전 흑자
        elif operating_profit > 0 or net_profit > -5:  # 손익분기점 근접
            results['scores']['profit'] = 8
        
        results['details']['profit'] = f"영업이익: {operating_profit:.1f}억원, 순이익: {net_profit:.1f}억원"
    
    return results

def check_growth_requirements(financial_data: Dict[str, Any], basic_info: Dict[str, Any]) -> Dict[str, Any]:
    """성장성 요건을 체크합니다."""
    results = {
        'revenue_growth': 0,
        'investment_attraction': 0,
        'scores': {
            'growth': 0,
            'investment': 0
        },
        'details': {}
    }
    
    # 매출 성장률 평가
    if 'growth_rates' in financial_data and 'revenue' in financial_data['growth_rates']:
        growth_rates = financial_data['growth_rates']['revenue']
        
        if growth_rates:
            # 최근 2년 평균 성장률 계산
            recent_rates = [rate for year, rate in growth_rates[-2:]]
            avg_growth = sum(recent_rates) / len(recent_rates) if recent_rates else 0
            
            if avg_growth >= 20:
                results['scores']['growth'] = 15
            elif avg_growth >= 10:
                results['scores']['growth'] = 10
            elif avg_growth >= 0:
                results['scores']['growth'] = 5
            
            results['details']['growth'] = f"평균 매출성장률: {avg_growth:.1f}%"
    
    # 투자유치 점수
    total_investment = basic_info['total_investment']
    if total_investment >= 15.0:
        results['scores']['investment'] = 5
    elif total_investment >= 10.0:
        results['scores']['investment'] = 3
    elif total_investment >= 5.0:
        results['scores']['investment'] = 1
    
    results['details']['investment'] = f"누적투자유치: {total_investment:.1f}억원"

    return results

def check_technology_requirements(investment_data: Dict[str, Any]) -> Dict[str, Any]:
    """기술/혁신성 요건을 체크합니다."""
    results = {
        'technology_grade': 0,
        'patent_score': 0,
        'scores': {
            'tech_grade': 0,
            'patents': 0
        },
        'details': {}
    }
    
    # 기술등급 평가
    tech_grade = investment_data['technology_grade']
    if tech_grade >= 4.5:
        results['scores']['tech_grade'] = 10
    elif tech_grade >= 4.0:
        results['scores']['tech_grade'] = 7
    elif tech_grade >= 3.5:
        results['scores']['tech_grade'] = 5
    
    results['details']['tech_grade'] = f"기술등급: {tech_grade}"
    
    # 특허 평가
    patents = investment_data['patents']
    patent_grade = investment_data['patent_grade']
    
    patent_score = 0
    if patents >= 10 and patent_grade >= 4.0:
        patent_score = 5
    elif patents >= 5 and patent_grade >= 3.5:
        patent_score = 3
    elif patents >= 1:
        patent_score = 1
    
    results['scores']['patents'] = patent_score
    results['details']['patents'] = f"특허 {patents}건 (평균등급: {patent_grade})"
    
    return results

# =============================================================================
# PHASE 3: 점수 산정 시스템
# =============================================================================

def calculate_quantitative_score(basic_info: Dict[str, Any], 
                                financial_data: Dict[str, Any],
                                investment_data: Dict[str, Any]) -> Dict[str, Any]:
    """정량적 분석을 통한 점수를 계산합니다."""
    
    # 각 요건별 체크
    basic_check = check_basic_requirements(basic_info)
    financial_check = check_financial_requirements(financial_data)
    growth_check = check_growth_requirements(financial_data, basic_info)
    tech_check = check_technology_requirements(investment_data)
    
    # 점수 집계
    scores = {
        'basic': {
            'capital': basic_check['scores']['capital'],
            'equity': basic_check['scores']['equity'], 
            'business_period': basic_check['scores']['business_period'],
            'subtotal': sum(basic_check['scores'].values())
        },
        'financial': {
            'revenue': financial_check['scores']['revenue'],
            'profit': financial_check['scores']['profit'],
            'stability': financial_check['scores']['stability'],
            'subtotal': sum(financial_check['scores'].values())
        },
        'growth': {
            'growth_rate': growth_check['scores']['growth'],
            'investment': growth_check['scores']['investment'],
            'subtotal': sum(growth_check['scores'].values())
        },
        'technology': {
            'tech_grade': tech_check['scores']['tech_grade'],
            'patents': tech_check['scores']['patents'],
            'subtotal': sum(tech_check['scores'].values())
        }
    }
    
    # 총점 계산
    total_quantitative = (scores['basic']['subtotal'] + 
                         scores['financial']['subtotal'] + 
                         scores['growth']['subtotal'] + 
                         scores['technology']['subtotal'])
    
    # 상세 정보 수집
    details = {
        'basic': basic_check['details'],
        'financial': financial_check['details'],
        'growth': growth_check['details'],
        'technology': tech_check['details']
    }
    
    return {
        'scores': scores,
        'total_quantitative': total_quantitative,
        'details': details,
        'max_possible': 85  # 정량적 분석 최대점수
    }

def get_grade_from_score(score: float) -> str:
    """점수에 따른 등급을 반환합니다."""
    if score >= 90:
        return "A (상장 가능성 매우 높음)"
    elif score >= 80:
        return "B (상장 가능성 높음)"
    elif score >= 70:
        return "C (상장 가능성 보통)" 
    elif score >= 60:
        return "D (상장 가능성 낮음)"
    else:
        return "F (상장 가능성 매우 낮음)"

# =============================================================================
# PHASE 4: LLM 분석 시스템
# =============================================================================

def setup_llm():
    """LLM을 초기화합니다."""
    print("🤖 LLM을 로드합니다...")
    return ChatOllama(
        model="qwen3:32b",
        base_url="http://192.168.110.102:11434",
        temperature=0
    )

def create_analysis_prompt():
    """LLM 분석을 위한 프롬프트를 생성합니다."""
    template = """당신은 코스닥 상장 전문 애널리스트입니다.

## 기업 정보
{company_summary}

## 정량적 분석 결과  
{quantitative_analysis}

## 최근 뉴스 동향
{news_summary}

## 코스닥 상장 기준 요약
**기본 요건**: 자본금 3억원 이상, 자기자본 10억원 이상, 영업활동 3년 이상
**재무 성과**: 흑자 기업 우대, 매출 규모 및 성장성 평가
**주식 분산**: 소액주주 500명 이상, 지분율 25% 이상 
**기술 특례**: 기술평가 A등급 또는 BBB 이상 2곳

위의 정보를 종합하여 다음을 분석해주세요:

### 📊 정성적 분석 (15점 만점)
1. **시장 전망** (7점): 업종 전망, 사업 확장성, 경쟁 환경
2. **경영 안정성** (5점): 최근 뉴스, 파트너십, 조직 변화  
3. **차별화 요소** (3점): 기술력, 특허, 경쟁 우위

### 🎯 종합 평가
- **예상 총점**: 정량점수 + 정성점수 (100점 만점)
- **상장 가능성 등급**: A~F 등급
- **예상 상장 시기**: 구체적인 타임라인
- **핵심 개선 과제**: 3가지 우선순위별 개선사항
- **리스크 요인**: 상장 준비 과정의 주요 위험요소

**답변 형식을 정확히 지켜주세요:**

### 📊 정성적 분석 (15점 만점)
**시장 전망: X/7점**
- 구체적 근거

**경영 안정성: X/5점**  
- 구체적 근거

**차별화 요소: X/3점**
- 구체적 근거

**정성적 점수 소계: X/15점**

### 🎯 종합 평가
**최종 총점: X/100점** (정량 X점 + 정성 X점)
**상장 가능성 등급: X등급**
**예상 상장 시기: X개월~X년 후**

**핵심 개선 과제:**
1. [가장 중요] 구체적 개선사항
2. [두 번째] 구체적 개선사항  
3. [세 번째] 구체적 개선사항

**주요 리스크 요인:**
- 리스크 1
- 리스크 2
- 리스크 3"""

    return PromptTemplate.from_template(template)

def prepare_company_summary(company_data: Dict[str, Any], basic_info: Dict[str, Any]) -> str:
    """기업 요약 정보를 생성합니다."""
    summary = f"""
**기업명**: {basic_info['company_name']}
**자본금**: {basic_info['capital']:.1f}억원
**직원 수**: {basic_info['employees']}명  
**연매출**: {basic_info['annual_revenue']:.1f}억원
**자기자본**: {basic_info['latest_equity']:.1f}억원
**누적투자**: {basic_info['total_investment']:.1f}억원
**영업기간**: {basic_info['business_years']}년
"""
    return summary.strip()

def prepare_news_summary(company_data: Dict[str, Any], max_news: int = 5) -> str:
    """뉴스 요약을 생성합니다."""
    if 'news' not in company_data or not company_data['news']:
        return "최근 뉴스 정보가 없습니다."
    
    news_list = company_data['news'][:max_news]
    summary = ""
    
    for i, news in enumerate(news_list, 1):
        summary += f"{i}. **{news.get('title', '제목없음')}** ({news.get('date', '날짜없음')})\n"
        if 'crawled_content' in news and news['crawled_content']:
            content = news['crawled_content'][:200] + "..."
            summary += f"   {content}\n\n"
        else:
            summary += f"   Link: {news.get('link', '')}\n\n"
    
    return summary.strip()

def analyze_with_llm(company_data: Dict[str, Any], 
                    basic_info: Dict[str, Any],
                    quantitative_result: Dict[str, Any],
                    llm) -> str:
    """LLM을 통한 정성적 분석을 수행합니다."""
    
    # 프롬프트 데이터 준비
    company_summary = prepare_company_summary(company_data, basic_info)
    news_summary = prepare_news_summary(company_data)
    
    # 정량적 분석 결과 포맷팅
    quant_summary = f"""
**정량적 분석 점수: {quantitative_result['total_quantitative']}/{quantitative_result['max_possible']}점**

**기본 요건 ({quantitative_result['scores']['basic']['subtotal']}/20점)**:
- 자본금: {quantitative_result['scores']['basic']['capital']}/5점
- 자기자본: {quantitative_result['scores']['basic']['equity']}/10점  
- 영업기간: {quantitative_result['scores']['basic']['business_period']}/5점

**재무 성과 ({quantitative_result['scores']['financial']['subtotal']}/30점)**:
- 매출 규모: {quantitative_result['scores']['financial']['revenue']}/10점
- 수익성: {quantitative_result['scores']['financial']['profit']}/15점
- 재무 안정성: {quantitative_result['scores']['financial']['stability']}/5점

**성장성 ({quantitative_result['scores']['growth']['subtotal']}/20점)**:
- 성장률: {quantitative_result['scores']['growth']['growth_rate']}/15점
- 투자유치: {quantitative_result['scores']['growth']['investment']}/5점

**기술/혁신 ({quantitative_result['scores']['technology']['subtotal']}/15점)**:
- 기술등급: {quantitative_result['scores']['technology']['tech_grade']}/10점
- 특허: {quantitative_result['scores']['technology']['patents']}/5점
"""
    
    # 프롬프트 생성 및 실행
    prompt = create_analysis_prompt()
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = chain.invoke({
            "company_summary": company_summary,
            "quantitative_analysis": quant_summary,
            "news_summary": news_summary
        })
        cleaned_result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
        return cleaned_result
    except Exception as e:
        print(f"❌ LLM 분석 중 오류: {e}")
        return f"LLM 분석 중 오류가 발생했습니다: {str(e)}"

# =============================================================================
# PHASE 5: 결과 출력 및 저장
# =============================================================================

def format_analysis_result(company_data: Dict[str, Any],
                          basic_info: Dict[str, Any], 
                          quantitative_result: Dict[str, Any],
                          llm_result: str) -> str:
    """분석 결과를 포맷팅합니다."""
    
    # 1. LLM 결과 파싱
    qualitative_score = 0
    match = re.search(r'정성적 점수 소계:\s*(\d+\.?\d*)/15점', llm_result)
    if match:
        qualitative_score = float(match.group(1))

    qualitative_analysis_text = llm_result
    final_summary_text = ""

    # 정성 분석과 종합 평가 분리
    if '### 🎯 종합 평가' in llm_result:
        parts = llm_result.split('### 🎯 종합 평가', 1)
        qualitative_analysis_text = parts[0]
        final_summary_text = "### 🎯 종합 평가" + parts[1]

    # 2. 정확한 최종 점수 및 등급 계산
    total_quantitative_score = quantitative_result['total_quantitative']
    final_total_score = total_quantitative_score + qualitative_score
    final_grade = get_grade_from_score(final_total_score)

    # 3. LLM의 요약 내용 추출
    timeline = "분석 필요"
    tasks = "분석 필요"
    risks = "분석 필요"
    
    timeline_match = re.search(r'예상 상장 시기:\s*(.*)', final_summary_text)
    if timeline_match: timeline = timeline_match.group(1).strip()

    tasks_match = re.search(r'핵심 개선 과제:\s*(.*?)(\n\*\*주요 리스크 요인:|$)', final_summary_text, re.DOTALL)
    if tasks_match: tasks = tasks_match.group(1).strip()

    risks_match = re.search(r'주요 리스크 요인:\s*(.*)', final_summary_text, re.DOTALL)
    if risks_match: risks = risks_match.group(1).strip()
    
    # 4. 수정된 종합 평가 블록 생성
    corrected_summary_block = f"""{qualitative_analysis_text.strip()}

### 🎯 종합 평가
**최종 총점: {final_total_score:.0f}/100점** (정량 {total_quantitative_score}점 + 정성 {qualitative_score:.0f}점)
**상장 가능성 등급: {final_grade}**
**예상 상장 시기:** {timeline}

**핵심 개선 과제:**
{tasks}

**주요 리스크 요인:**
{risks}
"""

    result = f"""
# {basic_info['company_name']} 코스닥 상장 가능성 분석 보고서

**분석 일시**: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}
**데이터 기준**: {company_data.get('extracted_at', 'N/A')}

## 📋 기업 개요
- **기업명**: {basic_info['company_name']}
- **자본금**: {basic_info['capital']:.1f}억원
- **직원 수**: {basic_info['employees']}명
- **연매출**: {basic_info['annual_revenue']:.1f}억원  
- **자기자본**: {basic_info['latest_equity']:.1f}억원
- **누적투자**: {basic_info['total_investment']:.1f}억원
- **영업기간**: {basic_info['business_years']}년 (추정)

## 📊 정량적 분석 결과 ({quantitative_result['total_quantitative']}/{quantitative_result['max_possible']}점)

### 1. 기본 요건 ({quantitative_result['scores']['basic']['subtotal']}/20점)
- **자본금**: {quantitative_result['scores']['basic']['capital']}/5점 - {quantitative_result['details']['basic'].get('capital', '')}
- **자기자본**: {quantitative_result['scores']['basic']['equity']}/10점 - {quantitative_result['details']['basic'].get('equity', '')}
- **영업기간**: {quantitative_result['scores']['basic']['business_period']}/5점 - {quantitative_result['details']['basic'].get('business_period', '')}

### 2. 재무 성과 ({quantitative_result['scores']['financial']['subtotal']}/30점)  
- **매출 규모**: {quantitative_result['scores']['financial']['revenue']}/10점 - {quantitative_result['details']['financial'].get('revenue', '')}
- **수익성**: {quantitative_result['scores']['financial']['profit']}/15점 - {quantitative_result['details']['financial'].get('profit', '')}
- **재무 안정성**: {quantitative_result['scores']['financial']['stability']}/5점 - {quantitative_result['details']['financial'].get('stability', '')}

### 3. 성장성 ({quantitative_result['scores']['growth']['subtotal']}/20점)
- **성장률**: {quantitative_result['scores']['growth']['growth_rate']}/15점 - {quantitative_result['details']['growth'].get('growth', '')}
- **투자유치**: {quantitative_result['scores']['growth']['investment']}/5점 - {quantitative_result['details']['growth'].get('investment', '')}

### 4. 기술/혁신성 ({quantitative_result['scores']['technology']['subtotal']}/15점)
- **기술등급**: {quantitative_result['scores']['technology']['tech_grade']}/10점 - {quantitative_result['details']['technology'].get('tech_grade', '')}
- **특허**: {quantitative_result['scores']['technology']['patents']}/5점 - {quantitative_result['details']['technology'].get('patents', '')}

## 🤖 LLM 정성적 분석

{corrected_summary_block}

---
*본 분석은 공개된 정보를 바탕으로 한 참고용 분석입니다. 실제 상장 가능성은 다양한 요인에 의해 달라질 수 있습니다.*
"""
    
    return result

def save_analysis_result(analysis_result: str, company_name: str, output_dir: str = "analysis_results") -> str:
    """분석 결과를 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 파일명 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company_name = re.sub(r'[^\w\-_\.]', '_', company_name)
    filename = f"kosdaq_analysis_{safe_company_name}_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(analysis_result)
        
        print(f"💾 분석 결과 저장: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return ""

# =============================================================================
# 메인 실행 함수
# =============================================================================

def analyze_single_company(json_file_path: str, llm, detailed: bool = False) -> Optional[str]:
    """단일 기업을 분석합니다."""
    print(f"\n{'='*80}")
    print(f"🏢 기업 분석 시작: {os.path.basename(json_file_path)}")
    print(f"{'='*80}")
    
    # 1. 데이터 로드
    company_data = load_company_data(json_file_path)
    if not company_data:
        return None
    
    # 2. 데이터 파싱
    print("📊 데이터 파싱 중...")
    basic_info = extract_basic_info(company_data)
    financial_data = extract_financial_data(company_data)
    investment_data = extract_investment_data(company_data)
    
    # 3. 정량적 분석
    print("🔢 정량적 분석 수행 중...")
    quantitative_result = calculate_quantitative_score(basic_info, financial_data, investment_data)
    
    # 4. LLM 정성적 분석
    print("🤖 LLM 정성적 분석 수행 중...")
    llm_result = analyze_with_llm(company_data, basic_info, quantitative_result, llm)
    
    # 5. 결과 통합 및 포맷팅
    print("📋 결과 정리 중...")
    final_result = format_analysis_result(company_data, basic_info, quantitative_result, llm_result)
    
    # 6. 결과 출력
    print("\n" + "="*80)
    print("📊 분석 결과")
    print("="*80)
    print(final_result)
    print("="*80)
    
    # 7. 파일 저장
    save_analysis_result(final_result, basic_info['company_name'])
    
    return final_result

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='코스닥 상장 가능성 분석기 v2.0')
    parser.add_argument('--file', type=str, help='분석할 JSON 파일 경로')
    parser.add_argument('--directory', type=str, help='일괄 분석할 디렉토리 경로')
    parser.add_argument('--detailed', action='store_true', help='상세 분석 모드')
    
    args = parser.parse_args()
    
    print("🚀 코스닥 IPO 가능성 분석기 v2.0을 시작합니다...")
    
    # LLM 초기화
    llm = setup_llm()
    
    if args.file:
        # 단일 파일 분석
        print(f"📄 단일 파일 분석: {args.file}")
        analyze_single_company(args.file, llm, args.detailed)
        
    elif args.directory:
        # 디렉토리 일괄 분석
        print(f"📁 디렉토리 일괄 분석: {args.directory}")
        json_files = glob(os.path.join(args.directory, "*.json"))
        
        if not json_files:
            print(f"❌ {args.directory}에서 JSON 파일을 찾을 수 없습니다.")
            return
        
        print(f"📊 {len(json_files)}개의 파일을 발견했습니다.")
        
        for json_file in json_files:
            try:
                analyze_single_company(json_file, llm, args.detailed)
            except Exception as e:
                print(f"❌ {json_file} 분석 중 오류: {e}")
                
    else:
        # 기본: 현재 첨부된 파일 분석
        default_file = "analysis_results/innoforest_company_data_t3q_20250702_134030.json"
        if os.path.exists(default_file):
            print(f"📄 기본 파일 분석: {default_file}")
            analyze_single_company(default_file, llm)
        else:
            print("❌ 분석할 파일을 지정해주세요.")
            print("사용법:")
            print("  python kosdaq_ipo_analyzer_v2.py --file <JSON파일경로>")
            print("  python kosdaq_ipo_analyzer_v2.py --directory <디렉토리경로>")

if __name__ == "__main__":
    main() 