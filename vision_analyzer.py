#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision-LLM으로 생성된 IR 마크다운 분석기 (v5 - 최종 안정화)

'계층적 분석 및 종합 파이프라인'을 사용하여 투자 분석에 필요한 핵심 정보를 추출합니다.
LLM의 출력에서 <think> 블록을 정규식으로 제거한 후 JSON 파싱을 수행하여 안정성을 극대화합니다.
"""

import re
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# 로컬 LLM 연동 (langchain_ollama)
try:
    from langchain_ollama import ChatOllama
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ langchain_ollama가 설치되지 않았습니다. pip install langchain-ollama langchain-core 로 설치하세요.")
    class ChatOllama: pass
    class StrOutputParser: pass
    class PromptTemplate: pass

# --- 설정 ---
MODEL_ID = "qwen3:32b" # 모델 ID는 환경에 맞게 수정하세요 (예: "qwen2:32b")
BASE_URL = "http://192.168.120.102:11434" # Ollama 서버 주소

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VisionMDAnalyzer:
    """
    Vision LLM이 생성한 마크다운(.md) 파일을 분석하여
    핵심 정보를 추출하고 구조화하는 클래스. (최종 안정화 버전)
    """

    def __init__(self, model_id: str = MODEL_ID, base_url: str = BASE_URL):
        if not OLLAMA_AVAILABLE:
            logger.error("필수 라이브러리가 설치되지 않아 LLM을 사용할 수 없습니다.")
            self.use_llm = False
            return
        try:
            self.llm = ChatOllama(model=model_id, base_url=base_url, temperature=0)
            self.use_llm = True
            logger.info(f"LLM 초기화 완료: {model_id} at {base_url}")
        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}. LLM 기능 없이 실행됩니다.")
            self.use_llm = False

    def _clean_and_parse_json(self, raw_output: str) -> Optional[Any]:
        """
        LLM의 원시 출력에서 <think> 블록을 제거하고, 남은 문자열을 JSON으로 파싱합니다.
        """
        try:
            # <think>...</think> 블록을 re.sub으로 제거합니다.
            cleaned_output = re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL).strip()
            
            # 정제된 문자열에서 JSON 객체 또는 배열을 찾습니다.
            match = re.search(r'(\{.*\}|\[.*\])', cleaned_output, re.DOTALL)
            if match:
                json_string = match.group(0)
                return json.loads(json_string)
            else:
                logger.warning(f"정제된 출력에서 JSON을 찾지 못했습니다. LLM 출력:\n---\n{cleaned_output}\n---")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}\n원시 출력 일부: {raw_output[:300]}...")
            return None
        except Exception as e:
            logger.error(f"JSON 처리 중 예기치 않은 오류 발생: {e}")
            return None

    def _split_md_by_headers(self, md_content: str) -> List[Dict[str, str]]:
        logger.info("1단계: 마크다운 구조적 분할 시작...")
        chunks = re.split(r'\n\s*\n(?=^#{1,2} )', md_content.strip(), flags=re.MULTILINE)
        structured_chunks = []
        for chunk in chunks:
            if not chunk.strip(): continue
            lines = chunk.strip().split('\n')
            header = lines[0].strip()
            content = '\n'.join(lines[1:]).strip()
            if not header.startswith('#'):
                header = "# 서문"
                content = chunk.strip()
            structured_chunks.append({'header': header, 'content': content})
        logger.info(f"분할 완료: {len(structured_chunks)}개의 구조적 섹션 생성.")
        return structured_chunks

    def _generate_chunk_summaries(self, chunks: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        if not self.use_llm: return [{**c, 'summary': '', 'keywords': []} for c in chunks]
        logger.info("2단계: 섹션별 요약 및 키워드 추출 (인덱싱) 시작...")
        template = """다음 텍스트의 핵심 내용을 한국어로 한 문장으로 요약하고, 가장 중요한 키워드를 5개만 쉼표(,)로 구분하여 나열해줘.\n\n--- 텍스트 시작 ---\n{text}\n--- 텍스트 끝 ---\n\n결과는 다음 형식으로만 출력해줘.\n요약: [여기에 요약]\n키워드: [여기에 키워드]\n/no_think\n"""
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        indexed_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"  - 인덱싱 처리 중... ({i+1}/{len(chunks)}) : {chunk['header']}")
            try:
                response = chain.invoke({"text": chunk['content']})
                summary_match = re.search(r"요약:\s*(.*)", response)
                keywords_match = re.search(r"키워드:\s*(.*)", response)
                summary = summary_match.group(1).strip() if summary_match else "요약 실패"
                keywords = [kw.strip() for kw in keywords_match.group(1).strip().split(',')] if keywords_match else []
                indexed_chunks.append({**chunk, 'summary': summary, 'keywords': keywords})
            except Exception as e:
                logger.warning(f"  - 인덱싱 실패: {chunk['header']}. 원본 내용만 사용. 오류: {e}")
                indexed_chunks.append({**chunk, 'summary': '', 'keywords': []})
        logger.info("인덱싱 완료.")
        return indexed_chunks

    def _group_chunks_by_theme(self, indexed_chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        if not self.use_llm: return {}
        logger.info("3-1단계: 주제별 그룹화 시작...")
        summaries_text = "\n".join(f"- 헤더: {chunk['header']}\n  요약: {chunk.get('summary', '')}" for chunk in indexed_chunks if chunk.get('summary'))
        template = """당신은 투자 분석가입니다. 다음은 한 IR 문서의 섹션별 요약 리스트입니다. 각 섹션의 '헤더'를 읽고, 아래 6가지 주제 중 가장 적합한 주제로 분류해주세요. 결과는 반드시 JSON 형식으로만 반환해주세요. 예시: {{"회사 개요": ["헤더1", "헤더2"], "경영진 및 조직": ["헤더3"]}}\n\n**분류할 주제:**\n["회사 개요", "경영진 및 조직", "재무 현황", "기술 및 제품", "사업 및 시장 전략", "기타"]\n\n**섹션별 요약 리스트:**\n---\n{summaries}\n---\n\n**JSON 출력:**\n/no_think\n"""
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        all_keys = ["회사 개요", "경영진 및 조직", "재무 현황", "기술 및 제품", "사업 및 시장 전략", "기타"]
        final_groups = {key: [] for key in all_keys}
        try:
            raw_output = chain.invoke({"summaries": summaries_text})
            response_data = self._clean_and_parse_json(raw_output)
            
            if isinstance(response_data, dict):
                for key, value in response_data.items():
                    if key in final_groups and isinstance(value, list):
                        final_groups[key].extend(value)
            logger.info("주제별 그룹화 완료.")
        except Exception as e:
            logger.error(f"주제별 그룹화 중 예외 발생: {e}. 빈 그룹을 반환합니다.")
        return final_groups

    def _extract_detailed_info(self, grouped_headers: Dict[str, List[str]], original_chunks: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.use_llm: return {}
        logger.info("3-2단계: 주제별 심층 정보 추출 시작...")
        chunk_map = {chunk['header']: chunk['content'] for chunk in original_chunks}
        extraction_prompts = {
            "회사 개요": """당신은 주어진 텍스트에서 정보를 추출하여 JSON 형식으로만 반환하는 AI입니다. 절대로 요약이나 설명을 생성하지 마시오.
응답은 아래에 명시된 JSON 스키마를 반드시 준수해야 합니다.

**추출할 정보:**
- 회사명 (corporation_name)
- 설립일 (foundation_date)
- 대표자 (ceo)
- 주요 사업 분야 (main_business)
- 본사 및 주요 시설 위치 (locations)
- 회사 연혁의 주요 마일스톤 (history_milestones)

**분석할 텍스트:**
```{context}```

**JSON 스키마:**
```json
{{
    "properties": {{
        "corporation_name": {{"type": "string", "description": "회사명"}},
        "foundation_date": {{"type": "string", "description": "설립일"}},
        "ceo": {{"type": "string", "description": "대표자 이름"}},
        "main_business": {{"type": "string", "description": "주요 사업 분야"}},
        "locations": {{"type": "array", "items": {{"type": "string"}}, "description": "본사, 연구소 등 주요 위치 목록"}},
        "history_milestones": {{"type": "array", "items": {{"type": "string"}}, "description": "회사 연혁의 주요 이벤트 목록"}}
    }},
    "required": ["corporation_name", "foundation_date", "ceo", "main_business"]
}}
```

/no_think""",
            "경영진 및 조직": """당신은 주어진 텍스트에서 정보를 추출하여 JSON 형식으로만 반환하는 AI입니다. 절대로 요약이나 설명을 생성하지 마시오.
응답은 아래에 명시된 JSON 스키마를 반드시 준수해야 합니다.

**추출할 정보:**
- 각 경영진의 이름(name), 직책(position), 최종 학력(education), 주요 경력(career). 모든 인물을 빠짐없이 포함해야 합니다.

**분석할 텍스트:**
```{context}```

**JSON 스키마:**
```json
{{
    "type": "array",
    "items": {{
        "type": "object",
        "properties": {{
            "name": {{"type": "string", "description": "이름"}},
            "position": {{"type": "string", "description": "직책"}},
            "education": {{"type": "string", "description": "최종 학력"}},
            "career": {{"type": "string", "description": "주요 경력"}}
        }},
        "required": ["name", "position"]
    }}
}}
```
/no_think""",
            "재무 현황": """당신은 주어진 텍스트에서 정보를 추출하여 JSON 형식으로만 반환하는 AI입니다. 절대로 요약이나 설명을 생성하지 마시오.
응답은 아래에 명시된 JSON 스키마를 반드시 준수해야 합니다.

**추출할 정보:**
- `financial_summary`: 연도별 재무 지표 (매출, 영업이익, 순이익, 자산, 부채, 자본).
- `funding_history`: 투자 유치 내역.
- `financial_plan`: 향후 자금 계획.

**분석할 텍스트:**
```{context}```

**JSON 스키마:**
```json
{{
    "properties": {{
        "financial_summary": {{
            "type": "array",
            "items": {{
                "type": "object",
                "properties": {{
                    "year": {{"type": "string"}},
                    "revenue": {{"type": "string"}},
                    "operating_profit": {{"type": "string"}},
                    "net_income": {{"type": "string"}},
                    "assets": {{"type": "string"}},
                    "liabilities": {{"type": "string"}},
                    "equity": {{"type": "string"}}
                }}
            }}
        }},
        "funding_history": {{"type": "string"}},
        "financial_plan": {{"type": "string"}}
    }}
}}
```
/no_think""",
            "기술 및 제품": """당신은 주어진 텍스트에서 정보를 추출하여 JSON 형식으로만 반환하는 AI입니다. 절대로 요약이나 설명을 생성하지 마시오.
응답은 아래에 명시된 JSON 스키마를 반드시 준수해야 합니다.

**추출할 정보:**
- 핵심 기술, 보유 특허, 주요 제품 라인업, 기술적 경쟁 우위.

**분석할 텍스트:**
```{context}```

**JSON 스키마:**
```json
{{
    "properties": {{
        "core_technologies": {{"type": "array", "items": {{"type": "string"}}, "description": "핵심 기술 목록"}},
        "patents": {{"type": "array", "items": {{"type": "string"}}, "description": "보유 특허 목록"}},
        "product_lineup": {{"type": "array", "items": {{"type": "string"}}, "description": "주요 제품 및 서비스 라인업"}},
        "tech_advantage": {{"type": "string", "description": "경쟁사 대비 기술적 우위 요약"}}
    }}
}}
```
/no_think""",
            "사업 및 시장 전략": """당신은 주어진 텍스트에서 정보를 추출하여 JSON 형식으로만 반환하는 AI입니다. 절대로 요약이나 설명을 생성하지 마시오.
응답은 아래에 명시된 JSON 스키마를 반드시 준수해야 합니다.

**추출할 정보:**
- 타겟 시장, 주요 경쟁사, 비즈니스 모델, 향후 확장 전략.

**분석할 텍스트:**
```{context}```

**JSON 스키마:**
```json
{{
    "properties": {{
        "target_market": {{"type": "string", "description": "타겟 시장의 규모 및 특징"}},
        "competitors": {{"type": "array", "items": {{"type": "string"}}, "description": "주요 경쟁사 목록"}},
        "business_model": {{"type": "string", "description": "비즈니스 모델 및 주요 수익원"}},
        "scale_up_strategy": {{"type": "string", "description": "향후 사업화 또는 확장 전략"}}
    }}
}}
```
/no_think"""
        }
        detailed_info = {}
        for theme, headers in grouped_headers.items():
            if theme not in extraction_prompts or not headers: continue
            logger.info(f"  - 심층 분석 중... ({theme})")
            context = "\n\n---\n\n".join(chunk_map.get(h, '') for h in headers if h in chunk_map)
            if not context.strip():
                logger.warning(f"  - '{theme}' 주제에 해당하는 내용이 없어 건너뜁니다.")
                detailed_info[theme] = {}
                continue
            template = extraction_prompts[theme]
            prompt = PromptTemplate.from_template(template)
            chain = prompt | self.llm | StrOutputParser()
            try:
                raw_output = chain.invoke({"context": context})
                extracted_data = self._clean_and_parse_json(raw_output)
                if extracted_data is not None:
                    detailed_info[theme] = extracted_data
                else:
                    detailed_info[theme] = {"error": "LLM 출력에서 JSON을 찾지 못함"}
            except Exception as e:
                logger.error(f"  - '{theme}' 정보 추출 실패: {e}")
                detailed_info[theme] = {"error": str(e)}
        logger.info("심층 정보 추출 완료.")
        return detailed_info

    def analyze(self, md_file_path: str) -> Dict[str, Any]:
        logger.info(f"분석 시작: {md_file_path}")
        try:
            md_content = Path(md_file_path).read_text(encoding='utf-8')
        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없습니다: {md_file_path}")
            return {}
        chunks = self._split_md_by_headers(md_content)
        indexed_chunks = self._generate_chunk_summaries(chunks)
        grouped_headers = self._group_chunks_by_theme(indexed_chunks)
        final_analysis = self._extract_detailed_info(grouped_headers, chunks)
        logger.info("분석 완료.")
        return {
            "file_info": {"path": md_file_path},
            "analysis_result": final_analysis,
            "debug_info": {"total_chunks": len(chunks), "grouped_headers": grouped_headers}
        }

    def save_results(self, analysis_result: Dict[str, Any], output_dir: str, file_stem: str):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        json_path = output_path / f"{file_stem}_vision_analysis.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 결과 저장 완료: {json_path}")
        md_path = output_path / f"{file_stem}_vision_summary.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {file_stem} Vision IR 분석 보고서\n\n")
            data = analysis_result.get("analysis_result", {})
            for theme, content in data.items():
                f.write(f"## 📊 {theme}\n\n")
                if isinstance(content, dict):
                    for key, value in content.items():
                        f.write(f"- **{key}**: {json.dumps(value, ensure_ascii=False, indent=2)}\n")
                elif isinstance(content, list):
                    for item in content:
                        f.write("- ---\n")
                        if isinstance(item, dict):
                            for key, value in item.items():
                                f.write(f"  - **{key}**: {value}\n")
                        else:
                            f.write(f"  - {item}\n")
                else:
                    f.write(f"{content}\n")
                f.write("\n")
        logger.info(f"Markdown 보고서 저장 완료: {md_path}")

def main():
    parser = argparse.ArgumentParser(description="Vision-LLM으로 생성된 IR 마크다운 분석기")
    parser.add_argument("md_path", type=str, help="분석할 마크다운 파일의 경로")
    parser.add_argument("--output_dir", type=str, default="analysis_results", help="분석 결과가 저장될 디렉토리")
    parser.add_argument("--model", type=str, default=MODEL_ID, help="Ollama 모델 ID")
    parser.add_argument("--url", type=str, default=BASE_URL, help="Ollama 서버 URL")
    args = parser.parse_args()
    if not OLLAMA_AVAILABLE:
        logger.error("필수 라이브러리가 없어 프로그램을 종료합니다. 설치 안내를 확인하세요.")
        return
    analyzer = VisionMDAnalyzer(model_id=args.model, base_url=args.url)
    if not analyzer.use_llm:
        logger.error("LLM을 사용할 수 없어 프로그램을 종료합니다.")
        return
    results = analyzer.analyze(args.md_path)
    if results:
        file_stem = Path(args.md_path).stem
        analyzer.save_results(results, args.output_dir, file_stem)
        print("\n" + "="*80)
        print("✅ 분석 및 결과 저장이 성공적으로 완료되었습니다.")
        print(f"📁 JSON 결과: {Path(args.output_dir) / f'{file_stem}_vision_analysis.json'}")
        print(f"📄 MD 보고서: {Path(args.output_dir) / f'{file_stem}_vision_summary.md'}")
        print("="*80)

if __name__ == "__main__":
    main()