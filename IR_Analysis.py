from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from datetime import date
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
import glob
import os
import json
import re

class StartupInvestmentInfo(BaseModel):
    company_name: Optional[str] = Field(None, description="Official company name or corporate name")
    industry: Optional[str] = Field(None, description="Primary business sector or industry vertical (e.g., Manufacturing, IT Services, Biotech, Fintech, Robotics, SaaS)")
    funding_stage: Optional[str] = Field(None, description="Current investment stage (e.g., Seed, Series A, Series B, Bridge, Pre-IPO)")
    last_funding_date: Optional[date] = Field(None, description="Date of the most recent funding round or capital raising")
    funding_amount_billion: Optional[int] = Field(None, description="Total cumulative funding raised (in 100 million KRW units)")
    valuation_billion: Optional[int] = Field(None, description="Company valuation at the most recent funding round (in 100 million KRW units)")

    contact_person: Optional[str] = Field(None, description="IR contact person, CEO, or primary point of contact name")
    contact_phone: Optional[str] = Field(None, description="Company main phone number or contact person's phone")

    latest_revenue_million: Optional[int] = Field(None, description="Most recent annual revenue (in million KRW)")
    operating_profit_million: Optional[int] = Field(None, description="Most recent annual operating profit or EBITDA (in million KRW)")
    annual_fixed_cost_million: Optional[int] = Field(None, description="Annual fixed costs or total operating expenses (in million KRW)")
    cash_runway_months: Optional[int] = Field(None, description="Number of months the company can operate with current cash reserves")
    breakeven_point: Optional[str] = Field(None, description="Expected timeline or plan to reach break-even point")

    debt_ratio_percent: Optional[int] = Field(None, description="Debt-to-asset ratio (total debt/total assets × 100)")
    num_employees: Optional[int] = Field(None, description="Total number of employees or team members")

    main_competitors: Optional[List[str]] = Field(None, description="List of primary competitors in the market")
    main_competitor_1: Optional[str] = Field(None, description="Top competitor name or competing product/service")
    main_competitor_2: Optional[str] = Field(None, description="Second major competitor or market share information")

    strengths: Optional[str] = Field(None, description="Core competitive advantages, differentiators, or key strengths (technology, team, patents, customer base)")
    weaknesses: Optional[str] = Field(None, description="Internal weaknesses, limitations, or areas needing improvement")
    opportunities: Optional[str] = Field(None, description="Market opportunities, growth drivers, or external favorable conditions")
    threats: Optional[str] = Field(None, description="Risk factors or threat elements (legal, technical, competitive, market risks)")

    num_patents: Optional[int] = Field(None, description="Number of registered patents owned")
    last_updated: Optional[date] = Field(None, description="Date when this information was last updated or reference date")
    recent_quarter_revenue_million: Optional[int] = Field(None, description="Most recent quarterly revenue (in million KRW)")
    annual_growth_percent: Optional[int] = Field(None, description="Year-over-year revenue growth rate (%)")

    main_operating_expenses: Optional[str] = Field(None, description="Breakdown of major operating expense categories (e.g., Personnel 50%, Marketing 20%, R&D 15%)")
    founder_background: Optional[str] = Field(None, description="Founder's or CEO's key experience, expertise, or professional background")
    key_personnel: Optional[str] = Field(None, description="Core executives' backgrounds, previous employers, or areas of expertise")
    board_members: Optional[List[str]] = Field(None, description="Board members, advisors, or mentors list")

    shareholding_structure: Optional[str] = Field(None, description="Ownership structure and equity distribution (founders, investors, employees)")
    product_roadmap: Optional[str] = Field(None, description="Product/service development roadmap, launch plans, or feature expansion timeline")
    tech_stack: Optional[List[str]] = Field(None, description="Core technology stack, development tools, infrastructure (e.g., Python, AWS, React)")

    market_size_billion: Optional[int] = Field(None, description="Target market size or Total Addressable Market (TAM) in 100 million KRW")
    market_growth_percent: Optional[int] = Field(None, description="Target market's compound annual growth rate (CAGR %)")
    legal_issues: Optional[bool] = Field(None, description="Whether there are ongoing legal disputes, litigation, or regulatory issues")
    num_ip_rights: Optional[int] = Field(None, description="Total intellectual property rights owned (patents, trademarks, copyrights, designs)")

    funding_round: Optional[str] = Field(None, description="Current or recent funding round name (e.g., Series A, Seed Investment)")
    main_investors: Optional[List[str]] = Field(None, description="List of major investors (VCs, strategic investors, angel investors)")
    fund_usage_plan: Optional[str] = Field(None, description="Investment fund allocation plan (e.g., R&D 40%, Marketing 30%, Hiring 20%)")

    exit_strategy: Optional[str] = Field(None, description="Exit strategy plan (IPO, M&A, acquisition, etc.)")
    rnd_to_revenue_ratio: Optional[int] = Field(None, description="R&D spending as percentage of revenue (%)")
    notes: Optional[str] = Field(None, description="Additional important notes, special circumstances, or other considerations")

# State 정의
class ExtractionState(TypedDict):
    info: StartupInvestmentInfo
    md_content: str
    iteration: int
    no_progress_count: int
    analysis_feedback: str
    total_fields: int
    last_action: str  # "extract" 또는 "analyze"

# 2. LLM 준비
llm = ChatOllama(
    model="qwen3:32b",
    base_url="http://192.168.110.102:11434",
    temperature=0
)

parser = JsonOutputParser(pydantic_object=StartupInvestmentInfo)

# 필드 추출 함수
def extract_fields(state: ExtractionState) -> ExtractionState:
    """MD 파일에서 빈 필드들을 추출합니다."""
    info = state["info"]
    md_content = state["md_content"]
    analysis_feedback = state["analysis_feedback"]
    iteration = state["iteration"] + 1
    
    # 빈 필드들 찾기
    fields_to_fill = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    field_descriptions = [StartupInvestmentInfo.model_fields[field].description for field in fields_to_fill]
    
    # 진행 상황 출력
    filled_count = state["total_fields"] - len(fields_to_fill)
    fill_ratio = filled_count / state["total_fields"] * 100
    print(f"\n[Iteration {iteration}] Filled: {filled_count}/{state['total_fields']} ({fill_ratio:.1f}%) | Remaining: {len(fields_to_fill)}")
    print(f"  Remaining fields: {fields_to_fill[:10]}{'...' if len(fields_to_fill) > 10 else ''}")
    
    if not fields_to_fill:
        return state
    
    # 추출 프롬프트 (실제 LLM 호출용)
    feedback_prompt = f"\nPrevious analysis feedback: {analysis_feedback}\n" if analysis_feedback else ""
    prompt = (f"""
        "You are an expert data extractor for startup investment information. Extract specific values from the MD file for the given fields.\n\n"
        "CRITICAL: You MUST return ONLY the specified field names as JSON keys. Do NOT create custom fields.\n\n"
        "EXTRACTION GUIDELINES:\n"
        "1. Look for EXACT information in tables, text, and structured data\n"
        "2. For company_name: Look for official company names, 회사명, 상호명\n"
        "3. For industry: Look for business sector, 업종, 사업분야, 주요제품/서비스\n"
        "4. For funding info: Look for 투자, 자금조달, 시리즈A/B, 밸류에이션, Post Value\n"
        "5. For financial data: Look for 매출, 영업이익, 자본금, 운영비\n"
        "6. For personnel: Look for 임직원수, 직원수, 대표이사, CEO, 경영진\n"
        "7. For competitors: Look for 경쟁사, 경쟁업체, competitor names\n"
        "8. Convert Korean numbers to integers: 억→100million, 천만→10million, 만→10thousand\n"
        "9. If information exists but needs calculation/inference, do the math\n"
        "10. Only return null if truly no relevant information exists\n\n"
        
        MD content:```{md_content}```
        
        feedback:```{feedback_prompt}```
        
        REQUIRED FIELDS (use these EXACT field names): ```{fields_to_fill}```
        Field descriptions: ```{field_descriptions}```
        
        "Return ONLY a valid JSON object with the EXACT field names listed above as keys. Extract real values, not nulls."
    """)
    
    # 프롬프트 저장용 (MD 내용 생략)
    os.makedirs("prompt", exist_ok=True)
    prompt_for_save = (
        "You are an expert data extractor for startup investment information. Extract specific values from the MD file for the given fields.\n\n"
        "CRITICAL: You MUST return ONLY the specified field names as JSON keys. Do NOT create custom fields.\n\n"
        "EXTRACTION GUIDELINES:\n"
        "1. Look for EXACT information in tables, text, and structured data\n"
        "2. For company_name: Look for official company names, 회사명, 상호명\n"
        "3. For industry: Look for business sector, 업종, 사업분야, 주요제품/서비스\n"
        "4. For funding info: Look for 투자, 자금조달, 시리즈A/B, 밸류에이션, Post Value\n"
        "5. For financial data: Look for 매출, 영업이익, 자본금, 운영비\n"
        "6. For personnel: Look for 임직원수, 직원수, 대표이사, CEO, 경영진\n"
        "7. For competitors: Look for 경쟁사, 경쟁업체, competitor names\n"
        "8. Convert Korean numbers to integers: 억→100million, 천만→10million, 만→10thousand\n"
        "9. If information exists but needs calculation/inference, do the math\n"
        "10. Only return null if truly no relevant information exists\n\n"
        f"REQUIRED FIELDS (use these EXACT field names): {fields_to_fill}\n"
        f"Field descriptions: {field_descriptions}\n"
        f"{feedback_prompt}"
        f"MD content: [MD_CONTENT_OMITTED - {len(md_content)} characters]\n\n"
        "Return ONLY a valid JSON object with the EXACT field names listed above as keys. Extract real values, not nulls."
    )
    
    with open(f"prompt/iteration_{iteration:02d}_extract_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_for_save)
    print(f"  Prompt saved to: prompt/iteration_{iteration:02d}_extract_prompt.txt")
    
    print(f"  Requesting extraction of {len(fields_to_fill)} fields...")
    result = llm.invoke(prompt)
    
    # LLM 응답 저장
    with open(f"prompt/iteration_{iteration:02d}_extract_response.txt", "w", encoding="utf-8") as f:
        f.write(str(result.content))
    print(f"  Response saved to: prompt/iteration_{iteration:02d}_extract_response.txt")
    
    # 결과 처리
    try:
        if isinstance(result.content, str):
            cleaned_content = re.sub(r'<think>.*?</think>', '', result.content, flags=re.DOTALL).strip()
            json_match = re.search(r'\{.*\}', cleaned_content, flags=re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted_data = json.loads(json_str)
            else:
                print(f"Warning: No JSON found in response: {cleaned_content[:100]}...")
                extracted_data = {}
        else:
            extracted_data = result.content
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON response: {result.content[:100]}...")
        print(f"JSON Error: {e}")
        extracted_data = {}
    
    # 무효한 값들 필터링 (Not specified, 데이터 없음 등은 null로 처리)
    invalid_values = {
        "Not specified", "not specified", "NOT SPECIFIED",
        "데이터 없음", "정보 없음", "해당 없음", "명시되지 않음",
        "N/A", "n/a", "NA", "na", "null", "NULL", "None", "NONE",
        "정보 부족", "확인 불가", "불명", "미확인", "미명시",
        "-", "—", "–", "", "정보가 없음", "자료 없음"
    }
    
    # 새로 채워진 필드 계산 (유효한 값만)
    newly_filled = 0
    for k, v in extracted_data.items():
        if k in StartupInvestmentInfo.model_fields and getattr(info, k) is None:
            # 무효한 값인지 확인
            is_invalid = False
            if isinstance(v, str):
                is_invalid = v.strip() in invalid_values or len(v.strip()) == 0
            elif v is None:
                is_invalid = True
            
            if not is_invalid:
                setattr(info, k, v)
                newly_filled += 1
                print(f"    ✓ {k}: {v}")
            else:
                print(f"    ✗ {k}: '{v}' (무효한 값으로 필터링됨)")
    
    print(f"  Successfully filled {newly_filled} new fields")
    
    # 진전 여부 확인
    new_remaining_count = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None])
    previous_remaining_count = len(fields_to_fill)
    
    if new_remaining_count == previous_remaining_count:
        no_progress_count = state["no_progress_count"] + 1
    else:
        no_progress_count = 0
    
    return {
        **state,
        "info": info,
        "iteration": iteration,
        "no_progress_count": no_progress_count,
        "last_action": "extract"
    }

# 분석 함수
def analyze_failure(state: ExtractionState) -> ExtractionState:
    """추출 실패 이유를 분석합니다."""
    info = state["info"]
    md_content = state["md_content"]
    iteration = state["iteration"]
    
    # 빈 필드들 찾기 (처음 10개만)
    failed_fields = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    failed_fields_sample = failed_fields[:10]  # 32B 모델을 위해 처음 10개만
    
    print("No progress detected. Running failure analysis...")
    
    # 간결한 분석 프롬프트
    prompt = (
        "Analyze why these fields couldn't be extracted from the Korean startup IR document:\n\n"
        f"Failed fields: {failed_fields_sample}\n\n"
        "For each field, provide:\n"
        "- Korean keywords to look for\n"
        "- Likely section/table names\n"
        "- Alternative extraction approach\n\n"
        f"MD content:\n{md_content}\n\n"
        "Keep response concise. Focus on actionable extraction tips."
    )
    
    # 분석 프롬프트 저장용 (MD 내용 생략)
    os.makedirs("prompt", exist_ok=True)
    prompt_for_save = (
        "Analyze why these fields couldn't be extracted from the Korean startup IR document:\n\n"
        f"Failed fields: {failed_fields_sample}\n\n"
        "For each field, provide:\n"
        "- Korean keywords to look for\n"
        "- Likely section/table names\n"
        "- Alternative extraction approach\n\n"
        f"MD content: [MD_CONTENT_OMITTED - {len(md_content)} characters]\n\n"
        "Keep response concise. Focus on actionable extraction tips."
    )
    
    with open(f"prompt/iteration_{iteration:02d}_analyze_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_for_save)
    print(f"  Analysis prompt saved to: prompt/iteration_{iteration:02d}_analyze_prompt.txt")
    
    result = llm.invoke(prompt)
    analysis_feedback = re.sub(r'<think>.*?</think>', '', result.content, flags=re.DOTALL).strip()
    
    # 분석 응답 저장
    with open(f"prompt/iteration_{iteration:02d}_analyze_response.txt", "w", encoding="utf-8") as f:
        f.write(analysis_feedback)
    print(f"  Analysis response saved to: prompt/iteration_{iteration:02d}_analyze_response.txt")
    
    print(f"  Analysis feedback received: {len(analysis_feedback)} characters")
    
    return {
        **state,
        "analysis_feedback": analysis_feedback,
        "no_progress_count": state["no_progress_count"],  # 분석 후에도 카운트 유지
        "last_action": "analyze"
    }

# 종료 조건 체크
def should_continue(state: ExtractionState) -> str:
    """다음 단계를 결정합니다."""
    info = state["info"]
    fields_to_fill = [field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is None]
    
    # 모든 필드가 채워졌으면 종료
    if not fields_to_fill:
        print("All fields have been filled!")
        return "end"
    
    # 5회 이상 진전이 없으면 종료
    if state["no_progress_count"] >= 5:
        print(f"No progress for {state['no_progress_count']} iterations. Stopping extraction.")
        return "end"
    
    # 방금 analyze를 했다면 반드시 extract로
    if state.get("last_action") == "analyze":
        return "extract"
    
    # 2회 이상 진전이 없으면 분석 실행
    if state["no_progress_count"] >= 2:
        return "analyze"
    
    # 그 외에는 계속 추출
    return "extract"

# 그래프 생성
workflow = StateGraph(ExtractionState)

# 노드 추가
workflow.add_node("extract", extract_fields)
workflow.add_node("analyze", analyze_failure)

# 시작점 설정
workflow.set_entry_point("extract")

# 조건부 엣지 추가
workflow.add_conditional_edges(
    "extract",
    should_continue,
    {
        "extract": "extract",
        "analyze": "analyze", 
        "end": END
    }
)

workflow.add_conditional_edges(
    "analyze",
    should_continue,
    {
        "extract": "extract",
        "analyze": "analyze",
        "end": END
    }
)

# 그래프 컴파일
app = workflow.compile()

# 3. md 파일 읽기 및 정보 추출
with open("./data/블루브릿지글로벌.md", "r", encoding="utf-8") as f:
    md_file_content = f.read()

print("=== Starting extraction from 블루브릿지글로벌.md ===")
print(f"MD file content length: {len(md_file_content)} characters")

# 초기 상태 설정
initial_state = ExtractionState(
    info=StartupInvestmentInfo(),
    md_content=md_file_content,
    iteration=0,
    no_progress_count=0,
    analysis_feedback="",
    total_fields=len(StartupInvestmentInfo.model_fields),
    last_action="start"
)

# 그래프 실행
final_state = app.invoke(initial_state)
info = final_state["info"]

print(f"\n=== Final Results ===")
final_filled = len([field for field in StartupInvestmentInfo.model_fields if getattr(info, field) is not None])
final_ratio = final_filled / len(StartupInvestmentInfo.model_fields) * 100
print(f"Total filled: {final_filled}/{len(StartupInvestmentInfo.model_fields)} ({final_ratio:.1f}%)")
print(f"Final result:")

# 결과를 JSON으로 저장
os.makedirs("result", exist_ok=True)

try:
    # JSON 형태로 저장 시도
    info_dict = info.model_dump()
    
    # 날짜 필드를 문자열로 변환 (JSON 직렬화를 위해)
    for key, value in info_dict.items():
        if hasattr(value, 'isoformat'):  # date 객체인 경우
            info_dict[key] = value.isoformat()
    
    json_result = json.dumps(info_dict, ensure_ascii=False, indent=2)
    
    with open("result/extraction_result.json", "w", encoding="utf-8") as f:
        f.write(json_result)
    print(f"✅ Results saved to: result/extraction_result.json")
    
    # JSON 형태로 출력도 시도
    print("=== JSON 형태 결과 ===")
    print(json_result)
    
except Exception as e:
    print(f"❌ JSON 저장 실패: {e}")
    print("📝 TXT 형태로 저장 시도...")
    
    try:
        # TXT 형태로 저장
        info_dict = info.model_dump()
        
        result_text = f"=== 로보스 IR 추출 결과 ===\n"
        result_text += f"추출 완료: {final_filled}/{len(StartupInvestmentInfo.model_fields)} ({final_ratio:.1f}%)\n\n"
        
        result_text += "=== 채워진 필드 ===\n"
        filled_fields = {k: v for k, v in info_dict.items() if v is not None}
        for field_name, value in filled_fields.items():
            field_desc = StartupInvestmentInfo.model_fields[field_name].description
            result_text += f"✓ {field_name}: {value}\n"
        
        result_text += "\n=== 빈 필드 ===\n"
        empty_fields = {k: v for k, v in info_dict.items() if v is None}
        for field_name, value in empty_fields.items():
            field_desc = StartupInvestmentInfo.model_fields[field_name].description
            result_text += f"✗ {field_name} ({field_desc}): 데이터 없음\n"
        
        with open("result/extraction_result.txt", "w", encoding="utf-8") as f:
            f.write(result_text)
        print(f"✅ Results saved to: result/extraction_result.txt")
        
    except Exception as txt_error:
        print(f"❌ TXT 저장도 실패: {txt_error}")

# 텍스트 형태로 출력
print("\n=== 텍스트 형태 결과 ===")
info_dict = info.model_dump()
for field_name, value in info_dict.items():
    field_desc = StartupInvestmentInfo.model_fields[field_name].description
    print(f"{field_name} ({field_desc}): {value}")

# 빈 필드와 채워진 필드 구분해서 출력
print(f"\n=== 채워진 필드 ===")
filled_fields = {k: v for k, v in info_dict.items() if v is not None}
for field_name, value in filled_fields.items():
    field_desc = StartupInvestmentInfo.model_fields[field_name].description
    print(f"✓ {field_name}: {value}")

print(f"\n=== 빈 필드 ===")
empty_fields = {k: v for k, v in info_dict.items() if v is None}
for field_name, value in empty_fields.items():
    field_desc = StartupInvestmentInfo.model_fields[field_name].description
    print(f"✗ {field_name} ({field_desc}): 데이터 없음")