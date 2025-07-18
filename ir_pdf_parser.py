#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IR 자료 PDF 파싱 및 요약 시스템
- PyMuPDF를 사용한 텍스트 추출
- 섹션별 분류 및 구조화
- 표/차트 데이터 처리
- 로컬 LLM(ChatOllama)을 사용한 자동 요약
"""

import fitz  # PyMuPDF
import pandas as pd
import json
import re
from typing import Dict, List, Tuple, Any
from pathlib import Path
import logging
from datetime import datetime
import argparse

# 로컬 LLM 연동
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ langchain_ollama가 설치되지 않았습니다. pip install langchain-ollama로 설치하세요.")

# LLM 설정
MODEL_ID = "qwen3:32b"
BASE_URL = "http://192.168.120.102:11434"

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IRPDFParser:
    """IR 자료 PDF 파싱 및 분석 클래스"""
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm and OLLAMA_AVAILABLE
        
        if self.use_llm:
            try:
                self.llm = ChatOllama(model=MODEL_ID, base_url=BASE_URL, temperature=0)
                logger.info(f"로컬 LLM 초기화 완료: {MODEL_ID}")
            except Exception as e:
                logger.warning(f"LLM 초기화 실패: {str(e)}. 프롬프트만 생성합니다.")
                self.use_llm = False
        
        self.section_keywords = {
            'company_overview': [
                '회사개요', '기업개요', '회사소개', 'company overview', 
                '사업영역', '비즈니스모델', '회사연혁', '기업현황'
            ],
            'financial_data': [
                '재무제표', '재무현황', '매출', '영업이익', '순이익', 
                'revenue', 'profit', '손익계산서', '재무상태표', 
                '현금흐름표', '재무지표', 'ebitda', 'roe', 'roa'
            ],
            'market_analysis': [
                '시장분석', '시장현황', '경쟁사', '시장규모', '타겟시장',
                'market size', 'tam', 'sam', '업계동향', '시장전망',
                '경쟁구도', '마켓셰어'
            ],
            'technology': [
                '기술', '핵심기술', '특허', 'r&d', '연구개발',
                '기술력', '차별화', '혁신', '플랫폼', '솔루션',
                '알고리즘', '개발현황'
            ],
            'organization': [
                '조직', '인력', '경영진', '임직원', '조직도', 
                '팀구성', '채용', '인사', '경영팀', 'ceo', 'cto',
                '대표', '대표이사', 'founder', '소장', '부회장',
                '박사', '석사', '학사', '경력', '전문가', '연구원'
            ],
            'business_model': [
                '비즈니스모델', '수익모델', '사업구조', '서비스',
                '제품', '고객', '파트너십', '협력사'
            ],
            'investment': [
                '투자', '자금조달', '투자유치', '밸류에이션',
                '투자계획', '자금계획', '증자', '펀딩'
            ]
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """PDF에서 페이지별 텍스트 추출"""
        logger.info(f"PDF 파일 처리 시작: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            pages_data = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # 기본 텍스트 추출
                raw_text = page.get_text()
                
                # 구조화된 텍스트 정보 추출
                text_dict = page.get_text("dict")
                
                # 이미지 정보
                images = page.get_images()
                
                # 페이지 정보 저장
                page_data = {
                    'page_number': page_num + 1,
                    'raw_text': raw_text,
                    'structured_text': text_dict,
                    'image_count': len(images),
                    'word_count': len(raw_text.split())
                }
                
                pages_data.append(page_data)
                logger.info(f"페이지 {page_num + 1} 처리 완료 - 단어 수: {len(raw_text.split())}")
            
            doc.close()
            
            return {
                'total_pages': len(pages_data),
                'pages': pages_data,
                'extraction_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"PDF 처리 중 오류 발생: {str(e)}")
            raise
    
    def classify_content_by_section(self, pages_data: List[Dict]) -> Dict[str, List[Dict]]:
        """섹션별 컨텐츠 분류"""
        logger.info("섹션별 컨텐츠 분류 시작")
        
        classified_sections = {section: [] for section in self.section_keywords.keys()}
        classified_sections['uncategorized'] = []
        
        for page_data in pages_data:
            page_text = page_data['raw_text'].lower()
            page_classified = False
            
            # 각 섹션별 키워드 매칭
            for section, keywords in self.section_keywords.items():
                keyword_matches = sum(1 for keyword in keywords if keyword in page_text)
                
                # 키워드가 2개 이상 매칭되거나, 강한 키워드가 있으면 해당 섹션으로 분류
                if keyword_matches >= 2 or any(strong_keyword in page_text for strong_keyword in keywords[:3]):
                    classified_sections[section].append({
                        'page_number': page_data['page_number'],
                        'content': page_data['raw_text'],
                        'keyword_matches': keyword_matches,
                        'word_count': page_data['word_count']
                    })
                    page_classified = True
                    logger.info(f"페이지 {page_data['page_number']}: {section} 섹션으로 분류 (키워드 매칭: {keyword_matches})")
                    break
            
            # 분류되지 않은 페이지
            if not page_classified:
                classified_sections['uncategorized'].append({
                    'page_number': page_data['page_number'],
                    'content': page_data['raw_text'],
                    'word_count': page_data['word_count']
                })
        
        # 섹션별 통계
        for section, content in classified_sections.items():
            if content:
                total_words = sum(item['word_count'] for item in content)
                logger.info(f"{section} 섹션: {len(content)}페이지, 총 {total_words}단어")
        
        return classified_sections
    
    def extract_financial_tables(self, pdf_path: str) -> List[pd.DataFrame]:
        """재무제표 및 표 데이터 추출"""
        logger.info("표 데이터 추출 시작")
        
        tables = []
        
        try:
            # camelot을 사용한 표 추출
            import camelot
            camelot_tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            for i, table in enumerate(camelot_tables):
                if len(table.df.columns) > 1 and len(table.df) > 1:  # 유효한 표만
                    tables.append({
                        'table_id': i + 1,
                        'page': table.page,
                        'dataframe': table.df,
                        'accuracy': table.accuracy if hasattr(table, 'accuracy') else 0.0
                    })
                    logger.info(f"표 {i+1} 추출 완료 (페이지 {table.page}): {table.df.shape}")
            
        except ImportError:
            logger.warning("camelot 라이브러리가 없어 표 추출을 건너뜁니다")
        except Exception as e:
            logger.warning(f"표 추출 중 오류: {str(e)}")
        
        return tables
    
    def extract_key_metrics(self, classified_content: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """핵심 지표 추출"""
        logger.info("핵심 지표 추출 시작")
        
        metrics = {
            'financial_metrics': {},
            'business_metrics': {},
            'market_metrics': {},
            'technology_metrics': {}
        }
        
        # 재무 지표 추출
        if 'financial_data' in classified_content:
            financial_text = ' '.join([item['content'] for item in classified_content['financial_data']])
            
            # 숫자 패턴 매칭
            revenue_pattern = r'매출.*?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:억|만|원|백만)'
            profit_pattern = r'(?:영업|순)이익.*?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:억|만|원|백만)'
            
            revenue_matches = re.findall(revenue_pattern, financial_text)
            profit_matches = re.findall(profit_pattern, financial_text)
            
            if revenue_matches:
                metrics['financial_metrics']['revenue'] = revenue_matches
            if profit_matches:
                metrics['financial_metrics']['profit'] = profit_matches
        
        # 시장 지표 추출
        if 'market_analysis' in classified_content:
            market_text = ' '.join([item['content'] for item in classified_content['market_analysis']])
            market_size_pattern = r'시장.*?규모.*?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:억|조|만|원|달러)'
            market_matches = re.findall(market_size_pattern, market_text)
            
            if market_matches:
                metrics['market_metrics']['market_size'] = market_matches
        
        return metrics
    
    def split_pdf_into_smart_chunks(self, pdf_data: Dict[str, Any], max_chunk_size: int = 3000) -> List[Dict[str, Any]]:
        """PDF를 의미 기반 스마트 청크로 분할"""
        logger.info("PDF 스마트 청크 분할 시작")
        
        # 조직/팀 관련 키워드 정의
        org_keywords = ['팀', '조직', '경영진', '멤버', '구성원', 'CEO', 'CTO', 'COO', '대표', '이사', '소장', 
                       '연구원', '개발자', '마케터', 'MD', '학력', '경력', '대학교', '석사', '박사', '전문학사']
        
        # 재무 관련 키워드 정의  
        finance_keywords = ['매출', '투자', '자금', '조달', '억', '원', '수익', '이익', '손실', '재무', '계획', 
                           '기업가치', '투자유치', '라운드', 'Pre-A', 'Series']
        
        # 기술 관련 키워드 정의
        tech_keywords = ['특허', '기술', 'R&D', '연구', '개발', '혁신', 'AI', '소프트웨어', '하드웨어', 
                        '알고리즘', '모델', '시스템', '플랫폼']
        
        chunks = []
        current_chunk = {"type": "general", "pages": [], "text": "", "keywords_found": set()}
        
        for page in pdf_data['pages']:
            page_text = page['raw_text']
            page_lower = page_text.lower()
            
            # 페이지 타입 식별
            org_score = sum(1 for keyword in org_keywords if keyword.lower() in page_lower)
            finance_score = sum(1 for keyword in finance_keywords if keyword.lower() in page_lower)
            tech_score = sum(1 for keyword in tech_keywords if keyword.lower() in page_lower)
            
            # 가장 높은 점수의 타입 결정
            page_type = "general"
            max_score = max(org_score, finance_score, tech_score)
            if max_score >= 3:  # 임계값 설정
                if org_score == max_score:
                    page_type = "organization"
                elif finance_score == max_score:
                    page_type = "finance"
                elif tech_score == max_score:
                    page_type = "technology"
            
            # 현재 청크와 타입이 다르거나 크기 제한 초과시 새 청크 시작
            if (current_chunk["type"] != page_type or 
                len(current_chunk["text"]) + len(page_text) > max_chunk_size):
                
                if current_chunk["text"]:  # 빈 청크가 아니면 저장
                    chunks.append(current_chunk)
                
                current_chunk = {
                    "type": page_type, 
                    "pages": [page['page_number']], 
                    "text": f"=== 페이지 {page['page_number']} ===\n{page_text}",
                    "keywords_found": set()
                }
            else:
                current_chunk["pages"].append(page['page_number'])
                current_chunk["text"] += f"\n=== 페이지 {page['page_number']} ===\n{page_text}"
            
            # 키워드 추가
            if org_score > 0:
                current_chunk["keywords_found"].update([kw for kw in org_keywords if kw.lower() in page_lower])
            if finance_score > 0:
                current_chunk["keywords_found"].update([kw for kw in finance_keywords if kw.lower() in page_lower])
            if tech_score > 0:
                current_chunk["keywords_found"].update([kw for kw in tech_keywords if kw.lower() in page_lower])
        
        # 마지막 청크 추가
        if current_chunk["text"]:
            chunks.append(current_chunk)
        
        logger.info(f"PDF를 {len(chunks)}개 청크로 분할 완료")
        for i, chunk in enumerate(chunks):
            logger.info(f"청크 {i+1}: {chunk['type']} (페이지 {chunk['pages']}, 길이: {len(chunk['text'])})")
        
        return chunks

    def extract_organization_info(self, chunk_text: str) -> str:
        """조직 정보 전용 추출"""
        if not self.use_llm:
            return "LLM을 사용할 수 없어 조직 정보를 추출할 수 없습니다."
        
        org_prompt = f"""
다음 텍스트에서 조직 구성원 정보를 정확히 추출해주세요:

{chunk_text}

다음 형식으로 각 구성원별 정보를 추출하세요:
## 조직 구성원

### [이름]
- **직책**: [직책명]
- **학력**: [학교명, 학위]
- **경력**: [주요 경력사항]
- **기타**: [추가 정보]

제약사항:
1. 문서에 명시된 정보만 추출
2. 없는 정보는 "정보 없음"으로 표기
3. 가상 인물/정보 생성 절대 금지
4. 모든 구성원 정보를 빠짐없이 포함
5. 이름, 직책, 학력, 경력이 있는 모든 인물 추출

/no_think
"""
        
        try:
            response = self.llm.invoke(org_prompt)
            result = response.content if hasattr(response, 'content') else str(response)
            logger.info("조직 정보 추출 완료")
            return result.strip()
        except Exception as e:
            logger.error(f"조직 정보 추출 실패: {str(e)}")
            return f"조직 정보 추출 실패: {str(e)}"

    def extract_finance_info(self, chunk_text: str) -> str:
        """재무 정보 전용 추출"""
        if not self.use_llm:
            return "LLM을 사용할 수 없어 재무 정보를 추출할 수 없습니다."
        
        finance_prompt = f"""
다음 텍스트에서 재무 정보를 정확히 추출해주세요:

{chunk_text}

다음 형식으로 재무 정보를 추출하세요:
## 재무 현황

### 매출 현황
- **연도별 매출**: [구체적 수치와 연도]
- **예상 매출**: [향후 계획]
- **매출 구성**: [매출원별 분석]

### 투자 현황  
- **투자 라운드**: [Pre-A, Series A 등]
- **투자 금액**: [구체적 금액]
- **기업가치**: [valuation 정보]
- **투자금 사용 계획**: [사용 용도]

### 수익성
- **영업이익**: [수치]
- **당기순이익**: [수치]
- **손익 전망**: [향후 계획]

제약사항:
1. 문서에 명시된 숫자만 사용
2. 추정/추론 금지, 팩트만 추출
3. 억/만원 단위 정확히 표기

/no_think
"""
        
        try:
            response = self.llm.invoke(finance_prompt)
            result = response.content if hasattr(response, 'content') else str(response)
            logger.info("재무 정보 추출 완료")
            return result.strip()
        except Exception as e:
            logger.error(f"재무 정보 추출 실패: {str(e)}")
            return f"재무 정보 추출 실패: {str(e)}"

    def extract_technology_info(self, chunk_text: str) -> str:
        """기술 정보 전용 추출"""
        if not self.use_llm:
            return "LLM을 사용할 수 없어 기술 정보를 추출할 수 없습니다."
        
        tech_prompt = f"""
다음 텍스트에서 기술 정보를 정확히 추출해주세요:

{chunk_text}

다음 형식으로 기술 정보를 추출하세요:
## 기술 현황

### 특허 현황
- **특허명**: [특허 제목]
- **특허 번호**: [번호]
- **출원일**: [날짜]
- **상태**: [등록/출원 상태]

### 핵심 기술
- **기술명**: [기술 이름]
- **기술 설명**: [간단한 설명]
- **기술 수준**: [성능 지표]

### R&D 현황
- **연구개발 인력**: [인원수]
- **연구 성과**: [주요 성과]
- **개발 계획**: [향후 계획]

제약사항:
1. 문서에 명시된 정보만 추출
2. 특허번호, 출원일 등 정확한 정보만 기재
3. 가상 기술/특허 생성 금지

/no_think
"""
        
        try:
            response = self.llm.invoke(tech_prompt)
            result = response.content if hasattr(response, 'content') else str(response)
            logger.info("기술 정보 추출 완료")
            return result.strip()
        except Exception as e:
            logger.error(f"기술 정보 추출 실패: {str(e)}")
            return f"기술 정보 추출 실패: {str(e)}"

    def generate_unified_template_prompt(self, pdf_data: Dict[str, Any]) -> str:
        """통합 템플릿 기반 프롬프트 생성 (기존 방식)"""
        logger.info("통합 템플릿 프롬프트 생성 시작")
        
        # 모든 페이지의 텍스트를 하나로 합치기
        all_text = ""
        for page in pdf_data['pages']:
            all_text += f"\n=== 페이지 {page['page_number']} ===\n"
            all_text += page['raw_text']
        
        template_prompt = f"""
다음 템플릿의 [ ] 빈칸을 PDF 내용에서 찾아 정확히 채워주세요:

## 회사 개요
- 회사명: [ ]
- 설립일: [ ]
- 대표자/CEO: [ ]
- 사업분야: [ ]
- 본사 위치: [ ]

## 경영진 구성
- CEO: [이름] (학력: [ ], 경력: [ ])
- CTO: [이름] (학력: [ ], 경력: [ ])
- COO: [이름] (학력: [ ], 경력: [ ])
- 기타 주요 임원: [ ]

## 재무 현황
- 최근 매출 (연도별): [ ]
- 영업이익: [ ]
- 순이익: [ ]
- 투자 유치 현황: [ ]
- 자금 조달 계획: [ ]

## 기술 현황
- 핵심 기술: [ ]
- 특허 보유 현황: [ ]
- R&D 투자: [ ]
- 기술적 경쟁력: [ ]

## 시장 분석
- 타겟 시장 규모: [ ]
- 주요 경쟁사: [ ]
- 시장 성장률: [ ]
- 시장 기회/리스크: [ ]

## 비즈니스 모델
- 주요 수익원: [ ]
- 비즈니스 모델: [ ]
- 고객군: [ ]

PDF 전체 내용:
{all_text}

제약사항:
- 문서에 명시된 정보만 정확히 추출
- 없는 정보는 "정보 없음"으로 표시
- 가상 정보/인물/숫자 생성 절대 금지
- 추론/추정/가정 금지

/no_think
"""
        return template_prompt
    
    def generate_unified_summary(self, pdf_data: Dict[str, Any]) -> str:
        """통합 템플릿을 사용하여 단일 요약 생성"""
        if not self.use_llm:
            logger.warning("LLM을 사용할 수 없습니다. 템플릿만 반환합니다.")
            return self.generate_unified_template_prompt(pdf_data)
        
        logger.info("통합 템플릿을 사용한 요약 생성 시작")
        
        try:
            # 통합 템플릿 프롬프트 생성
            template_prompt = self.generate_unified_template_prompt(pdf_data)
            
            # LLM에 프롬프트 전달
            response = self.llm.invoke(template_prompt)
            summary = response.content if hasattr(response, 'content') else str(response)
            
            logger.info("통합 요약 생성 완료")
            return summary.strip()
            
        except Exception as e:
            logger.error(f"통합 요약 생성 실패: {str(e)}")
            return f"요약 생성 실패: {str(e)}"
    
    def generate_summary_prompts(self, classified_content: Dict[str, List[Dict]], 
                                key_metrics: Dict[str, Any]) -> Dict[str, str]:
        """로컬 LLM용 요약 프롬프트 생성"""
        logger.info("요약 프롬프트 생성 시작")
        
        prompts = {}
        
        section_prompts = {
            'company_overview': """
문서 내용을 다음과 같이 간결하게 재구성하세요:

1. 회사명, 설립일, 대표자
2. 주요 사업 분야 및 제품/서비스  
3. 핵심 성과 및 현황

내용:
{content}

제약사항: 문서에 명시된 팩트만 나열, 분석/해석 금지, 각 항목 1-2문장 이내, 가상 정보 생성 절대 금지

/no_think
""",
            
            'financial_data': """
재무 정보를 다음과 같이 간결하게 정리하세요:

1. 매출 현황 (최근 연도별 매출)
2. 손익 현황 (영업이익, 순이익)  
3. 자금 조달 내역 (투자 라운드, 금액)

내용:
{content}
핵심 지표: {metrics}

제약사항: 문서의 숫자만 사용, 투자정보 추측 금지, 각 항목 간결하게, 가상 숫자/투자정보 생성 절대 금지

/no_think
""",
            
            'market_analysis': """
시장 정보를 다음과 같이 간결하게 정리하세요:

1. 시장 규모 및 성장률
2. 주요 경쟁사 및 경쟁 구도
3. 시장 기회 및 리스크

내용:
{content}

제약사항: 문서의 팩트만 나열, 각 항목 1-2문장 이내, 가상 시장정보/경쟁사 생성 절대 금지

/no_think
""",
            
            'technology': """
기술 정보를 다음과 같이 간결하게 정리하세요:

1. 핵심 기술 및 특허 현황
2. R&D 투자 및 개발 성과
3. 기술적 경쟁력 및 차별화 요소

내용:
{content}

제약사항: 문서의 기술 팩트만 나열, 각 항목 1-2문장 이내, 가상 기술정보/특허 생성 절대 금지

/no_think
""",
            
            'organization': """
조직 정보를 다음과 같이 간결하게 정리하세요:

1. 핵심 경영진 (이름, 직책, 학력, 경력)
2. 조직 규모 및 구성
3. 주요 역량 및 전문성

내용:
{content}

제약사항: 문서에 명시된 인명/직책/학력/경력만 추출하여 나열, 없는 정보는 창작하지 말고 "정보 없음"으로 표기

/no_think
"""
        }
        
        for section, prompt_template in section_prompts.items():
            if section in classified_content and classified_content[section]:
                content = '\n'.join([item['content'] for item in classified_content[section]])
                
                # 내용이 너무 길면 요약
                if len(content) > 3000:
                    content = content[:3000] + "... (내용 축약)"
                
                # 관련 지표 추가
                section_metrics = ""
                if section == 'financial_data' and 'financial_metrics' in key_metrics:
                    section_metrics = str(key_metrics['financial_metrics'])
                elif section == 'market_analysis' and 'market_metrics' in key_metrics:
                    section_metrics = str(key_metrics['market_metrics'])
                
                prompts[section] = prompt_template.format(
                    content=content,
                    metrics=section_metrics
                )
        
        return prompts
    
    def generate_llm_summaries(self, summary_prompts: Dict[str, str]) -> Dict[str, str]:
        """로컬 LLM을 사용하여 실제 요약 생성"""
        if not self.use_llm:
            logger.warning("LLM을 사용할 수 없습니다. 프롬프트만 반환합니다.")
            return {}
        
        logger.info("로컬 LLM을 사용한 요약 생성 시작")
        summaries = {}
        
        for section, prompt in summary_prompts.items():
            try:
                logger.info(f"{section} 섹션 요약 생성 중...")
                
                # LLM에 프롬프트 전달
                response = self.llm.invoke(prompt)
                summary = response.content if hasattr(response, 'content') else str(response)
                
                summaries[section] = {
                    'summary': summary.strip(),
                    'prompt_used': prompt,
                    'generated_at': datetime.now().isoformat()
                }
                
                logger.info(f"{section} 섹션 요약 완료 (길이: {len(summary)}자)")
                
            except Exception as e:
                logger.error(f"{section} 섹션 요약 생성 실패: {str(e)}")
                summaries[section] = {
                    'summary': f"요약 생성 실패: {str(e)}",
                    'prompt_used': prompt,
                    'generated_at': datetime.now().isoformat()
                }
        
        return summaries

    def create_comprehensive_summary(self, llm_summaries: Dict[str, Dict], 
                                   key_metrics: Dict[str, Any]) -> str:
        """전체 종합 요약 생성"""
        if not self.use_llm:
            return "LLM을 사용할 수 없어 종합 요약을 생성할 수 없습니다."
        
        # 종합 요약을 위한 프롬프트 생성
        comprehensive_prompt = f"""
다음 섹션별 정보를 바탕으로 핵심 내용만 간결하게 정리하세요:

섹션별 정보:
"""
        
        for section, data in llm_summaries.items():
            if 'summary' in data:
                comprehensive_prompt += f"\n### {section}:\n{data['summary']}\n"
        
        comprehensive_prompt += f"""
핵심 지표: {key_metrics}

다음 6개 항목으로 핵심만 간결하게 정리:
1. 회사 개요 (회사명, 사업분야)
2. 비즈니스 모델 (주요 수익원)
3. 재무 현황 (매출, 투자 등 숫자)
4. 기술 현황 (핵심 기술)
5. 시장 현황 (시장 규모, 경쟁)
6. 투자 포인트 (핵심 강점 3가지)

제약사항: 문서 팩트만 사용, 각 항목 2-3문장 이내, 분석/추론 금지, 가상 인물/회사/숫자 생성 절대 금지

/no_think
"""
        
        try:
            logger.info("종합 요약 생성 중...")
            response = self.llm.invoke(comprehensive_prompt)
            comprehensive_summary = response.content if hasattr(response, 'content') else str(response)
            logger.info("종합 요약 생성 완료")
            return comprehensive_summary.strip()
        except Exception as e:
            logger.error(f"종합 요약 생성 실패: {str(e)}")
            return f"종합 요약 생성 실패: {str(e)}"

    def save_summary_results(self, results: Dict[str, Any], output_dir: str, pdf_name: str):
        """요약 결과를 파일로 저장"""
        logger.info(f"요약 결과 저장: {output_dir}")
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # DataFrame을 직렬화 가능한 형태로 변환
        serializable_results = {}
        for key, value in results.items():
            if key == 'tables':
                serializable_results[key] = []
                for table in value:
                    table_data = table.copy()
                    if 'dataframe' in table_data:
                        table_data['dataframe'] = table_data['dataframe'].to_dict('records')
                    serializable_results[key].append(table_data)
            else:
                serializable_results[key] = value
        
        # JSON 형태로 전체 결과 저장
        json_file = Path(output_dir) / f"{pdf_name}_complete_analysis.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        # 읽기 쉬운 마크다운 형태로 요약 저장
        md_file = Path(output_dir) / f"{pdf_name}_summary.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_name} IR 자료 분석 요약\n\n")
            f.write(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**총 페이지**: {results['pdf_info']['total_pages']}\n")
            f.write(f"**추출된 표 수**: {len(results['tables'])}\n\n")
            
            # 종합 요약 (think 블록 제거)
            if 'comprehensive_summary' in results:
                comprehensive_summary = results['comprehensive_summary']
                # <think></think> 블록 제거
                comprehensive_summary = re.sub(r'<think>.*?</think>', '', comprehensive_summary, flags=re.DOTALL)
                f.write("## 📋 종합 요약\n\n")
                f.write(f"{comprehensive_summary.strip()}\n\n")
            
            # 섹션별 요약 (think 블록 제거)
            if 'llm_summaries' in results and results['llm_summaries']:
                f.write("## 📊 섹션별 상세 분석\n\n")
                
                for section, data in results['llm_summaries'].items():
                    section_name = {
                        'financial_data': '💰 재무 현황',
                        'market_analysis': '📈 시장 분석', 
                        'technology': '🔬 기술 현황',
                        'organization': '👥 조직 구조',
                        'business_model': '💼 비즈니스 모델',
                        'company_overview': '🏢 회사 개요',
                        'investment': '💵 투자 관련'
                    }.get(section, section)
                    
                    f.write(f"### {section_name}\n\n")
                    if 'summary' in data:
                        # <think></think> 블록 제거
                        summary = re.sub(r'<think>.*?</think>', '', data['summary'], flags=re.DOTALL)
                        f.write(f"{summary.strip()}\n\n")
            
            # 핵심 지표
            if 'key_metrics' in results:
                f.write("## 📈 핵심 지표\n\n")
                for category, metrics in results['key_metrics'].items():
                    if metrics:
                        f.write(f"**{category}**: {metrics}\n\n")
            
            # 추출된 표 정보 섹션 제거 (요청에 따라)
        
        logger.info(f"요약 결과 저장 완료: {md_file}")
    
    def process_ir_pdf_unified(self, pdf_path: str, output_dir: str = "raw_data_parsing") -> Dict[str, Any]:
        """통합 템플릿 방식의 IR PDF 처리 파이프라인"""
        logger.info(f"통합 템플릿 방식으로 IR PDF 처리 시작: {pdf_path}")
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 1. 텍스트 추출
        pdf_data = self.extract_text_from_pdf(pdf_path)
        
        # 2. 표 추출 (선택사항)
        tables = self.extract_financial_tables(pdf_path)
        
        # 3. 통합 요약 생성
        unified_summary = self.generate_unified_summary(pdf_data)
        
        # 결과 정리
        results = {
            'pdf_info': {
                'file_path': pdf_path,
                'total_pages': pdf_data['total_pages'],
                'processing_time': pdf_data['extraction_time']
            },
            'unified_summary': unified_summary,
            'tables': tables,
            'statistics': {
                'total_pages': pdf_data['total_pages'],
                'tables_extracted': len(tables),
                'total_words': sum(page['word_count'] for page in pdf_data['pages']),
                'processing_method': 'unified_template'
            }
        }
        
        # 결과 저장
        pdf_name = Path(pdf_path).stem
        self.save_unified_results(results, output_dir, pdf_name)
        
        return results
    
    def save_unified_results(self, results: Dict[str, Any], output_dir: str, pdf_name: str):
        """통합 요약 결과를 파일로 저장"""
        logger.info(f"통합 요약 결과 저장: {output_dir}")
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 마크다운 형태로 통합 요약 저장
        md_file = Path(output_dir) / f"{pdf_name}_unified_summary.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_name} IR 자료 통합 분석\n\n")
            f.write(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**총 페이지**: {results['pdf_info']['total_pages']}\n")
            f.write(f"**추출된 표 수**: {len(results['tables'])}\n")
            f.write(f"**처리 방식**: 통합 템플릿\n\n")
            
            # 통합 요약 내용
            f.write("## 📋 IR 자료 분석 결과\n\n")
            f.write(f"{results['unified_summary']}\n\n")
            
            # 통계 정보
            f.write("## 📊 처리 통계\n\n")
            stats = results['statistics']
            f.write(f"- **총 페이지 수**: {stats['total_pages']}\n")
            f.write(f"- **추출된 표 수**: {stats['tables_extracted']}\n")
            f.write(f"- **총 단어 수**: {stats['total_words']:,}\n")
            f.write(f"- **처리 방식**: {stats['processing_method']}\n")
        
        # JSON 형태로도 저장 (호환성)
        json_file = Path(output_dir) / f"{pdf_name}_unified_analysis.json"
        serializable_results = {}
        for key, value in results.items():
            if key == 'tables':
                serializable_results[key] = []
                for table in value:
                    table_data = table.copy()
                    if 'dataframe' in table_data:
                        table_data['dataframe'] = table_data['dataframe'].to_dict('records')
                    serializable_results[key].append(table_data)
            else:
                serializable_results[key] = value
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"통합 요약 결과 저장 완료: {md_file}")

    def process_ir_pdf_smart_chunks(self, pdf_path: str, output_dir: str = "raw_data_parsing") -> Dict[str, Any]:
        """스마트 청크 기반 2단계 IR PDF 처리 파이프라인"""
        logger.info(f"스마트 청크 방식으로 IR PDF 처리 시작: {pdf_path}")
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 1. 텍스트 추출
        pdf_data = self.extract_text_from_pdf(pdf_path)
        
        # 2. 스마트 청크 분할
        chunks = self.split_pdf_into_smart_chunks(pdf_data)
        
        # 3. 표 추출 (전체 PDF 대상)
        tables = self.extract_financial_tables(pdf_path)
        
        # 4. 청크별 정보 추출
        extracted_info = {
            'organization': [],
            'finance': [],
            'technology': [],
            'general': []
        }
        
        for chunk in chunks:
            chunk_type = chunk['type']
            chunk_text = chunk['text']
            
            if chunk_type == 'organization':
                logger.info(f"조직 정보 청크 처리 중 (페이지 {chunk['pages']})")
                org_info = self.extract_organization_info(chunk_text)
                extracted_info['organization'].append({
                    'pages': chunk['pages'],
                    'content': org_info,
                    'keywords_found': list(chunk['keywords_found'])
                })
            
            elif chunk_type == 'finance':
                logger.info(f"재무 정보 청크 처리 중 (페이지 {chunk['pages']})")
                finance_info = self.extract_finance_info(chunk_text)
                extracted_info['finance'].append({
                    'pages': chunk['pages'],
                    'content': finance_info,
                    'keywords_found': list(chunk['keywords_found'])
                })
            
            elif chunk_type == 'technology':
                logger.info(f"기술 정보 청크 처리 중 (페이지 {chunk['pages']})")
                tech_info = self.extract_technology_info(chunk_text)
                extracted_info['technology'].append({
                    'pages': chunk['pages'],
                    'content': tech_info,
                    'keywords_found': list(chunk['keywords_found'])
                })
            
            else:  # general
                # 일반 청크는 기존 통합 템플릿 방식으로 처리
                logger.info(f"일반 정보 청크 처리 중 (페이지 {chunk['pages']})")
                general_info = self.extract_general_info(chunk_text)
                extracted_info['general'].append({
                    'pages': chunk['pages'],
                    'content': general_info,
                    'keywords_found': list(chunk['keywords_found'])
                })
        
        # 5. 통합 요약 생성
        final_summary = self.merge_extracted_info(extracted_info)
        
        # 결과 정리
        results = {
            'pdf_info': {
                'file_path': pdf_path,
                'total_pages': pdf_data['total_pages'],
                'processing_time': pdf_data['extraction_time']
            },
            'chunks_info': {
                'total_chunks': len(chunks),
                'chunk_types': [chunk['type'] for chunk in chunks],
                'chunk_pages': [chunk['pages'] for chunk in chunks]
            },
            'extracted_info': extracted_info,
            'final_summary': final_summary,
            'tables': tables,
            'statistics': {
                'total_pages': pdf_data['total_pages'],
                'chunks_processed': len(chunks),
                'tables_extracted': len(tables),
                'total_words': sum(page['word_count'] for page in pdf_data['pages']),
                'processing_method': 'smart_chunks'
            }
        }
        
        # 결과 저장
        pdf_name = Path(pdf_path).stem
        self.save_smart_chunk_results(results, output_dir, pdf_name)
        
        return results

    def extract_general_info(self, chunk_text: str) -> str:
        """일반 정보 추출 (기본 템플릿 방식)"""
        if not self.use_llm:
            return "LLM을 사용할 수 없어 일반 정보를 추출할 수 없습니다."
        
        general_prompt = f"""
다음 텍스트에서 핵심 정보를 추출해주세요:

{chunk_text}

다음 항목들을 찾아서 정리하세요:
## 일반 정보

### 회사 개요
- **회사명**: [회사 이름]
- **설립일**: [설립 날짜]
- **사업 분야**: [주요 사업 영역]
- **본사 위치**: [주소]

### 사업 현황
- **주요 제품/서비스**: [제품 목록]
- **시장 전략**: [마케팅 계획]
- **성장 계획**: [향후 계획]

제약사항:
1. 문서에 명시된 정보만 추출
2. 없는 정보는 "정보 없음"으로 표기
3. 가상 정보 생성 절대 금지

/no_think
"""
        
        try:
            response = self.llm.invoke(general_prompt)
            result = response.content if hasattr(response, 'content') else str(response)
            logger.info("일반 정보 추출 완료")
            return result.strip()
        except Exception as e:
            logger.error(f"일반 정보 추출 실패: {str(e)}")
            return f"일반 정보 추출 실패: {str(e)}"

    def merge_extracted_info(self, extracted_info: Dict[str, List]) -> str:
        """추출된 정보를 통합하여 최종 요약 생성"""
        logger.info("추출된 정보 통합 시작")
        
        merged_summary = "# IR 자료 종합 분석 (스마트 청크 방식)\n\n"
        
        # 조직 정보 통합
        if extracted_info['organization']:
            merged_summary += "## 📋 조직 구성\n\n"
            for org_chunk in extracted_info['organization']:
                merged_summary += f"### 페이지 {'-'.join(map(str, org_chunk['pages']))}\n"
                merged_summary += f"{org_chunk['content']}\n\n"
        
        # 재무 정보 통합
        if extracted_info['finance']:
            merged_summary += "## 💰 재무 현황\n\n"
            for finance_chunk in extracted_info['finance']:
                merged_summary += f"### 페이지 {'-'.join(map(str, finance_chunk['pages']))}\n"
                merged_summary += f"{finance_chunk['content']}\n\n"
        
        # 기술 정보 통합
        if extracted_info['technology']:
            merged_summary += "## 🔬 기술 현황\n\n"
            for tech_chunk in extracted_info['technology']:
                merged_summary += f"### 페이지 {'-'.join(map(str, tech_chunk['pages']))}\n"
                merged_summary += f"{tech_chunk['content']}\n\n"
        
        # 일반 정보 통합
        if extracted_info['general']:
            merged_summary += "## 📈 기타 정보\n\n"
            for general_chunk in extracted_info['general']:
                merged_summary += f"### 페이지 {'-'.join(map(str, general_chunk['pages']))}\n"
                merged_summary += f"{general_chunk['content']}\n\n"
        
        logger.info("정보 통합 완료")
        return merged_summary

    def post_process_summary(self, markdown_text: str) -> str:
        """
        로직 기반으로 마크다운 요약본을 후처리하여 중복을 제거하고 정보를 통합합니다.
        """
        logger.info("로직 기반 요약 후처리 시작")
        if not markdown_text or not markdown_text.strip():
            return ""

        # '페이지' 정보를 담은 헤더를 제외한 순수 헤더를 추출하는 함수
        def get_clean_header(full_header):
            return re.sub(r'\s*\(페이지:?.*?\)', '', full_header).strip()

        # 헤더를 기준으로 문서를 청크로 분할합니다.
        chunks = re.split(r'\n(?=## |### )', markdown_text)
        
        # 최종 섹션들을 순서대로 저장할 리스트와, 내용을 병합할 딕셔너리
        header_order = []
        final_sections = {}
        
        placeholder_keywords = ["정보 없음", "제공되지 않음", "not available", "없음"]

        def is_placeholder(text):
            # 내용의 핵심이 플레이스홀더 키워드인지 검사
            # 여러 줄일 수 있으므로 각 줄을 검사
            lines = text.strip().split('\n')
            # 모든 줄이 플레이스홀더 관련 내용일 때만 True
            return all(any(keyword in line for keyword in placeholder_keywords) for line in lines if line.strip())

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            lines = chunk.split('\n')
            full_header = lines[0].strip()
            clean_header = get_clean_header(full_header)
            content = '\n'.join(lines[1:]).strip()

            # 헤더가 처음 나타나는 경우, 순서와 내용을 기록
            if clean_header not in final_sections:
                header_order.append(clean_header)
                final_sections[clean_header] = {'header': full_header, 'content': content}
            # 중복된 헤더를 만난 경우
            else:
                existing_section = final_sections[clean_header]
                existing_content = existing_section['content']
                
                # 병합 규칙 적용
                # 1. 기존 내용이 플레이스홀더이고 새 내용에 정보가 있으면 교체
                if is_placeholder(existing_content) and not is_placeholder(content):
                    logger.info(f"'{clean_header}' 섹션 업데이트: 플레이스홀더를 실제 정보로 교체합니다.")
                    final_sections[clean_header]['content'] = content
                    # 페이지 정보도 최신 정보로 업데이트
                    final_sections[clean_header]['header'] = full_header
                # 2. 둘 다 정보가 있는 경우, 내용을 합침
                elif not is_placeholder(existing_content) and not is_placeholder(content):
                    logger.info(f"'{clean_header}' 섹션 병합: 기존 정보에 새 정보를 추가합니다.")
                    # 중복 라인을 피하면서 병합
                    existing_lines = set(ex.strip() for ex in existing_content.split('\n') if ex.strip())
                    new_lines = set(ne.strip() for ne in content.split('\n') if ne.strip())
                    combined_lines = sorted(list(existing_lines.union(new_lines)))
                    final_sections[clean_header]['content'] = '\n'.join(combined_lines)
                # 3. 그 외의 경우 (새 내용이 플레이스홀더 등)는 기존 내용을 유지

        # 최종 마크다운 재구성
        final_markdown_parts = []
        for header_key in header_order:
            section = final_sections.get(header_key)
            if section and section['content']:
                final_markdown_parts.append(f"{section['header']}\n{section['content']}")
        
        logger.info("로직 기반 요약 후처리 완료")
        return "\n\n".join(final_markdown_parts)

    def save_smart_chunk_results(self, results: Dict[str, Any], output_dir: str, pdf_name: str):
        """스마트 청크 처리 결과를 파일로 저장 (후처리 포함)"""
        logger.info(f"스마트 청크 결과 저장: {output_dir}")
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 1차 요약본에 대해 로직 기반 후처리 수행
        raw_summary = results['final_summary']
        polished_summary = self.post_process_summary(raw_summary)
        
        # 마크다운 형태로 최종 요약 저장
        md_file = Path(output_dir) / f"{pdf_name}_smart_chunk_summary.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_name} IR 자료 스마트 청크 분석\n\n")
            f.write(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**처리 방식**: 스마트 청크 + 로직 기반 후처리\n\n")
            f.write("## 📋 최종 분석 결과\n\n")
            f.write(f"{polished_summary}\n\n")
            
            # 통계 정보 추가
            f.write("## 📊 처리 통계\n\n")
            stats = results['statistics']
            f.write(f"- **총 페이지 수**: {stats['total_pages']}\n")
            f.write(f"- **처리된 청크 수**: {stats['chunks_processed']}\n")
            f.write(f"- **추출된 표 수**: {stats['tables_extracted']}\n")
            f.write(f"- **총 단어 수**: {stats['total_words']:,}\n")

        # JSON 형태로도 저장 (후처리된 내용 포함)
        json_file = Path(output_dir) / f"{pdf_name}_smart_chunk_analysis.json"
        serializable_results = results.copy()
        serializable_results['polished_summary'] = polished_summary
        
        # DataFrame 직렬화
        if 'tables' in serializable_results:
            for table in serializable_results['tables']:
                if 'dataframe' in table and isinstance(table['dataframe'], pd.DataFrame):
                    table['dataframe'] = table['dataframe'].to_dict('records')
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"스마트 청크 결과 저장 완료: {md_file}")

    def process_ir_pdf(self, pdf_path: str, output_dir: str = "raw_data_parsing") -> Dict[str, Any]:
        """IR PDF 전체 처리 파이프라인 (LLM 요약 포함)"""
        logger.info(f"IR PDF 처리 시작: {pdf_path}")
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 1. 텍스트 추출
        pdf_data = self.extract_text_from_pdf(pdf_path)
        
        # 2. 섹션별 분류
        classified_content = self.classify_content_by_section(pdf_data['pages'])
        
        # 3. 표 추출
        tables = self.extract_financial_tables(pdf_path)
        
        # 4. 핵심 지표 추출
        key_metrics = self.extract_key_metrics(classified_content)
        
        # 5. 요약 프롬프트 생성
        summary_prompts = self.generate_summary_prompts(classified_content, key_metrics)
        
        # 6. LLM을 사용한 실제 요약 생성
        llm_summaries = {}
        comprehensive_summary = ""
        
        if self.use_llm and summary_prompts:
            llm_summaries = self.generate_llm_summaries(summary_prompts)
            comprehensive_summary = self.create_comprehensive_summary(llm_summaries, key_metrics)
        
        # 결과 정리
        results = {
            'pdf_info': {
                'file_path': pdf_path,
                'total_pages': pdf_data['total_pages'],
                'processing_time': pdf_data['extraction_time']
            },
            'classified_content': classified_content,
            'tables': tables,
            'key_metrics': key_metrics,
            'summary_prompts': summary_prompts,
            'llm_summaries': llm_summaries,
            'comprehensive_summary': comprehensive_summary,
            'statistics': {
                'sections_found': len([k for k, v in classified_content.items() if v and k != 'uncategorized']),
                'tables_extracted': len(tables),
                'total_words': sum(sum(item['word_count'] for item in section) for section in classified_content.values()),
                'summaries_generated': len(llm_summaries)
            }
        }
        
        # 결과 저장
        pdf_name = Path(pdf_path).stem
        self.save_summary_results(results, output_dir, pdf_name)
        
        # 기존 JSON도 함께 저장 (호환성)
        output_file = Path(output_dir) / f"{pdf_name}_analysis.json"
        self.save_results(results, str(output_file))
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """결과를 JSON 파일로 저장"""
        logger.info(f"결과 저장: {output_path}")
        
        # DataFrame을 직렬화 가능한 형태로 변환
        serializable_results = {}
        
        for key, value in results.items():
            if key == 'tables':
                serializable_results[key] = []
                for table in value:
                    table_data = table.copy()
                    if 'dataframe' in table_data:
                        table_data['dataframe'] = table_data['dataframe'].to_dict('records')
                    serializable_results[key].append(table_data)
            else:
                serializable_results[key] = value
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        logger.info("결과 저장 완료")
    
    def print_summary_report(self, results: Dict[str, Any]):
        """처리 결과 요약 보고서 출력"""
        print("\n" + "="*80)
        print("IR PDF 분석 결과 요약")
        print("="*80)
        
        # 기본 정보
        pdf_info = results['pdf_info']
        print(f"파일: {pdf_info['file_path']}")
        print(f"총 페이지: {pdf_info['total_pages']}")
        print(f"처리 시간: {pdf_info['processing_time']}")
        
        # 섹션별 분류 결과
        print(f"\n📊 섹션별 분류 결과:")
        classified = results['classified_content']
        for section, content in classified.items():
            if content:
                pages = [item['page_number'] for item in content]
                words = sum(item['word_count'] for item in content)
                print(f"  • {section}: {len(content)}페이지 (페이지 {pages}, {words:,}단어)")
        
        # 표 추출 결과
        tables = results['tables']
        if tables:
            print(f"\n📋 추출된 표: {len(tables)}개")
            for table in tables:
                print(f"  • 표 {table['table_id']}: 페이지 {table['page']} ({table['dataframe'].shape[0]}행 x {table['dataframe'].shape[1]}열)")
        
        # 핵심 지표
        metrics = results['key_metrics']
        print(f"\n📈 추출된 핵심 지표:")
        for category, data in metrics.items():
            if data:
                print(f"  • {category}: {data}")
        
        # LLM 요약 결과
        if 'llm_summaries' in results and results['llm_summaries']:
            print(f"\n🤖 LLM 생성 요약: {len(results['llm_summaries'])}개 섹션")
            for section in results['llm_summaries'].keys():
                print(f"  • {section}")
        
        # 종합 요약 미리보기
        if 'comprehensive_summary' in results and results['comprehensive_summary']:
            print(f"\n📝 종합 요약 (미리보기):")
            summary_preview = results['comprehensive_summary'][:200] + "..." if len(results['comprehensive_summary']) > 200 else results['comprehensive_summary']
            print(f"  {summary_preview}")
        
        # 요약 프롬프트
        prompts = results['summary_prompts']
        print(f"\n📝 생성된 요약 프롬프트: {len(prompts)}개 섹션")
        for section in prompts.keys():
            print(f"  • {section}")
        
        print(f"\n📊 통계:")
        stats = results['statistics']
        print(f"  • 발견된 섹션: {stats['sections_found']}개")
        print(f"  • 추출된 표: {stats['tables_extracted']}개")
        print(f"  • 총 단어 수: {stats['total_words']:,}개")
        if 'summaries_generated' in stats:
            print(f"  • 생성된 요약: {stats['summaries_generated']}개")
        
        print("="*80)
    
    def print_unified_report(self, results: Dict[str, Any]):
        """통합 처리 결과 요약 보고서 출력"""
        print("\n" + "="*80)
        print("IR PDF 통합 분석 결과")
        print("="*80)
        
        # 기본 정보
        pdf_info = results['pdf_info']
        print(f"파일: {pdf_info['file_path']}")
        print(f"총 페이지: {pdf_info['total_pages']}")
        print(f"처리 시간: {pdf_info['processing_time']}")
        
        # 처리 통계
        stats = results['statistics']
        print(f"\n📊 처리 통계:")
        print(f"  • 총 페이지 수: {stats['total_pages']}")
        print(f"  • 추출된 표: {stats['tables_extracted']}개")
        print(f"  • 총 단어 수: {stats['total_words']:,}개")
        print(f"  • 처리 방식: {stats['processing_method']}")
        
        # 통합 요약 미리보기
        if 'unified_summary' in results and results['unified_summary']:
            print(f"\n📝 통합 요약 (미리보기):")
            summary_preview = results['unified_summary'][:300] + "..." if len(results['unified_summary']) > 300 else results['unified_summary']
            print(f"  {summary_preview}")
        
        print("="*80)


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="IR PDF 파서 및 요약기")
    parser.add_argument("pdf_path", type=str, help="분석할 IR PDF 파일의 경로")
    parser.add_argument(
        "--method", 
        type=str, 
        default="smart_chunks", 
        choices=["unified", "smart_chunks"],
        help="분석 방법 선택: 'unified' (통합 템플릿) 또는 'smart_chunks' (스마트 청크)"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLM 사용을 비활성화합니다."
    )
    args = parser.parse_args()

    print(f"IR PDF 파서 시작: {args.pdf_path}")
    print(f"분석 방법: {args.method}, LLM 사용: {not args.no_llm}")

    # 파서 초기화
    parser_instance = IRPDFParser(use_llm=not args.no_llm)
    
    try:
        if args.method == "unified":
            # IR PDF 처리 (통합 템플릿 방식 사용)
            results = parser_instance.process_ir_pdf_unified(args.pdf_path, output_dir="raw_data_parsing")
            
            # 통합 요약 보고서 출력
            parser_instance.print_unified_report(results)
            
            pdf_name = Path(args.pdf_path).stem
            print(f"\n✅ 통합 템플릿 방식 처리 완료!")
            print(f"📁 상세 결과: raw_data_parsing/{pdf_name}_unified_analysis.json")
            print(f"📄 통합 요약: raw_data_parsing/{pdf_name}_unified_summary.md")

        elif args.method == "smart_chunks":
            # IR PDF 처리 (스마트 청크 방식 사용)
            results = parser_instance.process_ir_pdf_smart_chunks(args.pdf_path, output_dir="raw_data_parsing")
            
            # 스마트 청크 결과 보고서 출력 (간단하게)
            pdf_name = Path(args.pdf_path).stem
            print("\n" + "="*80)
            print("IR PDF 스마트 청크 분석 결과")
            print("="*80)
            print(f"파일: {results['pdf_info']['file_path']}")
            print(f"총 페이지: {results['pdf_info']['total_pages']}")
            print(f"처리된 청크 수: {results['chunks_info']['total_chunks']}")
            print(f"처리 방식: {results['statistics']['processing_method']}")
            print("="*80)

            print(f"\n✅ 스마트 청크 방식 처리 완료!")
            print(f"📁 상세 결과: raw_data_parsing/{pdf_name}_smart_chunk_analysis.json")
            print(f"📄 스마트 청크 요약: raw_data_parsing/{pdf_name}_smart_chunk_summary.md")

    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없습니다: {args.pdf_path}")
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
 