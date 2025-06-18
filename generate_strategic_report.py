import json
import re
import os
import argparse
import sys
from datetime import datetime
from typing import TypedDict, List, Annotated
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

# --- 1. LLM 및 상태 정의 ---
llm = ChatOllama(model="qwen3:32b", base_url="http://192.168.120.102:11434", temperature=0.3)
llm_validator = ChatOllama(model="qwen3:32b", base_url="http://192.168.120.102:11434", temperature=0.0) # 검증기는 엄격하게

class GraphState(TypedDict):
    """LangGraph의 상태를 정의합니다."""
    identifier: str
    initial_analysis: str
    competitor_analysis: str
    lean_canvas: str
    briefing_notes: str
    validation_feedback: str
    final_report: str
    max_retries: int
    current_retry: int
    notes_valid: bool
    report_valid: bool
    current_date: str

def remove_think_tags(text: str) -> str:
    """<think> 태그를 제거합니다."""
    think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
    return think_pattern.sub("", text).strip()

# --- 2. 핵심 체인 정의 (생성 및 검증) ---

def create_briefing_notes_chain():
    prompt = PromptTemplate.from_template("""You are a junior analyst. Based on the provided data, create a detailed briefing note.
If you are revising, incorporate the feedback to improve the notes.

[Feedback for Revision]
{validation_feedback}

[INPUT DATA]
Initial Analysis: {initial_analysis}
Competitor Analysis: {competitor_analysis}
Lean Canvas: {lean_canvas}

---
[TASK]
Create a comprehensive briefing note in Korean markdown covering: Business Model, Product, Sales, Marketing, Finance, and CS. For each topic, list key facts and a brief analysis.
The current date is {current_date}. Base your analysis on this date.

**## 분석 브리핑 노트**
... (your detailed notes here) ...
""")
    return prompt | llm | StrOutputParser()

def create_note_validator_chain():
    prompt = PromptTemplate.from_template("""You are a meticulous fact-checker and strategist. Your task is to validate the Briefing Notes against the Source Data.

[Source Data]
Initial Analysis: {initial_analysis}
Competitor Analysis: {competitor_analysis}
Lean Canvas: {lean_canvas}

[Briefing Notes to Validate]
{briefing_notes}

---
[TASK]
Validate the notes from two perspectives and provide a JSON output.
1. Hallucination Check: Is every statement in the notes directly supported by the Source Data?
2. Sufficiency Check: Are the notes detailed and specific enough to build a final strategic report covering Business Model, Product, Sales, Marketing, Finance, and CS?

The current date is {current_date}. Consider this when evaluating timeliness, but focus on fact-checking against the source data.

Provide your assessment in a valid JSON format:
{{
  "is_valid": boolean, // true if BOTH checks pass, otherwise false.
  "feedback": "string" // If invalid, provide specific, actionable feedback for revision. If valid, say 'Notes are valid'.
}}
""")
    parser = StrOutputParser() | RunnableLambda(remove_think_tags) | JsonOutputParser()
    return prompt | llm_validator | parser

def create_final_report_chain():
    prompt = PromptTemplate.from_template("""You are a senior business consultant. Using the validated briefing notes, write a final, actionable strategic report in Korean.
If you are revising, incorporate the feedback to improve the report.

[Feedback for Revision]
{validation_feedback}

[Validated Briefing Notes]
{briefing_notes}
---
[TASK]
Write the final report with the following structure. The current date is {current_date}. All strategic plans should be future-oriented from this date.

## 3. 전략적 대안 제시 (Strategic Alternatives Proposal)
### 3.1. 사업모델 (Business Model) ...
### 3.2. 제품의 경쟁력 (Product Competitiveness) ...
### 3.3. 영업 (Sales) ...
### 3.4. 마케팅 (Marketing) ...
### 3.5. 재무 (Finance) ...
### 3.6. CS (Customer Service) ...

## 4. 최종 권고 및 액션 플랜 (Final Recommendation & Action Plan)
### 4.1. 제품의 방향성 & 가이드라인 제시 ...
### 4.2. 성공하기 위한 전략 ...
""")
    return prompt | llm | StrOutputParser()

def create_report_validator_chain():
    prompt = PromptTemplate.from_template("""You are a senior strategy manager. Review the final report to ensure it meets all strategic objectives.

[Strategic Goals]
The report must provide clear, actionable advice on:
- Strategic Alternatives (Business Model, Product, Sales, Marketing, Finance, CS)
- Final Recommendations (Product Direction, Action Plan for success)

[Final Report to Validate]
{final_report}
---
[TASK]
Does the report fully and clearly address all the strategic goals? Is the advice concrete and actionable?
The current date is {current_date}. Ensure the recommendations are forward-looking from this date.

Provide your assessment in a valid JSON format:
{{
  "is_valid": boolean,
  "feedback": "string" // If invalid, explain which sections are weak or missing. If valid, say 'Report is valid'.
}}
""")
    parser = StrOutputParser() | RunnableLambda(remove_think_tags) | JsonOutputParser()
    return prompt | llm_validator | parser


# --- 3. LangGraph 노드 정의 ---

def load_data(state: GraphState):
    print("--- 1. 데이터 로드 중 ---")
    identifier = state['identifier']
    adv_path = f'bm_result/advanced_deep_research_report_{identifier}.json'
    comp_path = f'bm_result/competitive_analysis_report_{identifier}.json'
    lean_path = f'bm_result/lean_canvas_{identifier}.json'
    
    try:
        with open(adv_path, 'r', encoding='utf-8') as f:
            state['initial_analysis'] = json.load(f).get("final_report_korean", "")
        with open(comp_path, 'r', encoding='utf-8') as f:
            state['competitor_analysis'] = json.load(f).get("final_competitive_report", "")
        with open(lean_path, 'r', encoding='utf-8') as f:
            state['lean_canvas'] = json.dumps(json.load(f), ensure_ascii=False, indent=2)
        
        if not all([state['initial_analysis'], state['competitor_analysis'], state['lean_canvas']]):
            raise ValueError("One or more input files are missing necessary content.")
            
    except FileNotFoundError as e:
        print(f"🚨 ERROR: Required file not found: {e}")
        raise
    except Exception as e:
        print(f"🚨 ERROR: Failed to load data: {e}")
        raise
    
    state['current_retry'] = 0
    state['max_retries'] = 2
    state['validation_feedback'] = "N/A" # 첫 시도에는 피드백 없음
    state['notes_valid'] = False
    state['report_valid'] = False
    state['current_date'] = datetime.now().strftime('%Y-%m-%d')
    print("✅ 데이터 로드 완료")
    return state

def generate_briefing_notes(state: GraphState):
    print(f"--- 2. 브리핑 노트 생성 중 (시도: {state['current_retry'] + 1}) ---")
    try:
        chain = create_briefing_notes_chain()
        notes_raw = chain.invoke(state)
        notes_cleaned = remove_think_tags(notes_raw)
        
        # Markdown 코드 블록 제거 (` ```markdown ... ``` `)
        md_pattern = re.compile(r"^\s*```(markdown)?\s*|\s*```\s*$", re.MULTILINE)
        notes_final = md_pattern.sub("", notes_cleaned).strip()

        state['briefing_notes'] = notes_final
        print("✅ 브리핑 노트 생성 완료")
    except Exception as e:
        print(f"🚨 ERROR: Failed to generate briefing notes: {e}")
        raise
    return state

def validate_notes_node(state: GraphState):
    print("--- 3. 브리핑 노트 검증 중 ---")
    try:
        validator = create_note_validator_chain()
        result = validator.invoke(state)
        print(f"  - 검증 결과: {result}")
        
        if result['is_valid']:
            print("  - ✅ 브리핑 노트 검증 통과")
            state['notes_valid'] = True
            state['validation_feedback'] = ""
        else:
            print("  - ❌ 브리핑 노트 품질 미흡. 재작성 요청.")
            state['notes_valid'] = False
            state['validation_feedback'] = result['feedback']
            state['current_retry'] += 1
            
    except Exception as e:
        print(f"🚨 ERROR: Failed to validate notes: {e}")
        state['notes_valid'] = False
        state['validation_feedback'] = f"Validation failed: {e}"
        state['current_retry'] += 1
        
    return state

def synthesize_final_report(state: GraphState):
    print("--- 4. 최종 보고서 종합 중 ---")
    try:
        state['validation_feedback'] = "N/A"
        chain = create_final_report_chain()
        report_raw = chain.invoke(state)
        state['final_report'] = remove_think_tags(report_raw)
        print("✅ 최종 보고서 종합 완료")
    except Exception as e:
        print(f"🚨 ERROR: Failed to synthesize report: {e}")
        raise
    return state

def validate_final_report_node(state: GraphState):
    print("--- 5. 최종 보고서 검증 중 ---")
    try:
        validator = create_report_validator_chain()
        result = validator.invoke(state)
        print(f"  - 검증 결과: {result}")
        
        if result['is_valid']:
            print("  - ✅ 최종 보고서 검증 통과")
            state['report_valid'] = True
        else:
            print("  - ⚠️ 최종 보고서 개선 가능 (현재 버전으로 진행)")
            state['report_valid'] = True  # 현재는 통과시킴
            
    except Exception as e:
        print(f"🚨 ERROR: Failed to validate final report: {e}")
        state['report_valid'] = True  # 에러 시에도 통과시킴
        
    return state

# --- 4. 조건부 엣지 함수들 ---

def should_retry_notes(state: GraphState):
    """브리핑 노트 검증 후 다음 단계 결정"""
    if state['notes_valid']:
        return "synthesize_report"
    elif state['current_retry'] >= state['max_retries']:
        print("  - 🚨 최대 재시도 횟수 도달. 현재 노트로 진행.")
        return "synthesize_report"
    else:
        return "generate_notes"

def should_end(state: GraphState):
    """최종 검증 후 종료 여부 결정"""
    return END

# --- 5. 그래프 빌드 및 실행 ---

def build_graph():
    workflow = StateGraph(GraphState)
    
    # 노드 추가
    workflow.add_node("load_data", load_data)
    workflow.add_node("generate_notes", generate_briefing_notes)
    workflow.add_node("validate_notes", validate_notes_node)
    workflow.add_node("synthesize_report", synthesize_final_report)
    workflow.add_node("final_validation", validate_final_report_node)

    # 엣지 설정
    workflow.set_entry_point("load_data")
    workflow.add_edge("load_data", "generate_notes")
    workflow.add_edge("generate_notes", "validate_notes")
    
    # 조건부 엣지
    workflow.add_conditional_edges(
        "validate_notes",
        should_retry_notes,
        {
            "synthesize_report": "synthesize_report",
            "generate_notes": "generate_notes"
        }
    )
    
    workflow.add_edge("synthesize_report", "final_validation")
    workflow.add_conditional_edges(
        "final_validation",
        should_end,
        {
            END: END
        }
    )
    
    return workflow.compile()


def run_pipeline(identifier: str):
    try:
        app = build_graph()
        final_state = app.invoke({"identifier": identifier})

        print("\n--- 파이프라인 최종 결과 ---")
        if final_state.get('final_report'):
            # bm_result 디렉토리 생성
            os.makedirs('bm_result', exist_ok=True)
            
            final_report = final_state['final_report']
            output_data = {
                "source_identifier": identifier,
                "briefing_notes_markdown": final_state.get('briefing_notes', ''),
                "strategic_report_markdown": final_report
            }
            output_path = f'bm_result/strategic_report_{identifier}.json'
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                
                print(f"✅ 최종 전략 보고서가 {output_path} 에 성공적으로 저장되었습니다.")
                print("\n" + "="*30)
                print("✅ 최종 전략 보고서")
                print("="*30)
                print(final_report)
                
            except Exception as e:
                print(f"🚨 ERROR: Failed to save strategic report: {e}")
        else:
            print("🚨 최종 보고서를 생성하지 못했습니다.")
            
    except Exception as e:
        print(f"🚨 ERROR: Pipeline execution failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a final strategic report from analysis files using a validation graph.")
    parser.add_argument("identifier", type=str, help="The unique identifier for the set of analysis files (e.g., 'ROBOS_20250611_163629').")
    args = parser.parse_args()

    try:
        run_pipeline(args.identifier)
    except Exception as e:
        print(f"🚨 ERROR: An unexpected error occurred: {e}")
        sys.exit(1) 